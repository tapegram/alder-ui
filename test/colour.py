"""Shared CSS colour engine (stdlib only): oklch, oklab, hsl, hex, rgb, transparent,
var(--x) and color-mix(in oklab|srgb, ...) with premultiplied alpha, to sRGB 0..1.

Used by test/check.py (contrast table) and test/parity.py (computed-style diff).
"""
import math
import re

COLOUR_FUNCS = ("rgb", "rgba", "hsl", "hsla", "oklch", "oklab", "color", "color-mix")
NAMED = {"transparent": (0.0, 0.0, 0.0, 0.0), "black": (0.0, 0.0, 0.0, 1.0), "white": (1.0, 1.0, 1.0, 1.0)}


def _srgb_to_linear(c):
    return c / 12.92 if abs(c) <= 0.04045 else math.copysign(((abs(c) + 0.055) / 1.055) ** 2.4, c)


def _linear_to_srgb(c):
    return 12.92 * c if abs(c) <= 0.0031308 else math.copysign(1.055 * abs(c) ** (1 / 2.4) - 0.055, c)


def _oklab_to_srgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_linear_to_srgb(x) for x in (r, g, bb))


def _srgb_to_oklab(r, g, b):
    r, g, b = (_srgb_to_linear(x) for x in (r, g, b))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _split_top(s, seps):
    """Split s at top-level (paren depth 0) separator characters; drops empty parts."""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and ch in seps:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _num(tok, pct=1.0):
    """A number; `n%` scales so 100% == pct; `none` is 0."""
    tok = tok.strip().lower()
    if tok == "none":
        return 0.0
    if tok.endswith("%"):
        return float(tok[:-1]) / 100 * pct
    return float(tok)


def _angle(tok):
    tok = tok.strip().lower()
    for unit, k in (("deg", 1.0), ("grad", 0.9), ("rad", 180 / math.pi), ("turn", 360.0)):
        if tok.endswith(unit):
            return float(tok[: -len(unit)]) * k
    return _num(tok)


def _channels_alpha(body):
    """`a b c / alpha` or `a, b, c, alpha` -> ([a, b, c], alpha-token-or-None)."""
    if "/" in body:
        main, alpha = body.split("/", 1)
        chans = _split_top(main, " ,")
        return chans, alpha.strip()
    chans = _split_top(body, " ,")
    if len(chans) == 4:
        return chans[:3], chans[3]
    return chans, None


def _alpha(tok):
    return 1.0 if tok is None else _num(tok, 1.0)


def _hsl(h, s, l):
    def f(n):
        k = (n + h / 30) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1, min(k - 3, 9 - k, 1))
    return f(0), f(8), f(4)


def _mix(body, env):
    parts = _split_top(body, ",")
    if len(parts) != 3:
        raise ValueError("color-mix needs a space and two colours: %r" % body)
    space = parts[0].split()
    if len(space) < 2 or space[0] != "in" or space[1] not in ("oklab", "srgb"):
        raise ValueError("color-mix space not supported: %r" % parts[0])
    cols, pcts = [], []
    for p in parts[1:]:
        toks = _split_top(p, " ")
        pct = None
        if toks and toks[-1].endswith("%") and "(" not in toks[-1]:
            pct = float(toks.pop()[:-1])
        elif toks and toks[0].endswith("%") and "(" not in toks[0]:
            pct = float(toks.pop(0)[:-1])
        cols.append(_parse(" ".join(toks), env))
        pcts.append(pct)
    p1, p2 = pcts
    if p1 is None and p2 is None:
        p1 = p2 = 50.0
    elif p1 is None:
        p1 = 100 - p2
    elif p2 is None:
        p2 = 100 - p1
    total = p1 + p2
    if total <= 0:
        raise ValueError("color-mix percentages sum to zero: %r" % body)
    w1, w2 = p1 / total, p2 / total
    (r1, g1, b1, a1), (r2, g2, b2, a2) = cols
    if space[1] == "oklab":
        c1, c2 = _srgb_to_oklab(r1, g1, b1), _srgb_to_oklab(r2, g2, b2)
    else:
        c1, c2 = (r1, g1, b1), (r2, g2, b2)
    alpha = a1 * w1 + a2 * w2
    if alpha == 0:
        mixed = tuple(x * w1 + y * w2 for x, y in zip(c1, c2))
    else:  # premultiplied interpolation (CSS Color 4/5)
        mixed = tuple((x * a1 * w1 + y * a2 * w2) / alpha for x, y in zip(c1, c2))
    rgb = _oklab_to_srgb(*mixed) if space[1] == "oklab" else mixed
    return (*rgb, alpha * min(total, 100) / 100)


def _parse(s, env):
    """A CSS colour -> (r, g, b, a) floats in sRGB, unclamped."""
    s = s.strip()
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", s)
    if m:
        if m.group(1) not in env:
            raise ValueError("undefined %s" % m.group(1))
        return _parse(env[m.group(1)], env)
    low = s.lower()
    if low in NAMED:
        return NAMED[low]
    m = re.fullmatch(r"#([0-9a-fA-F]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            raise ValueError("bad hex colour: %r" % s)
        vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return tuple(vals) if len(vals) == 4 else (*vals, 1.0)
    m = re.fullmatch(r"([a-z-]+)\((.*)\)", low, re.S)
    if not m or m.group(1) not in COLOUR_FUNCS:
        raise ValueError("not a colour: %r" % s)
    fn, body = m.groups()
    if fn == "color-mix":
        return _mix(body, env)
    if fn in ("rgb", "rgba"):
        chans, a = _channels_alpha(body)
        return (*(_num(c, 255) / 255 for c in chans), _alpha(a))
    if fn in ("hsl", "hsla"):
        chans, a = _channels_alpha(body)
        h, sat, lig = _angle(chans[0]), _num(chans[1], 1.0), _num(chans[2], 1.0)
        if not chans[1].endswith("%"):
            sat /= 100
        if not chans[2].endswith("%"):
            lig /= 100
        return (*_hsl(h, sat, lig), _alpha(a))
    if fn == "oklch":
        chans, a = _channels_alpha(body)
        L, C, H = _num(chans[0], 1.0), _num(chans[1], 0.4), _angle(chans[2])
        return (*_oklab_to_srgb(L, C * math.cos(math.radians(H)), C * math.sin(math.radians(H))), _alpha(a))
    if fn == "oklab":
        chans, a = _channels_alpha(body)
        L, A, B = _num(chans[0], 1.0), _num(chans[1], 0.4), _num(chans[2], 0.4)
        return (*_oklab_to_srgb(L, A, B), _alpha(a))
    # color(<space> r g b / a)
    main, _, a = body.partition("/")
    space, *chans = main.split()
    a = a.strip() or None
    if len(chans) != 3:
        raise ValueError("color() needs three channels: %r" % s)
    vals = [_num(c, 1.0) for c in chans]
    if space == "srgb":
        return (*vals, _alpha(a))
    if space == "srgb-linear":
        return (*(_linear_to_srgb(v) for v in vals), _alpha(a))
    raise ValueError("color() space not supported: %r" % s)


def _byte(x):
    return int(math.floor(min(1.0, max(0.0, x)) * 255 + 0.5))


def parse(expr, env):
    """A CSS colour -> (r, g, b, alpha), sRGB clamped to 0..1, var(--x) looked up in env."""
    return tuple(min(1.0, max(0.0, x)) for x in _parse(expr, env))


def normalise_colour(s):
    """Any supported CSS colour -> (r, g, b, a), 8-bit sRGB, alpha 0-255. ValueError otherwise."""
    return tuple(_byte(x) for x in _parse(s, {}))


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


def contrast(fg, bg, env):
    """Contrast of fg on bg, both CSS colours; translucent colours are
    composited over the theme's --background first."""
    base = parse("var(--background)", env)
    b = over(parse(bg, env), base)
    return ratio_rgb(over(parse(fg, env), b), b)

