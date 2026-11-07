#!/usr/bin/env python3
"""Draw the pictures README.md uses.

README.md is written by hand and this script never touches it. The words inside
the pictures come from profile.toml; the numbers come from data/stats.json.
Text uses the visitor's system fonts, and nothing has a rounded corner.
Standard library only.
"""
import datetime
import json
import math
import pathlib
import tomllib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
STATS = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans','PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
MONO_EM = 0.6  # advance of a Latin monospace character, for laying out labels

THEMES = {
    "dark": dict(ink="#E6EDF3", sub="#9198A1", faint="#3D444D", red="#F0495A", blue="#5B93F0",
                 heat=["#1C222C", "#3D1E27", "#74222E", "#BC2A3C", "#FF6473"]),
    "light": dict(ink="#1F2328", sub="#59636E", faint="#D1D9E0", red="#D9263E", blue="#2D62CC",
                  heat=["#EDEFF2", "#FAD9DC", "#F2A6AE", "#E05666", "#A91529"]),
}
SLAB, ON_SLAB, TONE = "#D9263E", "#FFF8F0", "#7C1226"
ERA = {"flutter": "blue", "rust": "red"}
ERA_NAMES = [("Flutter", "flutter"), ("Rust", "rust")]

PROFILE = tomllib.loads((ROOT / "profile.toml").read_text(encoding="utf-8"))
OPENING = PROFILE["opening"]
TRACKS = [(track["name"], [tuple(node) for node in track["nodes"]]) for track in PROFILE["track"]]
SAVES = PROFILE["save"]


# ---------------------------------------------------------------- drawing helpers

def tokens(theme):
    if theme != "auto":
        return THEMES[theme]
    out = {}
    for key, value in THEMES["light"].items():
        out[key] = [f"var(--{key}{i})" for i in range(len(value))] if isinstance(value, list) else f"var(--{key})"
    return out


def auto_css():
    """Phone pictures pick their colours inside the file.

    GitHub's themed-picture owns any <source> that mentions prefers-color-scheme,
    so a width query cannot be combined with it there.
    """
    def block(theme):
        parts = []
        for key, value in THEMES[theme].items():
            if isinstance(value, list):
                parts += [f"--{key}{i}:{c}" for i, c in enumerate(value)]
            else:
                parts.append(f"--{key}:{value}")
        return ";".join(parts)
    return f":root{{{block('light')}}}@media (prefers-color-scheme:dark){{:root{{{block('dark')}}}}}"


def svg(width, height, theme, label, body, css="", defs=""):
    style = (auto_css() if theme == "auto" else "") + css + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title><style>{style}</style>'
            f'<defs>{defs}</defs>{body}</svg>')


def text(content, x, y, size, fill, font=MONO, anchor="start", weight=None):
    bold = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}"{bold}>{escape(content)}</text>')


def typed(content, x, y, size, fill, font, start, step):
    glyphs = "".join(f'<tspan class="ty" style="animation-delay:{start + i * step:.2f}s">{escape(ch)}</tspan>'
                     for i, ch in enumerate(content))
    return f'<text x="{x:.1f}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" xml:space="preserve">{glyphs}</text>'


def poly(points, fill, extra=""):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" {extra}/>'


def diamond(x, y, r, fill):
    return poly([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill)


def label_width(content, size):
    return sum(size * (MONO_EM if ch.isascii() else 1) for ch in content)


def stars(repo):
    return STATS["stars"].get(repo, 0)


def code39(content, height, unit):
    """Bars for a Code 39 string, as one path. Wide elements are 2.5 units."""
    table = {"*": "nwnnwnwnn", "M": "wnwnnnnwn", "C": "wnwnnwnnn", "D": "nnnnwwnnw", "F": "nnwnwwnnn",
             "S": "nnwnnnwwn", "T": "nnnnwnwwn", "E": "wnnnwwnnn", "V": "nwwnnnnnw"}
    out, cursor = [], 0.0
    for ch in f"*{content}*":
        for i, element in enumerate(table[ch]):
            width = unit * (2.5 if element == "w" else 1)
            if i % 2 == 0:
                out.append(f"M{cursor:.1f} 0h{width:.1f}v{height}h{-width:.1f}z")
            cursor += width
        cursor += unit
    return "".join(out)


def halftone(x0, y0, x1, y1, step, radius):
    """Screen tone made of diamonds, sized by radius(x, y)."""
    out, row, y = [], 0, y0
    while y <= y1:
        x = x0 + (step / 2 if row % 2 else 0)
        while x <= x1:
            r = radius(x, y)
            if r >= 0.35:
                out.append(f"M{x - r:.1f} {y:.1f}l{r:.1f} {-r:.1f} {r:.1f} {r:.1f} {-r:.1f} {r:.1f}z")
            x += step
        y += step * 0.5
        row += 1
    return "".join(out)


def own_source(count, width):
    """This file's code, as the texture on the red panel."""
    lines = pathlib.Path(__file__).read_text(encoding="utf-8").splitlines()
    return [line.rstrip()[:width] for line in lines if line.strip() and line.isascii()][:count]


def seven_segment(value, x, y, height, on, off):
    """Digits as skewed seven-segment polygons, the unlit segments still faintly there."""
    h = height
    w = h * 0.52
    t = h * 0.115
    c = t * 0.5
    gap = h * 0.16
    skew = h * 0.08
    lit = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
           "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}
    m = h / 2

    def horizontal(y0):
        a, b = t * 0.3, w - t * 0.3
        return [(a, y0), (a + c, y0 - c), (b - c, y0 - c), (b, y0), (b - c, y0 + c), (a + c, y0 + c)]

    def vertical(x0, y0, y1):
        a, b = y0 + t * 0.3, y1 - t * 0.3
        return [(x0, a), (x0 + c, a + c), (x0 + c, b - c), (x0, b), (x0 - c, b - c), (x0 - c, a + c)]

    shapes = {"a": horizontal(c), "g": horizontal(m), "d": horizontal(h - c), "f": vertical(c, c, m),
              "b": vertical(w - c, c, m), "e": vertical(c, m, h - c), "c": vertical(w - c, m, h - c)}
    on_path, off_path, cursor = [], [], x
    for ch in value:
        for name, pts in shapes.items():
            sheared = [(cursor + px + skew * (1 - py / h), y + py) for px, py in pts]
            d = "M" + "L".join(f"{px:.1f} {py:.1f}" for px, py in sheared) + "Z"
            (on_path if name in lit[ch] else off_path).append(d)
        cursor += w + gap
    return f'<path d="{"".join(off_path)}" fill="{off}"/><path d="{"".join(on_path)}" fill="{on}"/>', cursor - gap - x


def star_points(cx, cy, outer, inner):
    pts = []
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        a = math.radians(-90 + i * 36)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def months_since(date):
    a = datetime.date.fromisoformat(date)
    b = datetime.datetime.now(datetime.timezone.utc).date()
    return (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day)


# ---------------------------------------------------------------- opening

OPENING_CSS = """
@keyframes ty{from{fill-opacity:0}to{fill-opacity:1}}
.ty{animation:ty 1ms steps(1) backwards}
@keyframes slab{from{transform:translateX(420px)}}
.slab{animation:slab .5s cubic-bezier(.2,.9,.2,1) .3s backwards}
@keyframes s1{0%{transform:translateX(-46px);opacity:0}60%{transform:translateX(9px);opacity:1}}
@keyframes s2{0%{transform:translateX(52px);opacity:0}60%{transform:translateX(-7px);opacity:1}}
.n1{animation:s1 .32s steps(5) .45s backwards}.n2{animation:s2 .32s steps(5) .5s backwards}.n3{animation:s1 .32s steps(5) .55s backwards}
@keyframes rise{from{opacity:0;transform:translateY(8px)}}
.fade{animation:rise .3s ease-out backwards}
@keyframes nx{0%,100%{transform:translateY(0)}50%{transform:translateY(5px)}}
.nx{animation:nx 1.1s steps(2) infinite}
"""


def name_slices(x, baseline, size, length, fill, top):
    """The name lands in three slices. Slices overlap slightly so no seam stays."""
    cuts = [(top, 0.38), (top + size * 0.38, 0.26), (top + size * 0.64, 0.7)]
    defs = (f'<text id="name" x="{x}" y="{baseline}" font-family="{SANS}" font-size="{size}" font-weight="800" fill="{fill}" '
            f'textLength="{length}" lengthAdjust="spacingAndGlyphs">MCDFsteve</text>')
    uses = ""
    for i, (y, share) in enumerate(cuts, 1):
        defs += f'<clipPath id="c{i}"><rect x="0" y="{y:.1f}" width="{length + x + 40}" height="{size * share + .6:.1f}"/></clipPath>'
        uses += f'<g class="n{i}"><use href="#name" clip-path="url(#c{i})"/></g>'
    return defs, uses


def fetch_rows():
    """Rows under the name. Values with a {placeholder} are live numbers and show in red."""
    s = STATS
    uptime = months_since(s["since"])
    live = {"uptime": f"{uptime // 12}y {uptime % 12}m", "repos": s["repos"], "stars": s["stars_total"],
            "followers": s["followers"], "contributions": s["contributions"]}
    return [(row["key"], row["value"].format(**live), "red" if "{" in row["value"] else "ink") for row in OPENING["rows"]]


def vertical_columns(right, gap, top, bottom, largest):
    """The motto columns, right to left, shrunk when a column gets long."""
    texts = OPENING["vertical"]
    longest = max(len(chars) for chars in texts)
    pitch = min(largest * 1.12, (bottom - top) / max(longest - 1, 1))
    size = pitch / 1.12
    return [(chars, right - i * (size + gap)) for i, chars in enumerate(texts)], size, pitch


def panel(slab, source_x, tone_box, tone_top, columns, size, pitch, top, barcode=None):
    """The red panel: code as texture, screen tone, the motto set vertically."""
    clip = f'<clipPath id="slab"><polygon points="{" ".join(f"{x},{y}" for x, y in slab)}"/></clipPath>'
    rows = "".join(f'<tspan x="{source_x}" dy="10.5">{escape(line)}</tspan>' for line in own_source(34, 110))
    span = tone_box[3] - tone_top
    tone = halftone(*tone_box, 9.5, lambda x, y: max(0, (y - tone_top) / span) ** 1.4 * 5.6)
    out = ['<g class="slab"><g clip-path="url(#slab)">', poly(slab, SLAB),
           f'<text y="{slab[0][1] - 4}" font-family="{MONO}" font-size="7.6" fill="{ON_SLAB}" opacity=".26">{rows}</text>',
           f'<path d="{tone}" fill="{TONE}"/></g>']
    start = 0.8
    for chars, x in columns:
        for i, ch in enumerate(chars):
            out.append(f'<text class="ty" style="animation-delay:{start:.2f}s" x="{x:.1f}" y="{top + i * pitch:.1f}" '
                       f'font-family="{SANS}" font-size="{size}" font-weight="700" fill="{ON_SLAB}" text-anchor="middle">{escape(ch)}</text>')
            start += 0.04
    if barcode:
        out.append(f'<g transform="translate({barcode[0]} {barcode[1]}) rotate(90)"><path d="{code39("MCDFSTEVE", 17, 1.12)}" fill="{ON_SLAB}"/></g>')
    out.append("</g>")
    return clip, "".join(out)


def nameplate(width, y, t, plate):
    return (f'<rect x="0" y="{y}" width="{width}" height="2" fill="{t["red"]}"/>'
            + poly([(0, y - 20), (plate, y - 20), (plate - 20, y + 2), (0, y + 2)], t["red"])
            + text("MCDFsteve", 18, y - 3, 16, ON_SLAB, SANS, weight=700))


def opening(theme):
    t = tokens(theme)
    rule = 302
    slab = [(640, 0), (900, 0), (900, rule), (540, rule)]
    columns, size, pitch = vertical_columns(806, 28, 42, rule - 14, 34)
    clip, red = panel(slab, 530, (520, 120, 900, rule + 4), 120, columns, size, pitch, 42, (896, 16))
    defs, name = name_slices(26, 124, 88, 480, t["ink"], 56)
    prompt = OPENING["prompt"] + " "
    body = [red, text(prompt, 28, 42, 15, t["sub"]),
            typed("whoami", 28 + len(prompt) * 15 * MONO_EM, 42, 15, t["ink"], MONO, .1, .05), name]
    for i, (key, value, tone) in enumerate(fetch_rows()):
        y = 170 + i * 23
        body.append(f'<g class="fade" style="animation-delay:{.85 + i * .07:.2f}s">')
        body.append(text(key, 28, y, 15, t["blue"], weight=700) + text(value, 122, y, 15, t[tone]) + "</g>")
    body.append(nameplate(900, rule, t, 176))
    t0 = 1.5
    body.append(typed(OPENING["line"], 28, rule + 54, 24, t["ink"], SANS, t0, .05))
    t1 = t0 + len(OPENING["line"]) * .05 + .3
    body.append(typed(OPENING["motto"], 28, rule + 88, 16, t["sub"], MONO, t1, .02))
    body.append(f'<g class="ty" style="animation-delay:{t1 + .8:.2f}s"><polygon class="nx" points="850,{rule + 76} 872,{rule + 76} 861,{rule + 90}" fill="{t["red"]}"/></g>')
    return svg(900, rule + 108, theme, f"MCDFsteve：{OPENING['line']}{OPENING['motto']}", "".join(body), OPENING_CSS, clip + defs)


def opening_phone():
    t = tokens("auto")
    rule = 420
    slab = [(250, 118), (420, 118), (420, rule), (166, rule)]
    columns, size, pitch = vertical_columns(392, 19, 158, rule - 14, 27)
    clip, red = panel(slab, 160, (150, 260, 420, rule + 4), 260, columns, size, pitch, 158, None)
    defs, name = name_slices(18, 98, 72, 384, t["ink"], 38)
    prompt = OPENING["prompt"] + " "
    body = [red, text(prompt, 20, 26, 14, t["sub"]), typed("whoami", 20 + len(prompt) * 14 * MONO_EM, 26, 14, t["ink"], MONO, .1, .05), name]
    for i, (key, value, tone) in enumerate(fetch_rows()):
        y = 152 + i * 26
        body.append(text(key, 20, y, 14, t["blue"], weight=700) + text(value, 100, y, 14, t[tone]))
    body.append(nameplate(420, rule, t, 160))
    body.append(typed(OPENING["line"], 20, rule + 46, 20, t["ink"], SANS, 1.4, .05))
    body.append(typed(OPENING["motto"], 20, rule + 78, 14, t["sub"], MONO, 2.6, .02))
    body.append(f'<polygon class="nx" points="382,{rule + 66} 402,{rule + 66} 392,{rule + 79}" fill="{t["red"]}"/>')
    return svg(420, rule + 96, "auto", f"MCDFsteve：{OPENING['line']}{OPENING['motto']}", "".join(body), OPENING_CSS, clip + defs)


# ---------------------------------------------------------------- worldline

ROUTE_CSS = """
@keyframes dr{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.dr{stroke-dasharray:1;animation:dr 1.2s cubic-bezier(.4,0,.2,1) backwards}
@keyframes pu{0%{stroke-dashoffset:1;opacity:1}24%{stroke-dashoffset:0;opacity:1}24.1%,100%{opacity:0}}
.pu{opacity:0;stroke-dasharray:.06 .94;animation:pu 10s linear infinite}
@keyframes pop{from{opacity:0}}
.nd{animation:pop .2s steps(2) backwards}
"""


def run(path, colour, delay, width=2.5):
    return f'<path d="{path}" pathLength="1" fill="none" stroke="{colour}" stroke-width="{width}" class="dr" style="animation-delay:{delay:.2f}s"/>'


def worldline(theme):
    t = tokens(theme)
    x0, x1 = 86, 682
    first, last = (2025, 1), (2026, 12)
    span = (last[0] - first[0]) * 12 + last[1] - first[1]

    def px(date):
        year, month = int(date[:4]), int(date[5:7])
        return x0 + ((year - first[0]) * 12 + month - first[1]) / span * (x1 - x0)

    ys = [66 + i * 46 for i in range(len(TRACKS))]
    sink = (806, (ys[2] + ys[3]) / 2)
    out = []
    for year in (2025, 2026):
        x = px(f"{year}-01")
        out.append(f'<rect x="{x:.1f}" y="30" width="1" height="{ys[-1] - 16}" fill="{t["faint"]}"/>')
        out.append(text(str(year), x + 6, 28, 12, t["sub"]))
    key_x = 898
    for label, era in reversed(ERA_NAMES):
        key_x -= len(label) * 12 * MONO_EM
        out.append(text(label, key_x, 14, 12, t["sub"]))
        key_x -= 26
        out.append(f'<rect x="{key_x:.1f}" y="8" width="20" height="2.5" fill="{t[ERA.get(era, "sub")]}"/>')
        key_x -= 20
    for i, ((label, nodes), y) in enumerate(zip(TRACKS, ys)):
        out.append(text(label, 0, y + 5, 14, t["ink"], SANS))
        xs = [px(n[1]) for n in nodes]
        bend = sink[0] - abs(sink[1] - y)
        delay = .1 + i * .12
        for j, node in enumerate(nodes):
            end = xs[j + 1] if j + 1 < len(nodes) else bend
            out.append(run(f"M{xs[j]:.1f} {y}H{end:.1f}", t[ERA.get(node[2], "sub")], delay + j * .22))
        out.append(run(f"M{bend:.1f} {y}L{sink[0]} {sink[1]}", t["red"], delay + len(nodes) * .22 + .3))
        whole = f"M{xs[0]:.1f} {y}H{bend:.1f}L{sink[0]} {sink[1]}"
        out.append(f'<path d="{whole}" pathLength="1" fill="none" stroke="{t["ink"]}" stroke-width="2.5" class="pu" style="animation-delay:{2.2 + i * 1.6:.1f}s"/>')
        for j, (name, _, era) in enumerate(nodes):
            out.append(f'<g class="nd" style="animation-delay:{delay + j * .22 + .25:.2f}s">')
            out.append(diamond(xs[j], y, 5.5, t[ERA.get(era, "sub")]) + text(name, xs[j], y - 11, 12.5, t["ink"], anchor="middle") + "</g>")
    out.append(diamond(sink[0], sink[1], 11, t["red"]))
    out.append(text("Rust", sink[0] + 20, sink[1] + 7, 20, t["ink"], weight=600))
    return svg(900, ys[-1] + 18, theme, "世界线收束", "".join(out), ROUTE_CSS)


def worldline_phone():
    t = tokens("auto")
    out = []
    key_x = 0
    for label, era in ERA_NAMES:
        out.append(f'<rect x="{key_x:.1f}" y="8" width="18" height="2.5" fill="{t[ERA.get(era, "sub")]}"/>')
        out.append(text(label, key_x + 24, 14, 12.5, t["sub"]))
        key_x += 24 + len(label) * 12.5 * MONO_EM + 18
    bus = 404
    ys = [66 + i * 58 for i in range(len(TRACKS))]
    for (label, nodes), y in zip(TRACKS, ys):
        out.append(text(label, 0, y - 20, 13, t["sub"], SANS))
        cursor = 6.0
        marks = []
        for j, (name, _, era) in enumerate(nodes):
            nxt = cursor + len(name) * 13 * MONO_EM + 14
            end = nxt if j + 1 < len(nodes) else bus
            out.append(f'<rect x="{cursor:.1f}" y="{y + 11}" width="{end - cursor:.1f}" height="2" fill="{t[ERA.get(era, "sub")]}"/>')
            marks.append((cursor, name, era))
            cursor = nxt
        for x, name, era in marks:
            out.append(diamond(x, y + 12, 5, t[ERA.get(era, "sub")]) + text(name, x - 5, y + 2, 13, t["ink"]))
    bottom = ys[-1] + 44
    out.append(f'<rect x="{bus}" y="{ys[0] + 11}" width="2" height="{bottom - ys[0] - 11}" fill="{t["red"]}"/>')
    out.append(f'<path d="M{bus + 1} {ys[0] + 11}V{bottom}" pathLength="1" fill="none" stroke="{t["ink"]}" stroke-width="2" class="pu" style="animation-delay:2s"/>')
    out.append(diamond(bus + 1, bottom, 10, t["red"]))
    out.append(text("Rust", bus - 18, bottom + 7, 20, t["ink"], anchor="end", weight=600))
    return svg(420, bottom + 14, "auto", "世界线收束", "".join(out), ROUTE_CSS)


# ---------------------------------------------------------------- save slots

def icon(name, colour):
    s = f'fill="none" stroke="{colour}" stroke-width="3" stroke-linejoin="miter"'
    return {
        "bern": f'<path {s} d="M6 66V12L26 30H46L66 12V66Z"/><path fill="{colour}" d="M24 40h6v12h-6zM42 40h6v12h-6z"/>',
        "erika": f'<path {s} d="M24 14L58 36L24 58Z"/><path {s} d="M6 20V6H20M52 6H66V20M66 52V66H52M20 66H6V52"/>',
        "enji": "".join(f'<rect x="{6 + i * 10}" y="{36 - h}" width="5" height="{2 * h}" fill="{colour}"/>' for i, h in enumerate((8, 20, 30, 14, 26, 18, 6))),
        "nipaplay": f'<path {s} d="M6 12H66V54H6ZM28 22L46 33L28 44Z"/><path fill="{colour}" d="M14 61h44v3h-44z"/>',
        "saki": f'<path {s} d="M6 8H66V46H34L20 64V46H6Z"/><path fill="{colour}" d="M16 20h40v3h-40zM16 31h26v3h-26z"/>',
        "misarin": f'<path {s} d="M36 6L54 34L44 66H28L18 34Z"/><path {s} d="M36 6V38"/><path {s} d="M31 38h10v10h-10z"/>',
        "misuzu": f'<path {s} d="M26 56V12L60 6V48"/><path {s} d="M10 50H26V64H10ZM44 42H60V56H44Z"/>',
        "rustsend": f'<path {s} d="M6 34L66 6L50 66L32 44ZM66 6L32 44"/>',
    }.get(name, "")


def slot(theme, index, save, width=900):
    name, repo, era, stack, glyph = (save.get(k, "") for k in ("name", "repo", "era", "stack", "icon"))
    t = tokens(theme)
    count = str(stars(repo))
    number_w = len(count) * 16 * MONO_EM
    body = [f'<rect x="0" y="0" width="{width}" height="1" fill="{t["faint"]}"/>',
            poly([(0, 0), (34, 0), (28, 5), (0, 5)], t[ERA.get(era, "sub")]),
            f'<g transform="translate(0 16) scale(.5)">{icon(glyph, t["sub"])}</g>',
            text(f"SAVE {index:02d}", 48, 22, 11.5, t["sub"]),
            text(name, 48, 48, 24, t["ink"], SANS, weight=700),
            text(count, width, 44, 16, t["red"], anchor="end", weight=700),
            poly(star_points(width - number_w - 13, 38, 8, 3.4), t["red"])]
    if width == 900:
        body.append(text(stack, width - number_w - 36, 44, 13, t["sub"], anchor="end"))
    return svg(width, 58, theme, f"{name}，{count} Star", "".join(body))


# ---------------------------------------------------------------- observation

def language_rows():
    total = sum(STATS["languages"].values())
    top = list(STATS["languages"].items())[:5]
    rows = top + [("其他", total - sum(size for _, size in top))]
    return [(name, size / total) for name, size in rows]


def calendar(t, top, step, cell):
    weeks = STATS["weeks"]
    days = sorted(c for w in weeks for c in w if c)
    cuts = [days[int(len(days) * q)] for q in (.5, .8, .95)]  # only the busiest days get bright
    buckets = [[] for _ in t["heat"]]
    for wi, week in enumerate(weeks):
        for di, count in enumerate(week):
            level = 0 if count == 0 else 1 + sum(count > c for c in cuts)
            buckets[level].append(f"M{wi * step:.1f} {top + di * step:.1f}h{cell:.1f}v{cell:.1f}h{-cell:.1f}z")
    return "".join(f'<path d="{"".join(cells)}" fill="{colour}"/>' for colour, cells in zip(t["heat"], buckets))


def readouts():
    s = STATS
    return [("星标", s["stars_total"]), ("近一年贡献", s["contributions"]), ("公开仓库", s["repos"]), ("关注者", s["followers"])]


def observation(theme):
    s = STATS
    t = tokens(theme)
    off = t["heat"][0]

    def row_width(height):
        return sum(max(seven_segment(str(v), 0, 0, height, "", "")[1], label_width(k, 15)) for k, v in readouts()) + 56 * 3

    height = 78
    while row_width(height) > 900:  # numbers only grow; keep them inside the column
        height -= 2
    body, x = [], 0
    for label, value in readouts():
        body.append(text(label, x, 14, 15, t["sub"], SANS))
        markup, width = seven_segment(str(value), x, 28 + (78 - height), height, t["red"], off)
        body.append(markup)
        x += max(width, label_width(label, 15)) + 56
    top = 138
    body.append(calendar(t, top, 12, 10))
    right = (len(s["weeks"]) - 1) * 12 + 10
    end = datetime.date.fromisoformat(s["first_day"]) + datetime.timedelta(days=7 * (len(s["weeks"]) - 1))
    body.append(text(s["first_day"][:7], 0, top + 102, 12.5, t["sub"]))
    body.append(text(end.isoformat()[:7], right, top + 102, 12.5, t["sub"], anchor="end"))
    rows = language_rows()
    colours = {"Rust": t["red"], "Dart": t["blue"]}
    for i, (name, share) in enumerate(rows):
        y = top + 9 + i * 19
        body.append(text(name, 676, y, 13, t["ink"]))
        body.append(f'<rect x="768" y="{y - 9}" width="{max(share / rows[0][1] * 88, 1.5):.1f}" height="9" fill="{colours.get(name, t["sub"])}"/>')
        body.append(text(f"{share * 100:.1f}%", 900, y, 13, t["sub"], anchor="end"))
    return svg(900, 262, theme, "观测数据", "".join(body))


def observation_phone():
    s = STATS
    t = tokens("auto")
    off = t["heat"][0]
    body = []
    for (label, value), (x, y) in zip(readouts(), [(0, 0), (222, 0), (0, 112), (222, 112)]):
        body.append(text(label, x, y + 14, 15, t["sub"], SANS))
        body.append(seven_segment(str(value), x, y + 26, 62, t["red"], off)[0])
    step = 420 / len(s["weeks"])
    body.append(calendar(t, 236, step, step - 1.5))
    colours = {"Rust": t["red"], "Dart": t["blue"]}
    rows = language_rows()
    for i, (name, share) in enumerate(rows):
        y = 318 + i * 25
        body.append(text(name, 0, y, 15, t["ink"]))
        body.append(f'<rect x="112" y="{y - 11}" width="{max(share / rows[0][1] * 236, 2):.1f}" height="11" fill="{colours.get(name, t["sub"])}"/>')
        body.append(text(f"{share * 100:.1f}%", 420, y, 15, t["sub"], anchor="end"))
    return svg(420, 318 + len(rows) * 25 - 12, "auto", "观测数据", "".join(body))


def main():
    for theme in THEMES:
        out = ASSETS / theme
        out.mkdir(parents=True, exist_ok=True)
        files = {"opening": opening(theme), "worldline": worldline(theme), "observation": observation(theme)}
        for i, save in enumerate(SAVES, 1):
            files[f"save-{save['key']}"] = slot(theme, i, save)
        for name, doc in files.items():
            (out / f"{name}.svg").write_text(doc, encoding="utf-8")
    phone = ASSETS / "auto"
    phone.mkdir(exist_ok=True)
    files = {"opening": opening_phone(), "worldline": worldline_phone(), "observation": observation_phone()}
    for i, save in enumerate(SAVES, 1):
        files[f"save-{save['key']}"] = slot("auto", i, save, 420)
    for name, doc in files.items():
        (phone / f"{name}-phone.svg").write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    main()
