#!/usr/bin/env python3
"""Generate the fridge atlas with Nano Banana, one tile per prompt.

Authoring tool. NOT a build, CI or runtime dependency.

    python3 tools/voxel-fridge/nano_atlas.py                 # all tiles
    python3 tools/voxel-fridge/nano_atlas.py cream teal      # just those
    python3 tools/voxel-fridge/nano_atlas.py --pack-only     # repack cache

WHY ONE TILE PER PROMPT rather than one labelled kit sheet. A kit sheet has to
be sliced, and slicing means guessing rects out of a poster whose regions were
laid out for human reading — fragile in exactly the way that wastes a day. One
prompt per material gives a known-size image per surface with nothing to find:
the packer places it, and the manifest is generated rather than measured.

WHAT THE PROMPTS ASK FOR, and why it matters to the renderer. Each tile must be
ONE panel whose recessed border sits exactly at the image edge, because the
nine-slice ring samples the outer texels of the patch: put the border there and
it becomes the part's border at any size, with the flat middle tiling between.
Ask for a panel floating on a background instead and the ring samples
background, which is how an earlier attempt rendered a cabinet in solid black.

Generated art arrives anti-aliased at high resolution, so every tile is
integer-downscaled with NEAREST to 8 texels/unit and quantised to a handful of
colours. Without that it is a smooth illustration of pixel art rather than
pixel art, and the nearest-filtered sampler shows every half-tone.

Raw generations are cached in .cache/ so a repack costs nothing; delete a file
there to force one tile to regenerate. Output carries an invisible SynthID
watermark and C2PA credentials.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402

TEXELS_PER_UNIT = 8
PATCH = 96          # 12 units square, matching make_atlas.py
CORNER = 20
ATLAS = 512

STYLE = (
    "16-bit pixel art texture tile, top-down, orthographic, completely flat "
    "shading with NO lighting, NO gradients, NO drop shadow, NO perspective. "
    "Hard-edged chunky pixels, a strictly limited palette of at most six "
    "colours, crisp 1-pixel outlines. The panel FILLS THE ENTIRE IMAGE edge to "
    "edge with no background and no margin around it. Retro cozy medical "
    "palette. No text, no labels, no watermark."
)

# One surface, one prompt. The colour is stated explicitly because the model
# drifts warm otherwise - it drew a tan fridge side even when told "pale steel".
TILES = {
    "cream": (
        "A single square panel of CREAM PAINTED METAL, colour #e9e3d4. A "
        "recessed rectangular border runs just inside the panel edge with a "
        "1-pixel darker outline and a 1-pixel lighter highlight along its top "
        "and left. A small dark bolt sits just inside each of the four corners. "
        "The middle is a flat cream field with three or four single-pixel paint "
        "chips scattered in it.", {"corner": CORNER, "tile": [1, 1]}),
    "blueGrey": (
        "A single square panel of PALE BLUE-GREY PAINTED STEEL, colour #c3ced2. "
        "A recessed rectangular border runs just inside the panel edge with a "
        "1-pixel darker outline. A small dark bolt sits just inside each of the "
        "four corners. The middle is a flat blue-grey field with three or four "
        "single-pixel scuffs.", {"corner": CORNER, "tile": [1, 1]}),
    "teal": (
        "A single square panel of DEEP TEAL GREEN PAINTED METAL, colour "
        "#35785f. A recessed rectangular border runs just inside the panel edge "
        "with a 1-pixel darker outline. A small dark bolt sits just inside each "
        "of the four corners. The middle is a flat teal field with three or "
        "four single-pixel chips.", {"corner": CORNER, "tile": [1, 0]}),
    "plinth": (
        "A single square panel of DARK PURPLE PAINTED METAL, colour #5c4a72, "
        "flat and plain with a 1-pixel darker outline at the panel edge and no "
        "other detail.", {"corner": CORNER, "tile": [1, 0]}),
    "interior": (
        "A single square panel of the INSIDE BACK WALL of a refrigerator, "
        "saturated teal green, colour #357a67, flat and plain with a 1-pixel "
        "darker outline at the panel edge and no bolts.",
        {"corner": CORNER, "tile": [1, 1]}),
    "shelf": (
        "A single square swatch of very pale mint-white painted surface, colour "
        "#dbe9e4, completely plain, with a 1-pixel cooler outline along the "
        "outer edge of the swatch and nothing else on it.",
        {"corner": CORNER, "tile": [1, 1]}),
    # Phrased as a "swatch" rather than a "panel of painted metal": the latter
    # tripped the content filter on three attempts while the near-identical
    # plinth prompt passed. Not worth diagnosing - just reword and move on.
    "purple": (
        "A single square swatch of deep muted purple, colour #5c4a70, "
        "completely plain, with a 1-pixel darker outline along the outer edge "
        "of the swatch and nothing else on it.",
        {"corner": CORNER, "tile": [1, 1]}),
    "glass": (
        "A single square swatch of pale blue-green tinted surface, colour "
        "#bcd8d2, with ONE bold near-white diagonal band crossing it from the "
        "top-left corner downward, drawn as a hard stepped pixel staircase. "
        "Nothing else on the swatch.", {"corner": 2, "tile": [1, 1]}),
}

# The grille is the one structured tile: its slots must run edge to edge so the
# nine-slice joins them into continuous lines across a repeat.
GRILLE = (
    "A rectangular VENTILATION GRILLE panel in warm tan-gold metal, colour "
    "#d9a95f, filling the whole image. Four or five perfectly straight dark "
    "horizontal slots run from the LEFT EDGE to the RIGHT EDGE of the image, "
    "touching both edges so they would join if the image were repeated "
    "side by side. A small bolt sits in each corner.", {"corner": 14, "tile": [1, 0]})


def prepare(path, w, h, colours=8):
    """Integer-downscale with NEAREST to our density, then quantise."""
    im = Image.open(path).convert("RGB")
    # crop to the target aspect before scaling, so nothing is squashed
    want = w / h
    if im.width / im.height > want:
        new_w = round(im.height * want)
        im = im.crop(((im.width - new_w) // 2, 0, (im.width + new_w) // 2, im.height))
    else:
        new_h = round(im.width / want)
        im = im.crop((0, (im.height - new_h) // 2, im.width, (im.height + new_h) // 2))
    im = im.resize((w, h), Image.NEAREST)
    return im.quantize(colors=colours, method=Image.MEDIANCUT).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="tiles to (re)generate; default all")
    ap.add_argument("--pack-only", action="store_true", help="repack the cache")
    ap.add_argument("--colours", type=int, default=8)
    args = ap.parse_args()

    cache = HERE / ".cache"
    cache.mkdir(exist_ok=True)
    wanted = args.names or list(TILES) + ["grille"]

    if not args.pack_only:
        key = load_key()
        failed = []
        for name in wanted:
            prompt = GRILLE[0] if name == "grille" else TILES[name][0]
            out = cache / f"{name}.png"
            print(f"generating {name} ...", flush=True)
            try:
                generate_image(f"{STYLE}\n\n{prompt}", out, key)
            except Exception as exc:
                # One tile tripping a content filter must not lose the whole
                # run: the others are already paid for and cached.
                failed.append(name)
                print(f"  FAILED {name}: {str(exc)[:120]}")
        if failed:
            print(f"  retry these with: nano_atlas.py {' '.join(failed)}")

    # pack everything the cache has
    tiles, man = {}, {"texelsPerUnit": TEXELS_PER_UNIT, "surfaces": {}, "decals": {}}
    for name in list(TILES) + ["grille"]:
        src = cache / f"{name}.png"
        if not src.exists():
            print(f"  (no cached {name}, skipping)")
            continue
        meta = GRILLE[1] if name == "grille" else TILES[name][1]
        w, h = (48, 24) if name == "grille" else (PATCH, PATCH)
        tiles[name] = (prepare(src, w, h, args.colours), meta)

    if not tiles:
        sys.exit("nothing cached — run without --pack-only first")
    # The renderer asks for these by name. A missing one is a hard failure at
    # load, so catch it here where the fix is one more generation.
    NEEDED = {"cream", "blueGrey", "teal", "purple", "plinth", "interior",
              "shelf", "glass", "grille"}
    missing = NEEDED - set(tiles)
    if missing:
        print(f"  WARNING missing surfaces the renderer needs: "
              f"{' '.join(sorted(missing))}")

    atlas = Image.new("RGB", (ATLAS, ATLAS), "#20242b")
    x = y = rowh = 0
    for name, (im, meta) in sorted(tiles.items(), key=lambda kv: -kv[1][0].height):
        if x + im.width + 2 > ATLAS:
            x, y, rowh = 0, y + rowh + 2, 0
        atlas.paste(im, (x, y))
        man["surfaces"][name] = {"rect": [x, y, im.width, im.height], **meta}
        x += im.width + 2
        rowh = max(rowh, im.height)

    # Decals stay hand-authored: they are tiny, exact, and a generator cannot be
    # asked for "88x24 pixels with these six glyph pixels lit".
    hand = json.loads((HERE / "atlas.json").read_text())
    hand_img = Image.open(HERE / "atlas.png").convert("RGB")
    for name, d in hand["decals"].items():
        rx, ry, rw, rh = d["rect"]
        im = hand_img.crop((rx, ry, rx + rw, ry + rh))
        if x + im.width + 2 > ATLAS:
            x, y, rowh = 0, y + rowh + 2, 0
        atlas.paste(im, (x, y))
        man["decals"][name] = {"rect": [x, y, rw, rh]}
        x += im.width + 2
        rowh = max(rowh, im.height)

    # THE PALETTE. Pixel art is a small locked set of colours; a 3D render is
    # not, because every face tint multiplies every texel into a new value. So
    # the post pass snaps the frame to this palette, and this is where it comes
    # from: every colour in the atlas, at each of the five face tints, reduced
    # to 32. Without it the render has hundreds of near-identical colours and
    # reads as a 3D render OF pixel art rather than as pixel art.
    TINTS = (1.09, 1.00, 0.90, 0.86, 0.74)
    # Weight DISTINCT colours equally, not by area. Quantising the atlas image
    # directly let median-cut spend its 32 slots on whatever covers the most
    # pixels, and the grille - a small tan region - lost its colour entirely and
    # came out grey. One pixel per distinct colour per tint fixes that.
    distinct = {c for _, c in atlas.getcolors(1 << 20)}
    cells = [tuple(min(255, round(v * t)) for v in c) for c in distinct for t in TINTS]
    swatch = Image.new("RGB", (len(cells), 1))
    swatch.putdata(cells)
    pal = swatch.quantize(colors=32, method=Image.MEDIANCUT).convert("RGB")
    colours = sorted({c for _, c in pal.getcolors(1 << 20)})
    strip = Image.new("RGB", (len(colours), 1))
    strip.putdata(colours)
    strip.save(HERE / "palette.png")
    man["paletteSize"] = len(colours)
    print(f"palette.png {len(colours)} colours")

    man["size"] = [ATLAS, ATLAS]
    atlas.save(HERE / "atlas-nano.png")
    (HERE / "atlas-nano.json").write_text(json.dumps(man, indent=2))
    print(f"atlas-nano.png {ATLAS}x{ATLAS} @ {TEXELS_PER_UNIT} texels/unit · "
          f"{len(man['surfaces'])} surfaces, {len(man['decals'])} decals")


if __name__ == "__main__":
    main()
