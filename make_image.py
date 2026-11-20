#!/usr/bin/env python3
"""Draw entry.png: the world news of 20 November 2026 as one front page.

Ten stories: the overnight missile strike on Kyiv, then nine cards across
tech, the world court, South Asia, the Horn of Africa, Europe, crypto, the
COP31 draft, Latin America and the Arctic.

Design rules enforced by this script:

* 1024x1024 RGB, drawn at 2x and reduced with LANCZOS so hairlines and type
  stay clean at thumbnail size.
* Every string is measured with ImageFont.getlength() and either wrapped,
  auto-shrunk or dropped before it is drawn. Nothing is clipped, nothing
  overlaps, no text leaves its card: if a block cannot be made to fit, the
  program prints the failing block and exits 1 instead of shipping a smear.
* Deterministic: no clock, no randomness, no network. Two runs are
  byte-identical.
"""

from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# canvas
# --------------------------------------------------------------------------

BASE = 1024
SS = 2                       # supersampling factor
CANVAS = BASE * SS

PAL = {
    "bg": "#0B1220",
    "card": "#151F33",
    "hair": "#2A3A57",
    "body": "#D7DEEA",
    "head": "#FFFFFF",
    "amber": "#F2B33D",
    "teal": "#4FD1C5",
    "steel": "#B3BFD2",
    "block": "#6E7E9C",
    "foot": "#7E8CA6",
    "ink": "#0B1220",
    "teal_dim": "#3C8C86",
}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
_COND = os.path.join(FONT_DIR, "DejaVuSansCondensed-Bold.ttf")
_REG = os.path.join(FONT_DIR, "DejaVuSans.ttf")

_MISSING_COND = not os.path.exists(_COND)

_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(kind: str, size: float) -> ImageFont.FreeTypeFont:
    """Load a face at `size` base pixels, cached. Sizes snap to 0.5 px."""
    size = round(size * 2) / 2
    key = (kind, int(size * 2))
    if key not in _fonts:
        if kind == "bold":
            path = _BOLD
        elif kind == "cond":
            path = _COND if not _MISSING_COND else _BOLD
        elif kind == "reg":
            path = _REG
        else:                                    # pragma: no cover
            raise ValueError(kind)
        _fonts[key] = ImageFont.truetype(path, max(1, int(round(size * SS))))
    return _fonts[key]


def tw(text: str, f: ImageFont.FreeTypeFont, tracking: float = 0.0) -> float:
    """Width of `text` in base pixels, including letterspacing."""
    if not text:
        return 0.0
    total = sum(f.getlength(ch) for ch in text) / SS
    return total + tracking * (len(text) - 1)


def balanced_wrap(text: str, f: ImageFont.FreeTypeFont, limit: float,
                  max_lines: int = 3, tracking: float = 0.0
                  ) -> list[str] | None:
    """Wrap for display type: fewest lines, then the most even rag.

    Greedy wrapping leaves orphans like a lone 'TIME' on the last line; this
    minimises squared slack so a two-line break lands mid-phrase, and it
    penalises a last line much shorter than the others.
    """
    words = text.split()
    n = len(words)
    if not n:
        return None
    if any(tw(w, f, tracking) > limit for w in words):
        return None
    wid = [[0.0] * (n + 1) for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n + 1):
            wid[i][j] = tw(" ".join(words[i:j]), f, tracking)

    inf = float("inf")
    dp = [[inf] * (n + 1) for _ in range(max_lines + 1)]
    back = [[-1] * (n + 1) for _ in range(max_lines + 1)]
    dp[0][0] = 0.0
    for k in range(1, max_lines + 1):
        for j in range(1, n + 1):
            for i in range(j):
                if dp[k - 1][i] == inf or wid[i][j] > limit:
                    continue
                slack = limit - wid[i][j]
                cost = slack * slack
                if j == n and wid[i][j] < 0.45 * limit:
                    cost += (0.45 * limit - wid[i][j]) ** 2 * 2.0
                if dp[k - 1][i] + cost < dp[k][j]:
                    dp[k][j] = dp[k - 1][i] + cost
                    back[k][j] = i
    best_k, best_c = 0, inf
    for k in range(1, max_lines + 1):
        if dp[k][n] + k * 60.0 < best_c:
            best_k, best_c = k, dp[k][n] + k * 60.0
    if not best_k:
        return None
    out: list[str] = []
    j = n
    for k in range(best_k, 0, -1):
        i = back[k][j]
        out.append(" ".join(words[i:j]))
        j = i
    return out[::-1]


class Pen:
    """Draw helper that takes every coordinate in base (1024) pixels."""

    def __init__(self, draw: ImageDraw.ImageDraw) -> None:
        self.d = draw

    @staticmethod
    def _p(v: float) -> float:
        return round(v * SS)

    def _box(self, box):
        return [self._p(v) for v in box]

    def rect(self, box, fill=None, outline=None, width: float = 1.0):
        self.d.rectangle(self._box(box), fill=fill, outline=outline,
                         width=max(1, round(width * SS)))

    def rrect(self, box, r: float, fill=None, outline=None, width: float = 1.0):
        self.d.rounded_rectangle(self._box(box), radius=self._p(r), fill=fill,
                                 outline=outline, width=max(1, round(width * SS)))

    def line(self, pts, fill, width: float = 1.0):
        self.d.line([(self._p(x), self._p(y)) for x, y in pts], fill=fill,
                    width=max(1, round(width * SS)), joint="curve")

    def polygon(self, pts, fill=None, outline=None, width: float = 1.0):
        self.d.polygon([(self._p(x), self._p(y)) for x, y in pts], fill=fill,
                       outline=outline, width=max(1, round(width * SS)))

    def ellipse(self, box, fill=None, outline=None, width: float = 1.0):
        self.d.ellipse(self._box(box), fill=fill, outline=outline,
                       width=max(1, round(width * SS)))

    def arc(self, box, start, end, fill, width: float = 1.0):
        self.d.arc(self._box(box), start, end, fill=fill,
                   width=max(1, round(width * SS)))

    def dash_arc(self, box, start, end, fill, width: float = 1.5,
                 dash: float = 55.0, gap: float = 42.0):
        a = float(start)
        while a < end:
            b = min(a + dash, end)
            self.arc(box, a, b, fill, width)
            a = b + gap

    def text(self, xy, s: str, f, fill, anchor: str = "ls"):
        self.d.text((self._p(xy[0]), self._p(xy[1])), s, font=f, fill=fill,
                    anchor=anchor)

    def tracked(self, xy, s: str, f, fill, tracking: float,
                anchor: str = "ls"):
        """Letterspaced run. Anchor 'ls', 'rs' or 'ms'."""
        x, y = xy
        w = tw(s, f, tracking)
        if anchor == "rs":
            x -= w
        elif anchor == "ms":
            x -= w / 2
        for ch in s:
            self.d.text((self._p(x), self._p(y)), ch, font=f, fill=fill,
                        anchor="ls")
            x += f.getlength(ch) / SS + tracking


ROWS: list[tuple[str, str]] = []


def note(label: str, value: object) -> None:
    ROWS.append((label, str(value)))


def die(msg: str) -> None:
    print("FIT FAILURE: " + msg, file=sys.stderr)
    for label, value in ROWS:
        print(f"    {label:<30} {value}", file=sys.stderr)
    sys.exit(1)


def require(cond: bool, msg: str) -> None:
    if not cond:
        die(msg)


# --------------------------------------------------------------------------
# pictograms -- geometry only, no faces, no flags, no logos
# --------------------------------------------------------------------------

def _m(box, tx, ty):
    """Map unit coordinates onto a rectangle."""
    x0, y0, x1, y1 = box
    return x0 + (x1 - x0) * tx, y0 + (y1 - y0) * ty


def icon_bars(p: Pen, box, col, accent) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    for i, (bh, c) in enumerate(((0.30, col), (0.50, col), (0.72, accent))):
        bx = x0 + 0.06 * w + i * 0.16 * w
        p.rect([bx, y1 - bh * h, bx + 0.10 * w, y1], fill=c)
    p.line([_m(box, 0.40, 0.50), _m(box, 0.74, 0.22)], accent, 2.0)
    p.polygon([_m(box, 0.96, 0.04), _m(box, 0.70, 0.18), _m(box, 0.84, 0.32)],
              fill=accent)


def icon_gavel(p: Pen, box, col, accent) -> None:
    x0, y0, x1, y1 = box
    cx, cy = _m(box, 0.40, 0.28)
    hw, hh, ang = 0.16 * (x1 - x0), 0.075 * (y1 - y0), math.radians(-32)
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        pts.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    p.polygon(pts, fill=col)
    p.line([_m(box, 0.48, 0.42), _m(box, 0.80, 0.88)], col, 2.6)
    p.line([_m(box, 0.10, 0.86), _m(box, 0.40, 0.86)], accent, 2.0)


def icon_cyclone(p: Pen, box, col, accent) -> None:
    cx, cy = _m(box, 0.5, 0.5)
    half = min(box[2] - box[0], box[3] - box[1]) / 2.0
    for r, a0, extent in ((0.94, 205, 250), (0.66, 150, 235), (0.38, 95, 225)):
        rr = r * half
        p.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a0 + extent, col, 2.0)
    p.ellipse([cx - 1.7, cy - 1.7, cx + 1.7, cy + 1.7], fill=accent)


def icon_two_people(p: Pen, box, col, accent) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    for i, c in ((0, col), (1, accent)):
        cx = x0 + (0.30 + 0.40 * i) * w
        r = 0.115 * w
        p.ellipse([cx - r, y0 + 0.08 * h, cx + r, y0 + 0.08 * h + 2 * r], fill=c)
        p.rrect([cx - 0.25 * w, y0 + 0.42 * h, cx + 0.25 * w, y1 - 0.02 * h],
                0.12 * w, fill=c)


def icon_rings(p: Pen, box, col, accent) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    r = 0.20 * w
    cy = y0 + 0.52 * h
    for i, c in ((0, col), (1, accent), (2, col)):
        cx = x0 + (0.30 + 0.20 * i) * w
        p.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=2.2)


def icon_down(p: Pen, box, col, accent) -> None:
    p.line([_m(box, 0.10, 0.08), _m(box, 0.46, 0.34), _m(box, 0.32, 0.52),
            _m(box, 0.70, 0.82)], col, 2.6)
    p.polygon([_m(box, 0.90, 0.96), _m(box, 0.62, 0.90), _m(box, 0.74, 0.68)],
              fill=accent)


def icon_leaf(p: Pen, box, col, accent) -> None:
    """A leaf: two mirrored arcs meeting at the tip, with a short stem."""
    ax, ay = _m(box, 0.16, 0.88)
    bx, by = _m(box, 0.92, 0.12)
    bulge_len = 0.23 * (box[2] - box[0])
    nx, ny = -(by - ay), (bx - ax)
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    side_a, side_b = [], []
    steps = 18
    for i in range(steps + 1):
        t = i / steps
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        bulge = math.sin(math.pi * t) * bulge_len
        side_a.append((px + nx * bulge, py + ny * bulge))
        side_b.append((px - nx * bulge, py - ny * bulge))
    p.polygon(side_a + side_b[::-1], fill=col)
    p.line([(ax + nx * 0.3, ay + ny * 0.3), (bx - nx * 0.3, by - ny * 0.3)],
           PAL["card"], 1.3)
    p.line([_m(box, 0.16, 0.88), _m(box, 0.04, 0.97)], accent, 2.0)


def icon_crowd(p: Pen, box, col, accent) -> None:
    """A marchers' crowd: heads of uneven size, packed in three rows."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    dots = ((0.18, 0.24, 0.062), (0.42, 0.18, 0.054), (0.66, 0.24, 0.062),
            (0.84, 0.32, 0.050), (0.10, 0.56, 0.054), (0.32, 0.50, 0.066),
            (0.56, 0.56, 0.054), (0.78, 0.52, 0.062), (0.22, 0.84, 0.058),
            (0.46, 0.78, 0.066), (0.70, 0.84, 0.054), (0.90, 0.78, 0.046))
    for i, (tx, ty, r) in enumerate(dots):
        c = accent if i in (5, 9) else col
        cx, cy = x0 + tx * w, y0 + ty * h
        rr = r * w
        p.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=c)


def icon_iceberg(p: Pen, box, col, accent) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    wy = y0 + 0.50 * h
    p.polygon([(x0 + 0.30 * w, wy), (x0 + 0.46 * w, y0 + 0.12 * h),
               (x0 + 0.58 * w, y0 + 0.06 * h), (x0 + 0.68 * w, y0 + 0.26 * h),
               (x0 + 0.76 * w, wy)], fill=col)
    p.polygon([(x0 + 0.24 * w, wy), (x0 + 0.38 * w, wy + 0.26 * h),
               (x0 + 0.58 * w, wy + 0.36 * h), (x0 + 0.78 * w, wy + 0.18 * h),
               (x0 + 0.84 * w, wy)], fill=PAL["teal_dim"])
    p.line([(x0 + 0.02 * w, wy), (x1 - 0.02 * w, wy)], accent, 1.8)


ICONS = {
    "bars": icon_bars,
    "gavel": icon_gavel,
    "cyclone": icon_cyclone,
    "people": icon_two_people,
    "rings": icon_rings,
    "down": icon_down,
    "leaf": icon_leaf,
    "crowd": icon_crowd,
    "iceberg": icon_iceberg,
}


# --------------------------------------------------------------------------
# the lead pictogram: a bomber, three falling arcs, a city row
# --------------------------------------------------------------------------

def draw_lead_picto(p: Pen, box) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    grey = PAL["steel"]

    # swept-wing bomber, top view, nose to the left
    by = y0 + 0.17 * h
    bh = 0.17 * h
    p.polygon([(x0 + 0.02 * w, by),
               (x0 + 0.12 * w, by - 0.32 * bh),
               (x0 + 0.55 * w, by - 0.36 * bh),
               (x0 + 0.82 * w, by - 0.24 * bh),
               (x0 + 0.97 * w, by),
               (x0 + 0.82 * w, by + 0.22 * bh),
               (x0 + 0.55 * w, by + 0.32 * bh),
               (x0 + 0.12 * w, by + 0.28 * bh)], fill=grey)
    for sign in (-1, 1):
        p.polygon([(x0 + 0.38 * w, by),
                   (x0 + 0.70 * w, by + sign * 1.62 * bh),
                   (x0 + 0.82 * w, by + sign * 1.62 * bh),
                   (x0 + 0.60 * w, by)], fill=grey)
        p.polygon([(x0 + 0.86 * w, by),
                   (x0 + 0.93 * w, by + sign * 0.66 * bh),
                   (x0 + 0.97 * w, by + sign * 0.66 * bh),
                   (x0 + 0.94 * w, by)], fill=grey)

    # three dashed arcs falling from the aircraft to the city
    ay0 = y0 + 0.34 * h
    ay1 = y0 + 0.82 * h
    for fx in (0.20, 0.44, 0.68):
        cx = x0 + (fx + 0.05) * w
        rx = 0.055 * w
        p.dash_arc([cx - rx, ay0, cx + rx, ay1], 250, 470,
                   PAL["amber"], 1.5, dash=46, gap=54)

    # city row, one block lit
    base = y1 - 1.0
    heights = (0.34, 0.50, 0.26, 0.62, 0.40, 0.72, 0.30, 0.48, 0.36, 0.56)
    bw = 0.072 * w
    gap = 0.020 * w
    for i, hh in enumerate(heights):
        bx = x0 + 0.02 * w + i * (bw + gap)
        top = base - hh * (y1 - ay1 + 0.24 * h)
        col = PAL["amber"] if i == 5 else PAL["block"]
        p.rect([bx, top, bx + bw, base], fill=col)


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------

MX = 28
RIGHT = BASE - MX
CONTENT = RIGHT - MX

LEAD_TOP, LEAD_BOT = 160, 400
GRID_TOP, GRID_BOT = 410, 986
GUT = 12
COLS, ROWSN = 3, 3
CARD_W = (CONTENT - GUT * (COLS - 1)) / COLS
CARD_H = (GRID_BOT - GRID_TOP - GUT * (ROWSN - 1)) / ROWSN

DATE_TEXT = "20 NOVEMBER 2026"
KICKER = "WORLD NEWS · FRIDAY"
TAGLINE = "TEN STORIES · FIVE CONTINENTS"
FOOTER = "20 NOVEMBER 2026 · WORLD NEWS IN ONE IMAGE"

LEAD_KICKER = "EUROPE · KYIV"
LEAD_L1 = "RUSSIA FIRES MISSILES AT KYIV"
LEAD_L2 = "AFTER PUTIN'S VOW OF REVENGE"
LEAD_BODY = ("Explosions at 1:25 a.m. as Tu-160 bombers join a mass "
             "overnight strike.")
LEAD_BODY_LINES = ("Explosions at 1:25 a.m. as Tu-160 bombers",
                   "join a mass overnight strike.")

CARDS = [
    ("TECH & MARKETS", "ANTHROPIC IPO ABOVE $2 TRILLION",
     "Largest listing ever, ahead of SpaceX", "bars"),
    ("WORLD COURT", "ICJ: MYANMAR COMMITTED GENOCIDE",
     "Ruling on the 2017 Rohingya campaign", "gavel"),
    ("SOUTH ASIA", "CYCLONE AKVAN NEARS INDIA",
     "Red alerts in Odisha; ten trains cancelled", "cyclone"),
    ("HORN OF AFRICA", "SOMALIA ORDERS UAE ENVOY OUT",
     "Cites an \u201cinvasion\u201d; Abu Dhabi denies it", "people"),
    ("EUROPE", "40-PLUS LEADERS MEET ON UKRAINE",
     "Coalition of the Willing; Merz rejects a carve-up", "rings"),
    ("MARKETS", "BITCOIN AT A FOUR-MONTH LOW",
     "$61,876 as the sell-off deepens", "down"),
    ("CLIMATE", "DRAFT NAMES NO FOSSIL FUELS",
     "Revised COP31 text omits them again", "leaf"),
    ("LATIN AMERICA", "COLOMBIA PROTESTS, SECOND TIME",
     "Nationwide march against the president", "crowd"),
    ("ARCTIC", "DENMARK RATIFIES GREENLAND DEAL",
     "The Arctic deal with Washington", "iceberg"),
]


# a break that keeps 'NAMES NO' together so 'names' is read as the verb
PREFERRED_BREAKS = {6: ("DRAFT NAMES NO", "FOSSIL FUELS")}


def build() -> Image.Image:
    img = Image.new("RGB", (CANVAS, CANVAS), PAL["bg"])
    p = Pen(ImageDraw.Draw(img))

    # ---------------- masthead ----------------
    kf = font("bold", 20)
    ktr = 3.2
    kwid = tw(KICKER, kf, ktr)
    p.tracked((MX, 46), KICKER, kf, PAL["amber"], ktr)
    note("kicker", f"20px bold, track {ktr}, w={kwid:.0f}")

    tf = font("bold", 15.5)
    ttr = 1.9
    twid = tw(TAGLINE, tf, ttr)
    require(MX + kwid + 24 < RIGHT - twid, "masthead kicker/tagline collide")
    p.tracked((RIGHT, 45), TAGLINE, tf, PAL["teal"], ttr, anchor="rs")
    note("tagline", f"15.5px bold, track {ttr}, w={twid:.0f}, right-aligned")

    dsize = 78.0
    df = font("bold", dsize)
    dwid = tw(DATE_TEXT, df, 0.6)
    require(dwid <= CONTENT, f"date {dwid:.0f}px wider than {CONTENT}px")
    p.tracked((MX, 124), DATE_TEXT, df, PAL["head"], 0.6)
    note("date", f"78px bold, track 0.6, w={dwid:.0f}, baseline 124")

    p.rect([MX, 138, RIGHT, 141], fill=PAL["amber"])
    note("masthead rule", "y 138..141, amber")

    # ---------------- lead card ----------------
    lx0, ly0, lx1, ly1 = MX, LEAD_TOP, RIGHT, LEAD_BOT
    p.rrect([lx0, ly0, lx1, ly1], 12, fill=PAL["card"], outline=PAL["hair"],
            width=1.0)
    pad = 20
    ix0, iy0, ix1, iy1 = lx0 + pad, ly0 + pad, lx1 - pad, ly1 - pad

    chip_f = font("bold", 17)
    chip_tr = 2.6
    chip_w = tw(LEAD_KICKER, chip_f, chip_tr) + 22
    chip_h = 26
    require(chip_w < ix1 - ix0 - 320, "lead chip too wide")
    p.rrect([ix0, iy0 - 3, ix0 + chip_w, iy0 - 3 + chip_h], 5,
            fill=PAL["amber"])
    p.tracked((ix0 + 11, iy0 + 15), LEAD_KICKER, chip_f, PAL["ink"], chip_tr)
    note("lead chip", f"17px bold, {chip_w:.0f}x{chip_h} at y {iy0 - 3:.0f}")

    head_size = None
    for s in (46, 45, 44, 43, 42, 41, 40, 39, 38, 36, 34):
        f = font("bold", s)
        if max(tw(LEAD_L1, f), tw(LEAD_L2, f)) <= ix1 - ix0 - 6:
            head_size = s
            break
    require(head_size is not None, "lead headline does not fit")
    hf = font("bold", head_size)
    lh = round(head_size * 1.02)
    b1 = iy0 + chip_h + round(head_size * 0.80) + 2
    b2 = b1 + lh
    p.text((ix0, b1), LEAD_L1, hf, PAL["head"])
    p.text((ix0, b2), LEAD_L2, hf, PAL["head"])
    note("lead headline", f"{head_size:g}px bold, 2 lines, baselines {b1}/{b2},"
                          f" widest {max(tw(LEAD_L1, hf), tw(LEAD_L2, hf)):.0f}"
                          f"/{ix1 - ix0:.0f}")

    # pictogram, lower right of the lead card
    pw = 300.0
    py1 = iy1 - 2
    py0 = py1 - 72
    px1 = ix1
    px0 = px1 - pw
    require(py0 >= b2 + 14, "lead pictogram would touch the headline")
    draw_lead_picto(p, (px0, py0, px1, py1))
    note("lead pictogram", f"{pw:.0f}x{py1 - py0:.0f} at x {px0:.0f}..{px1:.0f}"
                           f", y {py0:.0f}..{py1:.0f}")

    # body line(s), left of the pictogram
    body_limit = px0 - ix0 - 20
    body_size, body_lines = None, []
    for s in (20, 19.5, 19, 18.5, 18, 17):
        f = font("reg", s)
        if all(tw(t, f) <= body_limit for t in LEAD_BODY_LINES):
            body_size, body_lines = s, list(LEAD_BODY_LINES)
            break
        lines = balanced_wrap(LEAD_BODY, f, body_limit, 2)
        if lines and len(lines) <= 2:
            body_size, body_lines = s, lines
            break
    require(body_size is not None, "lead body does not wrap in two lines")
    bf = font("reg", body_size)
    blh = round(body_size * 1.30)
    bb = py1 - (len(body_lines) - 1) * blh - 2
    for i, line in enumerate(body_lines):
        p.text((ix0, bb + i * blh), line, bf, PAL["body"])
    require(bb - round(body_size * 0.8) >= b2 + 10, "lead body crowds headline")
    note("lead body", f"{body_size:g}px reg, " + " / ".join(body_lines)
                      + f", width {body_limit:.0f}")

    # ---------------- grid ----------------
    PAD = 14
    INNER_W = CARD_W - 2 * PAD
    TOP_OFF = 46                       # first headline line, from card top

    def detail_for(text: str, room: float):
        """Largest detail setting that fits the room left under the headline."""
        for s in (15, 14.5, 14):
            f = font("reg", s)
            for maxl in (1, 2):
                if round(s * 1.26) * maxl > room:
                    continue
                lines = balanced_wrap(text, f, INNER_W, maxl)
                if lines and len(lines) <= maxl:
                    return s, lines
        return 0, []

    grid_size, plan = None, []
    for s in (26.5, 26, 25.5, 25, 24.5, 24, 23.5, 23, 22):
        f = font("bold", s)
        lh = round(s * 1.16)
        trial, deep, complete = [], 0, True
        for idx, (_region, headline, detail, _icon) in enumerate(CARDS):
            lines = None
            pref = PREFERRED_BREAKS.get(idx)
            if pref and all(tw(t, f) <= INNER_W for t in pref):
                lines = list(pref)
            if not lines:
                lines = balanced_wrap(headline, f, INNER_W, 3)
            if not lines or max(tw(t, f) for t in lines) > INNER_W:
                complete = False
                break
            deep += len(lines) == 3
            room = (CARD_H - PAD) - TOP_OFF - lh * len(lines) - 4
            ds, dl = detail_for(detail, room)
            trial.append((f, lh, lines, ds, dl))
            if not dl:
                complete = False
        if not complete or deep > 2:
            continue
        # largest setting that keeps at most two headlines at three lines, so
        # the rows stay a two-line grid with two deliberate stacks
        grid_size, plan = s, trial
        break
    require(grid_size is not None, "the grid cannot be set at any size")
    note("grid type", f"{grid_size:g}px bold, uniform across nine cards")

    for idx, ((region, headline, detail, icon), (hf, hlh, hlines, dsize,
                                                 dlines)) in enumerate(
            zip(CARDS, plan)):
        col, row = idx % COLS, idx // COLS
        cx0 = MX + col * (CARD_W + GUT)
        cy0 = GRID_TOP + row * (CARD_H + GUT)
        cx1, cy1 = cx0 + CARD_W, cy0 + CARD_H
        p.rrect([cx0, cy0, cx1, cy1], 10, fill=PAL["card"],
                outline=PAL["hair"], width=1.0)

        gx0, gy1 = cx0 + PAD, cy1 - PAD

        isz = 36
        p_box = (cx1 - PAD - isz, cy0 + 12, cx1 - PAD, cy0 + 12 + isz)
        ICONS[icon](p, p_box, PAL["teal"], PAL["amber"])

        ctr = 1.5
        chip_limit = p_box[0] - gx0 - 8
        csize = 14.5
        while csize > 11 and tw(region, font("bold", csize), ctr) > chip_limit:
            csize -= 0.5
        cf = font("bold", csize)
        cw = tw(region, cf, ctr)
        require(cw <= chip_limit,
                f"card {idx + 1} region '{region}' too wide ({cw:.0f}px)")
        p.tracked((gx0, cy0 + 27), region, cf, PAL["teal"], ctr)

        y = cy0 + TOP_OFF
        for line in hlines:
            p.text((gx0, y + round(grid_size * 0.80)), line, hf, PAL["head"])
            y += hlh
        widest = max(tw(t, hf) for t in hlines)
        require(widest <= INNER_W, f"card {idx + 1} headline too wide")

        if dlines:
            dlh = round(dsize * 1.26)
            # detail sits a constant distance under the headline, so the nine
            # cards keep one internal rhythm
            first_b = y + 6 + round(dsize * 0.80)
            require(first_b + dlh * (len(dlines) - 1) + 3 <= gy1,
                    f"card {idx + 1} detail overflows")
            for i, line in enumerate(dlines):
                p.text((gx0, first_b + i * dlh), line, font("reg", dsize),
                       PAL["body"])
        else:
            require(y <= gy1, f"card {idx + 1} text overflows")

        note(f"{idx + 1} {region}",
             f"{' / '.join(hlines)} | detail "
             + (f"{dsize:g}px x{len(dlines)}" if dlines else "dropped")
             + f" | widest {widest:.0f}/{INNER_W:.0f}")

    # ---------------- footer ----------------
    ff = font("reg", 12.5)
    ftr = 1.6
    fw = tw(FOOTER, ff, ftr)
    fy = 1010
    require(fy - 13 >= GRID_BOT + 10, "footer crowds the grid")
    p.tracked((BASE / 2, fy), FOOTER, ff, PAL["foot"], ftr, anchor="ms")
    note("footer", f"12.5px, track {ftr}, w={fw:.0f}, centred, baseline {fy}")

    return img.resize((BASE, BASE), Image.LANCZOS)


def main() -> int:
    img = build()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "entry.png")
    img.save(out_path, "PNG", optimize=True, compress_level=7)

    size = os.path.getsize(out_path)
    print(f"wrote {out_path}")
    print(f"  {img.size[0]}x{img.size[1]} {img.mode} {size} bytes")
    if _MISSING_COND:
        print("  note: DejaVuSansCondensed-Bold.ttf absent; bold used")
    print()
    width = max(len(label) for label, _ in ROWS) + 2
    for label, value in ROWS:
        print(f"  {label:<{width}} {value}")

    if img.size != (BASE, BASE) or img.mode != "RGB":
        print("error: wrong image geometry", file=sys.stderr)
        return 1
    if not 250000 <= size <= 1048576:
        print(f"error: {size} bytes outside 250000..1048576", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())