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
ATLAS = 512
TEXELS_PER_UNIT = 8
# A patch's TILING CENTRE is what repeats across a big face, so its size sets
# how often the chips recur. At a 48px patch the centre was 32 texels = 4 units
# and the crown's top face showed a regular dotted grid of them. At 96 the
# centre is 10 units, which is wider than most parts and reads as scatter.
PATCH = 96          # 12 units square
CORNER = 8          # 1 unit of fixed ring; the inner 80x80 tiles

# FLAT base colours, read off the multi-view sheet. There is deliberately no
# light/dark bevel pair here any more: see patch() for why.
P = {
    "cream":     "#e9e3d4",
    "blueGrey":  "#c3ced2",
    "teal":      "#35785f",
    "purple":    "#5c4a70",
    "plinth":    "#5c4a72",
    "interior":  "#2c6a5a",
    "shelf":     "#dbe9e4",
    "grilleTan": "#d9a95f",
}
GRILLE_FRAME = "#c08c45"
SLOT = "#3f3a33"
BOLT = "#5a646e"
DISP_FRAME, DISP_BG, DISP_GREEN, DISP_ORANGE = "#4a3e58", "#262b36", "#74de96", "#e2894e"
GLASS, STREAK = "#b9d4cd", "#f0f7f4"


def box(d, x, y, w, h, fill):
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=fill)


def shade(hexcol, f):
    """A tone of one flat colour. The palette stays one hex per surface; every
    outline, chip and bolt is derived, so recolouring a surface is one edit."""
    n = int(hexcol[1:], 16)
    ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255]
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c * f))) for c in ch)


def patch(img, ox, oy, name, seed=1, chips=5, bolts=True, edge_bolt=False):
    """One nine-slice patch, with the reference kit's detail in the right zones.

    Two failed attempts are worth recording, because the right answer sits
    exactly between them. First I painted a 2px light/dark BEVEL RING on all
    four sides of every patch: a cabinet is twenty boxes, so it came out as
    twenty embossed panels, busy and rusty. Then I stripped the patches to pure
    flat colour, which lost the retro pixel character entirely.

    The kit sheet says what it actually wants. Centres are "TILEABLE" fields
    carrying a few sparse chips. Item 4 is "PROTECTED CREAM CORNERS & EDGE
    STRIPS (FIXED)": outlined strips with bolts along them. So:

      the fixed ring (outer CORNER texels)  1px darker outline, a 1px lighter
                                            inner catch on top/left, and a bolt
                                            near each corner
      the tiling centre                     flat field plus a few 1px chips

    Every one of those lands in a zone the nine-slice treats correctly: the
    outline tiles along an edge into one continuous line, the corner bolts are
    in the corner zone so they appear exactly once per corner at any size, and
    an optional edge bolt sits in the tiling edge strip so a LONG panel grows a
    periodic row of them - which is what the sheet's long strips show.
    """
    base = P[name]
    line, lite, blt = shade(base, 0.80), shade(base, 1.07), shade(base, 0.58)
    d = ImageDraw.Draw(img)
    box(d, ox, oy, PATCH, PATCH, base)
    d.rectangle([ox, oy, ox + PATCH - 1, oy + PATCH - 1], outline=line, width=1)
    box(d, ox + 1, oy + 1, PATCH - 2, 1, lite)      # 1px catch, top
    box(d, ox + 1, oy + 1, 1, PATCH - 2, lite)      # and left
    if bolts:
        for bx in (ox + 3, ox + PATCH - 5):
            for by in (oy + 3, oy + PATCH - 5):
                box(d, bx, by, 2, 2, blt)
    if edge_bolt:
        # in the TILING edge strip, so it repeats down a long panel
        box(d, ox + PATCH // 2, oy + 3, 2, 2, blt)
        box(d, ox + 3, oy + PATCH // 2, 2, 2, blt)
    rnd = random.Random(seed)
    for _ in range(chips):
        cx = ox + CORNER + rnd.randrange(0, PATCH - 2 * CORNER - 1)
        cy = oy + CORNER + rnd.randrange(0, PATCH - 2 * CORNER - 1)
        box(d, cx, cy, 1, 1, rnd.choice([lite, line]))


def main():
    img = Image.new("RGB", (ATLAS, ATLAS), "#20242b")
    d = ImageDraw.Draw(img)
    man = {"texelsPerUnit": TEXELS_PER_UNIT, "size": [ATLAS, ATLAS],
           "surfaces": {}, "decals": {}}

    order = ["cream", "blueGrey", "teal", "purple", "plinth", "interior", "shelf"]
    for i, name in enumerate(order):
        ox, oy = (i % 5) * PATCH, (i // 5) * PATCH
        # Bolts only where the kit puts them: its islands are labelled
        # "SIDE-PANEL CORNER BOLT/DECAL". Cream carries the outline and the
        # catch but no rivets - run down the door stiles they read as a dotted
        # line, which the sheet's clean cream frame does not have.
        patch(img, ox, oy, name, seed=i + 3,
              chips=1 if name in ("shelf", "interior") else 3,
              bolts=(name == "blueGrey"))
        man["surfaces"][name] = {"rect": [ox, oy, PATCH, PATCH], "corner": CORNER}

    # --- grille: fixed end caps + a horizontally tiling slot run -----------
    # 48 x 24 = 6 x 3 units. The part MUST be 3 units tall: on an axis it does
    # not tile, a patch's pixel size IS the part's world size.
    gx, gy, gw, gh = 0, PATCH * 2, 48, 24
    box(d, gx, gy, gw, gh, GRILLE_FRAME)
    box(d, gx + 2, gy + 2, gw - 4, gh - 4, P["grilleTan"])
    # The kit's slots are CONTINUOUS lines, so they run across the whole patch
    # INCLUDING the corner ring. A slot that stopped at the ring broke into a
    # dotted mesh the moment the tile repeated.
    rows, rowh, gap = 3, 3, 4
    top = gy + (gh - (rows * rowh + (rows - 1) * gap)) // 2
    for r in range(rows):
        box(d, gx, top + r * (rowh + gap), gw, rowh, SLOT)
    for bx in (gx + 3, gx + gw - 5):          # fixed end-cap bolts, in the ring
        for by in (gy + 4, gy + gh - 6):
            box(d, bx, by, 2, 2, GRILLE_FRAME)
    man["surfaces"]["grille"] = {"rect": [gx, gy, gw, gh], "corner": CORNER}

    # --- fixed decals: blitted at native size, never scaled ----------------
    # temperature display, 88 x 24 = 11 x 3 units
    dx, dy, dw, dh = 56, PATCH * 2, 88, 24
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

    bx, by = 56, PATCH * 2 + 28           # corner bolt island, 4 x 4
    box(d, bx, by, 4, 4, P["blueGrey"])
    box(d, bx + 1, by + 1, 2, 2, BOLT)
    man["decals"]["bolt"] = {"rect": [bx, by, 4, 4]}

    # glass: pale field carrying the kit's fixed diagonal reflection streak
    gx2, gy2 = 152, PATCH * 2
    box(d, gx2, gy2, PATCH, PATCH, GLASS)
    # ONE bold staircase, top-left, like the sheet. Several faint ones read as
    # smudges on the glass rather than as a reflection.
    for i in range(13):
        px, py = gx2 + 26 - i * 2, gy2 + 2 + i * 3
        if gx2 <= px < gx2 + PATCH - 6:
            box(d, px, py, 6, 3, STREAK)
    man["surfaces"]["glass"] = {"rect": [gx2, gy2, PATCH, PATCH], "corner": 1}

    img.save(os.path.join(HERE, "atlas.png"))
    with open(os.path.join(HERE, "atlas.json"), "w") as f:
        json.dump(man, f, indent=2)
    print(f"atlas.png {ATLAS}x{ATLAS} @ {TEXELS_PER_UNIT} texels/unit · "
          f"{len(man['surfaces'])} surfaces, {len(man['decals'])} decals")


if __name__ == "__main__":
    main()
