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
SHEET = 128

# The brief's standard trim sheet layout, §4.1, at pixel-art resolution.
# Proportions match 64/128/512/128/192 of 1024. Mirrored by src/art/trimLayout.js.
STRIPS = {
    "edge":       (0, 8),     # painted bevels, borders
    "detail":     (8, 16),    # screw heads, panel seams, label holders
    "surface":    (24, 64),   # painted wood, laminate, painted metal
    "transition": (88, 16),   # wear gradients, dirt masks
    "alpha":      (104, 24),  # cutouts — grilles, handles
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


# ---------------------------------------------------------------- trim sheet
def make_trim():
    img = Image.new("RGB", (SHEET, SHEET), V(128))
    d = ImageDraw.Draw(img)
    rnd = random.Random(60912)

    # --- surface strip: a general material -------------------------------
    # Low contrast on purpose. Everything here is within about +/-22 of mid
    # grey, so the strip reads as "surface" at any scale and never competes
    # with the geometry for the eye.
    sy, sh = STRIPS["surface"]
    BOARD = 32                                     # two soft separations, not four
    dither_band(d, 0, sy, SHEET, sy + sh, 136, 128, spread=8)
    mottle(d, rnd, 0, sy, SHEET, sy + sh, 90, 11, 132)
    speckle(d, rnd, 0, sy, SHEET, sy + sh, 0.10, 13, 132)

    for p in range(sh // BOARD):
        top = sy + p * BOARD
        # the whisper of a board edge: a soft shadow with a soft lip, roughly
        # a fifth of the contrast the plank version used
        hline(d, top + 0, 0, SHEET, 108)
        hline(d, top + 1, 0, SHEET, 156)
        for _ in range(rnd.randint(2, 4)):         # broken grain, barely there
            dashed_grain(d, rnd.randint(top + 4, top + BOARD - 4),
                         132 + rnd.choice([-20, -14, 16, 22]), rnd)
        if rnd.random() < 0.5:
            knot(d, rnd.randrange(SHEET), rnd.randint(top + 8, top + BOARD - 8), 112, 124)

    # --- edge trim: a painted bevel, eight rows ---------------------------
    ey, eh = STRIPS["edge"]
    for i, v in enumerate((92, 128, 196, 172, 146, 130, 112, 98)):
        hline(d, ey + i, 0, SHEET, v)
    for _ in range(18):                            # nicks in the lit row
        x = rnd.randrange(SHEET)
        for i in range(rnd.randint(1, 3)):
            d.point((wrap_x(x + i), ey + 2), fill=V(160))

    # --- detail strip: bolts and a label rail -----------------------------
    dy, dh = STRIPS["detail"]
    dither_band(d, 0, dy, SHEET, dy + dh, 140, 112, spread=12)
    for x in range(4, SHEET, 16):                  # bolts: 2x2 with one lit pixel
        d.rectangle([x, dy + 3, x + 1, dy + 4], fill=V(58))
        d.point((x, dy + 3), fill=V(206))
    hline(d, dy + 10, 0, SHEET, 62)                # label rail
    hline(d, dy + 11, 0, SHEET, 210)
    hline(d, dy + 12, 0, SHEET, 158)
    hline(d, dy + 13, 0, SHEET, 88)
    for x in range(2, SHEET, 8):                   # label cards in the rail
        d.rectangle([x, dy + 11, x + 4, dy + 12], fill=V(224))

    # --- transition: a dithered wear ramp ---------------------------------
    ty, th = STRIPS["transition"]
    dither_band(d, 0, ty, SHEET, ty + th, 160, 104, spread=18)
    speckle(d, rnd, 0, ty, SHEET, ty + th, 0.14, 16, 132)

    # --- alpha: grille ----------------------------------------------------
    ay, ah = STRIPS["alpha"]
    d.rectangle([0, ay, SHEET, ay + ah], fill=V(44))
    for x in range(0, SHEET, 6):
        d.rectangle([x + 1, ay + 3, x + 3, ay + ah - 4], fill=V(196))
        vline(d, x + 1, ay + 3, ay + ah - 4, 236)
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
