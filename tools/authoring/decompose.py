#!/usr/bin/env python3
"""Reduce a carve to a slab table a part list can be written against.

    python3 tools/authoring/decompose.py carved.json --out slabs.json

Authoring tool. NOT a build, CI or runtime dependency.

WHY. voxel_carve.py greedy-merges runs of IDENTICAL colour, and a generated
view does not hold identical colours -- the arcade cabinet carved into 3080
boxes across "30" colours, of which nine were the same red to the eye
(#bf2122, #c02022, #c02222, #be2120, ...). One shade's width of noise between
two voxels stops the merge, so the body of the cabinet came out as hundreds of
slivers instead of one slab.

Nothing here looks at an image and nothing here guesses. It:

  1. CLUSTERS the colours by volume -- the biggest colour claims every shade
     within THRESHOLD of it, then the next biggest, and so on. A cluster is
     named by its dominant member, so the palette is lifted from the carve
     rather than imposed on it.
  2. RE-MERGES with voxel_carve.greedy against the clustered colours.
  3. RANKS the result by volume and reports how few slabs carry how much of
     the object, because that number is the whole question: a part list is
     about thirty parts (vaccineFridge.js is 34), so if the top thirty slabs
     do not carry the object, there is nothing for a part list to be written
     against.

The output is a table of extents and colours -- numbers, not pixels. That
matters: docs/BUILDING-A-PROP.txt 14.0 is that the moment anything reads a
proportion off a picture, the pipeline has lost the property it exists for.
Whatever writes the part list reads THIS, never the reference.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "voxel-fridge"))
from voxel_carve import greedy  # noqa: E402


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexs(c):
    return "#%02x%02x%02x" % c


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def load(path):
    """carved.json -> (occ, col, W, D, H) as voxel_carve's greedy() wants."""
    d = json.load(open(path))
    W, D, H = d["grid"]
    occ = [[[False] * H for _ in range(D)] for _ in range(W)]
    col = [[[None] * H for _ in range(D)] for _ in range(W)]
    for b in d["boxes"]:
        c = rgb(b["colour"])
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    occ[x][y][z] = True
                    col[x][y][z] = c
    return occ, col, W, D, H


def cluster(col, occ, W, D, H, threshold):
    """Biggest colour by volume claims every shade within threshold of it."""
    vol = Counter()
    for x in range(W):
        for y in range(D):
            for z in range(H):
                if occ[x][y][z]:
                    vol[col[x][y][z]] += 1
    remap, seeds = {}, []
    for c, _ in vol.most_common():
        if c in remap:
            continue
        hit = next((s for s in seeds if dist(s, c) < threshold), None)
        if hit is None:
            seeds.append(c)
            hit = c
        remap[c] = hit
        for other, _ in vol.most_common():
            if other not in remap and dist(hit, other) < threshold:
                remap[other] = hit
    for x in range(W):
        for y in range(D):
            for z in range(H):
                if occ[x][y][z]:
                    col[x][y][z] = remap[col[x][y][z]]
    return len(vol), len(seeds)


def _exposure(boxes, occ, W, D, H):
    """Faces of each slab that touch empty space -- the only faces ever drawn."""
    out = []
    for b in boxes:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        n = 0
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                       (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                        a, c, e = x + dx, y + dy, z + dz
                        if not (0 <= a < W and 0 <= c < D and 0 <= e < H) \
                                or not occ[a][c][e]:
                            n += 1
        out.append(n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carved")
    ap.add_argument("--threshold", type=int, default=48,
                    help="Manhattan RGB distance that counts as the same colour")
    ap.add_argument("--min-voxels", type=int, default=12,
                    help="slabs smaller than this are reported as crumbs")
    ap.add_argument("--out", default="slabs.json")
    args = ap.parse_args()

    occ, col, W, D, H = load(args.carved)
    before = json.load(open(args.carved))
    total = sum(1 for x in range(W) for y in range(D) for z in range(H) if occ[x][y][z])
    print(f"in:  {len(before['boxes'])} boxes, grid {W}x{D}x{H}, {total} voxels")

    n_col, n_seed = cluster(col, occ, W, D, H, args.threshold)
    print(f"     colours {n_col} -> {n_seed} (threshold {args.threshold})")

    boxes = greedy(occ, col, W, D, H)
    for b in boxes:
        b["voxels"] = ((b["max"][0] - b["min"][0]) * (b["max"][1] - b["min"][1])
                       * (b["max"][2] - b["min"][2]))

    # RANK BY EXPOSED SURFACE, NOT VOLUME. The carve fills its interior with
    # the nearest painted neighbour, so the bulkiest slabs are the black core
    # nobody can see: taking the top thirty by volume rendered a black blob
    # with the red shell, the magenta screen and the yellow marquee all cut.
    # Only a face touching empty space is ever drawn, so that is what a part
    # is worth.
    exposure = _exposure(boxes, occ, W, D, H)
    for b, e in zip(boxes, exposure):
        b["faces"] = e
    boxes.sort(key=lambda b: (-b["faces"], -b["voxels"]))
    surf = sum(b["faces"] for b in boxes)
    print(f"out: {len(boxes)} slabs, {surf} exposed faces")

    surf = sum(b["faces"] for b in boxes)
    run = 0
    marks = {}
    for i, b in enumerate(boxes, 1):
        run += b["faces"]
        for pct in (50, 90, 95, 99):
            if pct not in marks and run >= surf * pct / 100:
                marks[pct] = i
    print("\n     slabs needed to cover this share of VISIBLE SURFACE:")
    for pct in (50, 90, 95, 99):
        print(f"       {pct}% : {marks.get(pct, len(boxes))} slabs")

    crumbs = [b for b in boxes if b["voxels"] < args.min_voxels]
    print(f"\n     crumbs (<{args.min_voxels} voxels): {len(crumbs)} slabs, "
          f"{sum(b['voxels'] for b in crumbs)} voxels "
          f"({100*sum(b['voxels'] for b in crumbs)/total:.1f}% of volume)")

    print("\n     largest slabs:")
    print(f"       {'faces':>7}  {'colour':9}  x            y            z")
    for b in boxes[:14]:
        mn, mx = b["min"], b["max"]
        print(f"       {b['faces']:7}  {b['colour']:9}  "
              f"{mn[0]:3}..{mx[0]:<3}   {mn[1]:3}..{mx[1]:<3}   {mn[2]:3}..{mx[2]:<3}")

    json.dump({"grid": [W, D, H], "voxels": total, "slabs": boxes},
              open(args.out, "w"), indent=1)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
