"""Unit tests for test/parity.py's pure functions (stdlib unittest, no browser).

    python3 -m unittest test.test_parity -v
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import parity  # noqa: E402


def close(a, b, tol=1):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


class ColourTest(unittest.TestCase):
    def test_colour_forms_normalise_equal(self):
        a = parity.normalise_colour("rgb(23, 23, 23)")
        b = parity.normalise_colour("oklch(0.205 0 0)")
        self.assertTrue(close(a, b), (a, b))
        self.assertEqual(parity.normalise_colour("color-mix(in oklab, oklch(0.205 0 0) 90%, transparent)")[3], 230)

    def test_more_colour_forms(self):
        self.assertEqual(parity.normalise_colour("#171717"), (23, 23, 23, 255))
        self.assertEqual(parity.normalise_colour("#0000"), (0, 0, 0, 0))
        self.assertEqual(parity.normalise_colour("transparent"), (0, 0, 0, 0))
        self.assertTrue(close(parity.normalise_colour("color(srgb 0.0902 0.0902 0.0902)"), (23, 23, 23, 255)))
        self.assertTrue(close(parity.normalise_colour("oklab(0.205 0 0 / 50%)"), (23, 23, 23, 128)))
        self.assertTrue(close(parity.normalise_colour("hsl(0, 0%, 91%)"), (232, 232, 232, 255)))
        # srgb mixing of two opaque colours.
        self.assertEqual(parity.normalise_colour("color-mix(in srgb, #000 50%, #fff)"), (128, 128, 128, 255))
        # oklch(0.577 0.245 27.325) is shadcn's --destructive; red-dominant.
        r, g, b, a = parity.normalise_colour("oklch(0.577 0.245 27.325)")
        self.assertTrue(r > 200 and g < 60 and b < 60 and a == 255, (r, g, b, a))
        with self.assertRaises(ValueError):
            parity.normalise_colour("not-a-colour")

    def test_shadow_colours_normalised(self):
        self.assertEqual(
            parity.normalise_value("box-shadow", "rgba(0, 0, 0, 0.05) 0px 1px 2px 0px"),
            parity.normalise_value("box-shadow", "oklab(0 0 0 / 0.05) 0px 1px 2px 0px"),
        )

    def test_outline_and_border_colours_normalised(self):
        self.assertEqual(
            parity.normalise_value("outline", "oklch(0.708 0 0) solid 1px"),
            parity.normalise_value("outline", "rgb(161, 161, 161) solid 1px"),
        )
        self.assertEqual(
            parity.diff({"border-color": "oklch(0.922 0 0)"}, {"border-color": "rgb(229, 229, 229)"}), []
        )


class DiffTest(unittest.TestCase):
    def test_size_tolerance(self):
        self.assertEqual(parity.diff({"height": "36px"}, {"height": "36.4px"}), [])
        self.assertEqual(parity.diff({"height": "36px"}, {"height": "37px"}), [("height", "36px", "37px")])

    def test_colour_tolerance_is_one_per_channel(self):
        self.assertEqual(parity.diff({"color": "rgb(10, 10, 10)"}, {"color": "rgb(11, 9, 10)"}), [])
        self.assertEqual(len(parity.diff({"color": "rgb(10, 10, 10)"}, {"color": "rgb(12, 10, 10)"})), 1)

    def test_non_size_lengths_are_exact(self):
        self.assertEqual(len(parity.diff({"padding": "8px 16px"}, {"padding": "8px 16.4px"})), 1)
        self.assertEqual(len(parity.diff({"font-weight": "500"}, {"font-weight": "600"})), 1)


class AllowTest(unittest.TestCase):
    def test_allow_and_map(self):
        allow = {
            "pending": [],
            "map": {"alert/info/root": "alert/default/root"},
            "allow": [{"ref": "checkbox/*", "prop": "width", "reason": "test"}],
        }
        self.assertTrue(parity.allowed("checkbox/default/checked", "width", allow))
        self.assertFalse(parity.allowed("checkbox/default/checked", "height", allow))
        self.assertEqual(parity.target("alert/info/root", allow), "alert/default/root")
        self.assertEqual(parity.target("button/default/default", allow), "button/default/default")

    def test_allow_entries_have_reasons(self):
        bad = {"pending": [], "map": {}, "allow": [{"ref": "checkbox/*", "prop": "display"}]}
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "allow.json"
            p.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                parity.load_allow(p)

    def test_committed_allow_list_loads(self):
        allow = parity.load_allow(parity.ALLOW)
        self.assertIn("button", allow["pending"])


if __name__ == "__main__":
    unittest.main()
