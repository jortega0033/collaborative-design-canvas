"""Structural checks for the static UI (stdlib only, no browser)."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "design_canvas" / "static"

REQUIRED_LABELS = {
    "Document title": "doc-title",
    "Layer label": "layer-label",
    "X": "layer-x",
    "Y": "layer-y",
    "Width": "layer-w",
    "Height": "layer-h",
    "Fill": "layer-fill",
    "Text": "layer-text",
    "Font size": "layer-font",
}
REQUIRED_BUTTONS = {
    "New canvas": "new-canvas",
    "Load fixture": "load-fixture",
    "Add rectangle": "add-rect",
    "Add text": "add-text",
    "Save": "save",
    "Move up": "layer-up",
    "Move down": "layer-down",
    "Delete layer": "layer-delete",
    "Reload server version": "reload-server",
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []  # (tag, attrs dict)
        self.by_id = {}
        self.labels = []  # [for, text]
        self.button_text = {}
        self.script_content = ""
        self.style_tags = 0
        self._label = None
        self._button = None
        self._script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.elements.append((tag, a))
        if "id" in a:
            self.by_id[a["id"]] = (tag, a)
        if tag == "label":
            self._label = [a.get("for"), ""]
            self.labels.append(self._label)
        elif tag == "button":
            self._button = a.get("id")
            self.button_text[self._button] = ""
        elif tag == "script":
            self._script = True
        elif tag == "style":
            self.style_tags += 1

    def handle_endtag(self, tag):
        if tag == "label":
            self._label = None
        elif tag == "button":
            self._button = None
        elif tag == "script":
            self._script = False

    def handle_data(self, data):
        if self._label is not None:
            self._label[1] += data
        if self._button is not None:
            self.button_text[self._button] += data
        if self._script:
            self.script_content += data


def read(name):
    return (STATIC / name).read_text(encoding="utf-8")


class StaticUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read("index.html")
        cls.page = Page()
        cls.page.feed(cls.html)

    def test_files_exist(self):
        for name in ("index.html", "app.js", "styles.css", "tokens.css"):
            self.assertTrue((STATIC / name).is_file(), name)

    def test_ids_unique(self):
        ids = [a["id"] for _, a in self.page.elements if "id" in a]
        self.assertEqual(len(ids), len(set(ids)))

    def test_label_for_associations(self):
        by_text = {t.strip(): f for f, t in self.page.labels}
        for text, ctl in REQUIRED_LABELS.items():
            self.assertEqual(by_text.get(text), ctl, text)
            self.assertIn(ctl, self.page.by_id)

    def test_control_types(self):
        by_id = self.page.by_id
        for ctl in ("layer-x", "layer-y", "layer-w", "layer-h", "layer-font"):
            self.assertEqual(by_id[ctl][1].get("type"), "number", ctl)
        self.assertEqual(by_id["layer-fill"][1].get("type"), "color")
        self.assertEqual(by_id["doc-title"][1].get("type"), "text")

    def test_buttons(self):
        for text, bid in REQUIRED_BUTTONS.items():
            self.assertIn(bid, self.page.by_id, bid)
            self.assertEqual(self.page.by_id[bid][0], "button")
            self.assertEqual(self.page.button_text[bid].strip(), text)
        self.assertIn("hidden", self.page.by_id["reload-server"][1])

    def test_landmarks_and_regions(self):
        tags = [t for t, _ in self.page.elements]
        self.assertEqual(tags.count("h1"), 1)
        self.assertEqual(tags.count("header"), 1)
        self.assertEqual(tags.count("main"), 1)
        status = self.page.by_id["status"][1]
        self.assertEqual(status.get("role"), "status")
        self.assertEqual(status.get("aria-live"), "polite")
        self.assertEqual(sum(1 for _, a in self.page.elements if a.get("role") == "status"), 1)
        for lst in ("project-list", "layer-list"):
            self.assertEqual(self.page.by_id[lst][0], "ul")
            ref = self.page.by_id[lst][1].get("aria-labelledby")
            self.assertIn(ref, self.page.by_id, lst)
        self.assertIn("Project list", self.html)

    def test_canvas(self):
        tag, a = self.page.by_id["preview"]
        self.assertEqual(tag, "canvas")
        self.assertEqual((a.get("width"), a.get("height")), ("640", "400"))
        self.assertTrue(a.get("aria-label"))

    def test_no_inline_script_style_or_handlers(self):
        self.assertEqual(self.page.script_content.strip(), "")
        self.assertEqual(self.page.style_tags, 0)
        for tag, a in self.page.elements:
            self.assertNotIn("style", a, tag)
            for name in a:
                self.assertFalse(name.startswith("on"), "%s %s" % (tag, name))
            if tag == "script":
                self.assertEqual(a.get("src"), "/app.js")
        self.assertNotIn("javascript:", self.html.lower())

    def test_no_external_urls(self):
        pattern = re.compile(r"(https?:)?//[A-Za-z0-9]|url\(|@import|\bwss?:", re.I)
        for name in ("index.html", "app.js", "styles.css", "tokens.css"):
            m = pattern.search(read(name))
            self.assertIsNone(m, "%s: %s" % (name, m and m.group(0)))
        for tag, a in self.page.elements:
            for key in ("src", "href"):
                if key in a:
                    self.assertTrue(a[key].startswith("/") and not a[key].startswith("//"), a[key])

    def test_js_safety(self):
        js = read("app.js")
        for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(banned, js, banned)
        self.assertIn("textContent", js)
        self.assertIn("fillText", js)
        self.assertIn("dc.lastProject", js)
        self.assertIn("base_revision", js)

    def test_css_focus_and_overflow(self):
        css = read("styles.css")
        self.assertIn(":focus-visible", css)
        self.assertRegex(css, r"outline:\s*[3-9]px")
        self.assertIn("max-width: 640px", css)
        self.assertIn("overflow-x: hidden", css)
        self.assertIn("@media (min-width: 900px)", css)
        self.assertRegex(css, r"\[hidden\]\s*\{\s*display:\s*none")


if __name__ == "__main__":
    unittest.main()
