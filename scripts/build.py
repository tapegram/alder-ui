#!/usr/bin/env python3
"""Build al.css and al.js: tokens.css, base.css, typography.css, components/icons.css
(once it exists), then every component's CSS in manifest order,
all inside one cascade layer, @layer al, so a page's own (unlayered) CSS
always wins over alder-ui's whatever the specificity.

    python3 scripts/build.py          # write al.css and al.js
    python3 scripts/build.py --check  # exit 1 if al.css is out of date
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def component_paths():
    manifest = json.loads((ROOT / "custom-elements.json").read_text())
    return [mod["path"] for mod in manifest["modules"] if mod["path"].endswith(".css")]


def sheet_paths():
    """The bundle order: tokens, the base layer, typography, icons (once it
    exists), then the components in manifest order."""
    first = ["tokens.css", "base.css", "typography.css"]
    if (ROOT / "components" / "icons.css").exists():
        first.append("components/icons.css")
    return first + [p for p in component_paths() if p not in first]


def script_paths():
    manifest = json.loads((ROOT / "custom-elements.json").read_text())
    return [mod["path"] for mod in manifest["modules"] if mod["path"].endswith(".js")]


def build_js():
    """al.js: every script in manifest order, each in its own block so their
    names cannot clash. An ES module that imports nothing."""
    manifest = json.loads((ROOT / "custom-elements.json").read_text())
    parts = ["/*! alder-ui %s | Apache-2.0 | built by scripts/build.py from components/*.js; do not edit. */\n" % manifest["version"]]
    for rel in script_paths():
        parts.append("\n// ---- %s ----\n{\n%s\n}\n" % (rel, (ROOT / rel).read_text().strip("\n")))
    return "".join(parts)


def build():
    manifest = json.loads((ROOT / "custom-elements.json").read_text())
    parts = [
        "/*! alder-ui %s | Apache-2.0 | https://github.com/tapegram/alder-ui\n"
        " * Built by scripts/build.py from tokens.css, base.css, typography.css and components/;\n"
        " * do not edit. Geist and Geist Mono (SIL OFL 1.1) load from fonts/ beside this file. */\n"
        "\n@layer al {\n"
        % manifest["version"]
    ]
    for rel in sheet_paths():
        parts.append("\n/* ---- %s ---- */\n\n" % rel)
        parts.append((ROOT / rel).read_text().rstrip("\n") + "\n")
    parts.append("\n}\n")
    return "".join(parts)


def main(argv):
    outs = [(ROOT / "al.css", build()), (ROOT / "al.js", build_js())]
    if "--check" in argv:
        for out, text in outs:
            if not out.exists() or out.read_text() != text:
                print("%s is out of date: run python3 scripts/build.py" % out.name, file=sys.stderr)
                return 1
        return 0
    for out, text in outs:
        out.write_text(text)
        print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
