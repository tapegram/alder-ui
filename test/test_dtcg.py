"""Unit tests for scripts/dtcg.py.

    python3 -m unittest test.test_dtcg -v
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import dtcg  # noqa: E402

RESOLVER = {
    "$schema": "https://www.designtokens.org/schemas/2025.10/resolver.json",
    "version": "2025.10",
    "name": "Test",
    "description": "A test theme.",
    "sets": {"base": {"sources": [{"$ref": "base.tokens.json"}]}},
    "modifiers": {"scheme": {"contexts": {
        "light": [{"$ref": "light.tokens.json"}],
        "dark": [{"$ref": "dark.tokens.json"}]}, "default": "light"}},
}


def tok(value, **kw):
    return {"$value": value, "$description": "A token.", **kw}


def oklch(*c, **kw):
    return {"colorSpace": "oklch", "components": list(c), **kw}


def make(base=None, light=None, dark=None, resolver=None, raw=None):
    """Write a theme dir; return its Path. raw maps file name -> literal text."""
    d = pathlib.Path(tempfile.mkdtemp())
    files = {
        "theme.resolver.json": resolver or RESOLVER,
        "base.tokens.json": base or {},
        "light.tokens.json": light or {},
        "dark.tokens.json": dark or {},
    }
    for name, data in files.items():
        (d / name).write_text(json.dumps(data))
    for name, text in (raw or {}).items():
        (d / name).write_text(text)
    return d


def one(group_type, value, scheme="light"):
    """Load a one-token theme and return its CSS text."""
    d = make(**{scheme: {"g": {"$type": group_type, "x": tok(value)}}})
    t = dtcg.load_theme(d)
    scope = getattr(t, scheme)
    return dtcg.css_value(scope["--x"], scope)


class ValueTest(unittest.TestCase):
    def test_oklch_colour(self):
        self.assertEqual(one("color", oklch(0.3, 0.03, 50)), "oklch(0.3 0.03 50)")

    def test_alpha(self):
        self.assertEqual(one("color", oklch(1, 0, 0, alpha=0.1)), "oklch(1 0 0 / 0.1)")

    def test_srgb_hex(self):
        self.assertEqual(one("color", {"colorSpace": "srgb", "components": [0.9, 0.9, 0.9],
                                       "hex": "#eff1f5"}), "#eff1f5")
        self.assertEqual(one("color", {"colorSpace": "srgb", "components": [0, 0, 0],
                                       "alpha": 0.05}), "rgb(0 0 0 / 0.05)")

    def test_dimension(self):
        self.assertEqual(one("dimension", {"value": 0, "unit": "rem"}), "0")
        self.assertEqual(one("dimension", {"value": 0.5, "unit": "rem"}), "0.5rem")
        self.assertEqual(one("dimension", {"value": 1.0, "unit": "px"}), "1px")

    def test_font_array(self):
        self.assertEqual(one("fontFamily", ["Geist", "ui-sans-serif"]), '"Geist", ui-sans-serif')
        self.assertEqual(one("fontFamily", ["Geist Mono", "Menlo", "Courier New", "monospace"]),
                         '"Geist Mono", Menlo, "Courier New", monospace')
        self.assertEqual(one("fontFamily", "Georgia"), '"Georgia"')

    def test_shadow_layers(self):
        d = lambda v, u="px": {"value": v, "unit": u}
        layers = [
            {"color": {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0.05},
             "offsetX": d(0), "offsetY": d(1), "blur": d(2), "spread": d(0)},
            {"color": {"colorSpace": "srgb", "components": [0, 0, 0], "hex": "#000000"},
             "offsetX": d(0), "offsetY": d(0), "blur": d(0), "spread": d(1), "inset": True},
        ]
        self.assertEqual(one("shadow", layers),
                         "0 1px 2px 0 rgb(0 0 0 / 0.05), inset 0 0 0 1px #000000")

    def test_alias_colour_is_var(self):
        d = make(light={"color": {"$type": "color", "primary": tok(oklch(0.2, 0, 0)),
                                  "ring": tok("{color.primary}")}})
        t = dtcg.load_theme(d)
        self.assertEqual(dtcg.css_value(t.light["--ring"], t.light), "var(--primary)")

    def test_alias_in_shadow(self):
        z = {"value": 0, "unit": "px"}
        d = make(base={"shadow": {"$type": "shadow", "shadow-sm": tok(
            {"color": "{color.border}", "offsetX": z, "offsetY": z, "blur": z, "spread": z})}},
            light={"color": {"$type": "color", "border": tok(oklch(0.9, 0, 0))}})
        t = dtcg.load_theme(d)
        scope = {**t.base, **t.light}
        self.assertIn("var(--border)", dtcg.css_value(t.base["--shadow-sm"], scope))

    def test_alias_unresolved(self):
        d = make(light={"color": {"$type": "color", "ring": tok("{color.nope}")}})
        t = dtcg.load_theme(d)
        with self.assertRaises(dtcg.DTCGError) as cm:
            dtcg.css_value(t.light["--ring"], t.light)
        self.assertIn("color.nope", str(cm.exception))


class LoadTest(unittest.TestCase):
    def test_bad_json_names_file_and_line(self):
        d = make(raw={"light.tokens.json": '{\n "color": {\n  "$type": "color",\n },\n}'})
        with self.assertRaises(dtcg.DTCGError) as cm:
            dtcg.load_theme(d)
        self.assertIn("light.tokens.json", str(cm.exception))
        self.assertIn("line", str(cm.exception))

    def test_order_preserved(self):
        names = ["zeta", "alpha", "mid", "beta"]
        d = make(light={"color": {"$type": "color", **{n: tok(oklch(0.5, 0, 0)) for n in names}}})
        t = dtcg.load_theme(d)
        self.assertEqual(list(t.light), ["--" + n for n in names])

    def test_metadata_and_fields(self):
        d = make(light={"color": {"$type": "color", "a": tok(oklch(0.5, 0, 0))}})
        t = dtcg.load_theme(d)
        self.assertEqual((t.name, t.description), ("Test", "A test theme."))
        a = t.light["--a"]
        self.assertEqual((a.type, a.description, a.file), ("color", "A token.", "light.tokens.json"))

    def test_type_inherited(self):
        d = make(light={"color": {"$type": "color", "a": tok(oklch(0.5, 0, 0))}})
        self.assertEqual(dtcg.load_theme(d).light["--a"].type, "color")

    def test_type_mismatch(self):
        d = make(light={"color": {"$type": "color", "a": tok({"value": 1, "unit": "px"})}})
        with self.assertRaises(dtcg.DTCGError) as cm:
            dtcg.load_theme(d)
        self.assertIn("light.tokens.json", str(cm.exception))

    def test_ref_escape_rejected(self):
        r = json.loads(json.dumps(RESOLVER))
        r["sets"]["base"]["sources"] = [{"$ref": "../base.tokens.json"}]
        with self.assertRaises(dtcg.DTCGError):
            dtcg.load_theme(make(resolver=r))

    def test_resolved(self):
        d = make(base={"dimension": {"$type": "dimension", "radius": tok({"value": 0.5, "unit": "rem"})}},
                 light={"color": {"$type": "color", "a": tok(oklch(1, 0, 0))}},
                 dark={"color": {"$type": "color", "a": tok(oklch(0, 0, 0))}})
        common, light, dark = dtcg.resolved(dtcg.load_theme(d))
        self.assertEqual(common, {"--radius": "0.5rem"})
        self.assertEqual(light, {"--a": "oklch(1 0 0)"})
        self.assertEqual(dark, {"--a": "oklch(0 0 0)"})


if __name__ == "__main__":
    unittest.main()
