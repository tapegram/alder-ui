"""Read a theme directory of DTCG (format 2025.10) files and render CSS values.

A theme dir holds theme.resolver.json plus base/light/dark .tokens.json. A
token's name (last path segment) is its CSS custom property without the `--`.
Stdlib only.
"""
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


class DTCGError(Exception):
    pass


@dataclass
class Token:
    css: str          # CSS custom property name, with the leading --
    type: str         # color | dimension | fontFamily | shadow
    value: object     # the raw $value (alias strings stay "{group.name}")
    description: str
    file: str         # file name the token came from


@dataclass
class Theme:
    name: str
    description: str
    base: dict
    light: dict
    dark: dict


TYPES = ("color", "dimension", "fontFamily", "shadow")
ALIAS = re.compile(r"^\{([^{}]+)\}$")
GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "cursive", "fantasy",
                    "system-ui", "math", "emoji", "fangsong",
                    "SFMono-Regular", "Menlo", "Monaco", "Consolas"}


def _read(path, file):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DTCGError(f"{file}: file not found")
    except (OSError, UnicodeDecodeError) as e:
        raise DTCGError(f"{file}: cannot read: {e}")
    except json.JSONDecodeError as e:
        raise DTCGError(f"{file}: line {e.lineno}: {e.msg}")


def _ref_path(d, ref, where):
    if not isinstance(ref, str) or not ref or ref.startswith("/") or ".." in Path(ref).parts:
        raise DTCGError(f"{where}: bad $ref {ref!r}")
    return d / ref, ref


def _refs(node, where):
    if not isinstance(node, list):
        raise DTCGError(f"{where}: expected a list of $ref sources")
    out = []
    for s in node:
        if not isinstance(s, dict) or "$ref" not in s:
            raise DTCGError(f"{where}: source without $ref")
        out.append(s["$ref"])
    return out


def _fmt(n):
    if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n):
        raise ValueError(f"not a finite number: {n!r}")
    if n == int(n):
        return str(int(n))
    return repr(float(n))


def _is_alias(v):
    return isinstance(v, str) and ALIAS.match(v) is not None


def _alias(v, scope):
    path = ALIAS.match(v).group(1)
    if scope is not None and "--" + path.split(".")[-1] not in scope:
        raise DTCGError(f"alias {{{path}}} does not resolve")
    return f"var(--{path.split('.')[-1]})"


def _colour(v, scope):
    if _is_alias(v):
        return _alias(v, scope)
    if not isinstance(v, dict) or "colorSpace" not in v:
        raise ValueError("not a colour object")
    comps = v.get("components")
    if not isinstance(comps, list) or len(comps) != 3:
        raise ValueError("colour needs 3 components")
    alpha = v.get("alpha")
    if alpha == 1:
        alpha = None
    tail = "" if alpha is None else f" / {_fmt(alpha)}"
    space = v["colorSpace"]
    if space == "oklch":
        return f"oklch({' '.join(_fmt(c) for c in comps)}{tail})"
    if space == "srgb":
        if alpha is None and v.get("hex"):
            return v["hex"]
        rgb = " ".join(str(round(c * 255)) for c in comps)
        return f"rgb({rgb}{tail})"
    raise ValueError(f"unsupported colorSpace {space!r}")


def _dimension(v):
    if not isinstance(v, dict) or v.get("unit") not in ("px", "rem") or "value" not in v:
        raise ValueError("not a dimension object")
    if v["value"] == 0:
        return "0"
    return _fmt(v["value"]) + v["unit"]


def _family(name):
    if not isinstance(name, str):
        raise ValueError("font family must be a string")
    return name if name in GENERIC_FAMILIES or name.startswith("ui-") else f'"{name}"'


def _font(v):
    names = v if isinstance(v, list) else [v]
    return ", ".join(_family(n) for n in names)


def _shadow_layer(v, scope):
    if not isinstance(v, dict):
        raise ValueError("shadow layer must be an object")
    parts = [_dimension(v[k]) for k in ("offsetX", "offsetY", "blur", "spread")]
    parts.append(_colour(v["color"], scope))
    return ("inset " if v.get("inset") else "") + " ".join(parts)


def _render(type_, v, scope):
    """Render a value of `type_`; scope None skips alias existence checks."""
    if type_ == "color":
        return _colour(v, scope)
    if _is_alias(v):
        return _alias(v, scope)
    if type_ == "dimension":
        return _dimension(v)
    if type_ == "fontFamily":
        return _font(v)
    if type_ == "shadow":
        return ", ".join(_shadow_layer(x, scope) for x in (v if isinstance(v, list) else [v]))
    raise ValueError(f"unsupported $type {type_!r}")


def _walk(node, inherited, file, out):
    for key, val in node.items():
        if key.startswith("$"):
            continue
        if not isinstance(val, dict):
            raise DTCGError(f"{file}: {key}: expected a group or token object")
        typ = val.get("$type", inherited)
        if "$value" in val:
            if typ not in TYPES:
                raise DTCGError(f"{file}: {key}: missing or unsupported $type {typ!r}")
            desc = val.get("$description")
            if not isinstance(desc, str) or not desc:
                raise DTCGError(f"{file}: {key}: missing $description")
            css = "--" + key
            if css in out:
                raise DTCGError(f"{file}: {key}: duplicate token")
            try:
                _render(typ, val["$value"], None)
            except (ValueError, KeyError, TypeError) as e:
                raise DTCGError(f"{file}: {key}: value is not a valid {typ}: {e}")
            out[css] = Token(css, typ, val["$value"], desc, file)
        else:
            _walk(val, typ, file, out)


def _load_tokens(d, ref, where):
    path, file = _ref_path(d, ref, where)
    data = _read(path, file)
    if not isinstance(data, dict):
        raise DTCGError(f"{file}: top level must be an object")
    out = {}
    _walk(data, None, file, out)
    return out


def _merge(d, refs, where):
    out = {}
    for r in refs:
        for k, t in _load_tokens(d, r, where).items():
            if k in out:
                raise DTCGError(f"{t.file}: {k[2:]}: duplicate token")
            out[k] = t
    return out


def load_theme(dir):
    d = Path(dir)
    res = _read(d / "theme.resolver.json", "theme.resolver.json")
    w = "theme.resolver.json"
    try:
        base = _refs(res["sets"]["base"]["sources"], w)
        ctx = res["modifiers"]["scheme"]["contexts"]
        light, dark = _refs(ctx["light"], w), _refs(ctx["dark"], w)
        name, desc = res["name"], res["description"]
    except (KeyError, TypeError):
        raise DTCGError(f"{w}: needs name, description, sets.base.sources and "
                        "modifiers.scheme.contexts.light/dark")
    return Theme(name, desc, _merge(d, base, w), _merge(d, light, w), _merge(d, dark, w))


def css_value(tok, scope):
    try:
        return _render(tok.type, tok.value, scope)
    except DTCGError as e:
        raise DTCGError(f"{tok.file}: {tok.css[2:]}: {e}")
    except (ValueError, KeyError, TypeError) as e:
        raise DTCGError(f"{tok.file}: {tok.css[2:]}: {e}")


def resolved(theme):
    names = {**theme.base, **theme.light, **theme.dark}
    out = []
    for toks, scope in ((theme.base, names), (theme.light, {**theme.base, **theme.light}),
                        (theme.dark, {**theme.base, **theme.dark})):
        out.append({k: css_value(t, scope) for k, t in toks.items()})
    return tuple(out)
