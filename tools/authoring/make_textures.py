#!/usr/bin/env python3
"""
Authoring tool — NOT a build, CI, or runtime dependency (§11).

Run by hand; the PNGs it writes are committed to public/textures/ and the app
loads those. Delete this file and the game still runs.

    python3 tools/authoring/make_textures.py

PIXEL ART. Every sheet is small on purpose: at these sizes a texel lands at
roughly 2 cm in world space, so the texels read as texels the way they do in the
reference. That means:

  * no blur, no antialiasing, no gradients — value steps and ordered dithering
  * one-pixel marks: a groove is 1 px dark with 1 px bright lip beside it
  * a bolt is 2x2 px with a single lighter pixel, not a shaded circle
  * the sheets are sampled with NearestFilter, so a soft edge here is a mistake
    you will see at 10x magnification in game

Everything is painted as LUMINANCE around mid-grey; palette.js supplies the hue
at sample time, which is what holds a limited palette across the catalogue
(§4.4).
"""
import random
from PIL import Image, ImageDraw, ImageStat

OUT = "public/textures"
SHEET = 128       # sheet WIDTH, and the size of the square sheets
TRIM_H = 256      # the trim sheet is tall: one row per material

# The trim sheet layout, §4.1. These strips are MATERIALS — see the long note in
# src/art/trimLayout.js, which holds the same table and must be kept in step.
STRIPS = {
    "edge":       (0, 12),    # painted bevels and borders
    "detail":     (12, 16),   # screw heads, panel seams, label rails
    "paint":      (28, 24),   # painted metal and plastic — the DEFAULT
    "panel":      (52, 32),   # a big flat panel: seam border, corner bolts
    "wood":       (84, 32),   # real grain, broken dashes, one knot
    "steel":      (116, 24),  # bare metal: flat, faint sheen band, rivets
    "grille":     (140, 16),  # hard dark slots with lit lips
    "screen":     (156, 16),  # a lit display: near-black with a diagonal streak
    "glass":      (172, 16),  # pale and flat, one diagonal streak
    "paper":      (188, 16),  # card and labels: flat, the faintest fibre
    "fabric":     (204, 24),  # upholstery: an even weave
    "transition": (228, 28),  # wear gradients, dirt masks
}

V = lambda v: (int(max(0, min(255, v))),) * 3

# 4x4 Bayer matrix — ordered dithering is how pixel art does a gradient.
BAYER = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def dither_band(d, x0, y0, x1, y1, top, bottom, spread=26):
    """A vertical ramp built from two values and a Bayer threshold."""
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        t = (y - y0) / h
        base = top + (bottom - top) * t
        for x in range(x0, x1):
            hi = BAYER[y % 4][x % 4] / 16.0
            d.point((x, y), fill=V(base + (spread if hi > 0.5 else -spread) * 0.5))


def hline(d, y, x0, x1, v):
    d.rectangle([x0, y, x1 - 1, y], fill=V(v))


def vline(d, x, y0, y1, v):
    d.rectangle([x, y0, x, y1 - 1], fill=V(v))


def wrap_x(x, w=SHEET):
    return x % w


def dashed_grain(d, y, v, rnd, w=SHEET, run_range=(3, 9), gap_range=(4, 14)):
    """A grain line as short pixel dashes — broken up, so it never reads as a
    stripe running the width of the sheet."""
    x = rnd.randrange(0, w)
    drawn = 0
    while drawn < w:
        run = rnd.randint(*run_range)
        for i in range(run):
            d.point((wrap_x(x + i, w), y), fill=V(v))
        gap = rnd.randint(*gap_range)
        x = wrap_x(x + run + gap, w)
        drawn += run + gap


def speckle(d, rnd, x0, y0, x1, y1, amount, spread, base=None):
    """Isotropic single-pixel noise. This is what makes a flat panel read as
    "a material" rather than "a colour", and it has no direction at all."""
    n = int((x1 - x0) * (y1 - y0) * amount)
    for _ in range(n):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        v = (base if base is not None else 132) + rnd.choice([-spread, -spread // 2, spread // 2, spread])
        d.point((x, y), fill=V(v))


def mottle(d, rnd, x0, y0, x1, y1, count, spread, base):
    """Soft irregular blotches — deliberately round, never linear."""
    for _ in range(count):
        cx, cy = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        rx, ry = rnd.randint(3, 11), rnd.randint(2, 7)
        v = base + rnd.choice([-spread, spread])
        for yy in range(cy - ry, cy + ry + 1):
            if not (y0 <= yy < y1):
                continue
            for xx in range(cx - rx, cx + rx + 1):
                dx, dy = (xx - cx) / max(1, rx), (yy - cy) / max(1, ry)
                if dx * dx + dy * dy > 1.0:
                    continue
                if BAYER[yy % 4][xx % 4] / 16.0 > 0.55:
                    continue
                d.point((wrap_x(xx, x1 - x0) + x0 if x1 - x0 == SHEET else xx, yy), fill=V(v))


def knot(d, cx, cy, v_core, v_ring, w=SHEET):
    """A knot in four pixels-ish: a dark core with a ring. Tiny and deliberate."""
    for dx, dy in ((-2, 0), (-1, -1), (0, -1), (1, -1), (2, 0), (1, 1), (0, 1), (-1, 1)):
        d.point((wrap_x(cx + dx, w), cy + dy), fill=V(v_ring))
    d.point((wrap_x(cx, w), cy), fill=V(v_core))
    d.point((wrap_x(cx - 1, w), cy), fill=V(v_core))


def streak(d, x0, y0, x1, y1, v, step=2, spacing=13, width=2):
    """A hard diagonal highlight band, drawn as a pixel staircase.

    This is the single mark that makes a screen read as a screen in the
    reference set (docs/reference/03-retro-computers): a near-black rectangle
    with one or two bright diagonals across it and nothing else. No gradient,
    no glow — a staircase of solid pixels.
    """
    for sx in range(x0 - (y1 - y0) * step, x1, spacing):
        for row in range(y1 - y0):
            x = sx + row * step
            for k in range(width):
                if x0 <= x + k < x1:
                    d.point((x + k, y0 + row), fill=V(v))


# ---------------------------------------------------------------- trim sheet
def make_trim():
    img = Image.new("RGB", (SHEET, TRIM_H), V(128))
    d = ImageDraw.Draw(img)
    rnd = random.Random(60912)

    def strip(name):
        y, h = STRIPS[name]
        return y, h, y + h

    # --- edge: a painted bevel -------------------------------------------
    ey, eh, ee = strip("edge")
    for i, v in enumerate((88, 120, 200, 178, 158, 142, 130, 120, 112, 104, 96, 88)):
        hline(d, ey + i, 0, SHEET, v)
    for _ in range(18):                            # nicks in the lit row
        x = rnd.randrange(SHEET)
        for i in range(rnd.randint(1, 3)):
            d.point((wrap_x(x + i), ey + 2), fill=V(164))

    # --- detail: bolts and a label rail -----------------------------------
    dy, dh, de = strip("detail")
    dither_band(d, 0, dy, SHEET, de, 140, 112, spread=12)
    for x in range(4, SHEET, 16):                  # bolts: 2x2 with one lit pixel
        d.rectangle([x, dy + 3, x + 1, dy + 4], fill=V(58))
        d.point((x, dy + 3), fill=V(206))
    hline(d, dy + 10, 0, SHEET, 62)                # label rail
    hline(d, dy + 11, 0, SHEET, 210)
    hline(d, dy + 12, 0, SHEET, 158)
    hline(d, dy + 13, 0, SHEET, 88)
    for x in range(2, SHEET, 8):                   # label cards in the rail
        d.rectangle([x, dy + 11, x + 4, dy + 12], fill=V(224))

    # --- paint: painted metal and plastic, the default --------------------
    # Nearly flat. In the reference a plastic casing is one value with a very
    # slight tonal drift and a couple of moulding lines; anything more and the
    # object starts reading as stone. Everything here is within +/-10 of mid.
    py, ph, pe = strip("paint")
    dither_band(d, 0, py, SHEET, pe, 134, 129, spread=4)
    speckle(d, rnd, 0, py, SHEET, pe, 0.04, 6, 132)
    hline(d, py + ph // 2, 0, SHEET, 122)          # one moulding line
    hline(d, py + ph // 2 + 1, 0, SHEET, 142)

    # --- panel: a big flat panel with a drawn border and corner bolts ------
    # For door and side panels. The border is the whole point: the reference
    # draws a recessed rectangle into a flat face rather than modelling one.
    ny, nh, ne = strip("panel")
    dither_band(d, 0, ny, SHEET, ne, 135, 128, spread=4)
    speckle(d, rnd, 0, ny, SHEET, ne, 0.05, 7, 132)
    for x0 in range(0, SHEET, 64):                 # two panels across the strip
        x1 = x0 + 64
        d.rectangle([x0 + 5, ny + 4, x1 - 6, ne - 5], outline=V(92))
        d.rectangle([x0 + 6, ny + 5, x1 - 7, ne - 6], outline=V(166))
        for cx in (x0 + 3, x1 - 5):                # corner bolts
            for cy in (ny + 2, ne - 4):
                d.rectangle([cx, cy, cx + 1, cy + 1], fill=V(92))
                d.point((cx, cy), fill=V(186))

    # --- wood: real grain, because a worktop should read as wood ----------
    # This is the one strip that IS allowed a direction: it is only ever used
    # on parts that are actually made of wood, so the grain running along the
    # part is right rather than being a stripe on every object in the room.
    wy, wh, we = strip("wood")
    # Low contrast, and that is the lesson from the first cut of this strip: at
    # 2 cm per texel a grain line drawn at catalogue contrast reads as a stripe
    # painted across the furniture, not as wood. Everything here sits within
    # about +/-12 of mid grey; the eye reads it as timber from the DIRECTION,
    # which is the one thing this strip is allowed to have.
    dither_band(d, 0, wy, SHEET, we, 136, 128, spread=5)
    mottle(d, rnd, 0, wy, SHEET, we, 34, 6, 132)
    for _ in range(12):
        dashed_grain(d, rnd.randrange(wy + 1, we - 1),
                     132 + rnd.choice([-12, -9, -6, 7, 10, 12]), rnd,
                     run_range=(6, 18), gap_range=(3, 10))
    hline(d, wy, 0, SHEET, 120)                    # a board edge with a lit lip
    hline(d, wy + 1, 0, SHEET, 146)
    knot(d, rnd.randrange(SHEET), rnd.randint(wy + 6, we - 6), 118, 126)

    # --- steel: flat, one sheen band, rivets ------------------------------
    sy, sh, se = strip("steel")
    dither_band(d, 0, sy, SHEET, se, 136, 130, spread=4)
    speckle(d, rnd, 0, sy, SHEET, se, 0.05, 8, 132)
    for i in range(4):                             # a broad soft sheen
        hline(d, sy + 4 + i, 0, SHEET, 148 - i * 4)
    for x in range(6, SHEET, 22):                  # rivets
        d.rectangle([x, se - 5, x + 1, se - 4], fill=V(104))
        d.point((x, se - 5), fill=V(190))

    # --- grille: hard slots -----------------------------------------------
    gy, gh, ge = strip("grille")
    d.rectangle([0, gy, SHEET, ge - 1], fill=V(150))
    for x in range(0, SHEET, 6):
        d.rectangle([x + 1, gy + 2, x + 3, ge - 3], fill=V(52))
        vline(d, x + 4, gy + 2, ge - 3, 196)       # the lit lip beside each slot

    # --- screen: near-black with a hard diagonal streak --------------------
    # The fix for the thing that looked like rock. A display is not a surface
    # with a material; it is a dark rectangle with a reflection drawn on it.
    cy, ch, ce = strip("screen")
    d.rectangle([0, cy, SHEET, ce - 1], fill=V(52))
    speckle(d, rnd, 0, cy + 1, SHEET, ce - 1, 0.05, 7, 56)   # faint scanline grain
    for y in range(cy + 1, ce - 1, 2):             # scanlines
        hline(d, y, 0, SHEET, 44)
    streak(d, 0, cy + 1, SHEET, ce - 1, 150, spacing=37, width=3)
    streak(d, 0, cy + 1, SHEET, ce - 1, 190, spacing=37, width=1)
    hline(d, cy, 0, SHEET, 30)                     # the bezel shadow at the top
    hline(d, ce - 1, 0, SHEET, 78)                 # bounce at the bottom

    # --- glass: pale, flat, one streak ------------------------------------
    ly, lh, le = strip("glass")
    d.rectangle([0, ly, SHEET, le - 1], fill=V(168))
    dither_band(d, 0, ly, SHEET, le, 176, 160, spread=5)
    streak(d, 0, ly + 1, SHEET, le - 1, 226, spacing=41, width=3)
    streak(d, 0, ly + 1, SHEET, le - 1, 138, spacing=41, width=1)
    hline(d, le - 1, 0, SHEET, 120)                # the pane's bottom edge

    # --- paper: flat card, the faintest fibre -----------------------------
    ay, ah, ae = strip("paper")
    d.rectangle([0, ay, SHEET, ae - 1], fill=V(150))
    speckle(d, rnd, 0, ay, SHEET, ae, 0.05, 5, 150)
    hline(d, ae - 1, 0, SHEET, 122)                # the sheet's shadowed edge

    # --- fabric: an even weave --------------------------------------------
    fy, fh, fe = strip("fabric")
    d.rectangle([0, fy, SHEET, fe - 1], fill=V(132))
    for y in range(fy, fe):
        for x in range(SHEET):
            if (x + y) % 2 == 0:
                d.point((x, y), fill=V(126 if (x // 2 + y // 2) % 2 else 140))
    speckle(d, rnd, 0, fy, SHEET, fe, 0.06, 9, 132)

    # --- transition: a dithered wear ramp ---------------------------------
    ty, th, te = strip("transition")
    dither_band(d, 0, ty, SHEET, te, 160, 104, spread=18)
    speckle(d, rnd, 0, ty, SHEET, te, 0.14, 16, 132)

    return img


# --------------------------------------------------------------------- atlas
def panel(d, x0, y0, size, kind, seed):
    """One 64px atlas cell: a framed, recessed panel drawn pixel by pixel."""
    rnd = random.Random(seed)
    x1, y1 = x0 + size, y0 + size

    dither_band(d, x0, y0, x1, y1, 152, 104, spread=16)

    # outer frame: lit on top and left, dark on bottom and right
    hline(d, y0, x0, x1, 236)
    vline(d, x0, y0, y1, 206)
    hline(d, y1 - 1, x0, x1, 44)
    vline(d, x1 - 1, y0, y1, 56)

    # the recess: one dark line in, one lit line at the bottom of the well
    i = 5
    d.rectangle([x0 + i, y0 + i, x1 - i - 1, y1 - i - 1], outline=V(48))
    px0, py0, px1, py1 = x0 + i + 1, y0 + i + 1, x1 - i - 1, y1 - i - 1

    if kind == "wood":
        # one soft board line across the middle, then material
        dither_band(d, px0, py0, px1, py1, 140, 126, spread=9)
        mottle(d, rnd, px0, py0, px1, py1, 26, 12, 132)
        speckle(d, rnd, px0, py0, px1, py1, 0.10, 14, 132)
        mid = (py0 + py1) // 2
        hline(d, mid, px0, px1, 110)
        hline(d, mid + 1, px0, px1, 154)
        for _ in range(3):
            dashed_grain(d, rnd.randint(py0 + 2, py1 - 2), 132 + rnd.choice([-18, 20]),
                         rnd, w=px1 - px0)
        if rnd.random() < 0.6:
            knot(d, rnd.randint(px0 + 6, px1 - 8), rnd.randint(py0 + 4, py1 - 4), 112, 124)
    elif kind == "laminate":
        dither_band(d, px0, py0, px1, py1, 142, 124, spread=10)
        speckle(d, rnd, px0, py0, px1, py1, 0.14, 15, 132)
        mottle(d, rnd, px0, py0, px1, py1, 18, 9, 132)
    elif kind == "metal":
        # no brushed stripes — a faint isotropic grain and two soft highlights
        dither_band(d, px0, py0, px1, py1, 144, 122, spread=9)
        speckle(d, rnd, px0, py0, px1, py1, 0.16, 12, 132)
        for cx in (px0 + 2, px1 - 5):              # bolts
            for cy in (py0 + 2, py1 - 5):
                d.rectangle([cx, cy, cx + 2, cy + 2], fill=V(96))
                d.point((cx, cy), fill=V(178))
        for k in range(14):                        # a soft painted sheen
            d.rectangle([px0 + 8 + k, py1 - 3 - k, px0 + 9 + k, py1 - 2 - k], fill=V(170))
    elif kind == "glass":
        dither_band(d, px0, py0, px1, py1, 186, 148, spread=12)
        for k in range(16):
            d.rectangle([px0 + 5 + k, py1 - 3 - k, px0 + 7 + k, py1 - 2 - k], fill=V(246))
            if k < 8:
                d.point((px0 + 30 + k, py1 - 3 - k), fill=V(232))
        hline(d, py1 - 2, px0, px1, 88)            # a shelf behind the glass

    for cx, cy in ((x0 + 2, y0 + 2), (x1 - 4, y1 - 4), (x1 - 5, y0 + 3)):
        for _ in range(5):                         # corner wear, a few pixels
            d.point((cx + rnd.randint(-2, 2), cy + rnd.randint(-2, 2)),
                    fill=V(rnd.choice([214, 72])))


def make_atlas():
    size = 128
    cell = size // 2
    img = Image.new("RGB", (size, size), V(128))
    d = ImageDraw.Draw(img)
    for i, kind in enumerate(("wood", "laminate", "metal", "glass")):
        panel(d, (i % 2) * cell, (i // 2) * cell, cell, kind, 11 + i * 7)
    return img


# ------------------------------------------------------------ tiling surface
def make_tiling():
    size = 64
    tile = 16
    img = Image.new("RGB", (size, size), V(140))
    d = ImageDraw.Draw(img)
    rnd = random.Random(97)
    for ty in range(size // tile):
        for tx in range(size // tile):
            x0, y0 = tx * tile, ty * tile
            base = rnd.choice([138, 146, 152, 158])
            dither_band(d, x0, y0, x0 + tile, y0 + tile, base + 6, base - 8, spread=10)
            if rnd.random() < 0.3:                 # a worn tile here and there
                for _ in range(6):
                    d.point((x0 + rnd.randrange(2, tile - 2), y0 + rnd.randrange(2, tile - 2)),
                            fill=V(base - 24))
            speckle(d, rnd, x0 + 2, y0 + 2, x0 + tile, y0 + tile, 0.12, 10, base)
            hline(d, y0, x0, x0 + tile, 104)       # grout, with a lit lip
            hline(d, y0 + 1, x0, x0 + tile, 172)
            vline(d, x0, y0, y0 + tile, 104)
            vline(d, x0 + 1, y0, y0 + tile, 168)
    return img


# ---------------------------------------------------------------- hatch mask
def make_hatch():
    """Three densities in R/G/B; the shader picks a channel from the lighting
    term. White = no hatch. Spacing divides the size, so it tiles."""
    size = 64

    def diagonals(spacing, cross=False):
        layer = Image.new("L", (size, size), 255)
        d = ImageDraw.Draw(layer)
        for i in range(-size, size * 2, spacing):
            d.line([(i, 0), (i + size, size)], fill=0, width=1)
            if cross:
                d.line([(i, size), (i + size, 0)], fill=0, width=1)
        return layer

    return Image.merge("RGB", (diagonals(16), diagonals(8), diagonals(8, cross=True)))


def normalise(img, target=132):
    """Shift a sheet so its mean value lands on mid-grey.

    The shader multiplies the palette tint by this luminance, so a sheet that
    averages dark makes its module read dark — and a trim sheet and an atlas
    with different means put a visible value step across the Tier A/B seam.
    Matching the means is what lets §4.2's blend read as a painted seam.
    """
    delta = target - ImageStat.Stat(img.convert("L")).mean[0]
    return img.point(lambda v: max(0, min(255, int(round(v + delta)))))


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    for name, img in (
        ("trim.png", normalise(make_trim())),
        ("atlas.png", normalise(make_atlas())),
        ("tiling.png", normalise(make_tiling())),
        ("hatch.png", make_hatch()),   # a mask, not paint — never normalised
    ):
        path = os.path.join(OUT, name)
        img.save(path, optimize=True)
        print(f"{path}  {img.size[0]}x{img.size[1]}  {os.path.getsize(path) // 1024} KB")
