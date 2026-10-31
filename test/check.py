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
               value and slot in the manifest is styled (typography.css
               counts as al-page's stylesheet, and outside :where() its
               selectors weigh only element names)
  tokens-only  no literal colour and no literal font-family in components/,
               base.css, typography.css; every var(--x) is defined
  tokens       tokens.css has shadcn's names (Ref section 1) in light and
               dark, --radius 0.625rem, .dark/.light only (no data-theme, no
               media query); --al-width-* and --al-border-width are the only
               --al- tokens left; no border declaration uses a literal 1px
  contrast     WCAG AA for each text pairing the components draw (4.5:1,
               a failure; a verbatim shadcn gap in SPEC_GAPS is a WARN) and
               each border and ring (3:1, a WARN only), light and dark,
               computed from tokens.css; al-button's pairs (resting and
               hover) are derived from its CSS
  themes       each themes/<name>/ (a DTCG theme dir, see scripts/dtcg.py) loads;
               its token names are exactly tokens.css's (base: theme-wide
               tokens; light and dark: the 32 colours), in alder's table
               order; every value converts and every token has a
               $description; the theme passes the contrast table; zinc's
               values equal tokens.css's
  demos        each page links ../al.css, uses only declared attributes, values
               and slots, shows every variant/size/state of its element;
               index.html links every page
  scripts      every components/*.js is in the manifest, exists, is at most 60
               lines; the interactive demos have a <!-- no-js --> section
  bundle       al.css, al.js and index.html equal scripts/build.py's output
"""
import html.parser
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test"))
import build  # noqa: E402
import colour  # noqa: E402
import dtcg  # noqa: E402

FAILURES = []
WARNINGS = []


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
    "al-devpanel": ([("open", "boolean")], [""]),
    "al-tooltip": ([("for", "string")], [""]),
    "al-toast": ([("variant", '"info" | "success" | "warning" | "destructive"'), ("timeout", "number")], [""]),
    "al-toasts": ([("position", '"top-left" | "top-right" | "bottom-left" | "bottom-right"')], [""]),
    "al-tabs": ([], [""]),
    "al-tab": ([("name", "string"), ("selected", "boolean")], [""]),
    "al-panel": ([], [""]),
    "al-menu": ([("anchor", "string")], [""]),
    "al-popover": ([("placement", '"top" | "bottom" | "left" | "right"'), ("offset", '"sm" | "md" | "lg"'), ("anchor", "string")], [""]),
    "al-dialog": ([("heading", "string"), ("size", '"sm" | "md" | "lg"'), ("dismissible", "boolean")], ["header", "", "actions"]),
})
ADDED = {
    "al-select": [("help", "string")],
    "al-checkbox": [("invalid", "boolean"), ("help", "string")],
    "al-page": [("plain", "boolean")],
    "al-tabs": [("variant", '"default" | "line"')],
    "al-button": [("full", "boolean")],
}
# Additive growth since the API above (restyle): extra members appended to an
# attribute's string union, and extra slots appended after the original ones.
ADDED_VALUES = {  # (tag, attribute) -> [value, ...]
    ("al-button", "variant"): ["link"],
    ("al-button", "size"): ["xs", "icon", "icon-sm", "icon-lg"],
    ("al-stack", "gap"): ["xl"],
}
ADDED_SLOTS = {"al-card": ["description", "action"], "al-dialog": ["description"]}  # tag -> [slot, ...]

# Attributes the stylesheet deliberately does not draw: the framework copies
# them onto the native control, or renders them as markup.
NOT_STYLED = {
    ("al-tooltip", "for"): "read by al-tooltip.js, which finds the trigger by id",
    ("al-toast", "timeout"): "read by al-toast.js, which closes the toast",
    ("al-tab", "name"): "copied onto the radio input by al-tabs.js",
    ("al-tab", "selected"): "read by al-tabs.js, which checks the tab's radio",
    ("al-popover", "anchor"): "read by al-shim.js, which sets position-anchor to the element with that id",
    ("al-menu", "anchor"): "read by al-shim.js, which sets position-anchor to the element with that id",
    ("al-dialog", "heading"): "rendered by the framework as the header slot's <h2>",
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
    if not re.fullmatch(r"v\d+\.\d+\.\d+(-rc\.\d+)?", m.get("version", "")):
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
        want = [(n, t + "".join(' | "%s"' % v for v in ADDED_VALUES.get((tag, n), []))) for n, t in attrs]
        want += ADDED.get(tag, [])
        if got != want:
            fail("manifest", "%s attributes %s, want %s" % (tag, got, want))
        if [s["name"] for s in d.get("slots", [])] != slots + ADDED_SLOTS.get(tag, []):
            fail("manifest", "%s slots changed" % tag)
        if not d.get("description"):
            fail("manifest", "%s has no description" % tag)
        for a in d.get("attributes", []):
            if not a.get("description"):
                fail("manifest", "%s[%s] has no description" % (tag, a["name"]))
            if a["type"]["text"] == "boolean":
                if a.get("default") != "false":
                    fail("manifest", "%s[%s] is boolean; its default must be false" % (tag, a["name"]))
            elif a["type"]["text"] == "number" and re.fullmatch(r"\d+", a.get("default", "")):
                pass
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
THEME_CLASSES = {"dark", "light"}  # the token sheet's theme selectors (spec section 4)
ALDER_CLASSES = {"errors", "help", "_alder-click"}


def split_pseudos(comp):
    """A compound -> (bare, args): the compound with every :pseudo(...) removed
    (parentheses balanced), and the (name, argument) of each :has/:not/:is/:where."""
    bare, args, i = "", [], 0
    while i < len(comp):
        m = re.compile(r":{1,2}([\w-]+)\(").match(comp, i)
        if not m:
            bare += comp[i]
            i += 1
            continue
        depth, j = 1, m.end()
        while j < len(comp) and depth:
            depth += {"(": 1, ")": -1}.get(comp[j], 0)
            j += 1
        if m.group(1) in ("has", "not", "is", "where"):
            args.append((m.group(1), comp[m.end():j - 1]))
        i = j
    return bare, args


def check_selector(sel, els, file_tag, seen):
    if sel in ALDER_MARKUP:
        return
    if file_tag not in sel:
        fail("css", "%s.css: selector %r does not name <%s>" % (file_tag, sel, file_tag))
    last = None
    for comp in compounds(sel):
        bare, inner = split_pseudos(comp)
        m = re.match(r"([a-zA-Z][\w-]*)", bare)
        tag = m.group(1) if m else None
        for fn, sub in inner:
            for s in split_top(sub):
                check_selector_inner(s, els, last, seen, tag if fn != "has" else None)
        if tag and tag.startswith("al-"):
            if tag not in els:
                fail("css", "%s.css: unknown element <%s> in %r" % (file_tag, tag, sel))
                return
            last = tag
        for cls in re.findall(r"\.([\w-]+)", bare):
            if not (cls.startswith("al-") or cls in ALDER_CLASSES or cls in THEME_CLASSES):
                fail("css", "%s.css: class .%s is not al- prefixed" % (file_tag, cls))
        for name, op, val in ATTR_RE.findall(bare):
            if tag and tag.startswith("al-"):
                check_attr(tag, name, op, val, els, sel, file_tag, seen)
            elif name == "slot" and val:
                check_slot(last, val, els, sel, file_tag, seen)


def check_selector_inner(sel, els, parent, seen, host=None):
    """host: the al- tag of the compound that owns this :not/:is/:where argument (same
    element), so an attribute-only leading compound belongs to it. :has() passes None."""
    for i, comp in enumerate(compounds(sel)):
        bare, inner = split_pseudos(comp)
        m = re.match(r"(al-[\w-]+)", bare)
        owner = m.group(1) if m else (host if i == 0 and re.match(r"[.\[:]|$", bare) else None)
        for name, op, val in ATTR_RE.findall(bare):
            if name == "slot" and val and parent:
                check_slot(parent, val, els, sel, parent, seen)
            elif owner and owner in els and name != "slot":
                # an al- element inside :where()/:not()/:is()/:has(), e.g.
                # typography.css's :where(al-page:not([plain]))
                check_attr(owner, name, op, val, els, sel, owner, seen)
        for fn, sub in inner:
            for s in split_top(sub):
                check_selector_inner(s, els, owner if owner in els else parent, seen,
                                     owner if fn != "has" else None)


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


# typography.css is scoped to al-page:not([plain]), so it is al-page's too.
EXTRA_CSS = {"al-page": ["typography.css"]}


def strip_where(sel):
    """sel with every :where(...) argument list removed (they weigh nothing)."""
    out, i = "", 0
    while True:
        j = sel.find(":where(", i)
        if j < 0:
            return out + sel[i:]
        out += sel[i:j]
        depth, k = 0, j + len(":where")
        while k < len(sel):
            depth += {"(": 1, ")": -1}.get(sel[k], 0)
            k += 1
            if depth == 0:
                break
        i = k


def check_typography_weight():
    """typography.css: outside :where(), a selector holds only element names and
    combinators, at least one of them, so it weighs (0,0,n) with n >= 1: it
    beats the reset of its own element and loses to any component rule that
    names its element (al-dialog p, al-card > h2 + p)."""
    path = ROOT / "typography.css"
    if not path.exists():
        return
    for head, _ in rules(path.read_text()):
        for sel in split_top(head):
            rest = strip_where(sel)
            if re.search(r"[:\[.#]", rest):
                fail("css", "typography.css: %r has class/attribute/pseudo-class weight outside :where()" % sel)
            elif not re.search(r"(?:^|[\s>+~])[a-z][\w-]*", rest):
                fail("css", "typography.css: %r names no element outside :where() (weight 0,0,0)" % sel)


MOTION_GUARD = re.compile(r"prefers-reduced-motion\s*:\s*no-preference")
MOTION_PROP = re.compile(r"(?:^|[;{\s])((?:transition|animation)[\w-]*)\s*:\s*([^;]+)")


def unguarded_motion(css):
    """The selectors of style rules in css that declare a transition or
    animation (other than none) outside @media (prefers-reduced-motion:
    no-preference). Plan Global Constraints: all motion sits under that query."""
    css = strip_comments(css)
    out, stack, start = [], [], 0
    for i, c in enumerate(css):
        if c == "{":
            stack.append(css[start:i].strip())
            start = i + 1
        elif c == "}":
            head = stack.pop()
            body = css[start:i]
            start = i + 1
            if head.startswith("@") or any(MOTION_GUARD.search(h) for h in stack):
                continue
            if any(v.strip() != "none" for _, v in MOTION_PROP.findall(body)):
                out.append(" ".join(head.split()))
        elif c == ";" and stack and stack[-1].startswith("@"):
            start = i + 1
    return out


FOCUS_HEAD = re.compile(r":focus(?:-visible)?\b")
OUTLINE_NONE = re.compile(r"(?:^|[;{\s])outline(?:-style)?\s*:\s*(?:none\b|[^;]*\snone\b)")


def unguarded_focus(css):
    """True when a :focus or :focus-visible rule sets outline to none (outline: none,
    outline-style: none, or outline: <w> none ...) and css has no @media (forced-colors:
    active) block. Forced colors drops box-shadow rings, so the outline is the only
    indicator left (#15)."""
    css = strip_comments(css)
    if re.search(r"@media[^{]*forced-colors\s*:\s*active", css):
        return False
    return any(FOCUS_HEAD.search(head) and OUTLINE_NONE.search(body) for head, body in rules(css))


def check_focus():
    for p in styled_files():
        if unguarded_focus(p.read_text()):
            fail("css", "%s: a focus rule sets outline: none and the file has no @media (forced-colors: active) block" % p.name)


def check_motion():
    for p in styled_files():
        for sel in unguarded_motion(p.read_text()):
            fail("css", "%s: %r has motion outside @media (prefers-reduced-motion: no-preference)" % (p.name, sel))


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
        # Files outside components/ that style an element: their selectors are
        # checked as that element's and count toward what it styles.
        for extra in EXTRA_CSS.get(main, []):
            if (ROOT / extra).exists():
                for head, _ in rules((ROOT / extra).read_text()):
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
        if p.stem not in els and p.stem != "icons":
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
NAMED = {"white", "black", "red", "green", "blue", "gray", "grey", "silver", "yellow", "orange",
         "purple", "navy", "teal", "maroon", "olive", "lime", "aqua", "fuchsia", "pink", "brown"}


def check_tokens_only(defined):
    """No literal colour and no literal font-family in the styling files
    (lengths, font sizes, weights and line heights are fine); every var(--x)
    is defined by tokens.css or by one of the files."""
    files = styled_files()
    declared = set()
    for p in files:
        declared |= set(re.findall(r"(--[\w-]+)\s*:", strip_strings(strip_comments(p.read_text()))))
    for p in files:
        css = strip_strings(strip_comments(p.read_text()))
        for name in re.findall(r"var\((--[\w-]+)", css):
            if name not in defined and name not in declared:
                fail("tokens-only", "%s uses undefined %s" % (p.name, name))
        for head, body in rules(p.read_text()):
            for decl in body.split(";"):
                if ":" not in decl:
                    continue
                prop, val = [x.strip() for x in decl.split(":", 1)]
                val = strip_strings(val)
                if HEX.search(val) or COLOUR_FUNCS.search(val):
                    fail("tokens-only", "%s: %s { %s: %s } hard-codes a colour" % (p.name, head, prop, val))
                if set(re.findall(r"[a-z]+", re.sub(r"--[\w-]+", "", val).lower())) & NAMED:
                    fail("tokens-only", "%s: %s { %s: %s } uses a named colour" % (p.name, head, prop, val))
                if prop == "font-family" and not (val.startswith("var(") or val == "inherit"):
                    fail("tokens-only", "%s: %s { %s: %s } must use a token" % (p.name, head, prop, val))


# ---------------------------------------------------------------- icons

ICONS = ["check", "minus", "chevron-down", "chevron-left", "chevron-right", "x", "circle-check",
         "info", "triangle-alert", "octagon-x", "loader-circle", "ellipsis"]


def check_icons():
    """components/icons.css defines the twelve --_al-icon-* masks (quoted,
    URL-encoded SVG data URIs), and every --_al-icon-* used is one of them."""
    p = ROOT / "components" / "icons.css"
    css = strip_comments(p.read_text()) if p.exists() else ""
    defined = dict(re.findall(r"(--_al-icon-[\w-]+)\s*:\s*(url\(\"data:image/svg\+xml,[^\"]+\"\))\s*;", css))
    for n in ICONS:
        if "--_al-icon-" + n not in defined:
            fail("icons", "icons.css does not define --_al-icon-%s" % n)
    for q in sorted(ROOT.glob("components/*.css")):
        if q.name == "icons.css":
            continue
        for name in re.findall(r"var\((--_al-icon-[\w-]+)", q.read_text()):
            if name not in defined:
                fail("icons", "%s uses undefined %s" % (q.name, name))


# ---------------------------------------------------------------- tokens + contrast

# Ref §1's names (the shadcn token sheet), plus --destructive-foreground.
SHADCN = ["background", "foreground", "card", "card-foreground", "popover", "popover-foreground",
          "primary", "primary-foreground", "secondary", "secondary-foreground", "muted",
          "muted-foreground", "accent", "accent-foreground", "destructive",
          "destructive-foreground", "border", "input", "ring",
          "chart-1", "chart-2", "chart-3", "chart-4", "chart-5",
          "sidebar", "sidebar-foreground", "sidebar-primary", "sidebar-primary-foreground",
          "sidebar-accent", "sidebar-accent-foreground", "sidebar-border", "sidebar-ring"]
# The only alder-ui tokens left: the page widths and the border width.
AL_TOKENS = {"--al-width-narrow", "--al-width-normal", "--al-width-wide", "--al-border-width"}


def decls(body):
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body))


def load_tokens():
    """tokens.css's three blocks: light (":root, .light"), dark (".dark") and
    the theme-independent ":root"."""
    css = strip_comments((ROOT / "tokens.css").read_text())
    blocks = {}
    for head, body in rules(css):
        blocks.setdefault(" ".join(head.split()), {}).update(decls(body))
    light = blocks.get(":root, .light", {})
    dark = blocks.get(".dark", {})
    common = blocks.get(":root", {})
    return light, dark, common


def styled_files():
    """The CSS files that style (rather than define tokens): components/*.css,
    and base.css and typography.css once they exist."""
    out = [ROOT / n for n in ("base.css", "typography.css") if (ROOT / n).exists()]
    return out + sorted((ROOT / "components").glob("*.css"))


class Themed(tuple):
    """A (light, dark) pair of colour expressions, for a pairing the CSS
    writes differently under .dark (a `.dark al-button[...]` rule)."""


def button_pairs():
    """al-button's text/background pairs, derived from its CSS: for every
    variant (primary is the base rule) the text on the resting background and
    on the hover background (the hover text is --_al-hover-fg when set). A
    `.dark al-button[variant=...]` rule overrides the properties in dark."""
    css = (ROOT / "components" / "al-button.css").read_text()
    base, variants, dark = {}, {}, {}
    for head, body in rules(css):
        head = " ".join(head.split())
        d = {k: v.strip() for k, v in decls(body + ";").items() if k.startswith("--_al-")}
        if head == "al-button":
            base = d
            continue
        m = re.fullmatch(r'(\.dark )?al-button\[variant="(\w+)"\]', head)
        if m:
            (dark if m.group(1) else variants).setdefault(m.group(2), {}).update(d)
    out = []
    for v in ["primary"] + [k for k in variants if k != "primary"]:
        light = dict(base, **variants.get(v, {}))
        night = dict(light, **dark.get(v, {}))

        def pair(key):
            return light[key] if light[key] == night[key] else Themed((light[key], night[key]))

        out.append(("al-button %s" % v, pair("--_al-fg"), pair("--_al-bg"), 4.5))
        out.append(("al-button %s hover" % v, pair("--_al-hover-fg" if "--_al-hover-fg" in light else "--_al-fg"), pair("--_al-hover"), 4.5))
    return out


# (where it is used, foreground token, background token, minimum): only the
# pairings the components draw. 4.5 is text (a failure below it); 3.0 is a
# border or ring (a WARN below it, never a failure).
MUTED_50 = "color-mix(in oklab, var(--muted) 50%, transparent)"
INPUT_30 = "color-mix(in oklab, var(--input) 30%, transparent)"
INPUT_50 = "color-mix(in oklab, var(--input) 50%, transparent)"
DESTRUCTIVE_10 = "color-mix(in oklab, var(--destructive) 10%, transparent)"
DESTRUCTIVE_20 = "color-mix(in oklab, var(--destructive) 20%, transparent)"
RING_50 = "color-mix(in oklab, var(--ring) 50%, transparent)"
TABS_FG = "muted-foreground"
PAIRS = [
    ("body text, active tab, outline badge, fields", "foreground", "background", 4.5),
    ("al-card, al-alert, al-devpanel", "card-foreground", "card", 4.5),
    ("al-badge default", "primary-foreground", "primary", 4.5),
    ("al-badge secondary", "secondary-foreground", "secondary", 4.5),
    ("al-badge destructive", "--color-white",
     Themed(("destructive", "color-mix(in oklab, var(--destructive) 60%, transparent)")), 4.5),
    ("accent hover (pagination, menu, devpanel, dialog close; dark ghost and pagination hover are solid)", "accent-foreground", "accent", 4.5),
    ("help, caption, page N of M", "muted-foreground", "background", 4.5),
    # al-input, al-textarea, al-select: bg-transparent in light (on the page), bg-input/30 in dark
    ("placeholder on a field", "muted-foreground", Themed(("background", INPUT_30)), 4.5),
    ("field text on its fill", "foreground", Themed(("background", INPUT_30)), 4.5),
    ("al-select hover", "foreground", Themed(("background", INPUT_50)), 4.5),
    ("al-pagination active link hover", "accent-foreground", Themed(("accent", INPUT_50)), 4.5),
    ("al-alert dismiss icon hover (non-text)", "accent-foreground", "accent", 3.0),
    ("muted text on card (card and alert descriptions, devpanel tabs)", "muted-foreground", "card", 4.5),
    # al-tabs: an inactive trigger is text-muted-foreground (shadcn's text-foreground/60 fails AA
    # in some themes), on the list's bg-muted (default) or on the page (line, bg-transparent)
    ("al-tabs trigger", TABS_FG, "muted", 4.5),
    ("al-tabs line trigger", TABS_FG, "background", 4.5),
    ("al-table striped row", "foreground", MUTED_50, 4.5),
    ("muted text on a striped row (a th or td the app mutes)", "muted-foreground", MUTED_50, 4.5),
    ("ul.errors", "destructive", "background", 4.5),
    ("al-alert destructive title", "destructive", "card", 4.5),
    ("al-alert destructive description", "color-mix(in oklab, var(--destructive) 90%, transparent)", "card", 4.5),
    ("popover, al-menu, al-dialog", "popover-foreground", "popover", 4.5),
    ("al-toast", "popover-foreground", "popover", 4.5),
    ("al-menu destructive item", "destructive", "popover", 4.5),
    # hover/focus fill is destructive/10 (light) or /20 (dark), drawn over --popover
    ("al-menu destructive item hover", "destructive", Themed((DESTRUCTIVE_10, DESTRUCTIVE_20)), 4.5, "popover"),
    ("al-tooltip", "background", "foreground", 4.5),
    ("field border (non-text)", "input", "background", 3.0),
    ("menu keyboard focus outline (non-text)", "muted-foreground", "popover", 3.0),
    ("focus ring (non-text)", RING_50, "background", 3.0),
    ("invalid border (non-text)", "destructive", "background", 3.0),
]

# Non-text pairings that fail the run (rather than WARN) when below their ratio: the
# indicator is the only focus cue left in normal mode (#15, D4).
NON_TEXT_FAIL = {"menu keyboard focus outline (non-text)"}

SPEC_GAP_REASON = "verbatim shadcn token; spec \u00a74.2 fidelity"
# Text pairings below 4.5 that come from shadcn's verbatim tokens: kept for
# fidelity (spec section 4.2) and printed as WARN, not failed (ruling R7).
# Keyed (use, theme).
SPEC_GAPS = {
    ("al-menu destructive item hover", "light"): "zinc's verbatim --destructive on destructive/10 over the popover is 3.99:1 (shadcn's own pairing)",
    ("al-tabs trigger", "light"): "zinc's verbatim --muted-foreground on --muted is 4.34:1; the trigger now uses --muted-foreground so every theme passes",
}


def tok(name, theme=None):
    if isinstance(name, Themed):
        name = name[0 if theme != "dark" else 1]
    if name.startswith("var(") or name.startswith("color-mix(") or name == "transparent":
        return name
    return "var(%s)" % (name if name.startswith("--") else "--" + name)


def al_definitions(css):
    """The --al-* custom properties defined anywhere in css (comments stripped), at any nesting."""
    return set(re.findall(r"(--al-[\w-]+)\s*:", strip_comments(css)))


BORDER_DECL = re.compile(
    r"(?<![\w-])border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?(?:-width)?\s*:\s*([^;}]*)")


def border_literals(css):
    """Border declarations (border, border-<side>, border-width,
    border-<side>-width) whose value holds a literal 1px; they take
    var(--al-border-width) instead."""
    return [m.group(0).strip() for m in BORDER_DECL.finditer(strip_comments(css))
            if re.search(r"(?<![\w.-])1px(?![\w-])", m.group(1))]


def check_tokens(light, dark, common):
    for theme, vals in (("light", light), ("dark", dark)):
        for n in SHADCN:
            if "--" + n not in vals:
                fail("tokens", "%s theme lacks --%s" % (theme, n))
    if light.get("--radius", "").strip() != "0.625rem":
        fail("tokens", "--radius is %r in the light block, not 0.625rem" % light.get("--radius"))
    if set(light) - {"--radius"} != set(dark):
        fail("tokens", "light and dark define different tokens: %s"
             % sorted((set(light) - {"--radius"}) ^ set(dark)))
    raw = (ROOT / "tokens.css").read_text()
    for banned in ("[data-theme", "prefers-color-scheme"):
        if banned in raw:
            fail("tokens", "tokens.css mentions %s (themes are .dark and .light only)" % banned)
    for name in sorted(al_definitions(raw)):
        if name not in AL_TOKENS:
            fail("tokens", "tokens.css defines %s (only %s survive)" % (name, ", ".join(sorted(AL_TOKENS))))
    for p in styled_files():
        css = strip_comments(p.read_text())
        for name in sorted(set(re.findall(r"(--al-[\w-]+)\s*:", css))):
            if name not in AL_TOKENS:
                fail("tokens", "%s defines %s (only %s survive)" % (p.name, name, ", ".join(sorted(AL_TOKENS))))
        for name in sorted(set(re.findall(r"var\((--al-[\w-]+)", css))):
            if name not in AL_TOKENS:
                fail("tokens", "%s uses removed token %s" % (p.name, name))
        for decl in border_literals(css):
            fail("tokens", "%s: %s (use var(--al-border-width))" % (p.name, decl))


def theme_envs(light, dark, common):
    """The custom properties in force on a light page and on a .dark page."""
    return (("light", {**common, **light}), ("dark", {**common, **light, **dark}))


def contrast_table(light, dark, common, where="tokens.css", gaps=None):
    """gaps: apply SPEC_GAPS (shadcn's verbatim shortfalls); by default only
    for the tokens.css run, so a theme is held to the full ratios."""
    if gaps is None:
        gaps = where == "tokens.css"
    spec_gaps = SPEC_GAPS if gaps else {}
    rows = []
    for use, fg, bg, need, *surface in button_pairs() + PAIRS:
        surface = tok(surface[0]) if surface else "var(--background)"
        row = [use, tok(fg), tok(bg), need]
        for theme, vals in theme_envs(light, dark, common):
            fg_t, bg_t = tok(fg, theme), tok(bg, theme)
            try:
                r = colour.contrast(fg_t, bg_t, vals, surface)
            except (KeyError, ValueError) as e:
                fail("contrast", "%s: %s (%s): %s" % (where, use, theme, e))
                r = 0.0
            if r < need:
                msg = "%s: %s in %s: %s on %s is %.2f:1, needs %.1f:1" % (where, use, theme, fg_t, bg_t, r, need)
                if need < 4.5 and use not in NON_TEXT_FAIL:
                    WARNINGS.append("contrast: %s (non-text)" % msg)
                elif (use, theme) in spec_gaps:
                    WARNINGS.append("contrast: %s (%s)" % (msg, spec_gaps[(use, theme)]))
                else:
                    fail("contrast", msg)
            elif (use, theme) in spec_gaps and need >= 4.5:
                fail("contrast", "%s: stale SPEC_GAPS entry: %s in %s now passes (%.2f:1); delete it" % (where, use, theme, r))
            row.append(r)
        rows.append(row)
    for use, theme in sorted(spec_gaps):
        if not any(r[0] == use for r in rows):
            fail("contrast", "%s: SPEC_GAPS names %r, which is not a pairing" % (where, use))
    return rows


# ---------------------------------------------------------------- themes

THEME_ORDER = {
    "base": ["radius", "radius-sm", "radius-md", "radius-lg", "radius-xl",
             "al-width-narrow", "al-width-normal", "al-width-wide", "font-sans", "font-mono",
             "shadow-xs", "shadow-sm", "shadow-md", "shadow-lg", "al-border-width"],
    # alder's table order, not tokens.css's block order
    "colours": SHADCN[:],
}
THEMES = ["zinc", "brutal", "catppuccin", "paper", "pebble"]
# Derived in tokens.css with calc(); a theme states them as plain dimensions.
DERIVED_RADII = {"--radius-sm", "--radius-md", "--radius-lg", "--radius-xl"}
COLOUR_TOL = 0.5 / 255


def theme_expected(tokens):
    """The token names a theme must declare: (base, colours)."""
    light, dark, common = tokens
    base = ({k for k in common if k not in ("--color-white", "--color-black")}) | {"--radius"}
    return base, set(dark)


def same_atom(a, b):
    a, b = a.strip().strip('"'), b.strip().strip('"')
    if a == b:
        return True
    if "(" in a or "(" in b or a.startswith("#") or b.startswith("#"):
        try:
            ca, cb = colour.parse(a, {}), colour.parse(b, {})
        except (KeyError, ValueError):
            return False
        return all(abs(x - y) <= COLOUR_TOL for x, y in zip(ca, cb))
    ma, mb = (re.fullmatch(r"(-?[\d.]+)(px|rem)?", x) for x in (a, b))
    if ma and mb:
        zero = float(ma.group(1)) == 0 and float(mb.group(1)) == 0
        return zero or (float(ma.group(1)) == float(mb.group(1))
                        and (ma.group(2) or "px") == (mb.group(2) or "px"))
    return False


def same_value(a, b):
    """CSS values a and b mean the same: colours within half a byte per channel
    and alpha, dimensions as number + unit (0 equals 0px), lists and shadow
    layers item by item."""
    la, lb = split_top(a), split_top(b)
    if len(la) != len(lb):
        return False
    for x, y in zip(la, lb):
        ta, tb = split_top(x, " "), split_top(y, " ")
        if len(ta) != len(tb) or not all(same_atom(p, q) for p, q in zip(ta, tb)):
            return False
    return True


def check_theme(name, theme, tokens, expected):
    light_css, dark_css, common_css = tokens
    base_names, colour_names = expected
    for label, got, want, order in (("base", theme.base, base_names, THEME_ORDER["base"]),
                                    ("light", theme.light, colour_names, THEME_ORDER["colours"]),
                                    ("dark", theme.dark, colour_names, THEME_ORDER["colours"])):
        for n in sorted(want - set(got)):
            fail("themes", "%s: %s lacks %s" % (name, label, n))
        for n in sorted(set(got) - want):
            fail("themes", "%s: %s has unknown token %s" % (name, label, n))
        if set(got) == want and list(got) != ["--" + n for n in order]:
            fail("themes", "%s: %s tokens are out of order (alder reads them in file order); expected %s"
                 % (name, label, ", ".join(order)))
    try:
        common, light, dark = dtcg.resolved(theme)
    except dtcg.DTCGError as e:
        fail("themes", "%s: %s" % (name, e))
        return
    if name != "zinc":
        # --color-white/--color-black belong to every theme, not to its token files
        fixed = {k: common_css[k] for k in ("--color-white", "--color-black") if k in common_css}
        contrast_table(light, dark, {**fixed, **common}, where=name)
        return
    # zinc's contrast is tokens.css's: the parity check below proves the values equal
    for label, got, want in (("base", common, {**common_css, "--radius": light_css.get("--radius")}),
                             ("light", light, light_css), ("dark", dark, dark_css)):
        for n, v in got.items():
            if n in DERIVED_RADII or n not in want:
                continue
            if not same_value(v, want[n]):
                fail("themes", "zinc: %s %s is %s, tokens.css has %s" % (label, n, v, want[n]))


def check_themes(root, tokens):
    """Check every themes/<name>/ under root; returns how many were checked."""
    tdir = root / "themes"
    expected = theme_expected(tokens)
    if tdir.is_dir():
        for p in sorted(tdir.iterdir()):
            if p.is_dir() and p.name not in THEMES:
                fail("themes", "themes/%s is not in THEMES (%s)" % (p.name, ", ".join(THEMES)))
    count = 0
    for name in THEMES:
        d = tdir / name
        if not d.is_dir():
            fail("themes", "themes/%s is listed in THEMES but missing" % name)
            continue
        count += 1
        try:
            theme = dtcg.load_theme(d)
        except dtcg.DTCGError as e:
            fail("themes", "%s: %s" % (name, e))
            continue
        check_theme(name, theme, tokens, expected)
    return count


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


THEME_SCRIPT = ('<script>try{document.documentElement.classList.toggle("dark",localStorage.theme==="dark"||'
                '(!("theme" in localStorage)&&matchMedia("(prefers-color-scheme: dark)").matches))}catch(e){}</script>')


def check_demos(els):
    pages = {}
    for p in sorted((ROOT / "demo").glob("*.html")):
        text = p.read_text()
        link = text.find('href="../al.css"')
        if THEME_SCRIPT not in text or link < 0 or text.find(THEME_SCRIPT) > link:
            fail("demos", "demo/%s lacks the theme script line before ../al.css" % p.name)
        if "data-theme" in text or "dataset.theme" in text:
            fail("demos", "demo/%s uses data-theme" % p.name)
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


def check_tabs_nojs():
    """demo/tabs.html's no-JS form is the radio group only: labels wrapping radios and
    panels, no role, button or hidden (al-tabs.js builds those)."""
    text = (ROOT / "demo" / "tabs.html").read_text()
    i = text.index("<!-- no-js -->")
    sec = text[i:text.index("</section>", i)]
    if len(re.findall(r'<label><input type="radio"', sec)) < 2:
        fail("demos", "demo/tabs.html no-js section: tabs are not label-wrapped radios")
    for bad in ("role=", "<button", "hidden", "aria-"):
        if bad in sec:
            fail("demos", "demo/tabs.html no-js section contains %r: the no-JS form is radios and labels only" % bad)


def check_dialog_shape():
    """demo/dialog.html's dismissible dialog has the shape Alder's renderer emits
    (internal/ir/lower_html.go completeDialog): the close <form method="dialog">
    first with a type=submit button labelled "Close ...", then <h2 slot="header"
    id="<dialog id>-heading">, and the dialog's aria-labelledby naming that id."""
    class P(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.dlg, self.kids, self.depth, self.cur = None, [], 0, None
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "al-dialog" and "dismissible" in a:
                self.cur = "pending"
            elif tag == "dialog" and self.cur == "pending":
                self.dlg, self.cur, self.depth = a, "in", 0
            elif self.cur == "in":
                self.depth += 1
                if self.depth == 1 or (tag == "button" and self.depth == 2):
                    self.kids.append((tag, a))
        def handle_endtag(self, tag):
            if self.cur == "in":
                if tag == "dialog" and self.depth == 0:
                    self.cur = "done"
                else:
                    self.depth -= 1
    p = P()
    p.feed((ROOT / "demo" / "dialog.html").read_text())
    if not p.dlg:
        return fail("demos", "demo/dialog.html has no dismissible al-dialog")
    ids = p.dlg.get("id")
    first, second = (p.kids + [(None, {})] * 2)[:2]
    if first[0] != "form" or first[1].get("method") != "dialog":
        fail("demos", "dismissible dialog: the first child is not <form method=dialog>")
    if second[0] != "button" or second[1].get("type") != "submit" or not second[1].get("aria-label", "").startswith("Close"):
        fail("demos", "dismissible dialog: the close button is not <button type=submit aria-label='Close ...'>")
    h2 = next((a for t, a in p.kids if t == "h2"), {})
    if h2.get("slot") != "header" or h2.get("id") != ids + "-heading" or p.dlg.get("aria-labelledby") != ids + "-heading":
        fail("demos", "dismissible dialog: <h2 slot=header id=%s-heading> and aria-labelledby must match" % ids)


# ---------------------------------------------------------------- main

def main(argv):
    m, els = load_manifest()
    check_manifest(m, els)
    check_css(els)
    check_typography_weight()
    check_motion()
    check_focus()
    light, dark, common = load_tokens()
    defined = set(light) | set(dark) | set(common)
    check_tokens_only(defined)
    check_icons()
    check_tokens(light, dark, common)
    rows = contrast_table(light, dark, common)
    themes = check_themes(ROOT, (light, dark, common))
    check_demos(els)
    check_dialog_shape()
    check_tabs_nojs()
    if not (ROOT / "al.css").exists() or (ROOT / "al.css").read_text() != build.build():
        fail("bundle", "al.css is out of date: run python3 scripts/build.py")
    if not (ROOT / "index.html").exists() or (ROOT / "index.html").read_text() != build.showcase.build():
        fail("bundle", "index.html is out of date: run python3 scripts/build.py")
    if "--table" in argv:
        print("| use | foreground | background | needs | light | dark |")
        print("|---|---|---|---|---|---|")
        for use, fg, bg, need, lr, dr in rows:
            print("| %s | `%s` | `%s` | %.1f | %.2f | %.2f |" % (use, fg, bg, need, lr, dr))
    for w in WARNINGS:
        print("WARN", w)
    if FAILURES:
        for f in FAILURES:
            print("FAIL", f)
        print("%d failure(s)" % len(FAILURES))
        return 1
    print("ok: manifest, css, tokens-only, tokens, contrast (%d pairs x 2 themes), themes (%d), demos (%d pages), bundle"
          % (len(rows), themes, len(list((ROOT / "demo").glob("*.html")))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
