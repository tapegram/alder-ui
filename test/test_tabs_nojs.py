"""No-JS tab labels (Playwright; skipped without it): the default look and the
line variant, which must match the built line tab's underline indicator.

    .venv/bin/python -m unittest test.test_tabs_nojs -v
"""
import functools
import http.server
import pathlib
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

AFTER = """e => {
    const s = getComputedStyle(e, '::after');
    return {content: s.content, position: s.position, left: s.left, right: s.right,
            bottom: s.bottom, height: s.height, background: s.backgroundColor,
            opacity: s.opacity};
}"""
LABEL = """e => {
    const s = getComputedStyle(e);
    return {background: s.backgroundColor, shadow: s.boxShadow, radius: s.borderRadius};
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class TabsNoJsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/demo/tabs.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def page(self, js):
        page = self.browser.new_page(java_script_enabled=js)
        page.goto(self.url)
        return page

    def test_default_checked_label(self):
        page = self.page(False)
        try:
            s = page.eval_on_selector("al-tabs:not([variant]) label:has(> input:checked)", LABEL)
        finally:
            page.close()
        self.assertEqual(s["background"], "oklch(1 0 0)")
        self.assertIn("0px 1px 3px 0px", s["shadow"])  # shadow-sm

    def test_line_variant_checked_label(self):
        sel = "al-tabs[variant=line] label:has(> input:checked)"
        page = self.page(False)
        try:
            s = page.eval_on_selector(sel, LABEL)
            nojs = page.eval_on_selector(sel, AFTER)
        finally:
            page.close()
        self.assertEqual(s["background"], "rgba(0, 0, 0, 0)")
        self.assertEqual(s["shadow"], "none")
        page = self.page(True)
        try:
            built = page.eval_on_selector(
                "al-tabs[variant=line] [role=tab][aria-selected=true]", AFTER)
        finally:
            page.close()
        self.assertEqual(nojs, built)
        self.assertEqual(nojs["opacity"], "1")

    def test_line_variant_unchecked_label_has_no_underline(self):
        page = self.page(False)
        try:
            a = page.eval_on_selector(
                "al-tabs[variant=line] label:not(:has(> input:checked))", AFTER)
        finally:
            page.close()
        self.assertIn(a["opacity"], ("0",))
        self.assertEqual(a["content"], '""')
