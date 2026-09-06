#!/usr/bin/env python3
"""Build a PS1-shaped prop: extrude the side profile, texture with the sheet.

    python3 tools/authoring/ps1_extrude.py work/ps1 --out work/ps1/model.json

Authoring tool. NOT a build, CI or runtime dependency.

WHY NOT THE VOXEL CARVE. A carve returns a blocky volume -- 3620 boxes and
40296 triangles for one arcade cabinet -- because it is answering "which
voxels are solid". A PlayStation-era prop is the opposite shape of answer: a
few dozen flat facets, with all the detail in a small texture. Carving to a
grid and then fitting boxes back out of it spends the whole budget describing
a silhouette that two polygons could state exactly.

So state it exactly. For a prop whose form is a profile swept across its
width -- a cabinet, a counter, a bench, a fridge -- the SIDE elevation is that
profile, and the object is its extrusion. Trace the silhouette, simplify it to
a handful of corners, extrude across the measured width, and the geometry is
finished at a couple of dozen triangles.

AND THE ELEVATIONS ARE THE TEXTURES. This is the part the box-colour pipeline
could never reach: the reference's marquee art, screen art, panel lines,
labels and grime are painted detail, and a flat-coloured box has nowhere to
put them. Planar-mapped onto the faces they came from -- front elevation on
the front, side on the sides, back on the back -- they are exactly what a PS1
asset does, and the match is by construction rather than by search.

Simplification is Douglas-Peucker on the traced outline, so the corner count
is a tolerance rather than a guess.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


def silhouette_columns(path):
    """For each x, the top and bottom of the object. -> (W, H, tops, bottoms)"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    tops, bots, xs = {}, {}, []
    for x in range(w):
        col = [y for y in range(h) if not is_bg(px[x, y])]
        if col:
            tops[x] = col[0]
            bots[x] = col[-1]
            xs.append(x)
    return w, h, tops, bots, xs


def perp(pt, a, b):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def simplify(pts, tol):
    """Douglas-Peucker: the corner count is a tolerance, not a guess."""
    if len(pts) < 3:
        return pts
    worst, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = perp(pts[i], pts[0], pts[-1])
        if d > worst:
            worst, idx = d, i
    if worst <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def profile(side_path, tol=3.0):
    """The side silhouette as a closed polygon in normalised 0..1 coordinates,
    x = depth front-to-back, y = height up from the floor."""
    w, h, tops, bots, xs = silhouette_columns(side_path)
    x0, x1 = xs[0], xs[-1]
    y0 = min(tops.values())
    y1 = max(bots.values())
    W = x1 - x0 + 1
    H = y1 - y0 + 1

    upper = [(x, tops[x]) for x in range(x0, x1 + 1) if x in tops]
    lower = [(x, bots[x]) for x in range(x1, x0 - 1, -1) if x in bots]
    ring = simplify(upper, tol) + simplify(lower, tol)

    out, seen = [], set()
    for x, y in ring:
        u = round((x - x0) / W, 4)
        v = round((y1 - y) / H, 4)          # image y down -> model y up
        if (u, v) in seen:
            continue
        seen.add((u, v))
        out.append([u, v])
    return out, (W, H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--tol", type=float, default=3.0,
                    help="Douglas-Peucker tolerance in pixels; higher = fewer corners")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    poly, (pw, ph) = profile(d / "side.png", args.tol)
    fw, fh, *_ = silhouette_columns(d / "front.png")[:2] + (None,)
    # width comes from the front elevation's own object box
    w, h, tops, bots, xs = silhouette_columns(d / "front.png")
    width_px = xs[-1] - xs[0] + 1
    height_px = max(bots.values()) - min(tops.values()) + 1

    model = {
        "profile": poly,                 # closed ring, normalised
        "width": round(width_px / height_px, 4),   # x extent / height
        "depth": round(pw / ph, 4),                # y extent / height
        "textures": {n: f"{n}.png" for n in ("front", "side", "back", "top")},
    }
    tris = (len(poly) - 2) * 2 + len(poly) * 2
    print(f"side profile: {len(poly)} corners at tol {args.tol}")
    print(f"  width/height {model['width']}   depth/height {model['depth']}")
    print(f"  extruded solid ~= {tris} triangles")
    out = Path(args.out or (d / "model.json"))
    json.dump(model, open(out, "w"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
