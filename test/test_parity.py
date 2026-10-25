"""Unit tests for test/parity.py's pure functions (stdlib unittest, no browser).

    python3 -m unittest test.test_parity -v
"""
import json
import pathlib
import sys
import tempfile
import types
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
        self.assertIsInstance(allow["pending"], list)
        self.assertTrue(all(isinstance(c, str) and c for c in allow["pending"]))
        self.assertEqual(len(set(allow["pending"])), len(allow["pending"]))
        # #8: a wildcard prop hides everything, and box-* on the backdrop is two named props.
        self.assertFalse([e for e in allow["allow"] if e["prop"] == "*"])
        overlay = [e["prop"] for e in allow["allow"] if e["ref"] == "dialog/overlay/open"]
        self.assertFalse([p for p in overlay if p.startswith("box-") and "*" in p], overlay)

    def test_unused_entry(self):
        allow = {"pending": [], "map": {}, "allow": [
            {"ref": "button/*", "prop": "height", "reason": "t"},
            {"ref": "card/*", "prop": "gap", "reason": "t"},
            {"ref": "tabs/nojs-*/*", "prop": "*", "reason": "t"},
        ]}
        rows = [("button", "button/default/default", "light", "rest", "height", "1px", "2px"),
                ("tabs", "tabs/list/default", "dark", "rest", "gap", "1px", "2px")]
        unused = parity.unused_allow(rows, allow)
        self.assertEqual([e["ref"] for e in unused], ["card/*", "tabs/nojs-*/*"])

    def test_dark_only_row_counts_as_a_use(self):
        allow = {"pending": [], "map": {"a/x": "a/y"}, "allow": [{"ref": "a/y", "prop": "gap", "reason": "t"}]}
        rows = [("a", "a/x", "dark", "rest", "gap", "1px", "2px")]
        self.assertEqual(parity.unused_allow(rows, allow), [])


class CheckSetsTest(unittest.TestCase):
    def pages(self, ref, twin):
        mk = lambda d: types.SimpleNamespace(inventory={k: {"states": v} for k, v in d.items()})
        return mk(ref), mk(twin)

    def test_identical_sets_are_clean(self):
        ref, twin = self.pages({"a/b/c": ["hover"]}, {"a/b/c": ["hover"]})
        self.assertEqual(parity.check_sets(ref, twin, {}), [])

    def test_marker_on_one_page_only(self):
        ref, twin = self.pages({"a/b/c": [], "a/b/d": []}, {"a/b/c": [], "a/b/e": []})
        probs = parity.check_sets(ref, twin, {})
        self.assertEqual(len(probs), 2)
        self.assertIn("a/b/d is on the ref page only", probs[0])
        self.assertIn("a/b/e is on the twin page only", probs[1])

    def test_states_differ(self):
        ref, twin = self.pages({"a/b/c": ["hover"]}, {"a/b/c": ["hover", "focus"]})
        probs = parity.check_sets(ref, twin, {})
        self.assertEqual(len(probs), 1)
        self.assertIn("states differ", probs[0])


class ExpectConflictTest(unittest.TestCase):
    def test_labels_come_from_the_page(self):
        fake = types.SimpleNamespace(page=types.SimpleNamespace(evaluate=lambda js: ["a/b/c"]))
        self.assertEqual(parity.expect_conflicts(fake), ["a/b/c"])
        self.assertIn("data-expect", parity.EXPECT_CONFLICT_JS)
        self.assertIn("data-ref", parity.EXPECT_CONFLICT_JS)


class FontGateTest(unittest.TestCase):
    OK = {"geist": True, "mono": True}
    BAD = {"geist": False, "mono": True}

    def test_missing_ref_font_fails(self):
        status, msg = parity.font_gate(self.BAD, self.OK, ["button"])
        self.assertEqual(status, 1)
        self.assertIn("ref", msg)

    def test_missing_twin_font_fails_when_gating(self):
        status, msg = parity.font_gate(self.OK, self.BAD, ["button"])
        self.assertEqual(status, 1)
        self.assertIn("button", msg)

    def test_missing_twin_font_warns_when_nothing_gates(self):
        status, msg = parity.font_gate(self.OK, self.BAD, [])
        self.assertEqual(status, 0)
        self.assertIn("WARNING", msg)

    def test_fonts_present(self):
        self.assertEqual(parity.font_gate(self.OK, self.OK, ["button"]), (0, None))


class PageErrorTest(unittest.TestCase):
    def test_one_line_per_error_prefixed_by_page(self):
        a = types.SimpleNamespace(name="ref", errors=["boom", "bang"])
        b = types.SimpleNamespace(name="twin", errors=[])
        c = types.SimpleNamespace(name="close checks", errors=["oops"])
        lines = parity.page_error_lines([a, b, c])
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("parity: ref page error") and "boom" in lines[0])
        self.assertIn("bang", lines[1])
        self.assertIn("close checks", lines[2])

    def test_no_errors(self):
        self.assertEqual(parity.page_error_lines([types.SimpleNamespace(name="x", errors=[])]), [])


class CloseVerdictTest(unittest.TestCase):
    """check_closes' decision on what it measured after the exit transition (Review Focus 4)."""

    def state(self, **kw):
        st = {"opened": True, "connected": True, "display": "none", "hit": False}
        st.update(kw)
        return st

    def test_closed_completely(self):
        self.assertEqual(parity.close_problems(self.state()), [])

    def test_still_displayed(self):
        probs = parity.close_problems(self.state(display="grid"))
        self.assertEqual(len(probs), 1)
        self.assertIn("grid", probs[0])

    def test_still_takes_clicks(self):
        self.assertEqual(len(parity.close_problems(self.state(hit=True))), 1)
        self.assertEqual(len(parity.close_problems(self.state(display="block", hit=True))), 2)

    def test_disconnected_is_closed(self):
        # R19: a node removed from the document is closed, whatever it last measured.
        self.assertEqual(parity.close_problems(self.state(connected=False, display="block", hit=True)), [])

    def test_never_opened_is_a_problem(self):
        # Otherwise a dialog that never opened would pass vacuously.
        self.assertEqual(len(parity.close_problems(self.state(opened=False))), 1)
        self.assertEqual(len(parity.close_problems(self.state(opened=False, connected=False))), 1)


class CloseChecksTest(unittest.TestCase):
    """Review Focus 4 covers every overlay, and the popover by each way it closes."""

    def labels(self, comp):
        return [c[1] for c in parity.CLOSE_CHECKS if c[0] == comp]

    def test_every_overlay_is_checked(self):
        for comp in ("dialog", "popover", "menu", "tooltip", "toast"):
            self.assertTrue(self.labels(comp), comp)

    def test_toast_closes_by_timeout(self):
        # The toast closes itself: close is the ms it does so after, and the toast the
        # open js adds carries that timeout.
        (entry,) = [c for c in parity.CLOSE_CHECKS if c[:2] == ("toast", "timeout")]
        self.assertEqual(entry[4], 100)
        self.assertIn("'timeout', '100'", entry[3])

    def test_popover_closes_every_way(self):
        self.assertIn("hidePopover()", self.labels("popover"))
        self.assertIn("light dismiss", self.labels("popover"))
        self.assertTrue(any(c[5] for c in parity.CLOSE_CHECKS if c[0] == "popover"), "no run with commandForElement deleted")

class AnchorVerdictTest(unittest.TestCase):
    """anchor_problems: an overlay must sit against its anchor (R21: al-tooltip above)."""
    TRIGGER = [275, 982, 347, 1018]

    def test_above_and_centred(self):
        self.assertEqual(parity.anchor_problems([268, 949, 354, 977], self.TRIGGER, "above"), [])

    def test_unanchored_at_the_viewport_corner(self):
        self.assertEqual(len(parity.anchor_problems([5, 5, 90, 33], self.TRIGGER, "above")), 2)

    def test_wrong_side(self):
        self.assertEqual(len(parity.anchor_problems([268, 1023, 354, 1051], self.TRIGGER, "above")), 1)
        self.assertEqual(parity.anchor_problems([268, 1023, 354, 1051], self.TRIGGER, "below"), [])

    def test_not_open(self):
        self.assertEqual(len(parity.anchor_problems([0, 0, 0, 0], self.TRIGGER, "above")), 1)

    def test_unknown_side(self):
        with self.assertRaises(ValueError):
            parity.anchor_problems([268, 949, 354, 977], self.TRIGGER, "below ")


class ReportTest(unittest.TestCase):
    def test_allowed_row_does_not_fail(self):
        allow = {"pending": [], "map": {}, "allow": [{"ref": "button/*", "prop": "height", "reason": "t"}]}
        rows = [("button", "button/default/default", "light", "rest", "height", "1px", "2px")]
        text, failing = parity.report(rows, allow, ["button"], [])
        self.assertEqual(failing, [])
        self.assertIn("1 allowed", text)

    def test_pending_component_does_not_fail(self):
        allow = {"pending": ["button"], "map": {}, "allow": []}
        rows = [("button", "button/default/default", "light", "rest", "height", "1px", "2px")]
        text, failing = parity.report(rows, allow, ["button"], [])
        self.assertEqual(failing, [])
        self.assertIn("## pending: button", text)

    def test_expect_only_component_rows_are_printed(self):
        # A data-expect row whose component has no data-ref marker (stack, page) still
        # gates, so its rows must be shown, not only its name in the failing line.
        allow = {"pending": [], "map": {}, "allow": []}
        rows = [("stack", "stack/expect/p-1", "light", "expect", "margin-top", "0px", "24px")]
        text, failing = parity.report(rows, allow, ["button"], ["stack/expect/p-1"])
        self.assertEqual(failing, ["stack"])
        self.assertIn("### stack (1)", text)
        self.assertIn("| stack/expect/p-1 | light | expect | margin-top | `0px` | `24px` |", text)


if __name__ == "__main__":
    unittest.main()
