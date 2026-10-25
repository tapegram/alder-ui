"""Unit tests for test/colour.py and test/check.py's manifest check.

    python3 -m unittest discover -s test -p 'test_*.py'
"""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check  # noqa: E402
import colour  # noqa: E402


def close(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class ColourTest(unittest.TestCase):
    def test_oklch_white_black(self):
        self.assertTrue(close(colour.parse("oklch(1 0 0)", {})[:3], (1, 1, 1), 1e-3))
        self.assertTrue(close(colour.parse("oklch(0 0 0)", {})[:3], (0, 0, 0), 1e-3))

    def test_oklch_red600(self):
        r = colour.parse("oklch(0.577 0.245 27.325)", {})
        self.assertTrue(close([round(x * 255) for x in r[:3]], (231, 0, 11), 1), r)

    def test_oklch_alpha(self):
        self.assertEqual(colour.parse("oklch(1 0 0 / 10%)", {})[3], 0.1)

    def test_mix_transparent(self):
        r = colour.parse("color-mix(in oklab, var(--p) 90%, transparent)", {"--p": "oklch(0.205 0 0)"})
        self.assertEqual(r[3], 0.9)

    def test_contrast_known(self):
        self.assertAlmostEqual(colour.contrast("oklch(0.556 0 0)", "oklch(1 0 0)", {"--background": "oklch(1 0 0)"}), 4.73, delta=0.02)


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.saved = (dict(check.ADDED_VALUES), dict(check.ADDED_SLOTS), list(check.FAILURES))
        check.FAILURES.clear()
        self.m, self.els = check.load_manifest()
        self.els = copy.deepcopy(self.els)

    def tearDown(self):
        check.ADDED_VALUES.clear(); check.ADDED_VALUES.update(self.saved[0])
        check.ADDED_SLOTS.clear(); check.ADDED_SLOTS.update(self.saved[1])
        check.FAILURES[:] = self.saved[2]

    def manifest_failures(self):
        check.FAILURES.clear()
        check.check_manifest(self.m, self.els)
        return [f for f in check.FAILURES if "variant" in f or "slots" in f or "version" in f]

    def test_union_growth_allowed(self):
        for a in self.els["al-button"]["attributes"]:
            if a["name"] == "variant":
                a["type"]["text"] += ' | "brand"'
        self.assertTrue(self.manifest_failures())
        check.ADDED_VALUES[("al-button", "variant")] = ["link", "brand"]
        self.assertEqual(self.manifest_failures(), [])

    def test_slot_growth_allowed(self):
        self.els["al-dialog"]["slots"] += [{"name": "extra"}, {"name": "more"}]
        self.assertTrue(self.manifest_failures())
        check.ADDED_SLOTS["al-dialog"] = check.ADDED_SLOTS.get("al-dialog", []) + ["extra", "more"]
        self.assertEqual(self.manifest_failures(), [])

    def test_rc_version(self):
        for v, ok in (("v0.4.0-rc.1", True), ("v0.4.0", True), ("v0.4", False)):
            self.m["version"] = v
            self.assertEqual(not self.manifest_failures(), ok, v)


class MotionTest(unittest.TestCase):
    def test_unguarded_motion(self):
        css = """/* transition: all */
        a { color: red; transition: opacity 1s }
        b { transition: none }
        @media (prefers-reduced-motion: no-preference) { c { transition: all 1s } @starting-style { d { opacity: 0 } } }
        e::after { animation-name: spin }"""
        self.assertEqual(check.unguarded_motion(css), ["a", "e::after"])


if __name__ == "__main__":
    unittest.main()
