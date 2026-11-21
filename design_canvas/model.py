"""Domain model: constants, fixture and strict input validation.

All validation is pure and returns normalised values or raises
ValidationError carrying a list of {"field", "message"} details.
"""

import re
import unicodedata

SCENE = {"width": 640, "height": 400}
MAX_LAYERS = 200
MAX_TITLE = 80
MAX_LABEL = 60
MAX_TEXT = 500
MAX_REVISION = 2**31 - 1
MAX_DETAILS = 50

LAYER_TYPES = ("rect", "text")
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,40}")
_FILL_RE = re.compile(r"#[0-9A-Fa-f]{6}")

_COMMON_KEYS = ("id", "type", "label", "x", "y", "w", "h", "fill")
_TEXT_KEYS = ("text", "font_size")


class ValidationError(Exception):
    def __init__(self, details):
        super().__init__("validation failed")
        self.details = [{"field": f, "message": m} for f, m in details][:MAX_DETAILS]


def fixture_layers():
    """Fresh copy of the seed layers (exact contract content)."""
    return [
        {"id": "rect-1", "type": "rect", "label": "Platform block",
         "x": 40, "y": 60, "w": 120, "h": 72, "fill": "#2f6f9f"},
        {"id": "text-1", "type": "text", "label": "Station signs",
         "x": 40, "y": 160, "w": 240, "h": 32, "text": "Station signs",
         "font_size": 24, "fill": "#1f2933"},
    ]


def _str(value, field, lo, hi, errors, multiline=False, strip=False):
    if type(value) is not str:
        errors.append((field, "must be a string"))
        return None
    if strip:
        value = value.strip()
    if not lo <= len(value) <= hi:
        errors.append((field, "length must be %d to %d characters" % (lo, hi)))
        return None
    for ch in value:
        cat = unicodedata.category(ch)
        if cat == "Cs" or (cat == "Cc" and not (multiline and ch in "\n\t")):
            errors.append((field, "contains characters that are not allowed"))
            return None
    return value


def _int(value, field, lo, hi, errors):
    if type(value) is not int:  # rejects bool and float
        errors.append((field, "must be an integer"))
        return None
    if not lo <= value <= hi:
        errors.append((field, "must be between %d and %d" % (lo, hi)))
        return None
    return value


def _validate_layer(raw, prefix, errors):
    if type(raw) is not dict:
        errors.append((prefix, "must be an object"))
        return None
    ltype = raw.get("type")
    if type(ltype) is not str or ltype not in LAYER_TYPES:
        errors.append((prefix + ".type", "must be one of: rect, text"))
        return None
    keys = _COMMON_KEYS + (_TEXT_KEYS if ltype == "text" else ())
    ok = True
    for k in raw:
        if k not in keys:
            errors.append((prefix + "." + str(k), "unknown field"))
            ok = False
    for k in keys:
        if k not in raw:
            errors.append((prefix + "." + k, "is required"))
            ok = False
    if not ok:
        return None
    before = len(errors)
    out = {}
    out["id"] = None
    lid = raw["id"]
    if type(lid) is str and _ID_RE.fullmatch(lid):
        out["id"] = lid
    else:
        errors.append((prefix + ".id", "must match [A-Za-z0-9_-] and be 1 to 40 characters"))
    out["type"] = ltype
    out["label"] = _str(raw["label"], prefix + ".label", 1, MAX_LABEL, errors)
    out["x"] = _int(raw["x"], prefix + ".x", -2000, 2000, errors)
    out["y"] = _int(raw["y"], prefix + ".y", -2000, 2000, errors)
    out["w"] = _int(raw["w"], prefix + ".w", 1, 2000, errors)
    out["h"] = _int(raw["h"], prefix + ".h", 1, 2000, errors)
    if ltype == "text":
        out["text"] = _str(raw["text"], prefix + ".text", 0, MAX_TEXT, errors, multiline=True)
        out["font_size"] = _int(raw["font_size"], prefix + ".font_size", 8, 96, errors)
    fill = raw["fill"]
    if type(fill) is str and _FILL_RE.fullmatch(fill):
        out["fill"] = fill
    else:
        errors.append((prefix + ".fill", "must be a color like #rrggbb"))
    if len(errors) > before:
        return None
    # Canonical key order matches the contract.
    order = ["id", "type", "label", "x", "y", "w", "h"]
    if ltype == "text":
        order += ["text", "font_size"]
    order.append("fill")
    return {k: out[k] for k in order}


def validate_layers(raw, errors, field="layers"):
    if type(raw) is not list:
        errors.append((field, "must be an array"))
        return None
    if len(raw) > MAX_LAYERS:
        errors.append((field, "at most %d layers are allowed" % MAX_LAYERS))
        return None
    result, seen, bad = [], set(), False
    for i, item in enumerate(raw):
        layer = _validate_layer(item, "%s[%d]" % (field, i), errors)
        if layer is None:
            bad = True
            continue
        if layer["id"] in seen:
            errors.append(("%s[%d].id" % (field, i), "duplicate layer id"))
            bad = True
        seen.add(layer["id"])
        result.append(layer)
    return None if bad else result


def _check_object(body, allowed, required, errors):
    if type(body) is not dict:
        errors.append(("body", "must be a JSON object"))
        return False
    for k in body:
        if k not in allowed:
            errors.append((str(k), "unknown field"))
    for k in required:
        if k not in body:
            errors.append((k, "is required"))
    return not errors


def validate_create(body):
    """Return (title, fixture: bool)."""
    errors = []
    _check_object(body, ("title", "fixture"), ("title",), errors)
    title = fixture = None
    if type(body) is dict:
        if "title" in body:
            title = _str(body["title"], "title", 1, MAX_TITLE, errors, strip=True)
        fixture = body.get("fixture", False)
        if type(fixture) is not bool:
            errors.append(("fixture", "must be a boolean"))
    if errors:
        raise ValidationError(errors)
    return title, fixture


def validate_update(body):
    """Return (title, base_revision, layers)."""
    errors = []
    _check_object(body, ("title", "base_revision", "layers"),
                  ("title", "base_revision", "layers"), errors)
    title = rev = layers = None
    if type(body) is dict:
        if "title" in body:
            title = _str(body["title"], "title", 1, MAX_TITLE, errors, strip=True)
        if "base_revision" in body:
            rev = _int(body["base_revision"], "base_revision", 1, MAX_REVISION, errors)
        if "layers" in body:
            layers = validate_layers(body["layers"], errors)
    if errors:
        raise ValidationError(errors)
    return title, rev, layers
