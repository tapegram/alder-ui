#!/usr/bin/env python3
"""alder-ui's tests. Python 3 standard library only.

    python3 test/check.py           # run every check; exit 1 on any failure
    python3 test/check.py --table   # also print the contrast table

Checks:
  manifest     the elements, their attributes and slots are exactly the
               published API (no rename, no drop); version looks like a tag
  css          every selector names a declared element, attribute, value and
               slot (and every class is al- prefixed, or one of the classes
               Alder renders: errors, help, _alder-click); every element, attribute,
               value and slot in the manifest is styled
  tokens-only  no hard-coded colours, lengths or fonts in components/; every
               var(--x) is defined
  tokens       shadcn's names exist in light and dark; the two dark blocks agree
  contrast     WCAG AA for each text pairing (4.5:1) and control edge (3:1),
               light and dark, computed from tokens.css; al-button's pairs
               (resting and hover, color-mix evaluated in sRGB) are derived
               from its CSS
  demos        each page links ../al.css, uses only declared attributes, values
               and slots, shows every variant/size/state of its element;
               index.html links every page
  scripts      every components/*.js is in the manifest, exists, is at most 60
               lines; the interactive demos have a <!-- no-js --> section
  bundle       al.css and al.js equal scripts/build.py's output
"""
import colorsys
import html.parser
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

FAILURES = []


def fail(section, msg):
    FAILURES.append("%s: %s" % (section, msg))


# ---------------------------------------------------------------- manifest

# The API Alder's checker was built against. Names, attribute types and slots
# may not change; attributes may only be added (listed in ADDED, in their
# manifest positions after the original ones).
API = {
    "al-button": ([("variant", '"primary" | "secondary" | "outline" | "ghost" | "destructive"'), ("size", '"sm" | "md" | "lg"'), ("disabled", "boolean"), ("type", '"button" | "submit"')], [""]),
    "al-input": ([("label", "string"), ("placeholder", "string"), ("disabled", "boolean"), ("invalid", "boolean"), ("help", "string")], []),
    "al-textarea": ([("label", "string"), ("placeholder", "string"), ("disabled", "boolean"), ("invalid", "boolean"), ("help", "string")], []),
    "al-select": ([("label", "string"), ("disabled", "boolean"), ("invalid", "boolean")], []),
    "al-checkbox": ([("label", "string"), ("disabled", "boolean")], []),
    "al-table": ([("striped", "boolean"), ("dense", "boolean")], [""]),
    "al-card": ([], ["header", "", "footer", "actions"]),
    "al-badge": ([("variant", '"default" | "secondary" | "outline" | "destructive"')], [""]),
    # al-alert's `title` became `heading` in v0.1.1 by ruling (the global
    # title attribute drew a tooltip and doubled the accessible name).
    "al-alert": ([("variant", '"info" | "success" | "warning" | "destructive"'), ("heading", "string"), ("dismissible", "boolean")], [""]),
    "al-pagination": ([("page", "number"), ("pages", "number")], ["prev", "", "next"]),
    "al-stack": ([("gap", '"sm" | "md" | "lg"'), ("direction", '"row" | "column"')], [""]),
    "al-page": ([("width", '"narrow" | "normal" | "wide"')], [""]),
}
# v0.2.0, the interactive tier (added per element below)
API.update({
})
ADDED = {
    "al-select": [("help", "string")],
    "al-checkbox": [("invalid", "boolean"), ("help", "string")],
}

# Attributes the stylesheet deliberately does not draw: the framework copies
# them onto the native control, or renders them as markup.
NOT_STYLED = {
    ("al-button", "type"): "selects the native button's type; no look",
    ("al-input", "label"): "rendered as a real <label>",
    ("al-input", "placeholder"): "copied onto the <input>",
    ("al-textarea", "label"): "rendered as a real <label>",
    ("al-textarea", "placeholder"): "copied onto the <textarea>",
    ("al-select", "label"): "rendered as a real <label>",
    ("al-checkbox", "label"): "rendered as a real <label>",
}

# Attributes any element may carry (Alder's escape list, less its own
# message/form attributes, which never reach the HTML).
GLOBAL_ATTRS = {"id", "class", "style", "slot", "hidden", "title", "lang", "dir", "tabindex", "role",
                "popover", "popovertarget", "commandfor", "command"}

# Elements that live in another element's stylesheet and demo page: the
# interactive tier's parts (al-tabs holds al-tab and al-panel; al-toast holds
# its al-toasts region).
SUB = {"al-tab": "al-tabs", "al-panel": "al-tabs", "al-toasts": "al-toast"}
MAX_SCRIPT_LINES = 60


def is_global(name):
    return name in GLOBAL_ATTRS or name.startswith("data-") or name.startswith("aria-")


def union_values(type_text):
    vals = re.findall(r'"([^"]*)"', type_text)
    return vals if vals and re.fullmatch(r'\s*"[^"]*"(\s*\|\s*"[^"]*")*\s*', type_text) else None


def load_manifest():
    m = json.loads((ROOT / "custom-elements.json").read_text())
    els = {}
    for mod in m.get("modules", []):
        for d in mod.get("declarations", []):
            if d.get("customElement"):
                d["_path"] = mod["path"]
                els[d["tagName"]] = d
    return m, els


def check_manifest(m, els):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", m.get("version", "")):
        fail("manifest", "version %r is not a tag like v0.1.0" % m.get("version"))
    if m.get("schemaVersion") != "1.0.0":
        fail("manifest", "schemaVersion must be 1.0.0")
    if sorted(els) != sorted(API):
        fail("manifest", "elements %s, want %s" % (sorted(els), sorted(API)))
    check_scripts(m)
    for tag, (attrs, slots) in API.items():
        d = els.get(tag)
        if not d:
            continue
        if d["_path"] != "components/%s.css" % SUB.get(tag, tag):
            fail("manifest", "%s path %s" % (tag, d["_path"]))
        if not (ROOT / d["_path"]).exists():
            fail("manifest", "%s: %s missing" % (tag, d["_path"]))
        got = [(a["name"], a["type"]["text"]) for a in d.get("attributes", [])]
        want = attrs + ADDED.get(tag, [])
        if got != want:
            fail("manifest", "%s attributes %s, want %s" % (tag, got, want))
        if [s["name"] for s in d.get("slots", [])] != slots:
            fail("manifest", "%s slots changed" % tag)
        if not d.get("description"):
            fail("manifest", "%s has no description" % tag)
        for a in d.get("attributes", []):
            if not a.get("description"):
                fail("manifest", "%s[%s] has no description" % (tag, a["name"]))
            if a["type"]["text"] == "boolean":
                if a.get("default") != "false":
                    fail("manifest", "%s[%s] is boolean; its default must be false" % (tag, a["name"]))
            elif "default" in a:
                vals = union_values(a["type"]["text"])
                if vals is None or json.loads(a["default"]) not in vals:
                    fail("manifest", "%s[%s] default %s not in its type" % (tag, a["name"], a["default"]))


# ---------------------------------------------------------------- css

def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def strip_strings(css):
    return re.sub(r'"[^"]*"|\'[^\']*\'', '""', css)


def rules(css):
    """Yield (selector, body) for every style rule, descending into @media."""
    css = strip_comments(css)
    i, depth, start, stack = 0, 0, 0, []
    out = []
    while i < len(css):
        c = css[i]
        if c == "{":
            head = css[start:i].strip()
            stack.append(head)
            start = i + 1
        elif c == "}":
            head = stack.pop()
            body = css[start:i]
            if not head.startswith("@"):
                out.append((head, body))
            start = i + 1
        elif c == ";" and stack and stack[-1].startswith("@"):
            start = i + 1
        i += 1
    return out


def split_top(s, sep=","):
    parts, depth, cur = [], 0, ""
    for c in s:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if c == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += c
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


ATTR_RE = re.compile(r'\[\s*([a-zA-Z_-][\w-]*)\s*(?:([~|^$*]?=)\s*"?([^"\]]*)"?)?\s*\]')


def compounds(selector):
    """Split a selector into compound selectors (ignores combinators inside :has() etc.)."""
    out, depth, cur = [], 0, ""
    for c in selector:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if depth == 0 and c in " >+~":
            if cur:
                out.append(cur)
            cur = ""
        else:
            cur += c
    if cur:
        out.append(cur)
    return out


# Selectors for markup Alder renders round an element rather than inside one:
# the no-JavaScript click form (al-button.css).
ALDER_MARKUP = {"form._alder-click"}

# Classes Alder's rendered markup carries: the errors list and the help text
# of the input elements, and the click form.
ALDER_CLASSES = {"errors", "help", "_alder-click"}


def check_selector(sel, els, file_tag, seen):
    if sel in ALDER_MARKUP:
        return
    if file_tag not in sel:
        fail("css", "%s.css: selector %r does not name <%s>" % (file_tag, sel, file_tag))
    last = None
    for comp in compounds(sel):
        inner = re.findall(r":(?:has|not|is|where)\((.*)\)", comp)
        for sub in inner:
            for s in split_top(sub):
                check_selector_inner(s, els, last, seen)
        bare = re.sub(r":(?:has|not|is|where)\(.*\)", "", comp)
        m = re.match(r"([a-zA-Z][\w-]*)", bare)
        tag = m.group(1) if m else None
        if tag and tag.startswith("al-"):
            if tag not in els:
                fail("css", "%s.css: unknown element <%s> in %r" % (file_tag, tag, sel))
                return
            last = tag
        for cls in re.findall(r"\.([\w-]+)", bare):
            if not (cls.startswith("al-") or cls in ALDER_CLASSES):
                fail("css", "%s.css: class .%s is not al- prefixed" % (file_tag, cls))
        for name, op, val in ATTR_RE.findall(bare):
            if tag and tag.startswith("al-"):
                check_attr(tag, name, op, val, els, sel, file_tag, seen)
            elif name == "slot" and val:
                check_slot(last, val, els, sel, file_tag, seen)


def check_selector_inner(sel, els, parent, seen):
    for comp in compounds(sel):
        for name, op, val in ATTR_RE.findall(comp):
            if name == "slot" and val and parent:
                check_slot(parent, val, els, sel, parent, seen)


def check_attr(tag, name, op, val, els, sel, file_tag, seen):
    attrs = {a["name"]: a for a in els[tag].get("attributes", [])}
    if name in attrs:
        seen.add((tag, "attr", name))
        if val:
            vals = union_values(attrs[name]["type"]["text"])
            if vals is None or val not in vals:
                fail("css", "%s.css: %s[%s=%r] is not a declared value" % (file_tag, tag, name, val))
            seen.add((tag, "value", name, val))
    elif not is_global(name):
        fail("css", "%s.css: <%s> has no attribute %r (%s)" % (file_tag, tag, name, sel))


def check_slot(tag, val, els, sel, file_tag, seen):
    if not tag:
        fail("css", "%s.css: [slot=%r] outside an element in %r" % (file_tag, val, sel))
        return
    slots = [s["name"] for s in els[tag].get("slots", [])]
    if val not in slots:
        fail("css", "%s.css: <%s> has no slot %r" % (file_tag, tag, val))
    seen.add((tag, "slot", val))


def check_css(els):
    files = {}
    for tag, d in els.items():
        files.setdefault(d["_path"], []).append(tag)
    for rel, tags in files.items():
        path = ROOT / rel
        if not path.exists():
            continue
        css = path.read_text()
        seen = set()
        main = [t for t in tags if t not in SUB][0]
        for head, _ in rules(css):
            for sel in split_top(head):
                check_selector(sel, els, main, seen)
        for name in re.findall(r"attr\(([\w-]+)\)", strip_comments(css)):
            seen.add((main, "attr", name))
        for tag in tags:
            d = els[tag]
            if tag in SUB and not any(("%s" % tag) in h for h, _ in rules(css)):
                fail("css", "%s.css never styles <%s>" % (main, tag))
            for a in d.get("attributes", []):
                if (tag, a["name"]) in NOT_STYLED:
                    continue
                if (tag, "attr", a["name"]) not in seen:
                    fail("css", "%s.css never styles [%s]" % (tag, a["name"]))
                    continue
                vals = union_values(a["type"]["text"])
                default = json.loads(a["default"]) if "default" in a else None
                for v in vals or []:
                    if v != default and (tag, "value", a["name"], v) not in seen:
                        fail("css", "%s.css never styles [%s=%r]" % (tag, a["name"], v))
            for sl in d.get("slots", []):
                if sl["name"] and (tag, "slot", sl["name"]) not in seen:
                    fail("css", "%s.css never places slot %r" % (tag, sl["name"]))
    for p in sorted((ROOT / "components").glob("*.css")):
        if p.stem not in els:
            fail("css", "%s is not in the manifest" % p.name)


def check_scripts(m):
    """Scripts: the manifest lists each one, it exists, and it is short."""
    listed = [mod["path"] for mod in m["modules"] if mod["path"].endswith(".js")]
    for rel in listed:
        if not (ROOT / rel).exists():
            fail("scripts", "%s is in the manifest but missing" % rel)
    for p in sorted((ROOT / "components").glob("*.js")):
        if "components/" + p.name not in listed:
            fail("scripts", "%s is not in the manifest" % p.name)
        n = len(p.read_text().splitlines())
        if n > MAX_SCRIPT_LINES:
            fail("scripts", "%s has %d lines (max %d)" % (p.name, n, MAX_SCRIPT_LINES))
    if not (ROOT / "al.js").exists() or (ROOT / "al.js").read_text() != build.build_js():
        fail("bundle", "al.js is out of date: run python3 scripts/build.py")


# ---------------------------------------------------------------- tokens only

COLOUR_FUNCS = re.compile(r"\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(", re.I)
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
LENGTH = re.compile(r"(?<![\w-])-?\d*\.?\d+(px|rem|em|pt|vh|vw|ch|ex|%)\b")
NAMED = {"white", "black", "red", "green", "blue", "gray", "grey", "silver", "yellow", "orange",
         "purple", "navy", "teal", "maroon", "olive", "lime", "aqua", "fuchsia", "pink", "brown"}
TYPE_PROPS = {"font-size", "font-family", "font-weight", "line-height"}


def check_tokens_only(defined):
    for p in sorted((ROOT / "components").glob("*.css")):
        css = strip_strings(strip_comments(p.read_text()))
        local = set(re.findall(r"(--[\w-]+)\s*:", css))
        for name in re.findall(r"var\((--[\w-]+)", css):
            if name not in defined and name not in local:
                fail("tokens-only", "%s uses undefined %s" % (p.name, name))
        for head, body in rules(p.read_text()):
            for decl in body.split(";"):
                if ":" not in decl:
                    continue
                prop, val = [x.strip() for x in decl.split(":", 1)]
                val = strip_strings(val)
                if HEX.search(val) or COLOUR_FUNCS.search(val):
                    fail("tokens-only", "%s: %s { %s: %s } hard-codes a colour" % (p.name, head, prop, val))
                if set(re.findall(r"[a-z]+", val.lower())) & NAMED:
                    fail("tokens-only", "%s: %s { %s: %s } uses a named colour" % (p.name, head, prop, val))
                bare = re.sub(r"color-mix\([^)]*\)", "", val)
                if LENGTH.search(bare) and not (prop == "width" and val == "100%"):
                    fail("tokens-only", "%s: %s { %s: %s } hard-codes a length" % (p.name, head, prop, val))
                if prop in TYPE_PROPS and not (val.startswith("var(") or val == "inherit"):
                    fail("tokens-only", "%s: %s { %s: %s } must use a token" % (p.name, head, prop, val))


# ---------------------------------------------------------------- tokens + contrast

SHADCN = ["background", "foreground", "card", "card-foreground", "popover", "popover-foreground",
          "primary", "primary-foreground", "secondary", "secondary-foreground", "muted",
          "muted-foreground", "accent", "accent-foreground", "destructive",
          "destructive-foreground", "border", "input", "ring"]


def decls(body):
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body))


def load_tokens():
    css = strip_comments((ROOT / "tokens.css").read_text())
    blocks = {}
    for head, body in rules(css):
        blocks.setdefault(" ".join(head.split()), {}).update(decls(body))
    light = blocks.get(':root, [data-theme="light"]', {})
    dark = blocks.get('[data-theme="dark"]', {})
    media = blocks.get(':root:not([data-theme="light"])', {})
    common = blocks.get(":root", {})
    return light, dark, media, common


HSL = re.compile(r"hsl\(\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*\)")


def colour(expr, env):
    """Evaluate a CSS colour to (r, g, b, alpha) in sRGB, 0..1. Understands
    hsl(h s% l%), transparent, var(--x) (looked up in env) and
    color-mix(in srgb, A [p%], B [q%])."""
    expr = expr.strip()
    m = re.fullmatch(r"var\((--[\w-]+)\)", expr)
    if m:
        if m.group(1) not in env:
            raise ValueError("undefined %s" % m.group(1))
        return colour(env[m.group(1)], env)
    if expr == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    m = HSL.fullmatch(expr)
    if m:
        h, s, l = (float(x) for x in m.groups())
        return colorsys.hls_to_rgb(h / 360, l / 100, s / 100) + (1.0,)
    m = re.fullmatch(r"color-mix\((.*)\)", expr)
    if m:
        args = split_top(m.group(1))
        if args[0].split() != ["in", "srgb"]:
            raise ValueError("only color-mix in srgb: %r" % expr)
        parts = []
        for a in args[1:]:
            pm = re.fullmatch(r"(.*?)\s+([\d.]+)%", a)
            parts.append((pm.group(1), float(pm.group(2)) / 100) if pm else (a, None))
        (c1, p1), (c2, p2) = parts
        if p1 is None and p2 is None:
            p1 = p2 = 0.5
        elif p1 is None:
            p1 = 1 - p2
        elif p2 is None:
            p2 = 1 - p1
        total = p1 + p2
        w1, w2 = p1 / total, p2 / total
        a1, a2 = colour(c1, env), colour(c2, env)
        alpha = a1[3] * w1 + a2[3] * w2
        if alpha == 0:
            return (0.0, 0.0, 0.0, 0.0)
        rgb = tuple((a1[i] * a1[3] * w1 + a2[i] * a2[3] * w2) / alpha for i in range(3))
        return rgb + (alpha * min(total, 1.0),)
    raise ValueError("cannot evaluate colour %r" % expr)


def over(top, bottom):
    a = top[3]
    return tuple(top[i] * a + bottom[i] * (1 - a) for i in range(3)) + (1.0,)


def luminance_rgb(rgb):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb[:3]]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio_rgb(a, b):
    la, lb = luminance_rgb(a), luminance_rgb(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def ratio(fg, bg, env):
    """Contrast of fg on bg, both CSS colours; translucent colours are
    composited over the theme's --background first."""
    base = colour("var(--background)", env)
    b = over(colour(bg, env), base)
    return ratio_rgb(over(colour(fg, env), b), b)


def button_pairs():
    """al-button's text/background pairs, derived from its CSS: for every
    variant (primary is the base rule) the text on the resting background and
    on the hover background."""
    css = (ROOT / "components" / "al-button.css").read_text()
    base, variants = {}, {}
    for head, body in rules(css):
        head = " ".join(head.split())
        d = {k: v.strip() for k, v in decls(body + ";").items() if k.startswith("--_al-")}
        if head == "al-button":
            base = d
        else:
            m = re.fullmatch(r'al-button\[variant="(\w+)"\]', head)
            if m:
                variants[m.group(1)] = d
    out = []
    for v in ["primary"] + [k for k in variants if k != "primary"]:
        d = dict(base, **variants.get(v, {}))
        out.append(("al-button %s" % v, d["--_al-fg"], d["--_al-bg"], 4.5))
        out.append(("al-button %s hover" % v, d["--_al-fg"], d["--_al-hover"], 4.5))
    return out


# (where it is used, foreground token, background token, minimum)
PAIRS = [
    ("body text", "foreground", "background", 4.5),
    ("al-card", "card-foreground", "card", 4.5),
    ("al-badge default", "primary-foreground", "primary", 4.5),
    ("al-badge secondary", "secondary-foreground", "secondary", 4.5),
    ("al-badge outline", "foreground", "background", 4.5),
    ("al-badge destructive", "destructive-foreground", "destructive", 4.5),
    ("al-pagination link hover", "accent-foreground", "accent", 4.5),
    ("help, placeholder, th, card footer, page N of M", "muted-foreground", "background", 4.5),
    ("muted text on card", "muted-foreground", "card", 4.5),
    ("al-table striped row", "foreground", "muted", 4.5),
    ("ul.errors", "--al-destructive-text", "background", 4.5),
    ("al-alert info", "--al-info-soft-foreground", "--al-info-soft", 4.5),
    ("al-alert success", "--al-success-soft-foreground", "--al-success-soft", 4.5),
    ("al-alert warning", "--al-warning-soft-foreground", "--al-warning-soft", 4.5),
    ("al-alert destructive", "--al-destructive-soft-foreground", "--al-destructive-soft", 4.5),
    ("popover", "popover-foreground", "popover", 4.5),
    ("field border (non-text)", "input", "background", 3.0),
    ("focus ring (non-text)", "ring", "background", 3.0),
    ("invalid border (non-text)", "--al-destructive-text", "background", 3.0),
]


def tok(name):
    if name.startswith("var(") or name.startswith("color-mix(") or name == "transparent":
        return name
    return "var(%s)" % (name if name.startswith("--") else "--" + name)


def check_tokens(light, dark, media, common):
    for theme, vals in (("light", light), ("dark", dark)):
        for n in SHADCN:
            if "--" + n not in vals:
                fail("tokens", "%s theme lacks --%s" % (theme, n))
    if "--radius" not in common:
        fail("tokens", "--radius is not defined")
    if media != dark:
        fail("tokens", "the prefers-color-scheme dark block differs from [data-theme=\"dark\"]")
    if set(light) != set(dark):
        fail("tokens", "light and dark define different tokens: %s" % sorted(set(light) ^ set(dark)))


def contrast_table(light, dark):
    rows = []
    for use, fg, bg, need in button_pairs() + PAIRS:
        row = [use, tok(fg), tok(bg), need]
        for theme, vals in (("light", light), ("dark", dark)):
            try:
                r = ratio(tok(fg), tok(bg), vals)
            except (KeyError, ValueError) as e:
                fail("contrast", "%s (%s): %s" % (use, theme, e))
                r = 0.0
            if r < need:
                fail("contrast", "%s in %s: %s on %s is %.2f:1, needs %.1f:1" % (use, theme, tok(fg), tok(bg), r, need))
            row.append(r)
        rows.append(row)
    return rows


# ---------------------------------------------------------------- demos

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Demo(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.elements, self.links, self.hrefs, self.classes = [], [], [], [], []

    def handle_starttag(self, tag, attrs):
        parent = next((t for t in reversed(self.stack) if t.startswith("al-")), None)
        self.elements.append((tag, attrs, parent, self.getpos()[0]))
        d = dict(attrs)
        if tag == "link" and d.get("rel") == "stylesheet":
            self.links.append(d.get("href"))
        if tag == "a" and d.get("href"):
            self.hrefs.append(d["href"])
        if d.get("class") is not None:
            self.classes.append((tag, d["class"], self.getpos()[0]))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag in self.stack:
            while self.stack.pop() != tag:
                pass


def INTERACTIVE_DEMO(tag):
    return tag in ("al-dialog", "al-popover", "al-menu", "al-tabs", "al-toast", "al-tooltip", "al-devpanel")


def check_demos(els):
    pages = {}
    for p in sorted((ROOT / "demo").glob("*.html")):
        d = Demo()
        d.feed(p.read_text())
        d.close()
        pages[p.name] = d
        where = "demo/" + p.name
        if "../al.css" not in d.links:
            fail("demos", "%s does not link ../al.css" % where)
        for tag, cls, line in d.classes:
            for c in cls.split():
                if not (c.startswith("al-") or (c == "errors" and tag == "ul") or (c == "help" and tag == "small")):
                    fail("demos", "%s:%d: class %r (no demo-only classes)" % (where, line, c))
        for tag, attrs, parent, line in d.elements:
            if any(n == "style" for n, _ in attrs):
                fail("demos", "%s:%d: style attribute (no demo-only styling)" % (where, line))
            if tag.startswith("al-"):
                if tag not in els:
                    fail("demos", "%s:%d: unknown element <%s>" % (where, line, tag))
                    continue
                declared = {a["name"]: a for a in els[tag].get("attributes", [])}
                for name, val in attrs:
                    if name in declared:
                        t = declared[name]["type"]["text"]
                        if t == "boolean" and val not in (None, ""):
                            fail("demos", "%s:%d: <%s %s> is boolean; write it bare" % (where, line, tag, name))
                        vals = union_values(t)
                        if vals is not None and val not in vals:
                            fail("demos", "%s:%d: <%s %s=%r> is not one of %s" % (where, line, tag, name, val, vals))
                        if t == "number" and not re.fullmatch(r"\d+", val or ""):
                            fail("demos", "%s:%d: <%s %s=%r> is not a number" % (where, line, tag, name, val))
                    elif not is_global(name):
                        fail("demos", "%s:%d: <%s> has no attribute %r" % (where, line, tag, name))
            slot = dict(attrs).get("slot")
            if slot is not None:
                if not (parent and parent.startswith("al-") and parent in els):
                    fail("demos", "%s:%d: slot=%r outside an al- element" % (where, line, slot))
                elif slot not in [s["name"] for s in els[parent].get("slots", []) if s["name"]]:
                    fail("demos", "%s:%d: <%s> has no slot %r" % (where, line, parent, slot))
    for tag, decl in els.items():
        name = SUB.get(tag, tag)[3:] + ".html"
        d = pages.get(name)
        if not d:
            fail("demos", "demo/%s is missing" % name)
            continue
        used = [(t, dict(a)) for t, a, _, _ in d.elements if t == tag]
        if INTERACTIVE_DEMO(tag) and "<!-- no-js -->" not in (ROOT / "demo" / name).read_text():
            fail("demos", "demo/%s has no <!-- no-js --> section" % name)
        if not used:
            fail("demos", "demo/%s never uses <%s>" % (name, tag))
        for a in decl.get("attributes", []):
            vals = union_values(a["type"]["text"])
            if vals:
                for v in vals:
                    if not any(attrs.get(a["name"]) == v for _, attrs in used):
                        fail("demos", "demo/%s never shows %s %s=%r" % (name, tag, a["name"], v))
            elif not any(a["name"] in attrs for _, attrs in used):
                fail("demos", "demo/%s never shows %s[%s]" % (name, tag, a["name"]))
        for s in decl.get("slots", []):
            if s["name"] and not any(dict(at).get("slot") == s["name"] and par == tag for _, at, par, _ in d.elements):
                fail("demos", "demo/%s never fills %s slot %r" % (name, tag, s["name"]))
        if (tag not in SUB and "index.html" in pages and name not in pages["index.html"].hrefs):
            fail("demos", "demo/index.html does not link %s" % name)
    if "index.html" not in pages:
        fail("demos", "demo/index.html is missing")


# ---------------------------------------------------------------- main

def main(argv):
    m, els = load_manifest()
    check_manifest(m, els)
    check_css(els)
    light, dark, media, common = load_tokens()
    defined = set(light) | set(dark) | set(common)
    check_tokens_only(defined)
    check_tokens(light, dark, media, common)
    rows = contrast_table(light, dark)
    check_demos(els)
    if not (ROOT / "al.css").exists() or (ROOT / "al.css").read_text() != build.build():
        fail("bundle", "al.css is out of date: run python3 scripts/build.py")
    if "--table" in argv:
        print("| use | foreground | background | needs | light | dark |")
        print("|---|---|---|---|---|---|")
        for use, fg, bg, need, lr, dr in rows:
            print("| %s | `%s` | `%s` | %.1f | %.2f | %.2f |" % (use, fg, bg, need, lr, dr))
    if FAILURES:
        for f in FAILURES:
            print("FAIL", f)
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("ok: manifest, css, tokens-only, tokens, contrast (%d pairs x 2 themes), demos (%d pages), bundle"
          % (len(rows), len(list((ROOT / "demo").glob("*.html")))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
