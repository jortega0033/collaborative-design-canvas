import http.client
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
import io

from design_canvas import model, server as server_mod
from design_canvas.__main__ import main as cli_main
from design_canvas.server import CanvasServer
from design_canvas.storage import Storage

API = "/api/v1"


class Response:
    def __init__(self, status, headers, raw):
        self.status, self.headers, self.raw = status, headers, raw
        self.json = None
        if "json" in (headers.get("Content-Type") or ""):
            self.json = json.loads(raw.decode("utf-8"))


class Running:
    """A real server on port 0 backed by a data directory."""

    def __init__(self, data_dir):
        self.storage = Storage(data_dir)
        self.server = CanvasServer(self.storage, 0)
        self.port = self.server.port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.stopped = False

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        self.storage.close()

    def request(self, method, path, body=None, raw=None, headers=None, host=None,
                content_type="application/json", send_length=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            conn.putheader("Host", host if host is not None else "127.0.0.1:%d" % self.port)
            data = raw if raw is not None else (
                json.dumps(body).encode("utf-8") if body is not None else None)
            if data is not None:
                if content_type:
                    conn.putheader("Content-Type", content_type)
                if send_length:
                    conn.putheader("Content-Length", str(len(data)))
            for k, v in (headers or {}).items():
                conn.putheader(k, v)
            conn.endheaders(data)
            resp = conn.getresponse()
            payload = resp.read()
            return Response(resp.status, dict(resp.getheaders()), payload)
        finally:
            conn.close()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.app = self.start()

    def start(self):
        app = Running(self.dir)
        self.addCleanup(app.stop)
        return app

    def get(self, path, **kw):
        return self.app.request("GET", API + path, **kw)

    def post(self, path, body=None, **kw):
        return self.app.request("POST", API + path, body, **kw)

    def put(self, path, body=None, **kw):
        return self.app.request("PUT", API + path, body, **kw)

    def make(self, title="Canvas", fixture=True):
        r = self.post("/projects", {"title": title, "fixture": fixture})
        self.assertEqual(r.status, 201, r.raw)
        return r.json


class BasicsTest(ApiTestCase):
    def test_health_and_security_headers(self):
        r = self.get("/health")
        self.assertEqual((r.status, r.json), (200, {"status": "ok", "api": 1, "schema": 1}))
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertFalse([h for h in r.headers if h.lower().startswith("access-control-")])

    def test_create_fixture(self):
        p = self.make("Fixture")
        self.assertEqual(p["revision"], 1)
        self.assertEqual(p["layers"], model.fixture_layers())
        self.assertEqual(p["scene"], {"width": 640, "height": 400})
        self.assertEqual(self.get("/projects/%d" % p["id"]).json, p)

    def test_create_empty_and_list_sorted(self):
        self.make("beta", fixture=False)
        self.make("Alpha")
        r = self.get("/projects")
        self.assertEqual([p["title"] for p in r.json["projects"]], ["Alpha", "beta"])
        self.assertEqual([p["layer_count"] for p in r.json["projects"]], [2, 0])
        self.assertEqual(set(r.json["projects"][0]),
                         {"id", "title", "revision", "updated_at", "layer_count"})

    def test_not_found_and_method_not_allowed(self):
        self.assertEqual(self.get("/projects/999").status, 404)
        self.assertEqual(self.get("/projects/999").json["error"]["code"], "not_found")
        self.assertEqual(self.get("/projects/abc").status, 404)
        self.assertEqual(self.get("/nothing").status, 404)
        self.assertEqual(self.put("/projects/999", {
            "title": "x", "base_revision": 1, "layers": []}).status, 404)
        r = self.app.request("DELETE", API + "/projects/1")
        self.assertEqual(r.status, 405)
        self.assertIn("GET", r.headers["Allow"])
        r = self.app.request("OPTIONS", API + "/projects")
        self.assertEqual(r.status, 405)
        self.assertFalse([h for h in r.headers if h.lower().startswith("access-control-")])
        self.assertEqual(self.post("/health", {}).status, 405)

    def test_title_taken_on_create(self):
        self.make("Plan")
        r = self.post("/projects", {"title": "  PLAN "})
        self.assertEqual((r.status, r.json["error"]["code"]), (409, "title_taken"))
        self.assertEqual(len(self.get("/projects").json["projects"]), 1)


class PersistenceTest(ApiTestCase):
    def test_move_persists_across_restart(self):
        p = self.make("Move")
        layers = p["layers"]
        self.assertEqual(layers[0]["x"], 40)
        layers[0]["x"] = 80
        r = self.put("/projects/%d" % p["id"], {
            "title": "Move", "base_revision": 1, "layers": layers})
        self.assertEqual(r.status, 200, r.raw)
        self.assertEqual(r.json["revision"], 2)

        self.app.stop()
        self.app = self.start()  # new storage and server on the same directory

        got = self.get("/projects/%d" % p["id"]).json
        expected = model.fixture_layers()
        expected[0]["x"] = 80
        self.assertEqual(got["layers"], expected)
        self.assertEqual([l["id"] for l in got["layers"]], ["rect-1", "text-1"])
        self.assertEqual(got["revision"], 2)

    def test_reorder_persists(self):
        p = self.make("Order")
        layers = list(reversed(p["layers"]))
        self.assertEqual(self.put("/projects/%d" % p["id"], {
            "title": "Order", "base_revision": 1, "layers": layers}).status, 200)
        self.app.stop()
        self.app = self.start()
        got = self.get("/projects/%d" % p["id"]).json
        self.assertEqual([l["id"] for l in got["layers"]], ["text-1", "rect-1"])


class ConflictTest(ApiTestCase):
    def test_revision_conflict_returns_current_and_writes_nothing(self):
        p = self.make("Conflict")
        pid = p["id"]
        newer = self.put("/projects/%d" % pid, {
            "title": "Conflict", "base_revision": 1, "layers": p["layers"][:1]}).json
        r = self.put("/projects/%d" % pid, {
            "title": "Other", "base_revision": 1, "layers": []})
        self.assertEqual(r.status, 409)
        self.assertEqual(r.json["error"]["code"], "revision_conflict")
        self.assertEqual(r.json["error"]["current"], newer)
        self.assertEqual(self.get("/projects/%d" % pid).json, newer)

    def test_title_taken_on_put(self):
        self.make("One")
        two = self.make("Two")
        r = self.put("/projects/%d" % two["id"], {
            "title": "one", "base_revision": 1, "layers": []})
        self.assertEqual((r.status, r.json["error"]["code"]), (409, "title_taken"))
        self.assertEqual(self.get("/projects/%d" % two["id"]).json, two)

    def test_concurrent_puts_same_base_revision(self):
        p = self.make("Race", fixture=False)
        n = 8
        barrier = threading.Barrier(n)
        results = [None] * n

        def worker(i):
            body = {"title": "Race %d" % i, "base_revision": 1, "layers": [{
                "id": "r%d" % i, "type": "rect", "label": "L", "x": i, "y": 0,
                "w": 5, "h": 5, "fill": "#000000"}]}
            barrier.wait()
            results[i] = self.put("/projects/%d" % p["id"], body)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        statuses = sorted(r.status for r in results)
        self.assertEqual(statuses, [200] + [409] * (n - 1))
        winner = next(r for r in results if r.status == 200).json
        for r in results:
            if r.status == 409:
                self.assertEqual(r.json["error"]["code"], "revision_conflict")
        final = self.get("/projects/%d" % p["id"]).json
        self.assertEqual(final, winner)
        self.assertEqual(final["revision"], 2)


class ValidationTest(ApiTestCase):
    def valid_layer(self, **over):
        d = {"id": "a", "type": "rect", "label": "L", "x": 1, "y": 2, "w": 3, "h": 4,
             "fill": "#123456"}
        d.update(over)
        return d

    def test_422_cases(self):
        p = self.make("V", fixture=False)
        path = "/projects/%d" % p["id"]
        base = {"title": "V", "base_revision": 1}
        bad_layers = [
            [self.valid_layer(x=True)], [self.valid_layer(w=0)],
            [self.valid_layer(extra=1)], [self.valid_layer(fill="blue")],
            [self.valid_layer(), self.valid_layer()], [self.valid_layer(id="../x")],
            [self.valid_layer(type="text")],
            [self.valid_layer(id="r%d" % i) for i in range(201)],
            "not-a-list",
        ]
        for layers in bad_layers:
            with self.subTest(layers=str(layers)[:60]):
                r = self.put(path, dict(base, layers=layers))
                self.assertEqual(r.status, 422, r.raw)
                err = r.json["error"]
                self.assertEqual(err["code"], "validation_failed")
                self.assertTrue(err["details"])
        for body in ({"title": "", "base_revision": 1, "layers": []},
                     {"title": "V", "base_revision": "1", "layers": []},
                     {"title": "V", "base_revision": 1},
                     {"title": "V", "base_revision": 1, "layers": [], "x": 1},
                     [1, 2]):
            with self.subTest(body=body):
                self.assertEqual(self.put(path, body).status, 422)
        for body in ({}, {"title": ""}, {"title": "x" * 81}, {"title": "a", "fixture": "yes"},
                     {"title": "a", "other": 1}):
            with self.subTest(body=body):
                self.assertEqual(self.post("/projects", body).status, 422)
        # nothing was written by any rejected request
        self.assertEqual(self.get(path).json, p)

    def test_layer_cap_boundary_accepted(self):
        p = self.make("Cap", fixture=False)
        layers = [self.valid_layer(id="r%d" % i) for i in range(200)]
        r = self.put("/projects/%d" % p["id"], {"title": "Cap", "base_revision": 1,
                                                "layers": layers})
        self.assertEqual(r.status, 200, r.raw[:200])

    def test_malformed_requests(self):
        r = self.post("/projects", raw=b"{not json")
        self.assertEqual((r.status, r.json["error"]["code"]), (400, "bad_request"))
        self.assertEqual(self.post("/projects", raw=b'{"title":"a","title":"b"}').status, 400)
        self.assertEqual(self.post("/projects", raw=b'{"title":NaN}').status, 400)
        self.assertEqual(self.post("/projects", raw=b"\xff\xfe").status, 400)
        self.assertEqual(self.post("/projects", raw=b'{"title":"\\ud800"}').status, 422)
        self.assertEqual(self.post("/projects", raw=b"[" * 5000).status, 400)

    def test_content_type_and_length(self):
        r = self.post("/projects", raw=b'{"title":"a"}', content_type="text/plain")
        self.assertEqual((r.status, r.json["error"]["code"]), (415, "unsupported_media_type"))
        r = self.post("/projects", raw=b'{"title":"a"}', content_type=None)
        self.assertEqual(r.status, 415)
        r = self.post("/projects", raw=b'{"title":"a"}', send_length=False)
        self.assertEqual((r.status, r.json["error"]["code"]), (411, "length_required"))
        r = self.post("/projects", raw=b"{}", headers={"Content-Length": "abc"},
                      send_length=False)
        self.assertEqual(r.status, 400)
        r = self.post("/projects", raw=b'{"title":"json-charset"}',
                      content_type="Application/JSON; charset=utf-8")
        self.assertEqual(r.status, 201)

    def test_body_cap_413(self):
        raw = b" " * (server_mod.MAX_BODY + 1)
        r = self.post("/projects", raw=raw)
        self.assertEqual((r.status, r.json["error"]["code"]), (413, "payload_too_large"))
        self.assertEqual(self.get("/projects").json["projects"], [])

    def test_body_at_cap_not_413(self):
        pad = b" " * (server_mod.MAX_BODY - len(b'{"title":"a"}'))
        r = self.post("/projects", raw=b'{"title":"a"}' + pad)
        self.assertEqual(r.status, 201)


class OriginTest(ApiTestCase):
    def test_foreign_host_forbidden(self):
        for host in ("evil.example", "evil.example:%d" % self.app.port, "127.0.0.1:1",
                     "127.0.0.1.evil.example:%d" % self.app.port, ""):
            with self.subTest(host=host):
                r = self.get("/health", host=host)
                self.assertEqual((r.status, r.json["error"]["code"]), (403, "forbidden_origin"))
        r = self.app.request("GET", "/", host="evil.example")
        self.assertEqual(r.status, 403)

    def test_localhost_host_allowed(self):
        self.assertEqual(self.get("/health", host="localhost:%d" % self.app.port).status, 200)

    def test_foreign_origin_forbidden_on_mutations(self):
        for origin in ("http://evil.example", "null", "https://127.0.0.1:%d" % self.app.port,
                       "http://127.0.0.1"):
            with self.subTest(origin=origin):
                r = self.post("/projects", {"title": "o"}, headers={"Origin": origin})
                self.assertEqual((r.status, r.json["error"]["code"]), (403, "forbidden_origin"))
        r = self.put("/projects/1", {"title": "o", "base_revision": 1, "layers": []},
                     headers={"Origin": "http://evil.example"})
        self.assertEqual(r.status, 403)
        self.assertEqual(self.get("/projects").json["projects"], [])

    def test_own_origin_allowed(self):
        for host in ("127.0.0.1", "localhost"):
            origin = "http://%s:%d" % (host, self.app.port)
            r = self.post("/projects", {"title": "own " + host}, headers={"Origin": origin})
            self.assertEqual(r.status, 201)

    def test_origin_not_checked_on_reads(self):
        r = self.get("/health", headers={"Origin": "http://evil.example"})
        self.assertEqual(r.status, 200)


class StaticTest(ApiTestCase):
    def test_traversal_and_unlisted_paths_404(self):
        paths = ["/../design_canvas/server.py", "/%2e%2e/server.py", "/..%2fserver.py",
                 "/static/index.html", "/server.py", "/storage.py", "/design_canvas.sqlite3",
                 "/app.js/", "/app.js/../server.py", "/index.html/x", "/%61pp.js",
                 "/.git/config", "//etc/passwd", "/api", "/api/v1x/health", "/APP.JS",
                 "/..\\server.py", "/static/../app.js"]
        for path in paths:
            with self.subTest(path=path):
                r = self.app.request("GET", path)
                self.assertEqual(r.status, 404, path)
                self.assertEqual(r.json["error"]["code"], "not_found")
                self.assertIn("Content-Security-Policy", r.headers)

    def test_allowlisted_files_when_present(self):
        expect = {"/": "text/html", "/index.html": "text/html",
                  "/app.js": "application/javascript", "/styles.css": "text/css",
                  "/tokens.css": "text/css"}
        for path, ctype in expect.items():
            name = server_mod.STATIC_FILES[path][0]
            if not os.path.isfile(os.path.join(server_mod.STATIC_DIR, name)):
                continue
            with self.subTest(path=path):
                r = self.app.request("GET", path)
                self.assertEqual(r.status, 200)
                self.assertTrue(r.headers["Content-Type"].startswith(ctype))
                self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
                self.assertIn("script-src 'self'", r.headers["Content-Security-Policy"])
                self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_static_rejects_mutations(self):
        r = self.app.request("POST", "/", {"a": 1})
        self.assertEqual(r.status, 405)
        self.assertEqual(r.headers["Allow"], "GET, HEAD")

    def test_allowlist_never_uses_request_path(self):
        for name, _ in server_mod.STATIC_FILES.values():
            self.assertEqual(os.path.basename(name), name)


class CliTest(unittest.TestCase):
    def run_cli(self, argv):
        err = io.StringIO()
        with redirect_stderr(err):
            try:
                code = cli_main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, err.getvalue()

    def test_bad_data_dir_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = os.path.join(tmp, "file")
            with open(plain, "w") as fh:
                fh.write("x")
            for bad in ("", plain):
                with self.subTest(path=bad):
                    code, err = self.run_cli(["--data-dir", bad, "--port", "0"])
                    self.assertEqual(code, 2)
                    self.assertEqual(len(err.strip().splitlines()), 1)

    def test_missing_args_exit_2(self):
        self.assertEqual(self.run_cli([])[0], 2)
        self.assertEqual(self.run_cli(["--data-dir", "x"])[0], 2)
        self.assertEqual(self.run_cli(["--port", "0"])[0], 2)
        self.assertEqual(self.run_cli(["--data-dir", "x", "--port", "70000"])[0], 2)

    def test_newer_schema_exits_2(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            Storage(tmp).close()
            conn = sqlite3.connect(os.path.join(tmp, "design_canvas.sqlite3"))
            conn.execute("PRAGMA user_version = 7")
            conn.close()
            self.assertEqual(self.run_cli(["--data-dir", tmp, "--port", "0"])[0], 2)


if __name__ == "__main__":
    unittest.main()
