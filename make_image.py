#!/usr/bin/env python3
"""Draw "20 November 2026" as a single-page world news front page.

Pure deterministic drawing: rectangles, arcs, polygons and text. No
randomness, no network, no external images -- only the DejaVu fonts that
ship with the system.

    python3 make_image.py   ->   ./entry.png   (1024x1024, RGB)
"""

from __future__ import annotations

import math
import os
import sys
from typing import Callable, NamedTuple

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- palette ---

BG = (11, 18, 32)          # #0B1220 deep navy
CARD = (21, 31, 51)        # #151F33
RULE = (42, 58, 87)        # #2A3A57
BODY = (215, 222, 234)     # #D7DEEA
WHITE = (255, 255, 255)
AMBER = (242, 179, 61)     # #F2B33D
TEAL = (79, 209, 197)      # #4FD1C5
MUTED = (168, 180, 198)
STEEL = (146, 162, 185)
BLOCK = (72, 90, 120)      # unlit skyline blocks
GLOW = (255, 214, 140)

W = H = 1024
M = 38
L, R = M, W - M            # 38 .. 986
NB = "\u00a0"              # non-breaking space inside a phrase

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
BOLD = FONT_DIR + "DejaVuSans-Bold.ttf"
REG = FONT_DIR + "DejaVuSans.ttf"

_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


# ------------------------------------------------------------------ text ----

def track_width(text: str, f, tracking: float) -> float:
    if not text:
        return 0.0
    return sum(f.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(d, xy, text, f, fill, tracking: float = 0.0) -> float:
    """Letter-spaced text; the ink top of the line lands on xy[1]."""
    x, y = xy
    y -= f.getbbox(text)[1]
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking
    return x - tracking


def draw_text(d, xy, text, f, fill) -> float:
    x, y = xy
    y -= f.getbbox(text)[1]
    d.text((x, y), text, font=f, fill=fill)
    return x + f.getlength(text)


def fit_tracked(text, path, size, tracking, width, floor=20):
    s = size
    while s > floor and track_width(text, font(path, s), tracking) > width:
        s -= 1
    return font(path, s)


def fit_block(lines, path, size, width, leading=1.08, floor=20):
    """Largest size at which every given line fits `width`."""
    s = size
    while s > floor and max(font(path, s).getlength(t) for t in lines) > width:
        s -= 1
    return font(path, s), round(s * leading)


def wrap(text: str, f, width: float) -> list[str]:
    """Greedy wrap on ordinary spaces only, so NBSP keeps names together."""
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if f.getlength(trial) <= width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = w
    if cur:
        lines.append(cur)
    return [ln.replace(NB, " ") for ln in lines]


def fit_wrapped(text, path, size, width, max_lines, leading=1.28, floor=20):
    s = size
    while s > floor:
        f = font(path, s)
        ls = wrap(text, f, width)
        if len(ls) <= max_lines:
            return f, ls, round(s * leading)
        s -= 1
    f = font(path, floor)
    return f, wrap(text, f, width)[:max_lines], round(floor * leading)


# ------------------------------------------------------------- furniture ----

def card(d, box, radius=12) -> None:
    d.rounded_rectangle(box, radius=radius, fill=CARD, outline=RULE, width=1)


def hline(d, x0, y, x1, colour=RULE, thickness=1) -> None:
    d.rectangle((x0, y, x1, y + thickness - 1), fill=colour)


def dash(d, pts, colour, width=2, on=5.0, off=5.0) -> None:
    drawing = True
    left = float(on)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg <= 0:
            continue
        pos = 0.0
        while pos < seg:
            step = min(left, seg - pos)
            if drawing:
                a, b = pos / seg, (pos + step) / seg
                d.line((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a,
                        x0 + (x1 - x0) * b, y0 + (y1 - y0) * b),
                       fill=colour, width=width)
            pos += step
            left -= step
            if left <= 1e-9:
                drawing = not drawing
                left = on if drawing else off


def bezier(p0, p1, p2, steps=40):
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def rot_rect(cx, cy, w, h, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)
            for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2),
                           (w / 2, h / 2), (-w / 2, h / 2))]


def star(cx, cy, r_out, r_in, points=5, phase=-90.0):
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(phase + i * 180.0 / points)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ------------------------------------------------------------- pictograms ---

def pict_bomber(d, box) -> None:
    """Top-down bomber, three dashed bomb paths, a skyline taking the hit."""
    x0, y0, x1, y1 = box
    bw = x1 - x0
    s = bw / 260.0
    cx = (x0 + x1) / 2
    cy = y0 + 44 * s

    # flying-wing silhouette: nose, swept wings, tail
    body = [(0, -34), (9, -10), (104, 12), (104, 19), (30, 12), (14, 26),
            (14, 36), (-14, 36), (-14, 26), (-30, 12), (-104, 19),
            (-104, 12), (-9, -10)]
    d.polygon([(cx + px * s, cy + py * s) for px, py in body], fill=STEEL)

    # skyline: nine blocks standing on one baseline
    base = y1 - 12 * s
    n, gap = 9, 6.25
    bwd = (bw - 12 * s - gap * (n - 1) * s) / n
    heights = [58, 86, 44, 92, 104, 70, 96, 50, 68]
    hit = 4
    xs = []
    bx = x0 + 6 * s
    for i, hgt in enumerate(heights):
        top = base - hgt * s
        xs.append((bx, top, bx + bwd, base))
        if i == hit:
            d.rectangle((bx, top, bx + bwd, base), fill=AMBER)
            d.rectangle((bx, top, bx + bwd, top + 3 * s), fill=GLOW)
        else:
            d.rectangle((bx, top, bx + bwd, base), fill=BLOCK)
            # two slim window columns keep the blocks reading as buildings
            wy = top + 9 * s
            while wy < base - 8 * s:
                d.rectangle((bx + 4 * s, wy, bx + 7 * s, wy + 4 * s), fill=(30, 43, 66))
                d.rectangle((bx + bwd - 7 * s, wy, bx + bwd - 4 * s, wy + 4 * s),
                            fill=(30, 43, 66))
                wy += 9 * s
        bx += bwd + gap * s

    hline(d, x0 + 2 * s, base, x1 - 2 * s, (52, 68, 94), 3)

    # bomb paths: three trails landing on three different blocks
    for idx, off in ((2, -58), (hit, 0), (6, 58)):
        bx0, btop, bx1, _ = xs[idx]
        tgt = (bx0 + bx1) / 2
        p0 = (cx + off * s, cy + 42 * s)
        p1 = (cx + off * 0.88 * s, cy + 98 * s)
        p2 = (tgt, btop)
        dash(d, bezier(p0, p1, p2), AMBER, max(2, round(2 * s)),
             on=5 * s, off=6 * s)
        r = 3.0 * s
        d.rectangle((bx0 + 1 * s, btop - 2 * s, bx1 - 1 * s, btop), fill=GLOW)
        d.ellipse((p2[0] - r, p2[1] - r - 1 * s, p2[0] + r, p2[1] + r - 1 * s),
                  fill=GLOW)


def pict_ipo(d, box) -> None:
    """Three rising bars under an upward arrow."""
    x0, y0, x1, y1 = box
    s = (x1 - x0) / 48.0
    base = y1 - 7 * s
    bwid = 8 * s
    for fx, fh in ((0.10, 14), (0.38, 22), (0.66, 30)):
        bx = x0 + fx * (x1 - x0)
        d.rectangle((bx, base - fh * s, bx + bwid, base), fill=STEEL)
    p0 = (x0 + 3 * s, y0 + 30 * s)
    p1 = (x0 + 21 * s, y0 + 17 * s)
    p2 = (x1 - 5 * s, y0 + 3 * s)
    d.line([p0, p1, p2], fill=TEAL, width=max(2, round(2.6 * s)), joint="curve")
    tipx, tipy = p2
    d.polygon([(tipx + 1 * s, tipy - 1 * s), (tipx - 4 * s, tipy + 2 * s),
               (tipx - 1 * s, tipy + 7 * s)], fill=TEAL)


def pict_gavel(d, box) -> None:
    """Gavel resting beside its round block."""
    x0, y0, x1, y1 = box
    s = (x1 - x0) / 48.0
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    # handle rising to the right, head set across its far end
    d.polygon(rot_rect(cx - 1 * s, cy + 7 * s, 30 * s, 5 * s, 40), fill=STEEL)
    d.polygon(rot_rect(cx + 12 * s, cy - 7 * s, 16 * s, 12 * s, 130), fill=TEAL)
    r = 5.6 * s
    bx, by = cx + 13 * s, y1 - 6 * s
    d.ellipse((bx - r, by - r, bx + r, by + r), fill=STEEL)


def pict_cyclone(d, box) -> None:
    """A tightening spiral with a calm eye: the cyclone symbol."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    s = (x1 - x0) / 48.0
    steps = 96
    pts = []
    for i in range(steps + 1):
        t = i / steps
        ang = math.radians(-70 + 660 * t)
        r = 20 * s * (1 - 0.72 * t)
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    # three passes over the same spiral, thinning toward the eye
    for lo, hi, wdt, col in ((0.0, 0.4, 3.4, STEEL),
                             (0.35, 0.72, 2.6, STEEL),
                             (0.68, 0.9, 2.0, TEAL)):
        seg = pts[int(lo * steps):int(hi * steps) + 1]
        d.line(seg, fill=col, width=max(2, round(wdt * s)), joint="curve")
    d.ellipse((cx - 2 * s, cy - 2 * s, cx + 2 * s, cy + 2 * s), fill=TEAL)


def pict_flags(d, box) -> None:
    """Somalia's blue field and star, the UAE's bands, side by side."""
    x0, y0, x1, y1 = box
    s = (x1 - x0) / 48.0
    fw, fh = 21 * s, 15 * s
    gap = 5 * s
    total = fw * 2 + gap
    ax = (x0 + x1) / 2 - total / 2
    top = (y0 + y1) / 2 - fh / 2

    d.rectangle((ax, top, ax + fw, top + fh), fill=(58, 124, 194))
    d.polygon(star(ax + fw / 2, top + fh / 2, 5.4 * s, 2.2 * s), fill=WHITE)

    bx = ax + fw + gap
    d.rectangle((bx, top, bx + fw, top + fh), fill=WHITE)
    d.rectangle((bx, top, bx + fw, top + fh / 3), fill=(46, 150, 92))
    d.rectangle((bx, top + 2 * fh / 3, bx + fw, top + fh), fill=(26, 30, 38))
    d.rectangle((bx, top, bx + 7 * s, top + fh), fill=(200, 58, 58))
    for fl in ((ax, top, ax + fw, top + fh), (bx, top, bx + fw, top + fh)):
        d.rectangle(fl, outline=(20, 28, 44), width=1)


# ------------------------------------------------------------------ build ---

class Story(NamedTuple):
    """One secondary card: kicker, two headline lines, one deck, one icon."""
    chip: str
    lines: list[str]
    body: str
    art: Callable[..., None]


SIZES: dict[str, int] = {}


def build() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    over: list[str] = []

    def note(name, right, limit):
        if right > limit + 0.5:
            over.append(f"{name}: x {right:.0f} > {limit:.0f}")

    def note_y(name, bottom, limit):
        if bottom > limit:
            over.append(f"{name}: y {bottom:.0f} > {limit:.0f}")

    # ---- header ----------------------------------------------------------
    draw_tracked(d, (L, 38), "WORLD NEWS", font(BOLD, 24), AMBER, 7.0)
    ff = font(BOLD, 24)
    fwid = track_width("FRIDAY", ff, 7.0)
    draw_tracked(d, (R - fwid, 38), "FRIDAY", ff, (206, 215, 229), 7.0)

    date = "20 NOVEMBER 2026"
    df = fit_tracked(date, BOLD, 78, 1.0, R - L)
    draw_tracked(d, (L - 1, 70), date, df, WHITE, 1.0)
    note("date", L + track_width(date, df, 1.0), R)
    SIZES["day"] = int(df.size)

    hline(d, L, 166, R, AMBER, 4)

    # ---- lead ------------------------------------------------------------
    card(d, (L, 184, R, 474), radius=14)
    tx = L + 30
    text_w = 604
    text_r = tx + text_w

    cf = fit_tracked("EUROPE  \u00b7  KYIV", BOLD, 24, 4.0, text_w)
    note("lead chip", draw_tracked(d, (tx, 206), "EUROPE  \u00b7  KYIV", cf, AMBER, 4.0),
         text_r)

    head = ["RUSSIA FIRES MISSILES", "AT KYIV AFTER PUTIN'S", "VOW OF REVENGE"]
    hf, lh = fit_block(head, BOLD, 46, text_w, 1.08, 34)
    SIZES["lead"] = int(hf.size)
    y = 240
    for ln in head:
        draw_text(d, (tx, y), ln, hf, WHITE)
        note("lead head", tx + hf.getlength(ln), text_r)
        y += lh

    deck = ["Explosions at 1:25 a.m. as Tu-160 bombers join",
            "a mass overnight strike."]
    bf, blh = fit_block(deck, REG, 24, text_w, 1.30, 20)
    SIZES["deck"] = int(bf.size)
    y += 6
    for ln in deck:
        draw_text(d, (tx, y), ln, bf, BODY)
        note("lead deck", tx + bf.getlength(ln), text_r)
        y += blh
    note_y("lead", y, 474 - 12)

    pict_bomber(d, (text_r + 24, 204, R - 26, 452))

    # ---- four cards ------------------------------------------------------
    gutter = 16
    cw = (R - L - gutter) // 2
    row_h = 218
    rows = [490, 490 + row_h + gutter]
    cols = [L, L + cw + gutter]
    pad = 18
    inner = cw - 2 * pad
    art = 48

    cards = [
        Story(chip="TECH & MARKETS  \u00b7  NASDAQ",
              lines=["ANTHROPIC'S RECORD", "IPO PASSES $2 TRILLION"],
              body="The Claude maker's debut is the largest listing ever, "
                   "ahead of SpaceX.",
              art=pict_ipo),
        Story(chip="WORLD COURT  \u00b7  THE HAGUE",
              lines=["ICJ: MYANMAR", "COMMITTED GENOCIDE"],
              body="The UN's top court rules on the 2017 Rohingya campaign.",
              art=pict_gavel),
        Story(chip="SOUTH ASIA  \u00b7  ODISHA",
              lines=["CYCLONE AKVAN", "CLOSES IN ON INDIA"],
              body="Red alerts on the coast as the railways cancel ten trains.",
              art=pict_cyclone),
        Story(chip="HORN OF AFRICA  \u00b7  MOGADISHU",
              lines=["SOMALIA ORDERS", "UAE ENVOY OUT"],
              body="Mogadishu cites an 'invasion'; Abu" + NB + "Dhabi denies "
                   "meddling.",
              art=pict_flags),
    ]

    # one headline size for the whole grid keeps the rows visually even
    head_size = 34
    for s in cards:
        while head_size > 26 and max(
                font(BOLD, head_size).getlength(t) for t in s.lines) > inner:
            head_size -= 1
    hf2 = font(BOLD, head_size)
    hh = round(head_size * 1.18)
    SIZES["cards"] = head_size

    for i, s in enumerate(cards):
        x0 = cols[i % 2]
        y0 = rows[i // 2]
        card(d, (x0, y0, x0 + cw, y0 + row_h))
        px = x0 + pad

        s.art(d, (x0 + cw - pad - art, y0 + 14, x0 + cw - pad, y0 + 14 + art))

        chip_f = fit_tracked(s.chip, BOLD, 20, 0.0, inner - art - 8, 20)
        note(f"chip{i}", draw_tracked(d, (px, y0 + 24), s.chip, chip_f,
                                     TEAL, 0.0),
             x0 + cw - pad - art - 6)

        y = y0 + 14 + art + 8
        for ln in s.lines:
            draw_text(d, (px, y), ln, hf2, WHITE)
            note(f"head{i}", px + hf2.getlength(ln), x0 + cw - pad)
            y += hh

        bdf, blines, bdh = fit_wrapped(s.body, REG, 22, inner, 2, 1.26, 20)
        SIZES["body"] = int(bdf.size)
        y += 4
        for ln in blines[:2]:
            draw_text(d, (px, y), ln, bdf, BODY)
            note(f"body{i}", px + bdf.getlength(ln), x0 + cw - pad)
            y += bdh
        note_y(f"card{i}", y, y0 + row_h - 10)

    # ---- ticker ----------------------------------------------------------
    hline(d, L, 948, R, RULE, 1)
    lf = font(BOLD, 20)
    lab_end = draw_tracked(d, (L, 960), "ALSO TODAY", lf, AMBER, 3.0)
    items = ["40 leaders back Kyiv in Berlin \u00b7 Bitcoin at a four-month low",
             "COP31 draft omits fossil fuels \u00b7 Colombia protests again"]
    tf = font(REG, 22)
    x = lab_end + 18
    y = 959
    for ln in items:
        draw_text(d, (x, y), ln, tf, MUTED)
        note("ticker", x + tf.getlength(ln), R)
        y += 29

    if over:
        raise SystemExit("layout overflow: " + "; ".join(over))
    return img


def main() -> int:
    img = build()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    img.save(out, format="PNG", optimize=True)
    print(f"wrote {out} {img.width}x{img.height} {os.path.getsize(out)} bytes")
    print("type sizes: " + ", ".join(f"{k} {v}px" for k, v in SIZES.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())