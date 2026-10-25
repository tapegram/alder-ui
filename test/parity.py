#!/usr/bin/env python3
"""Computed-style parity between the shadcn reference grid and alder-ui's twin page.

    python3 test/parity.py [--shots] [--strict] [--only <component>]

Serves the repo root on 127.0.0.1, loads ref/dist/index.html (shadcn, the oracle) and
demo/parity.html (alder-ui, the markup Alder emits) in Chromium at 1280x2000, light and
dark (.dark on <html>), and for every marker compares getComputedStyle on spec section
8.3's property list plus the bounding-box size, at rest and in each state the marker's
data-ref-states lists (hover, focus-visible). Prints a Markdown table per component.
Then, for each gating component in CLOSE_CHECKS, opens and closes its overlay on a fresh
twin page with motion on (light and dark) and checks it is display: none and takes no
clicks once the exit transition has run (Review Focus 4).
And for each in ANCHOR_CHECKS, opens it and checks it sits against its anchor.

Markers (both pages):
  data-ref="<component>/<variant>/<state>"   the element whose computed style is read
  data-ref-states="hover focus"              states to drive (must match on both pages)
  data-ref-open                              an overlay; the ref renders it open, the twin's
                                             is opened (showModal / showPopover) one at a
                                             time and closed after its markers are read
Twin-only:
  data-ref-before / data-ref-after / data-ref-backdrop="<marker>"
                                             the marker is the element's ::before / ::after /
                                             ::backdrop (alder-ui draws icons, arrows and
                                             overlays as pseudo-elements)
  data-expect="prop:value; prop:value"       on an element with no data-ref: asserted
                                             against the twin's own computed style (for
                                             things shadcn lacks); its component is the
                                             nearest al-* ancestor-or-self, less "al-"
  data-expect-before="prop:value; ..."       the same, against the element's ::before

test/parity-allow.json:
  pending   components reported but not gating (every one, until its restyle lands)
  map       twin marker -> ref marker, for variants shadcn lacks (alert info -> default)
  allow     [{ref, prop, reason}]: fnmatch globs over the ref (or twin) marker and the
            property; every entry needs a one-line reason

Exit 1 on: a marker-set or state-list mismatch; a ref page whose Geist fonts did not load;
any unallowed diff in a non-pending component (or a twin whose fonts did not load while a
non-pending component exists); with --strict, a non-empty pending list.

Needs Playwright for Python and Chromium (requirements-dev.txt); --shots needs Pillow.
Imports nothing from ref/ and needs no Node.
"""
import argparse
import fnmatch
import functools
import http.server
import json
import pathlib
import re
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOW = ROOT / "test" / "parity-allow.json"
OUT = ROOT / "ref" / "out"
REF_URL = "/ref/dist/index.html"
TWIN_URL = "/demo/parity.html"
VIEWPORT = {"width": 1280, "height": 2000}
THEMES = ("light", "dark")

# Spec section 8.3's property list. `width` is read only for fixed-size controls
# (FIXED_WIDTH); the bounding-box size (box-width, box-height) is read for every
# element marker (not for pseudo-element markers, which have no box of their own).
PROPS = [
    "color", "background-color",
    "border-width", "border-style", "border-color", "border-radius",
    "box-shadow",
    "font-family", "font-size", "font-weight", "line-height", "letter-spacing",
    "padding", "height", "gap", "opacity", "outline", "text-decoration",
]
FIXED_WIDTH = [
    "button/*", "checkbox/*", "badge/*", "pagination/*", "alert/*/icon",
    "tooltip/arrow/*", "toast/*", "dialog/content/*", "dialog/close/*", "popover/content/*",
]
SIZE_PROPS = {"height", "width", "box-width", "box-height"}

NO_MOTION = "*, *::before, *::after, *::backdrop { transition: none !important; animation: none !important }"


# Colour parsing lives in test/colour.py (shared with check.py).
from colour import COLOUR_FUNCS, normalise_colour  # noqa: E402


# ------------------------------------------------------------------------ comparison

_COLOUR_START = re.compile(r"(?<![\w-])(%s)\(" % "|".join(re.escape(f) for f in sorted(COLOUR_FUNCS, key=len, reverse=True)), re.I)
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_WORD_COLOUR = re.compile(r"(?<![\w-])(transparent)(?![\w-])", re.I)
_TOKEN = re.compile(r"rgba\(\d+, \d+, \d+, \d+\)|[-+]?(?:\d*\.\d+|\d+)(?:e[-+]?\d+)?[a-zA-Z%]*|[A-Za-z_-][\w-]*|\S")


def _canon(rgba):
    return "rgba(%d, %d, %d, %d)" % rgba


def _replace_colours(s):
    out, i = [], 0
    while True:
        m = _COLOUR_START.search(s, i)
        if not m:
            out.append(s[i:])
            break
        depth, j = 0, m.end() - 1
        while j < len(s):
            if s[j] == "(":
                depth += 1
            elif s[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(s[i:m.start()])
        expr = s[m.start():j + 1]
        try:
            out.append(_canon(normalise_colour(expr)))
        except ValueError:
            out.append(expr)  # left as written: compared as a string, so a mismatch shows
        i = j + 1
    s = "".join(out)
    s = _HEX.sub(lambda m: _canon(normalise_colour(m.group(0))), s)
    return _WORD_COLOUR.sub(lambda m: _canon(normalise_colour(m.group(1))), s)


def normalise_value(prop, s):
    """A computed value with every colour in it as rgba(r, g, b, a) (8-bit, alpha 0-255),
    whitespace collapsed; font-family lists lose their quotes."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    if prop == "font-family":
        return ", ".join(p.strip().strip("\"'") for p in s.split(","))
    s = _replace_colours(s)
    return re.sub(r"\s*,\s*", ", ", s)


def _same(prop, a, b, tol_px):
    na, nb = normalise_value(prop, a), normalise_value(prop, b)
    if na == nb:
        return True
    ta, tb = _TOKEN.findall(na), _TOKEN.findall(nb)
    if len(ta) != len(tb):
        return False
    tol = tol_px if prop in SIZE_PROPS else 0.01
    for x, y in zip(ta, tb):
        if x == y:
            continue
        if x.startswith("rgba(") and y.startswith("rgba("):
            cx, cy = (tuple(int(v) for v in re.findall(r"\d+", t)) for t in (x, y))
            if any(abs(p - q) > 1 for p, q in zip(cx, cy)):
                return False
            continue
        mx = re.fullmatch(r"([-+]?(?:\d*\.\d+|\d+)(?:e[-+]?\d+)?)([a-zA-Z%]*)", x)
        my = re.fullmatch(r"([-+]?(?:\d*\.\d+|\d+)(?:e[-+]?\d+)?)([a-zA-Z%]*)", y)
        if mx and my and mx.group(2) == my.group(2) and abs(float(mx.group(1)) - float(my.group(1))) <= tol + 1e-9:
            continue
        return False
    return True


def diff(ref, twin, tol_px=0.5):
    """[(prop, ref_value, twin_value)] for each property whose values differ: colours
    within 1 per 8-bit channel are equal, sizes (height, width, box-*) within tol_px,
    other numbers within 0.01."""
    out = []
    for prop in list(ref) + [p for p in twin if p not in ref]:
        a, b = ref.get(prop), twin.get(prop)
        if a is None or b is None:
            if a != b:
                out.append((prop, a, b))
        elif not _same(prop, a, b, tol_px):
            out.append((prop, a, b))
    return out


# ------------------------------------------------------------------------ allow-list

def load_allow(path=ALLOW):
    data = json.loads(pathlib.Path(path).read_text())
    if not isinstance(data, dict) or set(data) - {"pending", "map", "allow"}:
        raise ValueError("%s: keys are pending, map, allow" % path)
    data.setdefault("pending", [])
    data.setdefault("map", {})
    data.setdefault("allow", [])
    if not all(isinstance(c, str) for c in data["pending"]):
        raise ValueError("%s: pending is a list of component names" % path)
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in data["map"].items()):
        raise ValueError("%s: map is {twin marker: ref marker}" % path)
    for i, e in enumerate(data["allow"]):
        for key in ("ref", "prop", "reason"):
            if not isinstance(e.get(key), str) or not e[key].strip():
                raise ValueError("%s: allow[%d] needs a non-empty %r: %r" % (path, i, key, e))
    return data


def target(marker, allow):
    """The ref marker a twin marker is compared against (the allow-list's map applied)."""
    return allow.get("map", {}).get(marker, marker)


def allowed(marker, prop, allow):
    """True when an allow entry's ref glob matches the marker (or its mapped ref marker)
    and its prop glob matches the property."""
    names = {marker, target(marker, allow)}
    return any(
        any(fnmatch.fnmatchcase(n, e["ref"]) for n in names) and fnmatch.fnmatchcase(prop, e["prop"])
        for e in allow.get("allow", [])
    )


def component(marker):
    return marker.split("/", 1)[0]


# --------------------------------------------------------------------------- browser

# Every marker on the page: [marker, pseudo, states, overlay-group index or -1].
INVENTORY_JS = """() => {
  const groups = [...document.querySelectorAll('[data-ref-open]')];
  const out = [];
  for (const [attr, pseudo] of [['data-ref', ''], ['data-ref-before', '::before'],
                                ['data-ref-after', '::after'], ['data-ref-backdrop', '::backdrop']]) {
    for (const el of document.querySelectorAll('[' + attr + ']')) {
      const states = (el.getAttribute('data-ref-states') || '').split(/\\s+/).filter(Boolean);
      const g = el.closest('[data-ref-open]');
      out.push([el.getAttribute(attr), pseudo, pseudo ? [] : states, g ? groups.indexOf(g) : -1]);
    }
  }
  return out;
}"""

# Computed values for the named markers (all when `only` is null).
READ_JS = """([props, fixed, only]) => {
  const out = {};
  for (const [attr, pseudo] of [['data-ref', null], ['data-ref-before', '::before'],
                                ['data-ref-after', '::after'], ['data-ref-backdrop', '::backdrop']]) {
    for (const el of document.querySelectorAll('[' + attr + ']')) {
      const m = el.getAttribute(attr);
      if (only && !only.includes(m)) continue;
      const cs = getComputedStyle(el, pseudo);
      const o = {};
      for (const p of props) o[p] = cs.getPropertyValue(p);
      if (fixed.includes(m)) o['width'] = cs.getPropertyValue('width');
      if (!pseudo) {
        const r = el.getBoundingClientRect();
        o['box-width'] = r.width + 'px';
        o['box-height'] = r.height + 'px';
      }
      out[m] = o;
    }
  }
  return out;
}"""

EXPECT_JS = """() => {
  const out = [];
  const seen = {};
  for (const el of document.querySelectorAll('[data-expect]:not([data-ref]), [data-expect-before]:not([data-ref])')) {
    let host = el;
    while (host && !host.localName.startsWith('al-')) host = host.parentElement;
    const comp = host ? host.localName.slice(3) : 'page';
    const n = seen[comp] = (seen[comp] || 0) + 1;
    for (const [attr, pseudo] of [['data-expect', null], ['data-expect-before', '::before']]) {
      if (!el.hasAttribute(attr)) continue;
      const want = {};
      for (const decl of el.getAttribute(attr).split(';')) {
        const i = decl.indexOf(':');
        if (i > 0) want[decl.slice(0, i).trim()] = decl.slice(i + 1).trim();
      }
      const cs = getComputedStyle(el, pseudo);
      const got = {};
      for (const p of Object.keys(want)) got[p] = cs.getPropertyValue(p);
      out.push([comp + '/expect/' + el.localName + '-' + n + (pseudo || ''), want, got]);
    }
  }
  return out;
}"""

FONTS_JS = """async () => {
  await document.fonts.ready;
  const loaded = (fam) => [...document.fonts].some(
    (f) => f.family.replace(/["']/g, '') === fam && f.status === 'loaded');
  // fonts.check() is also true when no face of that family exists at all (it falls back to
  // local fonts), so a loaded FontFace of the family is required too.
  return {
    geist: document.fonts.check('500 14px Geist') && loaded('Geist'),
    mono: document.fonts.check('14px "Geist Mono"') && loaded('Geist Mono'),
  };
}"""

OPEN_JS = """(i) => {
  const el = document.querySelectorAll('[data-ref-open]')[i];
  // The ref keeps focus where it was on open (onOpenAutoFocus prevented), so the twin's
  // autofocused close button is blurred: rest is read unfocused.
  if (el instanceof HTMLDialogElement) { if (!el.open) { el.showModal(); document.activeElement.blur(); } }
  else if (el.hasAttribute('popover')) { if (!el.matches(':popover-open')) el.showPopover(); }
}"""

CLOSE_JS = """(i) => {
  const all = [...document.querySelectorAll('[data-ref-open]')];
  for (const el of (i === null ? all : [all[i]])) {
    if (el instanceof HTMLDialogElement) { if (el.open) el.close(); }
    else if (el.hasAttribute('popover') && el.matches(':popover-open')) el.hidePopover();
  }
}"""

BLUR_IN_JS = """(i) => {
  const el = document.querySelectorAll('[data-ref-open]')[i];
  if (el.contains(document.activeElement)) document.activeElement.blur();
}"""

SETTLE_JS = "() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(_Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


class Page:
    """One of the two pages, loaded and settled, with its marker inventory."""

    def __init__(self, browser, base, url, name):
        self.name = name
        self.page = browser.new_page(viewport=VIEWPORT, color_scheme="light")
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto(base + url, wait_until="load")
        self.page.wait_for_selector("html[data-ref-ready]", state="attached", timeout=20000)
        self.page.add_style_tag(content=NO_MOTION)
        if name == "ref":  # sonner mounts its toasts a frame after ready
            self.page.wait_for_function(
                "() => [...document.querySelectorAll('[data-sonner-toast]')].every((t) => t.dataset.mounted === 'true')")
        self.settle()
        self.fonts = self.page.evaluate(FONTS_JS)
        self.inventory = {}
        for marker, pseudo, states, group in self.page.evaluate(INVENTORY_JS):
            if marker in self.inventory:
                raise SystemExit("parity: %s has marker %r twice" % (name, marker))
            self.inventory[marker] = {"pseudo": pseudo, "states": states, "group": group}

    def settle(self):
        self.page.evaluate(SETTLE_JS)

    def theme(self, theme):
        self.page.evaluate("(on) => document.documentElement.classList.toggle('dark', on)", theme == "dark")
        self.settle()

    def read(self, markers):
        fixed = [m for m in markers if any(fnmatch.fnmatchcase(m, g) for g in FIXED_WIDTH)]
        return self.page.evaluate(READ_JS, [PROPS, fixed, list(markers)])

    def locator(self, marker):
        return self.page.locator('[data-ref="%s"]' % marker)

    def drive(self, marker, state, fixed_as):
        """Read `marker` in `state` (hover / focus); fixed_as names the FIXED_WIDTH glob key."""
        loc = self.locator(marker)
        if state == "hover":
            loc.hover()
            self.settle()
            vals = self.page.evaluate(READ_JS, [PROPS, self._fixed(fixed_as, marker), [marker]])[marker]
            self.page.mouse.move(0, 0)
        elif state == "focus":
            self.page.keyboard.press("Shift")
            loc.focus()
            self.settle()
            if not loc.evaluate("(el) => el.matches(':focus-visible')"):
                raise SystemExit("parity: %s %s does not match :focus-visible after focus()" % (self.name, marker))
            vals = self.page.evaluate(READ_JS, [PROPS, self._fixed(fixed_as, marker), [marker]])[marker]
            loc.evaluate("(el) => el.blur()")
        else:
            raise SystemExit("parity: unknown state %r on %s" % (state, marker))
        self.settle()
        return vals

    @staticmethod
    def _fixed(fixed_as, marker):
        return [marker] if any(fnmatch.fnmatchcase(fixed_as, g) for g in FIXED_WIDTH) else []

    def open(self, group):
        self.page.evaluate(OPEN_JS, group)
        self.settle()
        # al-menu.js focuses the first item on the (async) toggle event; rest is unfocused.
        self.page.evaluate(BLUR_IN_JS, group)
        self.settle()

    def close(self, group=None):
        self.page.evaluate(CLOSE_JS, group)
        self.settle()


# ----------------------------------------------------------------------- close checks

# Review Focus 4: with motion on, an overlay must be gone once its exit transition has run.
# Each entry: (component, label, selector, open js, close, shim). The js take the element;
# open js may return another element, which is then the one checked (a toast it adds to
# the region). close is js, a Python callable (page, element) for a real pointer or key,
# or a number: the overlay closes itself after that many ms (a toast's timeout). shim=True
# deletes HTMLButtonElement.prototype.commandForElement before load, so
# components/al-shim.js installs its polyfill. Chromium's native invoker handling still
# runs on click (R20), so these runs do not isolate the shim: they show that the close and
# its CSS exit path still work with the shim loaded alongside the native path (which is
# what Review Focus 4 pins), and they use idempotent commands because a toggle would run
# twice and cancel out. Their labels say what was done, not "shim".
_SHOW_MODAL = "(el) => el.showModal()"
_SHOW_POPOVER = "(el) => el.showPopover()"
_INVOKE = "(el) => document.querySelector('[commandfor=\"' + el.id + '\"][command=\"%s\"]').click()"
_POPOVERTARGET = "(el) => document.querySelector('[popovertarget=\"' + el.id + '\"]').click()"
_TIP_TRIGGER = "document.getElementById(el.getAttribute('for'))"
_ADD_TOAST = ("(el) => { const t = document.createElement('al-toast'); t.setAttribute('timeout', '100');"
              " t.textContent = 'Timed toast'; el.appendChild(t); %s return t }")
CLOSE_CHECKS = [
    ("dialog", "close()", "#parity-dialog", _SHOW_MODAL, "(el) => el.close()", False),
    ("dialog", "close button", "#parity-dialog", _SHOW_MODAL,
     "(el) => el.querySelector(':scope > form[method=dialog] > button').click()", False),
    ("dialog", "command=close", "#parity-dialog", _INVOKE % "show-modal", _INVOKE % "close", False),
    ("dialog", "command=close, commandForElement deleted", "#parity-dialog", _INVOKE % "show-modal", _INVOKE % "close", True),
    ("dialog", ":target", "#parity-dialog", "(el) => { location.hash = el.id }", "() => { location.hash = '' }", False),
    ("popover", "hidePopover()", "#parity-popover", _SHOW_POPOVER, "(el) => el.hidePopover()", False),
    ("popover", "light dismiss", "#parity-popover", _POPOVERTARGET, lambda page, el: page.mouse.click(2, 2), False),
    ("popover", "command=hide-popover, commandForElement deleted", "#parity-popover", _SHOW_POPOVER, _INVOKE % "hide-popover", True),
    ("menu", "select an item", "#parity-menu", _SHOW_POPOVER,
     "(el) => el.querySelector(':scope > button').click()", False),
    ("tooltip", "blur", "al-tooltip[for=parity-tooltip-trigger]",
     "(el) => %s.focus()" % _TIP_TRIGGER, "(el) => %s.blur()" % _TIP_TRIGGER, False),
    ("tooltip", "pointerleave", "al-tooltip[for=parity-tooltip-trigger]",
     "(el) => %s.dispatchEvent(new PointerEvent('pointerenter'))" % _TIP_TRIGGER,
     "(el) => %s.dispatchEvent(new PointerEvent('pointerleave'))" % _TIP_TRIGGER, False),
    ("toast", "timeout", "#parity-toasts-timeout", _ADD_TOAST % "", 100, False),
    # An app's infinite animation on the toast must not hold up its removal (R24).
    ("toast", "timeout, infinite animation", "#parity-toasts-timeout",
     _ADD_TOAST % "t.animate([{ outlineColor: 'red' }, { outlineColor: 'blue' }], { duration: 1000, iterations: Infinity });",
     100, False),
]
CLOSE_WAIT_MS = 300  # longer than the 200ms dialog / 150ms overlay exit transitions

OPENED_JS = """(el) => {
  const r = el.getBoundingClientRect();
  return { opened: getComputedStyle(el).display !== 'none' && r.width > 0 && r.height > 0,
           x: r.left + r.width / 2, y: r.top + r.height / 2 };
}"""

CLOSED_JS = """([el, x, y]) => {
  if (!el.isConnected) return { connected: false, display: '', hit: false };
  const at = document.elementFromPoint(x, y);
  return { connected: true, display: getComputedStyle(el).display, hit: !!at && el.contains(at) };
}"""


def close_problems(st):
    """What is wrong with an overlay measured CLOSE_WAIT_MS after closing: st holds
    opened (it was shown before closing), connected (el.isConnected), display (computed)
    and hit (elementFromPoint at its open centre lands inside it). A disconnected node is
    closed (R19)."""
    if not st["opened"]:
        return ["did not open, so its closing proves nothing"]
    if not st["connected"]:
        return []
    out = []
    if st["display"] != "none":
        out.append("display is %r after the exit transition, not 'none'" % st["display"])
    if st["hit"]:
        out.append("still takes clicks at its centre")
    return out


def check_closes(page, selector, close_js, open_js=_SHOW_MODAL):
    """Open the overlay `selector` names (or the element open_js returns), close it with
    close_js (js, a callable taking the page and the element, or the ms after which it
    closes itself), wait out the exit transition, and return close_problems() for it. The
    page must have motion on."""
    el = page.query_selector(selector)
    if el is None:
        return ["%s is not on the page" % selector]
    el = el.evaluate_handle(open_js).as_element() or el
    if isinstance(close_js, (int, float)):
        # It closes itself: check it opened at once, then wait out its timeout as well.
        page.evaluate(SETTLE_JS)
        opened = el.evaluate(OPENED_JS)
        page.wait_for_timeout(close_js)
    else:
        page.wait_for_timeout(CLOSE_WAIT_MS)
        opened = el.evaluate(OPENED_JS)
        if callable(close_js):
            close_js(page, el)
        else:
            el.evaluate(close_js)
    page.wait_for_timeout(CLOSE_WAIT_MS)
    st = page.evaluate(CLOSED_JS, [el, opened["x"], opened["y"]])
    st["opened"] = opened["opened"]
    return close_problems(st)


def run_close_checks(browser, base, comps):
    """Every CLOSE_CHECKS entry whose component is in comps, light and dark, each on a fresh
    twin page with motion on. Returns failure lines."""
    fails = []
    for comp, label, selector, open_js, close_js, shim in CLOSE_CHECKS:
        if comp not in comps:
            continue
        for theme in THEMES:
            page = browser.new_page(viewport=VIEWPORT, color_scheme="light")
            try:
                if shim:
                    page.add_init_script("delete HTMLButtonElement.prototype.commandForElement")
                page.goto(base + TWIN_URL, wait_until="load")
                page.wait_for_selector("html[data-ref-ready]", state="attached", timeout=20000)
                page.evaluate("(on) => document.documentElement.classList.toggle('dark', on)", theme == "dark")
                if shim and page.evaluate("() => 'commandForElement' in HTMLButtonElement.prototype"):
                    fails.append("%s %s (%s): commandForElement is still defined after deleting it"
                                 % (comp, label, theme))
                    continue
                probs = check_closes(page, selector, close_js, open_js)
            finally:
                page.close()
            fails.extend("%s %s %s (%s): %s" % (comp, selector, label, theme, p) for p in probs)
            print("close: %s %s via %s (%s): %s" % (comp, selector, label, theme, "ok" if not probs else "FAIL"))
    return fails


# An anchored overlay must sit against its anchor, not wherever position-area lands with
# none (the viewport). Each entry: (component, label, selector, anchor selector, open js,
# side). The overlay is opened with motion off on a fresh twin page and its rect is checked.
ANCHOR_CHECKS = [
    ("tooltip", "hover", "al-tooltip[for=parity-tooltip-trigger]", "#parity-tooltip-trigger",
     "(el) => %s.dispatchEvent(new PointerEvent('pointerenter'))" % _TIP_TRIGGER, "above"),
    ("popover", "anchor attr", "#parity-popover-elsewhere", "#parity-anchor-target",
     "(el) => el.showPopover()", "below"),
]
ANCHOR_GAP_PX = 12  # the tooltip's 5px offset, with room; an unanchored one is far off

RECT_JS = "(el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom] }"


def anchor_problems(rect, anchor, side):
    """What is wrong with an overlay's rect [left, top, right, bottom] against its anchor's:
    it must be on `side` ("above"/"below") within ANCHOR_GAP_PX and centred on it (1px)."""
    if rect[2] - rect[0] <= 0:
        return ["has no size, so it did not open"]
    gap = anchor[1] - rect[3] if side == "above" else rect[1] - anchor[3]
    out = []
    if not 0 <= gap <= ANCHOR_GAP_PX:
        out.append("is %spx from the anchor's %s edge, not 0-%dpx %s it"
                   % (round(gap, 1), "top" if side == "above" else "bottom", ANCHOR_GAP_PX, side))
    off = (rect[0] + rect[2]) / 2 - (anchor[0] + anchor[2]) / 2
    if abs(off) > 1:
        out.append("is %spx off the anchor's centre" % round(off, 1))
    return out


def run_anchor_checks(browser, base, comps):
    """Every ANCHOR_CHECKS entry whose component is in comps, light theme only (placement
    does not depend on the theme). Returns failure lines."""
    fails = []
    for comp, label, selector, anchor_sel, open_js, side in ANCHOR_CHECKS:
        if comp not in comps:
            continue
        page = browser.new_page(viewport=VIEWPORT, color_scheme="light")
        try:
            page.goto(base + TWIN_URL, wait_until="load")
            page.wait_for_selector("html[data-ref-ready]", state="attached", timeout=20000)
            page.add_style_tag(content=NO_MOTION)
            el, anchor = page.query_selector(selector), page.query_selector(anchor_sel)
            # Centred in the viewport, so position-try has room on either side and
            # flips only when the overlay really is placed on the wrong side.
            anchor.evaluate("(a) => a.scrollIntoView({ block: 'center' })")
            el.evaluate(open_js)
            page.evaluate(SETTLE_JS)
            probs = anchor_problems(el.evaluate(RECT_JS), anchor.evaluate(RECT_JS), side)
        finally:
            page.close()
        fails.extend("%s %s %s: %s" % (comp, selector, label, p) for p in probs)
        print("anchor: %s %s via %s: %s" % (comp, selector, label, "ok" if not probs else "FAIL"))
    return fails


def collect(ref, twin, allow, only):
    """Rows of (component, twin marker, theme, state, prop, ref value, twin value)."""
    rows, expects = [], []
    twin_markers = sorted(m for m in twin.inventory if only is None or component(target(m, allow)) == only)
    groups = sorted({twin.inventory[m]["group"] for m in twin_markers} - {-1})
    for theme in THEMES:
        ref.theme(theme)
        twin.theme(theme)
        twin.close()  # every overlay shut; then opened one at a time
        want_ref = sorted({target(m, allow) for m in twin_markers})
        # Ref: overlays are rendered open, so everything is read at once. The twin reads
        # with its fixed-width rule keyed by the ref marker.
        ref_vals = ref.read(want_ref)
        twin_vals = {}
        rest = [m for m in twin_markers if twin.inventory[m]["group"] == -1]
        twin_vals.update(_read_as(twin, rest, allow))
        for g in groups:
            twin.open(g)
            twin_vals.update(_read_as(twin, [m for m in twin_markers if twin.inventory[m]["group"] == g], allow))
            twin.close(g)
        for m in twin_markers:
            t = target(m, allow)
            for prop, a, b in diff(ref_vals[t], twin_vals[m]):
                rows.append((component(t), m, theme, "rest", prop, a, b))
        ref_state = {}
        for m in twin_markers:
            t = target(m, allow)
            g = twin.inventory[m]["group"]
            for state in twin.inventory[m]["states"]:
                if (t, state) not in ref_state:
                    ref_state[(t, state)] = ref.drive(t, state, t)
                if g != -1:  # a marker inside an overlay is driven with its overlay open
                    twin.open(g)
                got = twin.drive(m, state, t)
                if g != -1:
                    twin.close(g)
                for prop, a, b in diff(ref_state[(t, state)], got):
                    rows.append((component(t), m, theme, state, prop, a, b))
        for label, want, got in twin.page.evaluate(EXPECT_JS):
            if only is not None and component(label) != only:
                continue
            expects.append(label)
            for prop, a, b in diff(want, got):
                rows.append((component(label), label, theme, "expect", prop, a, b))
    return rows, expects


def _read_as(twin, markers, allow):
    """Twin values, with `width` read where the mapped ref marker is fixed-size."""
    if not markers:
        return {}
    fixed = [m for m in markers if any(fnmatch.fnmatchcase(target(m, allow), g) for g in FIXED_WIDTH)]
    return twin.page.evaluate(READ_JS, [PROPS, fixed, markers])


def check_sets(ref, twin, allow):
    """Marker-set and state-list mismatches (always fatal)."""
    problems = []
    mapped = {}
    for m in twin.inventory:
        mapped.setdefault(target(m, allow), []).append(m)
    for t in sorted(set(ref.inventory) - set(mapped)):
        problems.append("marker %s is on the ref page only" % t)
    for t in sorted(set(mapped) - set(ref.inventory)):
        problems.append("marker %s is on the twin page only (%s)" % (t, ", ".join(mapped[t])))
    for t in sorted(set(mapped) & set(ref.inventory)):
        for m in mapped[t]:
            if ref.inventory[t]["states"] != twin.inventory[m]["states"]:
                problems.append("states differ for %s: ref %s, twin %s %s" % (
                    m, ref.inventory[t]["states"], m, twin.inventory[m]["states"]))
    return problems


# ----------------------------------------------------------------------------- shots

SHOT_JS = """([markers, attr]) => {
  let box = null;
  for (const m of markers) {
    const el = document.querySelector('[' + attr + '="' + m + '"]') ||
      document.querySelector('[data-ref-before="' + m + '"],[data-ref-after="' + m + '"],[data-ref-backdrop="' + m + '"]');
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    box = box ? { l: Math.min(box.l, r.left), t: Math.min(box.t, r.top), r: Math.max(box.r, r.right), b: Math.max(box.b, r.bottom) }
              : { l: r.left, t: r.top, r: r.right, b: r.bottom };
  }
  return box;
}"""


def _clip(page, markers):
    box = page.evaluate(SHOT_JS, [markers, "data-ref"])
    if not box:
        return None
    page.evaluate("(y) => window.scrollBy(0, y)", box["t"] - 8)
    box = page.evaluate(SHOT_JS, [markers, "data-ref"])
    x, y = max(0, box["l"] - 8), max(0, box["t"] - 8)
    w = min(VIEWPORT["width"], box["r"] + 8) - x
    h = min(VIEWPORT["height"], box["b"] + 8) - y
    return {"x": x, "y": y, "width": max(1, w), "height": max(1, h)}


def _image(page, markers):
    import io
    from PIL import Image
    clip = _clip(page, markers)
    if clip is None:
        return Image.new("RGB", (1, 1), "white")
    return Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")


def shots(ref, twin, allow, only):
    from PIL import Image, ImageChops
    OUT.mkdir(parents=True, exist_ok=True)
    by_comp = {}
    for m in twin.inventory:
        by_comp.setdefault(component(target(m, allow)), []).append(m)
    written = []
    for theme in THEMES:
        ref.theme(theme)
        twin.theme(theme)
        for comp, markers in sorted(by_comp.items()):
            if only is not None and comp != only:
                continue
            twin.close()
            for g in sorted({twin.inventory[m]["group"] for m in markers} - {-1}):
                twin.open(g)
            a = _image(ref.page, sorted({target(m, allow) for m in markers}))
            b = _image(twin.page, markers)
            twin.close()
            w, h = max(a.width, b.width), max(a.height, b.height)
            pa, pb = (Image.new("RGB", (w, h), "white") for _ in range(2))
            pa.paste(a, (0, 0))
            pb.paste(b, (0, 0))
            mask = ImageChops.difference(pa, pb).convert("L").point(lambda v: 255 if v > 16 else 0)
            d = Image.composite(Image.new("RGB", (w, h), (220, 0, 0)), Image.new("RGB", (w, h), "white"), mask)
            tri = Image.new("RGB", (w * 3 + 16, h), (128, 128, 128))
            for i, im in enumerate((pa, pb, d)):
                tri.paste(im, (i * (w + 8), 0))
            path = OUT / ("%s-%s.png" % (comp, theme))
            tri.save(path)
            written.append(path)
    return written


# ---------------------------------------------------------------------------- report

def report(rows, allow, comps, expects):
    pending = set(allow["pending"])
    shown = [r for r in rows if not allowed(r[1], r[4], allow)]
    n_allowed = len(rows) - len(shown)
    failing = sorted({r[0] for r in shown if r[0] not in pending})
    lines = []
    lines.append("## failing: %s" % (", ".join(failing) if failing else "none"))
    lines.append("## pending: %s" % (", ".join(c for c in comps if c in pending) or "none"))
    lines.append("## clean: %s" % (", ".join(c for c in comps if c not in pending and c not in failing) or "none"))
    lines.append("(%d differing values, %d allowed by test/parity-allow.json, %d data-expect checks)"
                 % (len(rows), n_allowed, len(expects)))
    # Components known only from data-expect rows (stack, page) gate too: show their rows.
    for comp in list(comps) + sorted({r[0] for r in shown} - set(comps)):
        mine = [r for r in shown if r[0] == comp]
        if not mine:
            continue
        lines.append("")
        lines.append("### %s%s (%d)" % (comp, " (pending)" if comp in pending else "", len(mine)))
        lines.append("")
        lines.append("| marker | theme | state | prop | ref | twin |")
        lines.append("|---|---|---|---|---|---|")
        for _, m, theme, state, prop, a, b in mine:
            lines.append("| %s | %s | %s | %s | `%s` | `%s` |" % (m, theme, state, prop, a, b))
    return "\n".join(lines), failing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--shots", action="store_true", help="also write ref/out/<component>-<theme>.png triptychs")
    ap.add_argument("--strict", action="store_true", help="also fail while any component is pending")
    ap.add_argument("--only", metavar="COMPONENT", help="compare one component")
    args = ap.parse_args(argv)
    allow = load_allow(ALLOW)
    from playwright.sync_api import sync_playwright

    httpd = serve()
    base = "http://127.0.0.1:%d" % httpd.server_address[1]
    status = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                ref = Page(browser, base, REF_URL, "ref")
                twin = Page(browser, base, TWIN_URL, "twin")
                print("# parity: ref %d markers, twin %d markers, themes %s"
                      % (len(ref.inventory), len(twin.inventory), "/".join(THEMES)))
                for p in (ref, twin):
                    if p.errors:
                        print("parity: %s page errors: %s" % (p.name, p.errors))
                        status = 1
                problems = check_sets(ref, twin, allow)
                for pr in problems:
                    print("parity: FAIL %s" % pr)
                if problems:
                    return 1
                if not (ref.fonts["geist"] and ref.fonts["mono"]):
                    print("parity: FAIL the ref page's Geist fonts did not load: %s" % ref.fonts)
                    return 1
                comps = sorted({component(target(m, allow)) for m in twin.inventory}
                               | {component(m) for m in ref.inventory})
                if args.only and args.only not in comps:
                    print("parity: no component %r (have %s)" % (args.only, ", ".join(comps)))
                    return 2
                twin_fonts = twin.fonts["geist"] and twin.fonts["mono"]
                gating = [c for c in comps if c not in allow["pending"] and (args.only in (None, c))]
                if not twin_fonts:
                    if gating:
                        print("parity: FAIL the twin page's Geist fonts did not load (%s), and these "
                              "components gate: %s" % (twin.fonts, ", ".join(gating)))
                        status = 1
                    else:
                        print("parity: WARNING the twin page's Geist fonts did not load (%s); every "
                              "compared component is pending, so this does not gate yet" % twin.fonts)
                rows, expects = collect(ref, twin, allow, args.only)
                text, failing = report(rows, allow, [c for c in comps if args.only in (None, c)], expects)
                print(text)
                if failing:
                    status = 1
                close_fails = run_close_checks(browser, base, gating)
                for f in close_fails:
                    print("parity: FAIL close %s" % f)
                anchor_fails = run_anchor_checks(browser, base, gating)
                for f in anchor_fails:
                    print("parity: FAIL anchor %s" % f)
                if close_fails or anchor_fails:
                    status = 1
                if args.strict and allow["pending"]:
                    print("parity: --strict and pending is not empty: %s" % ", ".join(allow["pending"]))
                    status = 1
                if args.shots:
                    for path in shots(ref, twin, allow, args.only):
                        print("shot: %s" % path.relative_to(ROOT))
            finally:
                browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    return status


if __name__ == "__main__":
    sys.exit(main())
