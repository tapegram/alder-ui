"""Keyboard focus styles that parity.py cannot reach, since it never presses Tab
(Playwright; skipped without it).

    .venv/bin/python -m unittest test.test_focus -v
"""
import functools
import http.server
import pathlib
import re
import sys
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from colour import normalise_colour  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

NO_MOTION = "*, *::before, *::after { transition: none !important; animation: none !important }"
FOCUSED_JS = "(sel) => document.activeElement && document.activeElement.matches(sel)"
STYLE_JS = """([sel, props]) => {
  const el = document.querySelector(sel), s = getComputedStyle(el), out = {};
  for (const p of props) out[p] = s.getPropertyValue(p);
  return out;
}"""
TOKEN_JS = "(name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def focus_style(page, selector, props):
    """Press Tab until `selector` is the focused element, then return {prop: computed
    value} for props, read from the first element `selector` matches."""
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    for _ in range(200):
        page.keyboard.press("Tab")
        if page.evaluate(FOCUSED_JS, selector):
            return page.evaluate(STYLE_JS, [selector, list(props)])
    raise AssertionError("Tab never reached %s" % selector)


def shadow_colour(box_shadow):
    """The colour of a computed box-shadow, as 8-bit sRGB plus alpha 0-255."""
    m = re.match(r"\s*(rgba?\([^)]*\)|color\([^)]*\)|oklab\([^)]*\)|oklch\([^)]*\)|\S+)", box_shadow)
    return normalise_colour(m.group(1))


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class _FocusBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/demo/parity.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def page(self, dark):
        page = self.browser.new_page(viewport={"width": 1280, "height": 800}, color_scheme="light")
        self.addCleanup(page.close)
        page.goto(self.url, wait_until="load")
        page.add_style_tag(content=NO_MOTION)
        page.evaluate("(on) => document.documentElement.classList.toggle('dark', on)", dark)
        return page

    def assert_colour(self, got, want, msg):
        self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(got, want)), "%s: %s != %s" % (msg, got, want))


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class FocusTest(_FocusBase):
    def check_ring(self, dark):
        page = self.page(dark)
        token = lambda n: page.evaluate(TOKEN_JS, n)
        # destructive: focus-visible:ring-destructive/20, dark /40
        st = focus_style(page, "#parity-badge-destructive", ["outline-style"])
        self.assertEqual(st["outline-style"], "none", "the inner link draws no outline")
        host = "al-badge:has(> #parity-badge-destructive)"
        got = page.evaluate(STYLE_JS, [host, ["box-shadow", "border-color"]])
        pct = 40 if dark else 20
        want = normalise_colour("color-mix(in oklab, %s %d%%, transparent)" % (token("--destructive"), pct))
        self.assert_colour(shadow_colour(got["box-shadow"]), want, "destructive ring")
        self.assertIn("3px", got["box-shadow"])
        # default badge: focus-visible:border-ring, ring-ring/50
        focus_style(page, "#parity-badge-default", [])
        got = page.evaluate(STYLE_JS, ["al-badge:has(> #parity-badge-default)", ["box-shadow", "border-color"]])
        self.assert_colour(normalise_colour(got["border-color"]), normalise_colour(token("--ring")), "border")
        want = normalise_colour("color-mix(in oklab, %s 50%%, transparent)" % token("--ring"))
        self.assert_colour(shadow_colour(got["box-shadow"]), want, "default ring")

    def test_badge_link_focus_ring(self):
        for dark in (False, True):
            with self.subTest(dark=dark):
                self.check_ring(dark)


    def test_menu_keyboard_focus(self):
        # D4: keyboard focus on a menu item draws a non-colour outline; hover alone does not
        page = self.page(False)
        page.evaluate("document.getElementById('parity-menu-trigger').focus()")
        page.keyboard.press("Enter")
        page.wait_for_function("document.getElementById('parity-menu').contains(document.activeElement)")
        page.keyboard.press("ArrowDown")
        sel = "#parity-menu > :focus-visible"
        self.assertTrue(page.evaluate("(s) => !!document.querySelector(s)", sel), "ArrowDown focuses an item")
        got = page.evaluate(STYLE_JS, [sel, ["outline-style", "outline-width", "outline-color", "outline-offset"]])
        self.assertEqual((got["outline-style"], got["outline-width"], got["outline-offset"]), ("solid", "2px", "-2px"))
        self.assert_colour(normalise_colour(got["outline-color"]),
                           normalise_colour(page.evaluate(TOKEN_JS, "--muted-foreground")), "outline colour")
        page.mouse.move(0, 0)
        page.evaluate("document.activeElement.blur()")
        box = page.locator("#parity-menu > a").first.bounding_box()
        page.mouse.move(box["x"] + 5, box["y"] + 5)
        got = page.evaluate(STYLE_JS, ["#parity-menu > a:hover", ["outline-style"]])
        self.assertEqual(got["outline-style"], "none")


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class ForcedColorsTest(_FocusBase):
    """#15: in forced colors the box-shadow ring is dropped, so each focusable draws an outline."""
    SELECTORS = {
        "button": "al-button > button",
        "input": "al-input input",
        "textarea": "al-textarea textarea",
        "select": "al-select select",
        "checkbox": "al-checkbox input",
        "pagination link": "al-pagination > a",
        "badge link": "#parity-badge-default",
        "no-JS tab label": "al-tabs > al-tab input",
        "alert dismiss": ".al-alert-dismiss",
        "menu item": "#parity-menu > a",
    }

    def test_forced_colors_focus_outline(self):
        for name, sel in self.SELECTORS.items():
            with self.subTest(name):
                page = self.browser.new_page(viewport={"width": 1280, "height": 800}, forced_colors="active")
                self.addCleanup(page.close)
                if name == "no-JS tab label":  # al-tabs.js would replace the labels with tabs
                    page.route("**/al.js", lambda route: route.abort())
                page.goto(self.url, wait_until="load")
                page.add_style_tag(content=NO_MOTION)
                if name == "alert dismiss":
                    page.evaluate("""() => { const a = document.createElement('al-alert');
                        a.setAttribute('dismissible', ''); a.textContent = 'Saved'; document.body.prepend(a) }""")
                if name == "menu item":
                    page.evaluate("document.getElementById('parity-menu').showPopover()")
                    page.evaluate("document.querySelector('#parity-menu > a').focus()")
                    st = page.evaluate(STYLE_JS, [sel, ["outline-style", "outline-width"]])
                else:
                    st = focus_style(page, sel, ["outline-style", "outline-width"])
                    if name == "no-JS tab label":  # the label draws it, the input is hidden
                        st = page.evaluate(STYLE_JS, ["al-tabs > al-tab > label:has(> input:focus-visible)",
                                                      ["outline-style", "outline-width"]])
                self.assertNotEqual(st["outline-style"], "none", st)
                self.assertGreaterEqual(float(st["outline-width"][:-2]), 2.0, st)
