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
class FocusTest(unittest.TestCase):
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
