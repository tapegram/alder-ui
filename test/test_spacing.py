"""Layout of components in grids and stacks (Playwright; skipped without it).
parity.py compares single components against shadcn; these pin how they sit in
a container: widths, alignment and gaps.

    .venv/bin/python -m unittest test.test_spacing -v
"""
import functools
import http.server
import pathlib
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOL = 0.5  # px, on positions and widths

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


# One server and browser for the whole module (every test class shares them).
_server = _pw = _browser = None


def setUpModule():
    global _server, _pw, _browser
    if sync_playwright is None:
        return
    handler = functools.partial(_Quiet, directory=str(ROOT))
    _server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch()


def tearDownModule():
    if _browser is not None:
        _browser.close()
        _pw.stop()
    if _server is not None:
        _server.shutdown()
        _server.server_close()


def open_page(demo):
    """A 1280x800 page on demo/<demo>; the caller closes it."""
    page = _browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto("http://127.0.0.1:%d/demo/%s" % (_server.server_address[1], demo))
    return page


def box(page, selector):
    """The element's getBoundingClientRect() as {x, y, width, height}."""
    return page.eval_on_selector(selector, """e => {
        const r = e.getBoundingClientRect();
        return {x: r.x, y: r.y, width: r.width, height: r.height};
    }""")


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class ButtonLayoutTest(unittest.TestCase):
    """al-button keeps its natural width in a grid or a column stack; `full` opts in
    to the container's width."""

    @classmethod
    def setUpClass(cls):
        cls.page = open_page("button.html")
        # check.py bans style attributes in demos, so the grid is set here.
        cls.page.eval_on_selector("#grid-form", "f => f.style.cssText = 'display:grid;gap:1rem'")

    @classmethod
    def tearDownClass(cls):
        cls.page.close()

    def near(self, a, b, msg=None):
        self.assertAlmostEqual(a, b, delta=TOL, msg=msg)

    def test_grid_buttons_start_aligned(self):
        form = box(self.page, "#grid-form")
        content_x = form["x"] + self.page.eval_on_selector("#grid-form", """e => {
            const s = getComputedStyle(e);
            return parseFloat(s.borderLeftWidth) + parseFloat(s.paddingLeft);
        }""")
        for id in ("g-bare", "g-button", "g-link"):
            with self.subTest(id=id):
                host = box(self.page, "#" + id)
                self.near(host["x"], content_x)
                self.assertLess(host["width"], form["width"] / 2)

    def test_inner_fills_host(self):
        for id, inner in (("g-button", "button"), ("g-link", "a")):
            with self.subTest(id=id):
                host = box(self.page, "#" + id)
                child = box(self.page, "#%s > %s" % (id, inner))
                self.near(child["x"], host["x"])
                self.near(child["width"], host["width"])

    def test_full_fills_grid(self):
        form = box(self.page, "#grid-form")
        host = box(self.page, "#g-full")
        self.near(host["width"], form["width"])
        self.near(box(self.page, "#g-full > button")["width"], host["width"])

    def test_column_stack(self):
        stack = box(self.page, "#col-stack")
        for id in ("c-bare", "c-button"):
            with self.subTest(id=id):
                host = box(self.page, "#" + id)
                self.near(host["x"], stack["x"])
                self.assertLess(host["width"], stack["width"] / 2)
        self.near(box(self.page, "#c-full")["width"], stack["width"])

    def test_icon_in_grid_is_square(self):
        icon = box(self.page, "#g-icon")
        self.near(icon["width"], 36)
        self.near(icon["height"], 36)

    def test_row_stack_centres(self):
        # The Variants section's row stack: align-items: center must still apply.
        stack = self.page.evaluate_handle("""() => [...document.querySelectorAll("h2")]
            .find(h => h.textContent === "Variants")
            .parentElement.querySelector('al-stack[direction="row"]')""")
        rects = stack.evaluate("""s => [s, ...s.querySelectorAll(":scope > al-button")].map(e => {
            const r = e.getBoundingClientRect();
            return r.y + r.height / 2;
        })""")
        self.assertGreater(len(rects), 1)
        for mid in rects[1:]:
            self.near(mid, rects[0])


if __name__ == "__main__":
    unittest.main()
