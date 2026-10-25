"""al-popover anchor= (#6): the shim anchors an opening popover to the element its
anchor attribute names, and falls back to the invoker when that id is missing
(Playwright; skipped without it).

    .venv/bin/python -m unittest test.test_anchor -v
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

NO_MOTION = "*, *::before, *::after { transition: none !important; animation: none !important }"
RECT_JS = "(el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom] }"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class AnchorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/demo/popover.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 800})
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto(self.url, wait_until="load")
        self.page.add_style_tag(content=NO_MOTION)

    def tearDown(self):
        self.page.close()

    def rect(self, sel):
        return self.page.eval_on_selector(sel, RECT_JS)

    def open_anchor(self):
        self.page.click("#b-anchor")
        self.page.wait_for_function("document.querySelector('#p-anchor').matches(':popover-open')")

    def assert_centred(self, sel, below=False):
        p, a = self.rect("#p-anchor"), self.rect(sel)
        self.assertGreater(p[2] - p[0], 0, "the popover did not open")
        off = (p[0] + p[2]) / 2 - (a[0] + a[2]) / 2
        self.assertLessEqual(abs(off), 1, "popover is %.1fpx off %s's centre" % (off, sel))
        if below:
            gap = p[1] - a[3]
            self.assertTrue(0 <= gap <= 12, "popover top is %.1fpx below %s's bottom" % (gap, sel))

    def test_anchor_attr(self):
        self.open_anchor()
        self.assert_centred("#b-top", below=True)

    def test_missing_anchor_falls_back(self):
        self.page.eval_on_selector("#p-anchor", "el => el.setAttribute('anchor', 'nope')")
        self.open_anchor()
        self.assert_centred("#b-anchor", below=True)
        self.assertEqual(self.errors, [])

    def test_renamed_anchor_falls_back(self):
        # Review Focus 1: the target's id goes away after an anchored open (a morph
        # renaming or removing it); the next open is back on the invoker.
        self.open_anchor()
        self.assert_centred("#b-top", below=True)
        self.page.eval_on_selector("#p-anchor", "el => el.hidePopover()")
        self.page.eval_on_selector("#b-top", "el => { el.id = 'b-top-renamed' }")
        self.open_anchor()
        self.assert_centred("#b-anchor", below=True)
        self.assertEqual(self.page.eval_on_selector("#p-anchor", "el => el.style.positionAnchor"), "")
        self.assertEqual(self.errors, [])

    def test_existing_anchor_name_kept(self):
        self.page.eval_on_selector("#b-top", "el => { el.style.anchorName = '--author' }")
        self.open_anchor()
        name = self.page.eval_on_selector("#b-top", "el => el.style.anchorName")
        self.assertTrue(name.startswith("--author,"), "anchor-name is %r" % name)
        self.assert_centred("#b-top", below=True)
        self.assertEqual(self.errors, [])

    def test_stylesheet_anchor_name_kept(self):
        # Review Focus 2, from a stylesheet: the shim's inline anchor-name must carry
        # the cascaded --author too, or the inline value would override it.
        self.page.add_style_tag(content="#b-top { anchor-name: --author }"
                                " #probe { position: fixed; position-anchor: --author;"
                                " position-area: top; width: 10px; height: 10px }")
        self.page.evaluate("document.body.append(Object.assign(document.createElement('div'), {id: 'probe'}))")
        self.open_anchor()
        names = self.page.eval_on_selector("#b-top", "el => getComputedStyle(el).anchorName")
        self.assertIn("--author", names)
        self.assertIn("--al-anchor-", names)
        self.assert_centred("#b-top", below=True)
        p, a = self.rect("#probe"), self.rect("#b-top")
        self.assertLessEqual(abs((p[0] + p[2]) / 2 - (a[0] + a[2]) / 2), 1, "probe is off #b-top")
        self.assertLessEqual(abs(p[3] - a[1]), 1, "probe is not above #b-top")
        self.assertEqual(self.errors, [])

    def test_reopen_after_retarget(self):
        self.open_anchor()
        self.page.eval_on_selector("#p-anchor", "el => el.hidePopover()")
        self.page.eval_on_selector("#p-anchor", "el => el.setAttribute('anchor', 'b-left')")
        self.open_anchor()
        self.assert_centred("#b-left", below=True)
        self.assertEqual(self.errors, [])

    def test_menu_anchor_attr(self):
        # al-menu[anchor] too: block-end span-inline-end, so its start edge sits at the
        # target's (plus the 4px margin), not under the invoker.
        self.page.goto(self.url.replace("popover.html", "menu.html"), wait_until="load")
        self.page.add_style_tag(content=NO_MOTION)
        # menu.html fits in 800px with the target near the bottom, where the menu
        # would flip above it; a taller viewport leaves room below.
        self.page.set_viewport_size({"width": 1280, "height": 1200})
        self.page.click("[commandfor=m-anchor]")
        self.page.wait_for_function("document.querySelector('#m-anchor').matches(':popover-open')")
        m, a = self.rect("#m-anchor"), self.rect("#m-target")
        self.assertTrue(0 <= m[0] - a[0] <= 8, "menu left is %.1fpx from the target's" % (m[0] - a[0]))
        self.assertTrue(0 <= m[1] - a[3] <= 12, "menu top is %.1fpx below the target" % (m[1] - a[3]))
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
