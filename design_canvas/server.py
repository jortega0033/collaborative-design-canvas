"""HTTP layer: loopback-only JSON API plus an allowlisted static UI."""

import json
import os
import re
import sys
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import model
from .storage import NotFound, RevisionConflict, TitleTaken

MAX_BODY = 262144
DRAIN_LIMIT = 1024 * 1024
API_PREFIX = "/api/v1"
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Fixed allowlist: URL path -> (file name inside STATIC_DIR, content type).
# No part of the request path is ever used to build a filesystem path.
_INDEX = ("index.html", "text/html; charset=utf-8")
STATIC_FILES = {
    "/": _INDEX,
    "/index.html": _INDEX,
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}

SECURITY_HEADERS = (
    ("Content-Security-Policy",
     "default-src 'self'; style-src 'self'; script-src 'self'; "
     "base-uri 'none'; form-action 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Cache-Control", "no-store"),
)

_PROJECT_PATH = re.compile(r"/projects/([1-9][0-9]{0,8})")
_READ = ("GET", "HEAD")
_ERROR_CODES = {
    400: "bad_request", 403: "forbidden_origin", 404: "not_found",
    405: "method_not_allowed", 409: "conflict", 411: "length_required",
    413: "payload_too_large", 414: "bad_request", 415: "unsupported_media_type",
    422: "validation_failed", 431: "bad_request", 500: "internal_error",
}


class ApiError(Exception):
    def __init__(self, status, code, message, extra=None, headers=None):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.extra = extra or {}
        self.headers = headers or {}


def _reject_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key")
        out[k] = v
    return out


def _reject_constant(name):
    raise ValueError("invalid constant")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # one request per connection
    timeout = 10

    def version_string(self):
        return "DesignCanvas"

    def log_message(self, format, *args):
        pass

    # -- response helpers -------------------------------------------------

    def _send(self, status, body, ctype, extra=None):
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in SECURITY_HEADERS:
                self.send_header(k, v)
            self.send_header("Connection", "close")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if getattr(self, "command", None) != "HEAD":
                self.wfile.write(body)
        except OSError:
            pass
        self.close_connection = True

    def _json(self, status, payload, extra=None):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra)

    def _error(self, status, code, message, extra=None, headers=None):
        self._drain()
        err = {"code": code, "message": message}
        err.update(extra or {})
        self._json(status, {"error": err}, headers)

    def send_error(self, code, message=None, explain=None):
        # Replaces the stdlib HTML error page (also used for parse failures).
        headers = None
        if code == 501:
            code, headers = 405, {"Allow": "GET, HEAD"}
        text = HTTPStatus(code).phrase if code in HTTPStatus._value2member_map_ else "Error"
        self._error(code, _ERROR_CODES.get(code, "bad_request"), text, headers=headers)

    def _drain(self):
        """Discard a bounded amount of unread request body so the client can
        read our error response instead of seeing a connection reset."""
        if getattr(self, "_body_done", True):
            return
        self._body_done = True
        try:
            cl = self.headers.get("Content-Length", "")
            left = min(int(cl), DRAIN_LIMIT) if cl.isascii() and cl.isdigit() and len(cl) < 12 else 0
            while left > 0:
                chunk = self.rfile.read(min(left, 65536))
                if not chunk:
                    break
                left -= len(chunk)
        except (OSError, ValueError):
            pass

    # -- checks -----------------------------------------------------------

    def _allowed_hosts(self):
        port = self.server.server_address[1]
        hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        if port == 80:
            hosts |= {"127.0.0.1", "localhost"}
        return hosts

    def _check_host_origin(self, method):
        hosts = self._allowed_hosts()
        values = self.headers.get_all("Host") or []
        if len(values) != 1 or values[0].strip().lower() not in hosts:
            raise ApiError(403, "forbidden_origin", "Host not allowed")
        if method not in _READ:
            origins = self.headers.get_all("Origin") or []
            if len(origins) > 1 or (
                    origins and origins[0].strip().lower() not in {"http://" + h for h in hosts}):
                raise ApiError(403, "forbidden_origin", "Origin not allowed")

    def _read_json(self):
        cl = self.headers.get("Content-Length")
        if self.headers.get("Transfer-Encoding") is not None:
            raise ApiError(400, "bad_request", "Transfer-Encoding is not supported")
        if cl is None:
            raise ApiError(411, "length_required", "Content-Length is required")
        cl = cl.strip()
        if not (cl.isascii() and cl.isdigit() and len(cl) <= 12):
            raise ApiError(400, "bad_request", "Invalid Content-Length")
        n = int(cl)
        if n > MAX_BODY:
            raise ApiError(413, "payload_too_large",
                           "Request body exceeds %d bytes" % MAX_BODY)
        raw = self.rfile.read(n)
        self._body_done = True
        if len(raw) != n:
            raise ApiError(400, "bad_request", "Request body shorter than Content-Length")
        media = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if media != "application/json":
            raise ApiError(415, "unsupported_media_type",
                           "Content-Type must be application/json")
        try:
            return json.loads(raw.decode("utf-8"),
                              object_pairs_hook=_reject_duplicates,
                              parse_constant=_reject_constant)
        except (ValueError, RecursionError):
            raise ApiError(400, "bad_request", "Malformed JSON body")

    # -- dispatch ---------------------------------------------------------

    def _handle(self):
        method = self.command
        self._body_done = method not in ("POST", "PUT")
        try:
            self._dispatch(method)
        except ApiError as exc:
            self._error(exc.status, exc.code, exc.message, exc.extra, exc.headers)
        except (TimeoutError, ConnectionError):
            self.close_connection = True
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self._error(500, "internal_error", "Internal server error")

    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _handle

    def _dispatch(self, method):
        self._check_host_origin(method)
        path = self.path.split("?", 1)[0]
        if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            self._api(method, path[len(API_PREFIX):])
        else:
            self._static(method, path)

    def _static(self, method, path):
        entry = STATIC_FILES.get(path)
        if entry is None:
            raise ApiError(404, "not_found", "Not found")
        if method not in _READ:
            raise ApiError(405, "method_not_allowed", "Method not allowed",
                           headers={"Allow": "GET, HEAD"})
        name, ctype = entry
        try:
            with open(os.path.join(STATIC_DIR, name), "rb") as fh:
                data = fh.read()
        except OSError:
            raise ApiError(404, "not_found", "Not found")
        self._send(200, data, ctype)

    def _api(self, method, rest):
        store = self.server.storage
        if rest == "/health":
            self._allow(method, "GET, HEAD")
            return self._json(200, {"status": "ok", "api": 1, "schema": 1})
        if rest == "/projects":
            self._allow(method, "GET, HEAD, POST")
            if method == "POST":
                title, fixture = self._validated(model.validate_create, self._read_json())
                layers = model.fixture_layers() if fixture else []
                try:
                    project = store.create_project(title, layers)
                except TitleTaken:
                    raise self._title_taken()
                return self._json(201, project, {
                    "Location": "%s/projects/%d" % (API_PREFIX, project["id"])})
            return self._json(200, {"projects": store.list_projects()})
        m = _PROJECT_PATH.fullmatch(rest)
        if m:
            pid = int(m.group(1))
            self._allow(method, "GET, HEAD, PUT")
            if method == "PUT":
                body = self._read_json()
                title, rev, layers = self._validated(model.validate_update, body)
                try:
                    project = store.update_project(pid, title, rev, layers)
                except NotFound:
                    raise self._not_found()
                except TitleTaken:
                    raise self._title_taken()
                except RevisionConflict as exc:
                    raise ApiError(
                        409, "revision_conflict",
                        "Project was changed; server revision is %d" % exc.current["revision"],
                        {"current": exc.current})
                return self._json(200, project)
            try:
                return self._json(200, store.get_project(pid))
            except NotFound:
                raise self._not_found()
        raise self._not_found()

    @staticmethod
    def _allow(method, allowed):
        if method not in allowed.split(", "):
            raise ApiError(405, "method_not_allowed", "Method not allowed",
                           headers={"Allow": allowed})

    @staticmethod
    def _validated(fn, body):
        try:
            return fn(body)
        except model.ValidationError as exc:
            raise ApiError(422, "validation_failed", "Validation failed",
                           {"details": exc.details})

    @staticmethod
    def _not_found():
        return ApiError(404, "not_found", "Not found")

    @staticmethod
    def _title_taken():
        return ApiError(409, "title_taken", "A project with this title already exists")


class CanvasServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"  # on Windows it would permit port sharing
    request_queue_size = 64

    def __init__(self, storage, port=0):
        self._workers = []
        self._workers_lock = threading.Lock()
        self.storage = storage
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def port(self):
        return self.server_address[1]

    def process_request(self, request, client_address):
        thread = threading.Thread(
            target=self.process_request_thread,
            args=(request, client_address), daemon=True)
        with self._workers_lock:
            self._workers = [t for t in self._workers if t.is_alive()]
            self._workers.append(thread)
        thread.start()

    def server_close(self):
        super().server_close()
        with self._workers_lock:
            workers = list(self._workers)
        deadline = time.monotonic() + 12  # socket timeout is 10 s
        for t in workers:
            t.join(max(0.0, deadline - time.monotonic()))

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], OSError):
            return  # client went away or timed out
        traceback.print_exc(file=sys.stderr)
