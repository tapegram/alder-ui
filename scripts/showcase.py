"""index.html, the one-page showcase GitHub Pages serves at the repo root:
the colour tokens, then every demo page's content in order, unmodified, with
its h1 as the section heading. It links al.css and al.js beside it, so it
always shows the library as built. Only the page chrome (the sticky nav and
the token swatches) has styles of its own.

scripts/build.py writes it; test/check.py fails when it is out of date.
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dtcg  # noqa: E402

# The themes the select offers, in order; test_showcase asserts this equals
# check.THEMES (check.py imports from scripts/, so it cannot be imported here).
THEMES = ["zinc", "brutal", "catppuccin", "paper", "pebble"]

# The demo pages in index order; parity.html is a test fixture, not a demo.
ORDER = ["button", "input", "textarea", "select", "checkbox", "table", "card",
         "badge", "alert", "pagination", "stack", "page", "dialog", "popover",
         "menu", "tabs", "toast", "tooltip", "devpanel"]

THEME = ('<script>try{document.documentElement.classList.toggle("dark",localStorage.theme==="dark"'
         '||(!("theme" in localStorage)&&matchMedia("(prefers-color-scheme: dark)").matches));'
         'var t=localStorage.dsTheme;if(%s.indexOf(t)>0)document.documentElement.classList.add("theme-"+t)}catch(e){}</script>'
         % json.dumps(THEMES, separators=(",", ":")))

CHROME = """\
.ds-top{position:sticky;top:0;z-index:5;background:var(--background);border-bottom:1px solid var(--border);padding:10px max(16px, env(safe-area-inset-left, 0px))}
.ds-nav{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px}
.ds-nav a{color:var(--muted-foreground);text-decoration:none}
.ds-nav a:hover,.ds-nav a:focus-visible{color:var(--foreground)}
.ds-sec{scroll-margin-top:96px;border-top:1px solid var(--border);padding-top:32px}
.ds-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.ds-sw{display:flex;flex-direction:column;gap:6px;min-width:0}
.ds-sw span{height:44px;border-radius:var(--radius);border:1px solid var(--border)}
.ds-sw code{font-size:11px;overflow-wrap:anywhere}"""


def theme_css(name):
    """The showcase's blocks for one theme: custom properties only, scoped to
    html.theme-<name> (light, with the theme's base) and html.theme-<name>.dark.
    Zinc is the stylesheet's own default, so it has none."""
    if name == "zinc":
        return ""
    common, light, dark = dtcg.resolved(dtcg.load_theme(str(ROOT / "themes" / name)))
    block = lambda sel, props: "%s{%s}" % (sel, "".join("%s:%s;" % kv for kv in props.items()))
    return (block("html.theme-%s" % name, {**common, **light})
            + block("html.theme-%s.dark" % name, dark))


def theme_select():
    opts = ""
    for n in THEMES:
        t = dtcg.load_theme(str(ROOT / "themes" / n))
        opts += '<option value="%s" title="%s">%s</option>' % (n, html.escape(t.description), html.escape(t.name))
    return ('<al-select label="Theme"><label>Theme<select id="ds-theme" onchange="setTheme(this.value)">%s</select></label></al-select>'
            % opts)


def colour_tokens():
    """Every theme colour token in tokens.css order (not --radius, fonts,
    shadows, Tailwind's --color-* or alder-ui's own --al-*)."""
    names = []
    for n in re.findall(r"^\s*(--[a-z0-9-]+):", (ROOT / "tokens.css").read_text(), re.M):
        if n not in names and not re.match(r"--(al-|_|radius|font|shadow|color-)", n):
            names.append(n)
    return names


def section(name):
    """One demo page's content: everything in its outer al-page after the
    back-link row, h1 as the section heading and h2s demoted to h3."""
    src = (ROOT / "demo" / ("%s.html" % name)).read_text()
    body = re.split(r"<al-page[^>]*>", src.split("<body>", 1)[1], maxsplit=1)[1]
    body = body.rsplit("</al-page>", 1)[0].split("</al-stack>\n<h1>", 1)[1]
    title, rest = body.split("</h1>", 1)
    rest = re.sub(r"<(/?)h2>", r"<\1h3>", rest.rsplit("</al-stack>", 1)[0])
    if name == "toast":
        # The sticky corner regions would cover the whole page here; keep only
        # the region the "Show a toast" button adds to.
        rest = re.sub(r'<al-toasts popover="manual" position="[^"]*"( id="demo-toasts")?>.*?</al-toasts>\n',
                      lambda m: '<al-toasts popover="manual" position="bottom-right" id="demo-toasts"></al-toasts>\n'
                      if m.group(1) else "", rest)
        rest = rest.replace("These are sticky", "On demo/toast.html these are sticky")
    sec = '<section id="%s" class="ds-sec"><al-stack gap="md"><h2>%s</h2>%s</al-stack></section>\n'
    return title, sec % (name, title, rest)


def build():
    version = json.loads((ROOT / "custom-elements.json").read_text())["version"]
    parts = [section(n) for n in ORDER]
    nav = "".join('<a href="#%s">%s</a>' % (n, t.replace("al-", "")) for n, (t, _) in zip(ORDER, parts))
    swatches = "".join('<div class="ds-sw"><span style="background:var(%s)"></span><code>%s</code></div>' % (t, t)
                       for t in colour_tokens())
    return """<!doctype html>
<!-- Built by scripts/build.py from demo/*.html; do not edit. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>alder-ui %(v)s</title>
%(theme)s
<link rel="stylesheet" href="al.css">
<script type="module" src="al.js"></script>
<script>
function toggleTheme(){var d=document.documentElement.classList.toggle("dark");try{localStorage.theme=d?"dark":"light"}catch(e){}}
function setTheme(n){var c=document.documentElement.classList;c.forEach(function(x){if(x.indexOf("theme-")===0)c.remove(x)});if(n!=="zinc")c.add("theme-"+n);try{localStorage.dsTheme=n}catch(e){}}
</script>
<style>
%(chrome)s
</style>
<style id="ds-themes">
%(themes)s
</style>
</head>
<body>
<div class="ds-top"><al-stack gap="sm"><al-stack direction="row" gap="sm"><strong>alder-ui %(v)s</strong><al-button variant="outline" size="sm"><button type="button" onclick="toggleTheme()">Toggle theme</button></al-button>%(select)s</al-stack><nav class="ds-nav"><a href="#tokens">tokens</a>%(nav)s</nav></al-stack></div>
<al-page>
<al-stack gap="lg">
<h1>alder-ui %(v)s</h1>
<p>A light-DOM, token-based design system with shadcn/ui's look (new-york-v4, neutral): plain CSS in <code>@layer al</code>, plus small scripts that progressively enhance the interactive elements. This page links the built <code>al.css</code> and <code>al.js</code> and shows every element's demo as it renders. The per-element pages, which also show the no-JavaScript fallbacks, are in <a href="demo/index.html">demo/</a>. Source and docs: <a href="https://github.com/tapegram/alder-ui">github.com/tapegram/alder-ui</a>.</p>
<section id="tokens" class="ds-sec"><al-stack gap="md"><h2>Colour tokens</h2><p>shadcn's canonical neutral theme, verbatim oklch values. Re-theme by pasting a shadcn or tweakcn export after <code>al.css</code>.</p><div class="ds-grid">%(swatches)s</div></al-stack></section>
%(sections)s</al-stack>
</al-page>
<script>try{var s=document.getElementById("ds-theme"),t=localStorage.dsTheme;if(%(known)s.indexOf(t)>0)s.value=t}catch(e){}</script>
</body>
</html>
""" % {"v": version, "theme": THEME, "known": json.dumps(THEMES), "chrome": CHROME, "select": theme_select(),
       "themes": "\n".join(theme_css(n) for n in THEMES[1:]), "nav": nav, "swatches": swatches,
       "sections": "".join(s for _, s in parts)}
