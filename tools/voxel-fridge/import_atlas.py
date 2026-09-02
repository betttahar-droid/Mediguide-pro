#!/usr/bin/env python3
"""Import a GENERATED kit sheet as the renderer's atlas.

make_atlas.py hand-authors a sheet that imitates the reference. This imports
the real thing instead: point it at the Nano Banana kit sheet, describe where
its labelled regions are, and it produces the atlas.png + atlas.json the
renderer already consumes. No renderer changes — main.js prefers
`atlas-nano.*` when both exist, so importing is a drop-in swap.

    python3 tools/voxel-fridge/import_atlas.py --sheet ~/kit-sheet.png
    python3 tools/voxel-fridge/import_atlas.py --sheet ... --spec myspec.json
    python3 tools/voxel-fridge/import_atlas.py --sheet ... --dump regions/

WHY A SPEC RATHER THAN AUTO-DETECTION. The kit sheet is a labelled poster:
regions sit on a dark background with text over it, at sizes chosen for human
reading, not for the 8-texels-per-unit grid the renderer needs. Guessing the
rects from pixels would be fragile in exactly the way that wastes a day. The
spec below is the honest interface: measured once, adjusted by eye with
--dump, and then it is data.

WHAT THE IMPORT ACTUALLY DOES
  crop       each named region out of the sheet
  downscale  by an integer factor with NEAREST, so texels stay square and
             hard-edged; the sheet is drawn at roughly 4x our density
  quantise   to a small palette, killing any soft edges the generator left
  pack       into one atlas with the corner/tile metadata each surface needs

The metadata is the part a generated sheet cannot carry: "this region's outer
14 texels are FIXED and its middle tiles on x only" is a decision about the
MODEL, not about the image. See PARTS.md for what each mode means.
"""
import argparse
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEXELS_PER_UNIT = 8

# Measured off the labelled kit sheet at 1536x1024. Rects are [x, y, w, h] in
# SHEET pixels; `scale` is the integer downscale to our density; `corner` and
# `tile` are the nine-slice metadata from PARTS.md. Adjust with --dump, which
# writes every crop out so they can be checked by eye before committing.
DEFAULT_SPEC = {
    "sheet": [1536, 1024],
    "texelsPerUnit": TEXELS_PER_UNIT,
    "surfaces": {
        "cream":    {"rect": [22, 62, 360, 405],  "scale": 4, "corner": 20, "tile": [1, 1]},
        "blueGrey": {"rect": [424, 62, 328, 405], "scale": 4, "corner": 20, "tile": [1, 1]},
        "teal":     {"rect": [26, 540, 356, 432], "scale": 4, "corner": 20, "tile": [1, 0]},
        "grille":   {"rect": [845, 705, 580, 112], "scale": 4, "corner": 14, "tile": [1, 0]},
        "glass":    {"rect": [852, 872, 160, 88],  "scale": 4, "corner": 2,  "tile": [1, 1]},
    },
    "decals": {
        "display": {"rect": [850, 545, 228, 92], "scale": 4},
        "bolt":    {"rect": [455, 545, 72, 72],  "scale": 4},
        "handle":  {"rect": [450, 745, 96, 232], "scale": 4},
    },
    # Surfaces the sheet has no tile for, derived from one flat colour instead.
    # A kit sheet only draws what the object shows; the cavity liner, the
    # shelves and the plinth are colours, not printed panels.
    "derived": {
        "interior": "#357a67",
        "shelf":    "#dbe9e4",
        "plinth":   "#5c4a72",
        "purple":   "#5c4a70",
    },
}


def prepare(img, rect, scale, colours):
    """Crop, integer-downscale with NEAREST, quantise."""
    x, y, w, h = rect
    crop = img.crop((x, y, x + w, y + h))
    tw, th = max(1, crop.width // scale), max(1, crop.height // scale)
    small = crop.resize((tw, th), Image.NEAREST)
    return small.quantize(colors=colours, method=Image.MEDIANCUT).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True, help="the generated kit sheet PNG")
    ap.add_argument("--spec", help="JSON overriding DEFAULT_SPEC")
    ap.add_argument("--colours", type=int, default=12, help="palette size per region")
    ap.add_argument("--dump", help="also write each crop here, to check by eye")
    ap.add_argument("--out", default="atlas-nano", help="output basename")
    args = ap.parse_args()

    spec = DEFAULT_SPEC
    if args.spec:
        with open(args.spec) as f:
            spec.update(json.load(f))

    sheet = Image.open(args.sheet).convert("RGB")
    if list(sheet.size) != spec["sheet"]:
        print(f"note: sheet is {sheet.size}, spec measured at {tuple(spec['sheet'])} — "
              f"rects will be scaled proportionally")
        sx, sy = sheet.width / spec["sheet"][0], sheet.height / spec["sheet"][1]
    else:
        sx = sy = 1.0

    tiles, man = {}, {"texelsPerUnit": spec["texelsPerUnit"], "surfaces": {}, "decals": {}}
    for kind in ("surfaces", "decals"):
        for name, d in spec[kind].items():
            r = [round(d["rect"][0] * sx), round(d["rect"][1] * sy),
                 round(d["rect"][2] * sx), round(d["rect"][3] * sy)]
            tiles[name] = (kind, prepare(sheet, r, d["scale"], args.colours), d)

    for name, hexcol in spec.get("derived", {}).items():
        px = Image.new("RGB", (48, 48), hexcol)
        tiles[name] = ("surfaces", px, {"corner": 20, "tile": [1, 1]})

    # pack: simple shelf packer, which is plenty for a dozen regions
    pad, size = 2, 512
    atlas = Image.new("RGB", (size, size), "#20242b")
    x = y = rowh = 0
    for name, (kind, im, d) in sorted(tiles.items(), key=lambda kv: -kv[1][1].height):
        if x + im.width + pad > size:
            x, y, rowh = 0, y + rowh + pad, 0
        if y + im.height > size:
            raise SystemExit(f"atlas {size}px is too small — raise it or lower --colours")
        atlas.paste(im, (x, y))
        entry = {"rect": [x, y, im.width, im.height]}
        if kind == "surfaces":
            entry["corner"] = d.get("corner", 20)
            entry["tile"] = d.get("tile", [1, 1])
        man[kind][name] = entry
        if args.dump:
            os.makedirs(args.dump, exist_ok=True)
            im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
                os.path.join(args.dump, f"{name}.png"))
        x += im.width + pad
        rowh = max(rowh, im.height)

    man["size"] = [size, size]
    atlas.save(os.path.join(HERE, f"{args.out}.png"))
    with open(os.path.join(HERE, f"{args.out}.json"), "w") as f:
        json.dump(man, f, indent=2)
    print(f"{args.out}.png {size}x{size} @ {spec['texelsPerUnit']} texels/unit · "
          f"{len(man['surfaces'])} surfaces, {len(man['decals'])} decals")
    print("reload the prototype — main.js prefers atlas-nano.* when it exists")


if __name__ == "__main__":
    main()
