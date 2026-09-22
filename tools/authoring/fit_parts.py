#!/usr/bin/env python3
"""Fit a SMALL number of big boxes to a carve, the way a part list is written.

    python3 tools/authoring/fit_parts.py carved.json --parts 40 --out parts.json

Authoring tool. NOT a build, CI or runtime dependency.

WHY NOT decompose.py. That one PARTITIONS the carve exactly: every voxel ends
up in some slab, no slab holds a voxel the carve does not have. Exactness is
the problem. The carve's surface is a staircase and its colour wobbles a shade
per voxel, so an exact partition of the arcade cabinet is 911 slabs, and the
top 120 of them by visible surface still do not read as a cabinet -- because
dropping the tail DELETES geometry rather than consolidating it.

A hand-written part list is not the biggest N pieces of the truth. It is a
RE-DESCRIPTION: one add() for the whole red body, which happens to disagree
with the carve by a voxel here and there. So fit boxes that are allowed to be
wrong:

    grow a box from a seed while it stays FILL% solid and PURITY% one colour

which lets one box swallow a staircase edge and a shade of noise, and lets
forty boxes stand in for nine hundred. The cost is phantom material where a
box overshoots, which is reported rather than hidden.

Everything here reads the carve, never an image.
"""
import argparse
import json
import random
import sys
from collections import Counter

import numpy as np


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load(path, threshold):
    d = json.load(open(path))
    W, D, H = d["grid"]
    occ = np.zeros((W, D, H), bool)
    col = np.full((W, D, H), -1, np.int16)
    vol = Counter()
    for b in d["boxes"]:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        vol[b["colour"]] += (x1 - x0) * (y1 - y0) * (z1 - z0)
    # cluster colours: biggest claims every shade within threshold
    seeds, remap = [], {}
    for c, _ in vol.most_common():
        hit = next((s for s in seeds
                    if sum(abs(a - b) for a, b in zip(rgb(s), rgb(c))) < threshold), None)
        if hit is None:
            seeds.append(c)
            hit = c
        remap[c] = seeds.index(hit)
    for b in d["boxes"]:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        occ[x0:x1, y0:y1, z0:z1] = True
        col[x0:x1, y0:y1, z0:z1] = remap[b["colour"]]
    return occ, col, seeds, (W, D, H)


def surface(occ):
    """Solid voxels with at least one empty neighbour -- the only ones drawn."""
    s = np.zeros_like(occ)
    s[:-1] |= occ[:-1] & ~occ[1:];  s[1:] |= occ[1:] & ~occ[:-1]
    s[:, :-1] |= occ[:, :-1] & ~occ[:, 1:]; s[:, 1:] |= occ[:, 1:] & ~occ[:, :-1]
    s[:, :, :-1] |= occ[:, :, :-1] & ~occ[:, :, 1:]
    s[:, :, 1:] |= occ[:, :, 1:] & ~occ[:, :, :-1]
    b = np.zeros_like(occ); b[0]=b[-1]=True; b[:,0]=b[:,-1]=True; b[:,:,0]=b[:,:,-1]=True
    return (s | b) & occ


def grow(occ, col, seed, ncol, fill, purity, surf):
    """Grow a box from one voxel while it stays mostly solid and mostly one colour."""
    x, y, z = seed
    lo = [x, y, z]
    hi = [x + 1, y + 1, z + 1]
    W, D, H = occ.shape
    cap = [W, D, H]
    while True:
        best = None
        for axis in range(3):
            for lohi in (0, 1):
                nlo, nhi = lo[:], hi[:]
                if lohi:
                    if nhi[axis] >= cap[axis]:
                        continue
                    nhi[axis] += 1
                else:
                    if nlo[axis] <= 0:
                        continue
                    nlo[axis] -= 1
                sub_o = occ[nlo[0]:nhi[0], nlo[1]:nhi[1], nlo[2]:nhi[2]]
                n = sub_o.size
                soli = int(sub_o.sum())
                if soli < fill * n:
                    continue
                sub_s = surf[nlo[0]:nhi[0], nlo[1]:nhi[1], nlo[2]:nhi[2]]
                sub_c = col[nlo[0]:nhi[0], nlo[1]:nhi[1], nlo[2]:nhi[2]][sub_s]
                # PURITY ON THE SKIN, NOT THE FILL. The carve paints its
                # interior by nearest neighbour from whatever faces got
                # painted, so an unpainted back bleeds black through the
                # whole core -- judging a box by its interior made the body
                # of the cabinet one black slab that swallowed the red shell.
                if sub_c.size:
                    counts = np.bincount(sub_c, minlength=ncol)
                    if counts.max() < purity * sub_c.size:
                        continue
                gain = soli
                if best is None or gain > best[0]:
                    best = (gain, nlo, nhi)
        if best is None:
            return lo, hi
        _, lo, hi = best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carved")
    ap.add_argument("--parts", type=int, default=40)
    ap.add_argument("--threshold", type=int, default=48)
    ap.add_argument("--fill", type=float, default=0.85, help="min solid fraction of a box")
    ap.add_argument("--purity", type=float, default=0.80, help="min single-colour fraction")
    ap.add_argument("--seeds", type=int, default=160, help="candidate seeds per part")
    ap.add_argument("--out", default="parts.json")
    args = ap.parse_args()

    rng = random.Random(7)
    occ, col, palette, (W, D, H) = load(args.carved, args.threshold)
    total = int(occ.sum())
    print(f"in:  grid {W}x{D}x{H}, {total} voxels, {len(palette)} colour clusters")

    surf = surface(occ)
    print(f"     {int(surf.sum())} surface voxels ({100*surf.sum()/total:.1f}% of volume)")
    uncovered = occ.copy()
    boxes = []
    for i in range(args.parts):
        idx = np.argwhere(uncovered)
        if not len(idx):
            break
        picks = idx[rng.sample(range(len(idx)), min(args.seeds, len(idx)))]
        best = None
        for s in picks:
            lo, hi = grow(occ, col, tuple(s), len(palette), args.fill, args.purity, surf)
            gain = int(uncovered[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].sum())
            if best is None or gain > best[0]:
                best = (gain, lo, hi)
        gain, lo, hi = best
        if gain <= 0:
            break
        sub_s = surf[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        sub_c = col[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]][sub_s]
        if not sub_c.size:
            sub_c = col[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]][
                occ[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]]
        c = palette[int(np.bincount(sub_c, minlength=len(palette)).argmax())]
        lo = [int(v) for v in lo]
        hi = [int(v) for v in hi]
        boxes.append({"min": lo, "max": hi, "colour": c, "gain": gain})
        uncovered[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = False

    covered = total - int(uncovered.sum())
    fitted = np.zeros_like(occ)
    for b in boxes:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        fitted[x0:x1, y0:y1, z0:z1] = True
    phantom = int((fitted & ~occ).sum())
    inter = int((fitted & occ).sum())
    union = int((fitted | occ).sum())
    print(f"out: {len(boxes)} parts")
    print(f"     covers {covered}/{total} = {100*covered/total:.1f}% of the carve")
    print(f"     phantom {phantom} voxels ({100*phantom/total:.1f}% of true)")
    print(f"     volume IoU vs the carve {100*inter/union:.2f}%")

    json.dump({"grid": [W, D, H],
               "boxes": [{"min": b["min"], "max": b["max"], "colour": b["colour"]}
                         for b in boxes]}, open(args.out, "w"), indent=1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
