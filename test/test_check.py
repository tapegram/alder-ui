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

    def test_var_case_kept(self):
        r = colour.parse("color-mix(in oklab, var(--P) 90%, transparent)", {"--P": "oklch(0.2 0 0)"})
        self.assertEqual(r[3], 0.9)

    def test_mix_known_values(self):
        # expected values from Chromium 156 getComputedStyle (oklab results converted to sRGB)
        cases = [
            ("color-mix(in oklab, #000 50%, #fff)", (0.38863, 0.38855, 0.38854, 1)),  # Chromium 156 oklab(0.499997 2.28e-5 1.0e-5)
            ("color-mix(in srgb, rgb(255 0 0) 50%, rgb(0 0 255 / 0.5))", (0.666667, 0, 0.333333, 0.75)),  # Chromium 156
            ("color-mix(in oklab, #3b82f6 30%, oklab(0.5 0.1 -0.1))", (0.46108, 0.35102, 0.70793, 1)),  # Chromium 156 oklab(0.53692 0.0600326 -0.125511)
            ("color-mix(in srgb, #ff0000 25%, rgb(0 128 0))", (0.25, 0.376471, 0, 1)),  # Chromium 156
        ]
        for expr, want in cases:
            got = colour.parse(expr, {})
            self.assertTrue(close(got, want, 0.004), (expr, got, want))

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


class TokenScanTest(unittest.TestCase):
    def test_al_definitions(self):
        self.assertEqual(check.al_definitions(":root{--al-x:1} @media print{:root{--al-y:2}}"), {"--al-x", "--al-y"})
        self.assertEqual(check.al_definitions("/* --al-z: 1 */ a{color:red}"), set())


class SelectorTest(unittest.TestCase):
    def setUp(self):
        self.saved = list(check.FAILURES)
        check.FAILURES.clear()
        self.m, self.els = check.load_manifest()

    def tearDown(self):
        check.FAILURES[:] = self.saved

    def failures(self, sel, tag):
        check.FAILURES.clear()
        check.check_selector(sel, self.els, tag, set())
        return list(check.FAILURES)

    def test_attr_of_non_al_compound(self):
        # [colspan] belongs to td, not to al-table
        self.assertEqual(self.failures("al-table:has(td[colspan])", "al-table"), [])
        self.assertEqual(self.failures("al-table td[colspan]", "al-table"), [])
        self.assertEqual(self.failures(":is(al-card, .x[foo])", "al-card"), [])
        # nested functional pseudos: [foo] belongs to td / .x, not to the al- element around them
        self.assertEqual(self.failures("al-card:has(al-button:is(td[foo]))", "al-card"), [])
        self.assertEqual(self.failures(":is(al-card:not(td[foo]))", "al-card"), [])
        self.assertEqual(self.failures("al-card:is(td:not(.x[foo]), b)", "al-card"), [])
        # ...but :not(.x[foo]) on an al- element is that element's attribute
        self.assertTrue(self.failures("al-card:is(al-button:not(.x[foo]), b)", "al-card"))

    def test_attr_only_compound_in_not(self):
        self.assertTrue(self.failures(":where(al-page:not([nonesuch]))", "al-page"))
        self.assertTrue(self.failures("al-card:not([nonesuch])", "al-card"))
        self.assertEqual(self.failures("al-card:has([nonesuch])", "al-card"), [])
        seen = set()
        check.FAILURES.clear()
        check.check_selector(":where(al-page:not([plain]))", self.els, "al-page", seen)
        self.assertEqual(check.FAILURES, [])
        self.assertIn(("al-page", "attr", "plain"), seen)

    def test_attr_goes_to_own_compound(self):
        self.assertTrue(self.failures("al-card[nonesuch]", "al-card"))
        self.assertTrue(self.failures("al-card:has(al-button[nonesuch])", "al-card"))
        self.assertTrue(self.failures("al-card:is(x):hover[nonesuch]", "al-card"))


class MotionTest(unittest.TestCase):
    def test_unguarded_motion(self):
        css = """/* transition: all */
        a { color: red; transition: opacity 1s }
        b { transition: none }
        @media (prefers-reduced-motion: no-preference) { c { transition: all 1s } @starting-style { d { opacity: 0 } } }
        e::after { animation-name: spin }"""
        self.assertEqual(check.unguarded_motion(css), ["a", "e::after"])


class FocusGuardTest(unittest.TestCase):
    def test_unguarded_focus(self):
        rule = "a:focus-visible{outline:none}"
        self.assertTrue(check.unguarded_focus(rule))
        self.assertFalse(check.unguarded_focus(rule + "@media (forced-colors: active){a:focus-visible{outline:2px solid CanvasText}}"))
        self.assertTrue(check.unguarded_focus("a:focus{outline-style:none}"))
        self.assertTrue(check.unguarded_focus("a:focus-visible{outline:1px none red}"))
        self.assertFalse(check.unguarded_focus("a:focus-visible{outline:1px solid red}"))
        self.assertFalse(check.unguarded_focus("a:hover{outline:none}"))
        self.assertFalse(check.unguarded_focus("/* a:focus{outline:none} */ a{color:red}"))


if __name__ == "__main__":
    unittest.main()
