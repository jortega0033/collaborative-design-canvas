import copy
import unittest

from design_canvas import model


def rect(**over):
    d = {"id": "rect-1", "type": "rect", "label": "R", "x": 0, "y": 0,
         "w": 10, "h": 10, "fill": "#aabbcc"}
    d.update(over)
    return d


def text(**over):
    d = {"id": "text-1", "type": "text", "label": "T", "x": 0, "y": 0,
         "w": 10, "h": 10, "text": "hi", "font_size": 12, "fill": "#000000"}
    d.update(over)
    return d


def update(layers, **over):
    d = {"title": "T", "base_revision": 1, "layers": layers}
    d.update(over)
    return d


class FixtureTest(unittest.TestCase):
    def test_fixture_exact_and_fresh(self):
        layers = model.fixture_layers()
        self.assertEqual(layers[0], {
            "id": "rect-1", "type": "rect", "label": "Platform block",
            "x": 40, "y": 60, "w": 120, "h": 72, "fill": "#2f6f9f"})
        self.assertEqual(layers[1], {
            "id": "text-1", "type": "text", "label": "Station signs",
            "x": 40, "y": 160, "w": 240, "h": 32, "text": "Station signs",
            "font_size": 24, "fill": "#1f2933"})
        layers[0]["x"] = 1
        self.assertEqual(model.fixture_layers()[0]["x"], 40)

    def test_fixture_passes_validation(self):
        _, _, out = model.validate_update(update(model.fixture_layers()))
        self.assertEqual(out, model.fixture_layers())


class CreateTest(unittest.TestCase):
    def test_ok_and_trim(self):
        self.assertEqual(model.validate_create({"title": "  Hi  "}), ("Hi", False))
        self.assertEqual(model.validate_create({"title": "a", "fixture": True}), ("a", True))

    def test_bad(self):
        bad = [None, [], {}, {"title": ""}, {"title": "   "}, {"title": "x" * 81},
               {"title": 5}, {"title": "a", "fixture": 1}, {"title": "a", "extra": 1},
               {"title": "a\nb"}, {"title": "\ud800"}]
        for body in bad:
            with self.subTest(body=body):
                with self.assertRaises(model.ValidationError):
                    model.validate_create(body)

    def test_title_boundary(self):
        self.assertEqual(model.validate_create({"title": "x" * 80})[0], "x" * 80)


class LayerTest(unittest.TestCase):
    def check_bad(self, layer):
        with self.assertRaises(model.ValidationError) as cm:
            model.validate_update(update([layer]))
        return cm.exception.details

    def test_valid_boundaries(self):
        layers = [rect(id="a" * 40, x=-2000, y=2000, w=1, h=2000, label="l" * 60),
                  text(text="", font_size=8), text(id="t2", text="x" * 500, font_size=96)]
        self.assertEqual(model.validate_update(update(layers))[2], layers)

    def test_invalid_values(self):
        cases = [
            rect(id=""), rect(id="a" * 41), rect(id="bad id"), rect(id="a\n"),
            rect(label=""), rect(label="x" * 61), rect(label="a\x00b"),
            rect(x=2001), rect(x=-2001), rect(w=0), rect(h=2001),
            rect(x=True), rect(x=1.0), rect(x="1"), rect(x=None),
            rect(fill="#abc"), rect(fill="red"), rect(fill="#aabbcc\n"), rect(fill="#gggggg"),
            rect(type="circle"), rect(type=None),
            rect(extra=1), rect(text="no"),
            text(font_size=7), text(font_size=97), text(font_size=True),
            text(text="x" * 501), text(text=5),
            "nope", None, [],
        ]
        for layer in cases:
            with self.subTest(layer=layer):
                self.check_bad(layer)

    def test_missing_fields(self):
        layer = rect()
        del layer["fill"]
        details = self.check_bad(layer)
        self.assertEqual(details[0]["field"], "layers[0].fill")
        t = text()
        del t["font_size"]
        self.check_bad(t)

    def test_text_allows_newline_and_tab(self):
        out = model.validate_update(update([text(text="a\nb\tc")]))[2]
        self.assertEqual(out[0]["text"], "a\nb\tc")

    def test_duplicate_ids(self):
        with self.assertRaises(model.ValidationError):
            model.validate_update(update([rect(), rect()]))

    def test_layer_cap(self):
        ok = [rect(id="r%d" % i) for i in range(200)]
        self.assertEqual(len(model.validate_update(update(ok))[2]), 200)
        with self.assertRaises(model.ValidationError):
            model.validate_update(update(ok + [rect(id="extra")]))

    def test_update_envelope(self):
        base = update([])
        for k in ("title", "base_revision", "layers"):
            body = copy.deepcopy(base)
            del body[k]
            with self.assertRaises(model.ValidationError):
                model.validate_update(body)
        for over in ({"base_revision": 0}, {"base_revision": True}, {"base_revision": "1"},
                     {"base_revision": 2**40}, {"layers": {}}, {"extra": 1}, {"title": ""}):
            with self.subTest(over=over):
                payload = update([])
                payload.update(over)
                with self.assertRaises(model.ValidationError):
                    model.validate_update(payload)

    def test_canonical_key_order(self):
        shuffled = dict(reversed(list(text().items())))
        out = model.validate_update(update([shuffled]))[2][0]
        self.assertEqual(list(out), ["id", "type", "label", "x", "y", "w", "h",
                                     "text", "font_size", "fill"])


if __name__ == "__main__":
    unittest.main()
