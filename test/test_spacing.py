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


def open_page(demo, width=1280):
    """A <width>x800 page on demo/<demo>; the caller closes it."""
    page = _browser.new_page(viewport={"width": width, "height": 800})
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


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class DialogFooterButtonTest(unittest.TestCase):
    """The dialog footer stretches plain buttons in its phone column, but an icon
    button stays square and `full` stays full width at every size."""

    def footer(self, width):
        page = open_page("parity.html", width)
        try:
            page.emulate_media(reduced_motion="reduce")  # no zoom-in while measuring
            page.evaluate("""() => {
                const f = document.querySelector('#parity-dialog > [slot=actions]');
                f.insertAdjacentHTML('beforeend',
                    '<al-button id="f-icon" size="icon" variant="outline"><button type="button" aria-label="Add">+</button></al-button>' +
                    '<al-button id="f-full" full><button type="button">Full</button></al-button>');
                document.getElementById('parity-dialog').showModal();
            }""")
            content = page.eval_on_selector("#parity-dialog > [slot=actions]", """f => {
                const s = getComputedStyle(f);
                return f.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
            }""")
            return content, {id: box(page, sel) for id, sel in (
                ("icon", "#f-icon"), ("icon-inner", "#f-icon > button"),
                ("full", "#f-full"), ("full-inner", "#f-full > button"))}
        finally:
            page.close()

    def test_footer(self):
        for width in (400, 1280):
            content, b = self.footer(width)
            with self.subTest(width=width):
                for id in ("icon", "icon-inner"):
                    self.assertAlmostEqual(b[id]["width"], 36, delta=TOL, msg=id)
                    self.assertAlmostEqual(b[id]["height"], 36, delta=TOL, msg=id)
                for id in ("full", "full-inner"):
                    self.assertAlmostEqual(b[id]["width"], content, delta=TOL, msg=id)


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class BadgeLayoutTest(unittest.TestCase):
    """al-badge keeps its own width in a column stack (demo/stack.html's column)."""

    def test_column_stack(self):
        page = open_page("stack.html")
        try:
            stack = box(page, 'al-stack[direction="column"]')
            n = page.eval_on_selector_all('al-stack[direction="column"] > al-badge', "es => es.length")
            self.assertGreater(n, 0)
            for i in range(1, n + 1):
                with self.subTest(badge=i):
                    badge = box(page, 'al-stack[direction="column"] > al-badge:nth-of-type(%d)' % i)
                    self.assertAlmostEqual(badge["x"], stack["x"], delta=TOL)
                    self.assertLess(badge["width"], stack["width"] / 2)
        finally:
            page.close()

@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class DetailListTest(unittest.TestCase):
    """dl is a detail list: two columns from 40rem, stacked below."""

    def first_pair(self, width, sel="#detail"):
        page = open_page("page.html", width)
        try:
            return (box(page, sel + " > dt"), box(page, sel + " > dd"),
                    page.eval_on_selector(sel, """e => {
                        const s = getComputedStyle(e);
                        return {display: s.display, cols: s.gridTemplateColumns,
                                column: s.columnGap, row: s.rowGap};
                    }"""))
        finally:
            page.close()

    def test_dl_two_columns_wide(self):
        dt, dd, s = self.first_pair(1280)
        self.assertEqual(s["display"], "grid")
        self.assertAlmostEqual(dd["y"], dt["y"], delta=TOL)
        self.assertGreater(dd["x"], dt["x"])
        self.assertEqual(s["column"], "24px")
        self.assertEqual(s["row"], "8px")

    def test_dl_stacked_narrow(self):
        dt, dd, s = self.first_pair(600)
        self.assertGreaterEqual(dd["y"], dt["y"] + dt["height"] - TOL)
        self.assertAlmostEqual(dd["x"], dt["x"], delta=TOL)
        self.assertEqual(s["row"], "8px")

    def test_dt_dd_look(self):
        page = open_page("page.html")
        try:
            r = page.evaluate("""() => {
                const color = v => {
                    const p = document.createElement('span');
                    p.style.color = 'var(' + v + ')';
                    document.body.append(p);
                    const c = getComputedStyle(p).color;
                    p.remove();
                    return c;
                };
                const dt = getComputedStyle(document.querySelector('#detail > dt'));
                const dd = getComputedStyle(document.querySelector('#detail > dd'));
                return {dt: [dt.color, dt.fontSize, dt.lineHeight],
                        dd: [dd.color, dd.marginLeft],
                        muted: color('--muted-foreground'), fg: color('--foreground')};
            }""")
        finally:
            page.close()
        self.assertEqual(r["dt"], [r["muted"], "14px", "20px"])
        self.assertEqual(r["dd"], [r["fg"], "0px"])

    def test_dialog_dl_is_grid(self):
        page = open_page("dialog.html")
        try:
            s = page.eval_on_selector("#delete-detail", """e => {
                const s = getComputedStyle(e);
                return {display: s.display, cols: s.gridTemplateColumns.split(' ').length};
            }""")
        finally:
            page.close()
        self.assertEqual(s["display"], "grid")
        self.assertEqual(s["cols"], 2)

    def test_dl_margin_top_follows_flow_rhythm(self):
        page = open_page("page.html")
        try:
            r = page.evaluate("""() => {
                const top = e => getComputedStyle(e).marginTop;
                const dl = document.getElementById('detail');
                const alone = document.createElement('dl');
                dl.parentNode.append(alone);  // last child, after a table, not prose
                return {afterP: top(dl), notAfterProse: top(alone),
                        sides: [getComputedStyle(dl).marginLeft, getComputedStyle(dl).marginBottom]};
            }""")
        finally:
            page.close()
        self.assertEqual(r["afterP"], "24px")
        self.assertEqual(r["notAfterProse"], "0px")
        self.assertEqual(r["sides"], ["0px", "0px"])

    def test_plain_dl_unstyled(self):
        page = open_page("page.html")
        try:
            r = page.evaluate("""() => [
                getComputedStyle(document.querySelector('#plain-detail')).display,
                getComputedStyle(document.querySelector('#plain-detail > dt')).fontSize]""")
        finally:
            page.close()
        # the reset zeroes the browser's 40px dd margin, so assert what the typography would change
        self.assertEqual(r, ["block", "16px"])


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class StackTest(unittest.TestCase):
    """al-stack gaps, and children that draw nothing add no gap."""

    @classmethod
    def setUpClass(cls):
        cls.page = open_page("stack.html")

    @classmethod
    def tearDownClass(cls):
        cls.page.close()

    def test_gap_xl(self):
        gap = self.page.eval_on_selector("#xl-stack", "e => getComputedStyle(e).rowGap")
        self.assertEqual(gap, "40px")

    def test_hidden_children_add_no_gap(self):
        one, two = box(self.page, "#ps-1"), box(self.page, "#ps-2")
        self.assertAlmostEqual(two["y"] - (one["y"] + one["height"]), 24, delta=TOL)


if __name__ == "__main__":
    unittest.main()
