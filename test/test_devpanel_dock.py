"""The developer panel docked as the body's last child (Playwright; skipped
without it): on a short page it sits at the bottom of the window, not after the
content, and dragging the grip up moves its top edge while the bottom stays put.

    .venv/bin/python -m unittest test.test_devpanel_dock -v
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

PANEL = "#docked"
GRIP = "#docked > [data-grip]"
TAB = "#docked > nav > button[aria-controls='d-sql']"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class DevpanelDockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/test/fixtures/devpanel-docked.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def page(self):
        page = self.browser.new_page(viewport={"width": 1000, "height": 800})
        page.goto(self.url)
        page.wait_for_selector(PANEL)
        return page

    def rect(self, page):
        return page.eval_on_selector(PANEL, "e => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom} }")

    def test_collapsed_panel_sits_at_the_bottom_of_a_short_page(self):
        page = self.page()
        try:
            r = self.rect(page)
        finally:
            page.close()
        self.assertAlmostEqual(r["bottom"], 800, delta=1, msg="the bar docks to the window's bottom edge")

    def test_open_panel_sits_at_the_bottom(self):
        page = self.page()
        try:
            page.click(TAB)
            page.wait_for_selector(GRIP, state="visible")
            r = self.rect(page)
        finally:
            page.close()
        self.assertAlmostEqual(r["bottom"], 800, delta=1)

    def test_drag_up_moves_the_top_edge_and_keeps_the_bottom(self):
        page = self.page()
        try:
            page.click(TAB)
            page.wait_for_selector(GRIP, state="visible")
            before = self.rect(page)
            box = page.query_selector(GRIP).bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] - 150)
            page.mouse.up()
            after = self.rect(page)
        finally:
            page.close()
        self.assertAlmostEqual(after["bottom"], 800, delta=1, msg="the bottom stays at the window's edge")
        self.assertLess(after["top"], before["top"] - 100, "the top edge follows the pointer up")

    def test_the_bar_does_not_cover_the_end_of_the_page(self):
        page = self.page()
        try:
            pad = page.evaluate("() => parseFloat(getComputedStyle(document.body).paddingBottom)")
            bar = page.eval_on_selector(PANEL, "e => e.getBoundingClientRect().height")
        finally:
            page.close()
        self.assertGreaterEqual(pad, bar - 1, "the body leaves room for the collapsed bar")


if __name__ == "__main__":
    unittest.main()
