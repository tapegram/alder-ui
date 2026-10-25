"""al-page padding at a small and a wide viewport (Playwright; skipped without it).
parity.py runs at 1280px only, so the base `padding: 2rem 1rem` is pinned here.

    .venv/bin/python -m unittest test.test_page -v
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


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/demo/page.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def padding(self, width):
        page = self.browser.new_page(viewport={"width": width, "height": 800})
        try:
            page.goto(self.url)
            return page.eval_on_selector("al-page", """e => {
                const s = getComputedStyle(e);
                return [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft];
            }""")
        finally:
            page.close()

    def test_small_viewport(self):
        # py-8 px-4
        self.assertEqual(self.padding(600), ["32px", "16px", "32px", "16px"])

    def test_wide_viewport(self):
        # py-8 sm:px-6
        self.assertEqual(self.padding(1280), ["32px", "24px", "32px", "24px"])


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class DialogFooterTest(unittest.TestCase):
    """The dialog footer stacks full-width buttons on a phone and right-aligns intrinsic
    ones from 40rem (parity.py runs at 1280px only)."""

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

    def footer(self, width):
        page = self.browser.new_page(viewport={"width": width, "height": 800})
        try:
            page.goto(self.url, wait_until="load")
            page.evaluate("document.getElementById('parity-dialog').showModal()")
            return page.evaluate("""() => {
                const f = document.querySelector('#parity-dialog > [slot=actions]');
                const s = getComputedStyle(f), r = f.getBoundingClientRect();
                const left = r.left + parseFloat(s.borderLeftWidth) + parseFloat(s.paddingLeft);
                const right = r.right - parseFloat(s.borderRightWidth) - parseFloat(s.paddingRight);
                return { left, right, width: right - left,
                         buttons: [...f.querySelectorAll('button')].map((b) => {
                           const q = b.getBoundingClientRect(); return { left: q.left, right: q.right, width: q.width };
                         }) };
            }""")
        finally:
            page.close()

    def test_dialog_footer_phone(self):
        f = self.footer(600)
        self.assertEqual(len(f["buttons"]), 2)
        for b in f["buttons"]:
            self.assertAlmostEqual(b["width"], f["width"], delta=0.5)

    def test_dialog_footer_wide(self):
        f = self.footer(1280)
        self.assertEqual(len(f["buttons"]), 2)
        for b in f["buttons"]:
            self.assertLess(b["width"], f["width"] - 1)
        self.assertAlmostEqual(f["buttons"][-1]["right"], f["right"], delta=0.5)
