#!/usr/bin/env python3
"""Cut the surface sheet into a nine-slice TONE MASK atlas.

    python3 tools/authoring/cut_surfaces.py

Authoring tool. NOT a build, CI or runtime dependency.

WHAT A TONE MASK IS, AND WHY NOT A COLOUR ATLAS.

The tiles are generated in neutral grey and stored here as three levels:

      0 = draw this texel in the material's SHADE tone
    128 = leave it the material's BASE colour
    255 = draw it in the material's LIT tone

So the atlas carries STRUCTURE and the material carries COLOUR. One "plate"
tile then renders correctly on cream, on teal and on blue-grey, and the frame
can still snap to a locked palette because no colour ever comes out of the
texture. A colour atlas cannot do either: it ties every tile to one material
and it puts the atlas in charge of the palette, which is exactly what sank the
earlier atlas attempt (a whole cabinet rendered black off one bad upload flag,
and colour management fights on top of that).

THE NINE-SLICE MARGIN is measured, not declared. Each tile's recessed border
sits at its own outer edge; the margin is the distance from that edge in to
where the flat field starts, found as the first long run of the base tone
along the centre row. The renderer maps that margin onto a FIXED WORLD width,
so the border stays native at any part size while the middle tiles between.
That is the whole resize property, and it is why the margin has to be a real
measurement rather than a guess: guess it short and the border gets clipped,
guess it long and the bolts drift inward as the part grows.
"""
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from cut_fittings import islands, rows  # noqa: E402

SRC = ROOT / "docs" / "style-bible" / "surfaces.png"
OUT_PNG = ROOT / "tools" / "voxel-fridge" / "surfaces.png"
OUT_JSON = ROOT / "tools" / "voxel-fridge" / "surfaces.json"

# Reading order across the generated sheet. Verified against the printed grid
# map below rather than assumed — the generator drew seven panels when five
# were asked for, and a hard-coded count would have mis-named every one.
NAMES = ["plate", "plateSeam", "vent",
         "plate2", "trim", "vent2", "recess"]

TEXELS = 40      # tile resolution. Chunky enough to read as pixel art, fine
                 # enough that a 3-4 texel border survives the nine-slice ring.


def to_mask(tile, texels=TEXELS):
    """Three-level tone mask, nearest-downscaled to the texel grid."""
    im = tile.convert("RGB").resize((texels, texels), Image.NEAREST)
    px = im.load()
    lum = [[sum(px[x, y]) / 3 for y in range(texels)] for x in range(texels)]
    flat = sorted(v for col in lum for v in col)
    # Split at the terciles of the tile's OWN luminance range rather than at
    # fixed thresholds: the generator does not hit the same greys twice, and a
    # fixed cut turned one tile entirely to shade.
    lo = flat[len(flat) // 4]
    hi = flat[len(flat) * 3 // 4]
    out = Image.new("L", (texels, texels))
    o = out.load()
    for x in range(texels):
        for y in range(texels):
            v = lum[x][y]
            o[x, y] = 0 if v < lo - 6 else (255 if v > hi + 6 else 128)
    return out


def margin_of(mask):
    """Texels from the tile edge in to where its flat field starts.

    Sampled on several rows and columns and taken as the MEDIAN. A single
    centre row is not enough: on the seamed plate that row lands on the seam
    and on the vent it lands between slots, so the base run breaks early and
    the margin came back as 2 and 1 texels for borders that are plainly wider.
    The border ring is on every row, so the median finds it and the rows that
    cross a feature are outvoted.
    """
    px = mask.load()
    n = mask.size[0]

    def scan(get):
        for i in range(n // 2):
            if all(get(i + k) == 128 for k in range(3)):
                return i
        return n // 4

    vals = []
    for f in (0.18, 0.3, 0.5, 0.7, 0.82):
        j = int(n * f)
        vals += [scan(lambda i, j=j: px[i, j]), scan(lambda i, j=j: px[n - 1 - i, j]),
                 scan(lambda i, j=j: px[j, i]), scan(lambda i, j=j: px[j, n - 1 - i])]
    vals.sort()
    return max(1, vals[len(vals) // 2])


def main():
    im = Image.open(SRC).convert("RGB")
    # No merge_close here. A surface panel is one connected island, and the
    # gap that fittings need (26px, to fuse a vent's separate bars) is larger
    # than the 25px this sheet leaves between its two rows — it chained all
    # seven panels into a single blob.
    grid = rows(islands(im))
    flat = [b for row in grid for b in row]
    print(f"found {len(flat)} tiles in {len(grid)} rows: {[len(r) for r in grid]}")
    if len(flat) != len(NAMES):
        print(f"  WARNING: {len(flat)} tiles but {len(NAMES)} names — names "
              f"below will be wrong. Check {SRC.name} and adjust NAMES.")

    tiles = []
    for i, (x0, y0, x1, y1) in enumerate(flat):
        name = NAMES[i] if i < len(NAMES) else f"tile{i}"
        mask = to_mask(im.crop((max(0, x0), max(0, y0), x1, y1)))
        tiles.append((name, mask, margin_of(mask)))

    W = len(tiles) * (TEXELS + 2) + 2
    atlas = Image.new("L", (W, TEXELS + 4), 128)
    man = {}
    x = 2
    for name, mask, m in tiles:
        atlas.paste(mask, (x, 2))
        man[name] = {"rect": [x, 2, TEXELS, TEXELS],
                     "margin": round(m / TEXELS, 4), "marginTexels": m}
        c = Counter(list(mask.getdata()))
        print(f"  {name:10s} margin {m:2d}/{TEXELS} texels  "
              f"shade {c[0]:4d}  base {c[128]:4d}  lit {c[255]:4d}")
        x += TEXELS + 2

    atlas.convert("RGB").save(OUT_PNG)
    OUT_JSON.write_text(json.dumps(
        {"size": [W, TEXELS + 4], "texels": TEXELS, "tiles": man}, indent=1) + "\n")
    print(f"wrote {OUT_PNG.relative_to(ROOT)} ({W}x{TEXELS + 4}) and "
          f"{OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
