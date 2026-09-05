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
         "vent2", "trim", "recess"]

TEXELS = 20      # tile resolution, deliberately tiny. A published prop in
                 # this style states its budget outright: 138 triangles and a
                 # 64x32 pixel texture for a whole door. At 40 texels a tile
                 # carried marks finer than the model's own pixel grid, which
                 # is precisely the look this style does not have.


def to_mask(tile, texels=TEXELS):
    """Three-level tone mask, nearest-downscaled to the texel grid.

    Split around the MEDIAN by a fraction of the tile's own p10-p90 spread.
    Quartiles with a fixed slack were too crude at this resolution: on a tile
    that is mostly field with a thin border, the upper quartile lands inside the
    field and the mask came back with zero lit texels on one tile and zero shade
    on another — the border simply vanished.
    """
    im = tile.convert("RGB").resize((texels, texels), Image.NEAREST)
    px = im.load()
    lum = [[sum(px[x, y]) / 3 for y in range(texels)] for x in range(texels)]
    flat = sorted(v for col in lum for v in col)
    base = flat[len(flat) // 2]
    spread = max(8.0, flat[int(len(flat) * 0.9)] - flat[int(len(flat) * 0.1)])
    cut = spread * 0.22
    out = Image.new("L", (texels, texels))
    o = out.load()
    for x in range(texels):
        for y in range(texels):
            v = lum[x][y]
            o[x, y] = 0 if v < base - cut else (255 if v > base + cut else 128)
    return out


def margin_of(mask, verbose=False):
    """The nine-slice margin: border thickness plus any corner feature inside it.

    Nine-slice draws the four corners 1:1 and stretches the rest, so the margin
    must contain the border AND the bolts sitting just inside it. Three earlier
    definitions failed, each for its own reason, so this one is explicit:

      1. "distance to the first flat texel" stopped inside the border line and
         left the bolts in the stretched middle, where they smeared across the
         face as big pale squares;
      2. "the outermost column carrying content" saturated at once, because
         every column crosses the top and bottom borders;
      3. "the outermost L-band carrying content" saturated for the same reason:
         band k always includes (k,0) and (0,k), which lie ON those borders.

    So: measure the border along a centre line first, then look for corner
    content strictly INSIDE it.
    """
    px = mask.load()
    n = mask.size[0]
    cap = int(n * 0.35)
    mid = n // 2

    # 1. border thickness, along the centre row and column
    def run_to_field(get):
        for i in range(cap):
            if all(get(i + k) == 128 for k in range(2)):
                return i
        return cap
    border = max(1, min(run_to_field(lambda i: px[i, mid]),
                        run_to_field(lambda i: px[mid, i])))

    # 2. the outermost L-band with content, ignoring the border lines
    last = 0
    prof = []
    for k in range(border, cap):
        band = [(i, j) for i in range(border, k + 1) for j in range(border, k + 1)
                if max(i, j) == k]
        # Require a real SHARE of the band, not a single texel. Downscaling
        # leaves a stray non-base texel here and there from the source's
        # anti-aliasing, and "any texel" let one of those saturate the scan —
        # a plain bordered tile reported corner features all the way to the cap.
        hits = sum(1 for i, j in band
                   for q in (px[i, j], px[n - 1 - i, j],
                             px[i, n - 1 - j], px[n - 1 - i, n - 1 - j])
                   if q != 128)
        hit = hits >= max(3, 0.25 * len(band) * 4)
        prof.append('#' if hit else '.')
        if hit:
            last = k + 1
    if verbose:
        print(f"       border {border}  corner bands [{''.join(prof)}] -> {last}")
    return max(border + 1, min(cap, last))


def is_full_bleed(mask, margin):
    """True when the tile's MIDDLE is content rather than a flat field.

    A vent's slots run edge to edge, so the margin scan above saturates at the
    cap and would freeze most of the tile. Such a tile wants its middle TILED at
    a fixed world period instead — a taller vent then gets more slots rather
    than longer ones. Decided from the art here rather than hand-flagged per
    material, so a new tile classifies itself.
    """
    px = mask.load()
    n = mask.size[0]
    mid = range(margin, n - margin)
    if len(list(mid)) < 3:
        return True
    rows_with_content = sum(
        1 for j in mid if any(px[i, j] != 128 for i in mid))
    return rows_with_content > 0.5 * len(list(mid))


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
        m = margin_of(mask, verbose=True)
        if is_full_bleed(mask, m):
            m = 1                       # a pattern tile keeps only its rim fixed
        tiles.append((name, mask, m, is_full_bleed(mask, m)))

    W = len(tiles) * (TEXELS + 2) + 2
    atlas = Image.new("L", (W, TEXELS + 4), 128)
    man = {}
    x = 2
    for name, mask, m, bleed in tiles:
        atlas.paste(mask, (x, 2))
        man[name] = {"rect": [x, 2, TEXELS, TEXELS],
                     "margin": round(m / TEXELS, 4), "marginTexels": m,
                     "tileMid": bool(bleed)}
        c = Counter(list(mask.getdata()))
        print(f"  -> {name:10s} margin {m:2d}/{TEXELS}  "
              f"{'TILE mid' if bleed else 'stretch '}  "
              f"shade {c[0]:4d} base {c[128]:4d} lit {c[255]:4d}")
        x += TEXELS + 2

    atlas.convert("RGB").save(OUT_PNG)
    OUT_JSON.write_text(json.dumps(
        {"size": [W, TEXELS + 4], "texels": TEXELS, "tiles": man}, indent=1) + "\n")
    print(f"wrote {OUT_PNG.relative_to(ROOT)} ({W}x{TEXELS + 4}) and "
          f"{OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
