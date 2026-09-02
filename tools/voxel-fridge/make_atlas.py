#!/usr/bin/env python3
"""Author the fridge texture atlas, laid out the way the reference kit is.

The reference atlas sheet labels its own regions, and those labels ARE the
architecture:

    1 CREAM PAINTED-METAL CENTER      (TILEABLE)
    2 PALE BLUE-GRAY SIDE-PANEL       (TILEABLE)
    3 DEEP TEAL BASE & DOOR-FRAME     (TILEABLE)
    4 PROTECTED CREAM CORNERS & EDGE STRIPS  (FIXED)
    5 SIDE-PANEL CORNER BOLT ISLANDS  (FIXED)
    6 PURPLE HANDLE                   (FIXED)
    7 TEMPERATURE DISPLAY             (FIXED)
    8 GRILLE: END CAPS (FIXED) + SLOTS (TILEABLE HORIZONTAL)
    9 GLASS DIAGONAL REFLECTION       (FIXED)

Tileable centre, fixed corners, fixed decals: that is a NINE-SLICE SPRITE KIT.
So every surface is one PATCH whose outer CORNER ring is fixed and whose middle
tiles, and the shader reconstructs any part size from it (sliceAxis in main.js).
Nothing is ever stretched: corners blit at native size, edges tile along one
axis, the centre tiles on both.

TEXEL DENSITY IS THE WHOLE BALLGAME. It has to roughly match the density the
object is RENDERED at, or fine detail turns to moire. The reference draws the
96-unit cabinet about 850 px tall, i.e. ~9 px per unit, so this sheet is
authored at 8 texels per unit and main.js renders at 8 px per unit - one texel,
one pixel. Authored at 32, the condenser grille's slots aliased into a
shimmering mesh, because six texels were fighting over every screen pixel.

Writes atlas.png and atlas.json (the manifest the renderer reads). Swapping in
a hand-painted or generated sheet is a manifest edit, not a code change, as
long as it keeps the layout and the density.

    python3 tools/voxel-fridge/make_atlas.py
"""
import json
import os
import random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = 256
TEXELS_PER_UNIT = 8
PATCH = 48          # 6 units square
CORNER = 8          # 1 unit of fixed ring; the inner 32x32 tiles

# Palette read off the reference sheet: base, light bevel, dark bevel, outline.
P = {
    "cream":     ("#ede4d3", "#faf5e9", "#d8cebb", "#b9ab92"),
    "blueGrey":  ("#c6cfd4", "#dde4e8", "#b3bec5", "#94a2ab"),
    "teal":      ("#4e8672", "#63997f", "#417460", "#2c5647"),
    "purple":    ("#5a4966", "#6f5c7d", "#4a3b54", "#332a3e"),
    "plinth":    ("#5b4a6f", "#6d5a83", "#4a3b5a", "#3a2f47"),
    "interior":  ("#1f4a40", "#2a5b4f", "#173a32", "#123029"),
    "shelf":     ("#c3d0c9", "#dbe4de", "#a9b9b1", "#8b9d95"),
    "grilleTan": ("#d9a75f", "#e8bd7d", "#b1813f", "#8c6430"),
}
SLOT = "#3f3a33"
BOLT = "#5a646e"
DISP_FRAME, DISP_BG, DISP_GREEN, DISP_ORANGE = "#4a3e58", "#262b36", "#74de96", "#e2894e"
GLASS, STREAK = "#c9d6d9", "#eef4f2"


def box(d, x, y, w, h, fill):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=fill)


def patch(img, ox, oy, name, seed=1, speckles=4):
    """One nine-slice patch: fixed bevelled ring, tiling speckled centre."""
    base, lite, dark, line = P[name]
    d = ImageDraw.Draw(img)
    box(d, ox, oy, PATCH, PATCH, base)
    # The fixed ring, as pixel-art bevel: outline, then light top/left and dark
    # bottom/right. It lives in the corner/edge zone, so the shader never scales
    # it - this is the kit's "PROTECTED CORNERS & EDGE STRIPS".
    b = 2
    d.rectangle([ox, oy, ox + PATCH - 1, oy + PATCH - 1], outline=line, width=b)
    box(d, ox + b, oy + b, PATCH - 2 * b, b, lite)
    box(d, ox + b, oy + b, b, PATCH - 2 * b, lite)
    box(d, ox + b, oy + PATCH - 2 * b, PATCH - 2 * b, b, dark)
    box(d, ox + PATCH - 2 * b, oy + b, b, PATCH - 2 * b, dark)
    # Tiling centre: sparse single-texel flecks only. Anything denser reads as
    # noise at playing distance, which is what made the old sheets look rusty.
    rnd = random.Random(seed)
    span = PATCH - 2 * CORNER
    for _ in range(speckles):
        px = ox + CORNER + rnd.randrange(0, span - 1)
        py = oy + CORNER + rnd.randrange(0, span - 1)
        box(d, px, py, 1, 1, rnd.choice([lite, dark]))


def main():
    img = Image.new("RGB", (ATLAS, ATLAS), "#20242b")
    d = ImageDraw.Draw(img)
    man = {"texelsPerUnit": TEXELS_PER_UNIT, "size": [ATLAS, ATLAS],
           "surfaces": {}, "decals": {}}

    order = ["cream", "blueGrey", "teal", "purple", "plinth", "interior", "shelf"]
    for i, name in enumerate(order):
        ox, oy = (i % 5) * PATCH, (i // 5) * PATCH
        patch(img, ox, oy, name, seed=i + 3)
        man["surfaces"][name] = {"rect": [ox, oy, PATCH, PATCH], "corner": CORNER}

    # --- grille: fixed end caps + a horizontally tiling slot run -----------
    # 48 x 24 = 6 x 3 units. The part MUST be 3 units tall: on an axis it does
    # not tile, a patch's pixel size IS the part's world size.
    gx, gy, gw, gh = 0, PATCH * 2, PATCH, 24
    box(d, gx, gy, gw, gh, P["grilleTan"][2])
    box(d, gx + 1, gy + 1, gw - 2, gh - 2, P["grilleTan"][0])
    # The kit's slots are CONTINUOUS lines, so they run across the whole patch
    # INCLUDING the corner ring. A slot that stopped at the ring broke into a
    # dotted mesh the moment the tile repeated.
    rows, rowh, gap = 3, 3, 4
    top = gy + (gh - (rows * rowh + (rows - 1) * gap)) // 2
    for r in range(rows):
        box(d, gx, top + r * (rowh + gap), gw, rowh, SLOT)
    for bx in (gx + 2, gx + gw - 4):          # fixed end-cap bolts, in the ring
        for by in (gy + 3, gy + gh - 5):
            box(d, bx, by, 2, 2, P["grilleTan"][3])
    man["surfaces"]["grille"] = {"rect": [gx, gy, gw, gh], "corner": CORNER}

    # --- fixed decals: blitted at native size, never scaled ----------------
    # temperature display, 88 x 24 = 11 x 3 units
    dx, dy, dw, dh = PATCH + 4, PATCH * 2, 88, 24
    box(d, dx, dy, dw, dh, DISP_FRAME)
    box(d, dx + 2, dy + 2, dw - 4, dh - 4, DISP_BG)
    box(d, dx + 7, dy + 10, 4, 4, DISP_ORANGE)
    glyphs = {
        "4": [[1, 0, 1], [1, 0, 1], [1, 1, 1], [0, 0, 1], [0, 0, 1]],
        "C": [[1, 1, 1], [1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 1, 1]],
    }
    cx = dx + 18
    for g in "4C":
        for ry, row in enumerate(glyphs[g]):
            for rx, v in enumerate(row):
                if v:
                    box(d, cx + rx * 3, dy + 6 + ry * 3, 3, 3, DISP_GREEN)
        cx += 12
    man["decals"]["display"] = {"rect": [dx, dy, dw, dh]}

    bx, by = PATCH + 4, PATCH * 2 + 28           # corner bolt island, 4 x 4
    box(d, bx, by, 4, 4, P["blueGrey"][2])
    box(d, bx + 1, by + 1, 2, 2, BOLT)
    man["decals"]["bolt"] = {"rect": [bx, by, 4, 4]}

    # glass: pale field carrying the kit's fixed diagonal reflection streak
    gx2, gy2 = PATCH * 3, PATCH * 2
    box(d, gx2, gy2, PATCH, PATCH, GLASS)
    for i in range(11):
        px, py = gx2 + 30 - i * 3, gy2 + 3 + i * 3
        if gx2 <= px < gx2 + PATCH - 5:
            box(d, px, py, 5, 3, STREAK)
    for i in range(6):
        px, py = gx2 + 42 - i * 3, gy2 + 5 + i * 3
        if gx2 <= px < gx2 + PATCH - 2:
            box(d, px, py, 2, 3, STREAK)
    man["surfaces"]["glass"] = {"rect": [gx2, gy2, PATCH, PATCH], "corner": 1}

    img.save(os.path.join(HERE, "atlas.png"))
    with open(os.path.join(HERE, "atlas.json"), "w") as f:
        json.dump(man, f, indent=2)
    print(f"atlas.png {ATLAS}x{ATLAS} @ {TEXELS_PER_UNIT} texels/unit · "
          f"{len(man['surfaces'])} surfaces, {len(man['decals'])} decals")


if __name__ == "__main__":
    main()
