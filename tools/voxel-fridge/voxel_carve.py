#!/usr/bin/env python3
"""Carve a voxel model out of orthographic reference views.

    python3 tools/voxel-fridge/voxel_carve.py \
        --front front.png --side side.png [--top top.png] \
        --height 96 --out carved.json

WHY THIS EXISTS. Every earlier pass had me READING proportions off the
reference and typing coordinates into a build function — and every pass got
something wrong, because "how wide is that door frame as a fraction of the
cabinet" is not a judgement a person makes reliably twelve times in a row.
Shape-from-silhouette removes the judgement: for an axis-aligned object, a
voxel is solid exactly when all three orthographic silhouettes agree it is.
The geometry then IS the reference's silhouette rather than my reading of it.

This is what MagicaVoxel artists do by hand — read the views, derive the
dimensions, lift the palette, build the volume — done arithmetically.

THE CARVE
    occupancy[x][y][z] = front[x][z] AND side[y][z] AND top[x][y]
With no top view, the object is assumed solid through its depth wherever the
front and side agree, which is right for a cabinet and wrong for a torus; the
--top flag exists for when it matters.

COLOUR is projected from the views onto the voxels that face them: the front
view paints the lowest-y solid voxel in each column, the side view the
highest-x, the top view the highest-z. Interior voxels take the nearest
painted neighbour, so a carved model has no unpainted holes when it is cut.

OUTPUT is a greedy-meshed box list — runs merged along x, then y, then z — so
the renderer draws tens of boxes rather than tens of thousands of voxels, and
each box still carries one flat colour. That is the same part list
buildFridge() writes by hand, which is the point: it drops straight in.
"""
import argparse
import json
from collections import Counter

from PIL import Image


def crop_to_object(path):
    """The view cropped to its object. The OBJECT's aspect is what sets the
    voxel grid, never the image's — a generator leaves whatever margin it likes,
    and deriving the grid from the raw image made a 34-wide cabinet 54 wide."""
    im = Image.open(path).convert("RGB")
    corners = [im.getpixel(p) for p in
               ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
    bg = Counter(corners).most_common(1)[0][0]
    px = im.load()

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    xs = [x for x in range(im.width) for y in range(0, im.height, 2) if not is_bg(px[x, y])]
    ys = [y for y in range(im.height) for x in range(0, im.width, 2) if not is_bg(px[x, y])]
    if not xs:
        raise SystemExit(f"{path}: no object found — is the background flat?")
    return im.crop((min(xs), min(ys), max(xs) + 1, max(ys) + 1)), bg


def load_view(path, w, h, colours=0):
    """Downscale a view to the voxel grid and return (mask, colours)."""
    im, _ = crop_to_object(path)
    im = im.resize((w, h), Image.NEAREST)
    # Quantise BEFORE carving. Every distinct colour becomes its own box, so a
    # render straight out of the engine carved into 978 boxes where the object
    # is really about forty; locking the views to a small palette first is what
    # makes the greedy merge do its job.
    if colours:
        im = im.quantize(colors=colours, method=Image.MEDIANCUT).convert("RGB")
    px = im.load()
    # The object was cropped to its own bounds, so anything matching the crop's
    # own corner is still background — a silhouette is never a perfect rectangle.
    corner = px[0, 0]
    mask = [[sum(abs(a - b) for a, b in zip(px[x, y], corner)) >= 40
             for y in range(h)] for x in range(w)]
    cols = [[px[x, y] for y in range(h)] for x in range(w)]
    return mask, cols


def carve(front, side, top, W, D, H):
    """occupancy[x][y][z], with z counted UP from the floor."""
    fm, fc = front
    sm, sc = side
    occ = [[[False] * H for _ in range(D)] for _ in range(W)]
    col = [[[None] * H for _ in range(D)] for _ in range(W)]
    for x in range(W):
        for z in range(H):
            if not fm[x][H - 1 - z]:
                continue
            for y in range(D):
                if not sm[y][H - 1 - z]:
                    continue
                if top is not None and not top[0][x][y]:
                    continue
                occ[x][y][z] = True
    # paint: the front view owns the y=0 face, the side view the x=W-1 face
    for x in range(W):
        for z in range(H):
            for y in range(D):
                if occ[x][y][z]:
                    col[x][y][z] = fc[x][H - 1 - z]
                    break
    for y in range(D):
        for z in range(H):
            for x in range(W - 1, -1, -1):
                if occ[x][y][z] and col[x][y][z] is None:
                    col[x][y][z] = sc[y][H - 1 - z]
                    break
    # fill any voxel the views never saw with its nearest painted neighbour
    for x in range(W):
        for y in range(D):
            for z in range(H):
                if occ[x][y][z] and col[x][y][z] is None:
                    for xx in range(x, -1, -1):
                        if col[xx][y][z]:
                            col[x][y][z] = col[xx][y][z]
                            break
                    else:
                        col[x][y][z] = fc[x][H - 1 - z]
    return occ, col


def greedy(occ, col, W, D, H):
    """Merge runs of same-colour voxels into boxes: x, then y, then z."""
    used = [[[False] * H for _ in range(D)] for _ in range(W)]
    boxes = []
    for z in range(H):
        for y in range(D):
            for x in range(W):
                if not occ[x][y][z] or used[x][y][z]:
                    continue
                c = col[x][y][z]
                x1 = x
                while x1 + 1 < W and occ[x1 + 1][y][z] and not used[x1 + 1][y][z] \
                        and col[x1 + 1][y][z] == c:
                    x1 += 1
                y1 = y
                while y1 + 1 < D and all(occ[i][y1 + 1][z] and not used[i][y1 + 1][z]
                                         and col[i][y1 + 1][z] == c
                                         for i in range(x, x1 + 1)):
                    y1 += 1
                z1 = z
                while z1 + 1 < H and all(occ[i][j][z1 + 1] and not used[i][j][z1 + 1]
                                         and col[i][j][z1 + 1] == c
                                         for i in range(x, x1 + 1) for j in range(y, y1 + 1)):
                    z1 += 1
                for i in range(x, x1 + 1):
                    for j in range(y, y1 + 1):
                        for k in range(z, z1 + 1):
                            used[i][j][k] = True
                boxes.append({"min": [x, y, z], "max": [x1 + 1, y1 + 1, z1 + 1],
                              "colour": "#%02x%02x%02x" % c})
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", required=True)
    ap.add_argument("--side", required=True)
    ap.add_argument("--top")
    ap.add_argument("--height", type=int, default=96, help="voxels tall")
    ap.add_argument("--width", type=int, help="default: from the front view's aspect")
    ap.add_argument("--depth", type=int, help="default: from the side view's aspect")
    ap.add_argument("--colours", type=int, default=24,
                    help="quantise views before carving; 0 to disable")
    ap.add_argument("--out", default="carved.json")
    args = ap.parse_args()

    H = args.height
    fi, _ = crop_to_object(args.front)
    si, _ = crop_to_object(args.side)
    W = args.width or max(1, round(H * fi.width / fi.height))
    D = args.depth or max(1, round(H * si.width / si.height))
    print(f"front {fi.width}x{fi.height} (1:{fi.height/fi.width:.2f})  "
          f"side {si.width}x{si.height} (1:{si.height/si.width:.2f})")

    front = load_view(args.front, W, H, args.colours)
    side = load_view(args.side, D, H, args.colours)
    top = (load_view(args.top, W, D, args.colours)[0],) if args.top else None

    occ, col = carve(front, side, top, W, D, H)
    solid = sum(1 for x in range(W) for y in range(D) for z in range(H) if occ[x][y][z])
    boxes = greedy(occ, col, W, D, H)
    json.dump({"grid": [W, D, H], "boxes": boxes}, open(args.out, "w"), indent=1)
    print(f"grid {W}x{D}x{H} · {solid} voxels · {len(boxes)} boxes "
          f"({solid / max(1, len(boxes)):.0f} voxels per box)")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
