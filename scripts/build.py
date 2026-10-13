#!/usr/bin/env python3
"""Build al.css: tokens.css, then every component's CSS in manifest order,
all inside one cascade layer, @layer al, so a page's own (unlayered) CSS
always wins over alder-ui's whatever the specificity.

    python3 scripts/build.py          # write al.css
    python3 scripts/build.py --check  # exit 1 if al.css is out of date
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def component_paths():
    manifest = json.loads((ROOT / "custom-elements.json").read_text())
    return [mod["path"] for mod in manifest["modules"]]


def build():
    manifest = json.loads((ROOT / "custom-elements.json").read_text())
    parts = [
        "/*! alder-ui %s | Apache-2.0 | https://github.com/tapegram/alder-ui\n"
        " * Built by scripts/build.py from tokens.css and components/; do not edit. */\n"
        "\n@layer al {\n"
        % manifest["version"]
    ]
    for rel in ["tokens.css"] + component_paths():
        parts.append("\n/* ---- %s ---- */\n\n" % rel)
        parts.append((ROOT / rel).read_text().rstrip("\n") + "\n")
    parts.append("\n}\n")
    return "".join(parts)


def main(argv):
    out = ROOT / "al.css"
    text = build()
    if "--check" in argv:
        if not out.exists() or out.read_text() != text:
            print("al.css is out of date: run python3 scripts/build.py", file=sys.stderr)
            return 1
        return 0
    out.write_text(text)
    print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
