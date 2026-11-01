"""The developer panel's resize grip (Playwright; skipped without it): dragging
and the keyboard change the open section's height, the height is clamped and
remembered, and the grip survives a patch that replaces the panel's children.

    .venv/bin/python -m unittest test.test_devpanel_resize -v
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

# the demo's third panel: it starts open, and the page has a button that patches its children
PANEL = "#p-patched"
GRIP = "#p-patched > [data-grip]"
OPEN_SECTION = "#p-patched > section:not([hidden])"
PATCH = "al-button:has(button) button:text('Patch')"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class DevpanelResizeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/demo/devpanel.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def open_panel(self, page):
        """The panel starts open; return its open section's height."""
        page.wait_for_selector(OPEN_SECTION, state="visible")
        return page.eval_on_selector(OPEN_SECTION, "e => e.getBoundingClientRect().height")

    def page(self):
        page = self.browser.new_page()
        page.goto(self.url)
        page.wait_for_selector(GRIP)
        return page

    def test_grip_is_present_and_labelled(self):
        page = self.page()
        try:
            self.open_panel(page)
            role = page.get_attribute(GRIP, "role")
            label = page.get_attribute(GRIP, "aria-label")
            first = page.eval_on_selector(PANEL, "e => e.firstElementChild.hasAttribute('data-grip')")
        finally:
            page.close()
        self.assertEqual(role, "separator")
        self.assertEqual(label, "Resize the developer panel")
        self.assertTrue(first, "the grip is the panel's first child, its top edge")

    def test_drag_up_makes_the_panel_taller(self):
        page = self.page()
        try:
            before = self.open_panel(page)
            box = page.query_selector(GRIP).bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] - 120)
            page.mouse.up()
            after = page.eval_on_selector(OPEN_SECTION, "e => e.getBoundingClientRect().height")
        finally:
            page.close()
        self.assertGreater(after, before + 50, "dragging the grip up should grow the panel")

    def test_arrow_keys_resize_the_focused_grip(self):
        page = self.page()
        try:
            self.open_panel(page)
            page.focus(GRIP)
            page.keyboard.press("ArrowUp")
            page.keyboard.press("ArrowUp")
            taller = page.eval_on_selector(OPEN_SECTION, "e => e.getBoundingClientRect().height")
            page.keyboard.press("Home")
            reset = page.eval_on_selector(PANEL, "e => e.style.getPropertyValue('--devpanel-h')")
        finally:
            page.close()
        self.assertGreater(taller, 0)
        self.assertEqual(reset, "", "Home clears the height back to the default")

    def test_the_height_is_clamped_and_remembered(self):
        page = self.page()
        try:
            self.open_panel(page)
            # far past the bottom of the window: the panel may not be dragged shut
            box = page.query_selector(GRIP).bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 10000)
            page.mouse.up()
            h = page.eval_on_selector(PANEL, "e => e.style.getPropertyValue('--devpanel-h')")
            stored = page.evaluate("() => localStorage.getItem('al-devpanel-h')")
        finally:
            page.close()
        self.assertEqual(h, "64px", "clamped to the minimum, not dragged shut")
        self.assertEqual(stored, "64px", "the height is remembered")

    def test_the_grip_survives_a_patch(self):
        page = self.page()
        try:
            self.open_panel(page)
            # the demo's Patch button replaces the panel's children, as a server would
            page.click(PATCH)
            page.wait_for_selector(GRIP)
            first = page.eval_on_selector(PANEL, "e => e.firstElementChild.hasAttribute('data-grip')")
        finally:
            page.close()
        self.assertTrue(first, "the grip is restored as the first child after a patch")


if __name__ == "__main__":
    unittest.main()
