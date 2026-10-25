"""A pasted shadcn/tweakcn theme re-themes alder-ui, in light, in dark, and
inside a .light subtree of a .dark page (Playwright; skipped without it).

    .venv/bin/python -m unittest test.test_theme -v
"""
import functools
import http.server
import pathlib
import sys
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "test"))

from colour import normalise_colour  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

PASTED = ":root{--primary:oklch(0.6 0.2 260)} .dark{--primary:oklch(0.7 0.2 140)}"
PRIMARY = "al-button[variant=primary] > button"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class ThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_Quiet, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.url = "http://127.0.0.1:%d/demo/button.html" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.goto(self.url)

    def tearDown(self):
        self.page.close()

    def style(self, selector, prop):
        # al-button transitions background-color: finish any running
        # transition so the computed value is the end state.
        return self.page.eval_on_selector(selector, """(e, p) => {
            document.getAnimations().forEach(a => a.finish());
            return getComputedStyle(e).getPropertyValue(p);
        }""", prop)

    def set_dark(self, on):
        self.page.evaluate("on => document.documentElement.classList.toggle('dark', on)", on)

    def assertColour(self, got, want):
        g, w = normalise_colour(got), normalise_colour(want)
        self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(g, w)), "%s (%s) != %s (%s)" % (got, g, want, w))

    def test_pasted_theme_wins(self):
        self.page.add_style_tag(content=PASTED)
        self.assertColour(self.style(PRIMARY, "background-color"), "oklch(0.6 0.2 260)")
        self.set_dark(True)
        self.assertColour(self.style(PRIMARY, "background-color"), "oklch(0.7 0.2 140)")

    def add_cards(self):
        self.page.evaluate("""() => {
            for (const [id, cls] of [['light-card', 'light'], ['dark-card', '']]) {
                const c = document.createElement('al-card');
                c.id = id;
                if (cls) c.className = cls;
                c.textContent = id;
                document.querySelector('al-page').append(c);
            }
        }""")

    def test_light_subtree_in_dark(self):
        self.add_cards()
        self.set_dark(True)
        # The page really is dark: a card outside the subtree takes .dark's --card.
        self.assertColour(self.style("#dark-card", "background-color"), "oklch(0.205 0 0)")
        self.assertEqual(self.style("#dark-card", "color-scheme"), "dark")
        self.assertColour(self.style("#light-card", "background-color"), "oklch(1 0 0)")
        self.assertEqual(self.style("#light-card", "color-scheme"), "light")

    def test_pasted_theme_in_light_subtree(self):
        # README "Light and dark": a pasted light block written as `:root, .light`
        # reaches a .light subtree of a dark page (Review Focus 2, clause 3) ...
        self.page.add_style_tag(content=":root, .light{--card:oklch(0.6 0.2 260)} .dark{--card:oklch(0.3 0.1 140)}")
        self.add_cards()
        self.set_dark(True)
        self.assertColour(self.style("#dark-card", "background-color"), "oklch(0.3 0.1 140)")
        self.assertColour(self.style("#light-card", "background-color"), "oklch(0.6 0.2 260)")

    def test_bare_root_paste_misses_light_subtree(self):
        # ... and a bare `:root` block does not: the subtree keeps alder-ui's layered
        # .light default (pins the README's warning; if this starts failing, the
        # README sentence is stale).
        self.page.add_style_tag(content=":root{--card:oklch(0.6 0.2 260)} .dark{--card:oklch(0.3 0.1 140)}")
        self.add_cards()
        self.set_dark(True)
        self.assertColour(self.style("#light-card", "background-color"), "oklch(1 0 0)")


if __name__ == "__main__":
    unittest.main()
