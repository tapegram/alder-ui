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


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class LayoutColourTest(unittest.TestCase):
    """Theme-dependent #13 pins (a data-expect value is one string for both themes), and
    the RTL menu origin (parity.py never sets dir=rtl)."""

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

    def page(self, theme="light", rtl=False):
        page = self.browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(self.url, wait_until="load")
        page.evaluate("([dark, rtl]) => { document.documentElement.classList.toggle('dark', dark);"
                      " if (rtl) document.documentElement.dir = 'rtl'; }", [theme == "dark", rtl])
        page.wait_for_timeout(400)  # let the 150ms colour transitions settle
        return page

    def test_selected_row_beats_striped_even_row(self):
        # 13.3: tr[aria-selected] is --muted, not the 50% mix of the striped even row
        for theme in ("light", "dark"):
            page = self.page(theme)
            try:
                got = page.evaluate("""() => {
                    const bg = (e) => getComputedStyle(e).backgroundColor;
                    const probe = document.createElement('i');
                    probe.style.backgroundColor = 'var(--muted)';
                    document.body.append(probe);
                    const muted = bg(probe);
                    const rows = document.querySelectorAll('#parity-table-striped tr');
                    return { muted, selected: bg(rows[1]), odd: bg(rows[0]) };
                }""")
            finally:
                page.close()
            self.assertEqual(got["selected"], got["muted"], theme)
            self.assertNotEqual(got["selected"], got["odd"], theme)

    def test_alert_bare_text_matches_paragraph(self):
        # 13.5: heading + bare text is coloured like heading + p (title and description)
        for theme in ("light", "dark"):
            for variant in ("info", "destructive"):
                page = self.page(theme)
                try:
                    got = page.evaluate("""(v) => {
                        const bare = document.getElementById('parity-alert-bare-' + v);
                        const twin = document.getElementById('parity-alert-p-' + v);
                        const c = (e, ps) => getComputedStyle(e, ps).color;
                        return { bare: c(bare), desc: c(twin.querySelector('p')),
                                 bareTitle: c(bare, '::before'), title: c(twin, '::before') };
                    }""", variant)
                finally:
                    page.close()
                self.assertEqual(got["bare"], got["desc"], (theme, variant))
                self.assertEqual(got["bareTitle"], got["title"], (theme, variant))

    def origin(self, rtl):
        page = self.page(rtl=rtl)
        try:
            page.evaluate("document.getElementById('parity-menu').showPopover()")
            return page.evaluate("""() => {
                const m = document.getElementById('parity-menu');
                return { origin: getComputedStyle(m).transformOrigin, width: m.offsetWidth };
            }""")
        finally:
            page.close()

    def test_menu_origin_ltr(self):
        self.assertEqual(self.origin(False)["origin"].split(" ")[0], "0px")

    def test_menu_origin_rtl(self):
        # 13.8 / D6: the resting origin follows the inline start; a flipped menu cannot
        got = self.origin(True)
        x, y = got["origin"].split(" ")
        self.assertEqual(y, "0px")
        self.assertAlmostEqual(float(x[:-2]), got["width"], delta=1.0)


if __name__ == "__main__":
    unittest.main()
