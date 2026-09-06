#!/usr/bin/env python3
"""Cut a prop's fittings out of its elevation, with an anchor rule for each.

    python3 tools/authoring/extract_fittings.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY. A nine-sliced panel resizes without smearing, but only the PANEL does.
Everything sitting on it -- a marquee, a screen, a control deck, a coin door --
must keep its real size and move to stay where it belongs, which is what
style.js's screws() already does by hand: "always the same size, always the
same inset from the corner. Inset is in world units, so a bigger panel gets
its screws in the same place relative."

This derives that rule for every fitting instead of one.

WHY NOT ASK THE IMAGE MODEL FOR VARIANTS. The obvious way to learn each
fitting's behaviour is to have Nano Banana redraw the prop bigger and diff the
two. Measured, it does not work: asked for the same cabinet noticeably taller
with its fittings unchanged, it returned the IDENTICAL aspect ratio (0.421) at
2.73x scale -- the same picture, larger, screen and all. It is reliable at
drawing one part and unreliable at redrawing a whole prop to a spec, which is
the same conclusion nano_atlas.py reached ("one tile per prompt rather than
one labelled kit sheet").

So the rules come from ONE elevation, by arithmetic:

  BASE      the dominant colour is the panel; everything else is a fitting
  FITTINGS  connected blobs of not-base, dilated so a multi-coloured feature
            (a screen full of game art) comes out as one fitting rather than
            forty
  ANCHOR    which corner or edge each fitting is nearest, in thirds
  OFFSET    its distance from that anchor, in units of the ORIGINAL height,
            which are world units and do not change when the prop resizes

And the decal images are cut straight from the elevation, so they match the
prop exactly and cost nothing to make.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image


def object_crop(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    xs = [x for x in range(w) if any(not is_bg(px[x, y]) for y in range(0, h, 2))]
    ys = [y for y in range(h) if any(not is_bg(px[x, y]) for x in range(0, w, 2))]
    return im.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1)), bg


def base_colour(ob, colours=12):
    q = ob.quantize(colors=colours, method=Image.MEDIANCUT).convert("RGB")
    px = q.load()
    c = Counter(px[x, y] for x in range(ob.width) for y in range(ob.height))
    return q, c.most_common(1)[0][0]


def bands_of_detail(ob, quantile=0.55, min_rows=0.02):
    """Fittings as BANDS OF ROWS that are not plain.

    Colour blobs do not work on this art and the palette says why: the base
    panel is a family of browns 5..43 apart, while a dark outline network at
    89..141 runs around every feature and joins them all into one blob at any
    threshold. But the row-difference signal that nine_slice.py uses already
    separates plain from detailed by an order of magnitude, and a cabinet's
    fittings ARE horizontal bands -- marquee, screen, control deck, coin door.
    So segment by that instead: contiguous runs of high-difference rows are
    fittings, the low-difference runs between them are panel.
    """
    W, H = ob.size
    px = ob.load()
    diff = []
    for y in range(H - 1):
        sdif = sum(abs(px[x, y][c] - px[x, y + 1][c])
                   for x in range(0, W, 2) for c in range(3))
        diff.append(sdif / max(1, (W // 2) * 3))
    k = max(1, H // 60)
    sm = [sum(diff[max(0, i - k):i + k + 1]) / len(diff[max(0, i - k):i + k + 1])
          for i in range(len(diff))]
    thresh = sorted(sm)[int(quantile * (len(sm) - 1))]
    runs, start = [], None
    for i, v in enumerate(sm + [-1.0]):
        if v > thresh and start is None:
            start = i
        elif v <= thresh and start is not None:
            if i - start >= min_rows * H:
                runs.append((start, i))
            start = None
    return runs


def cols_of_detail(ob, y0, y1, quantile=0.55, min_cols=0.06):
    """Column-localised features inside a band of rows.

    A row scan alone misses anything that is plain ALONG a row: the coin door
    is a big flat rectangle centred on the lower panel, so its interior has
    almost no row-to-row change and it fell into the "plain" gap -- which then
    became the repeating base tile, and a wider cabinet came out with two coin
    doors on it. Scanning columns inside each gap finds it.
    """
    W = ob.width
    px = ob.load()
    diff = []
    for x in range(W - 1):
        sdif = sum(abs(px[x, y][c] - px[x + 1, y][c])
                   for y in range(y0, y1, 2) for c in range(3))
        diff.append(sdif / max(1, ((y1 - y0) // 2) * 3))
    k = max(1, W // 40)
    sm = [sum(diff[max(0, i - k):i + k + 1]) / len(diff[max(0, i - k):i + k + 1])
          for i in range(len(diff))]
    thresh = sorted(sm)[int(quantile * (len(sm) - 1))]
    runs, start = [], None
    for i, v in enumerate(sm + [-1.0]):
        if v > thresh and start is None:
            start = i
        elif v <= thresh and start is not None:
            if i - start >= min_cols * W:
                runs.append((start, i))
            start = None
    # MERGE NEARBY RUNS. A coin door is a flat rectangle: its two vertical
    # EDGES are high-difference and its middle is not, so the scan returned
    # the edges as two thin slivers and the door itself as background. Joining
    # runs separated by less than a fitting's width recovers the whole part.
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 0.18 * W:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    return merged


def extent_of(ob, y0, y1, base, tol, step=2):
    """Horizontal extent of the non-panel pixels inside a band."""
    px = ob.load()
    xs = [x for x in range(0, ob.width, step)
          for y in range(y0, y1, step)
          if sum(abs(a - b) for a, b in zip(px[x, y], base)) > tol]
    if not xs:
        return 0, ob.width
    return min(xs), min(ob.width, max(xs) + step)


def blobs(mask, W, H, step, dilate):
    """Connected components of a boolean grid, with dilation to merge a
    multi-coloured feature into one fitting."""
    grid = [[False] * H for _ in range(W)]
    for (x, y) in mask:
        for dx in range(-dilate, dilate + 1):
            for dy in range(-dilate, dilate + 1):
                a, b = x + dx, y + dy
                if 0 <= a < W and 0 <= b < H:
                    grid[a][b] = True
    seen = [[False] * H for _ in range(W)]
    out = []
    for sx in range(W):
        for sy in range(H):
            if not grid[sx][sy] or seen[sx][sy]:
                continue
            stack = [(sx, sy)]
            seen[sx][sy] = True
            xs, ys, n = [], [], 0
            while stack:
                x, y = stack.pop()
                xs.append(x); ys.append(y); n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = x + dx, y + dy
                    if 0 <= a < W and 0 <= b < H and grid[a][b] and not seen[a][b]:
                        seen[a][b] = True
                        stack.append((a, b))
            out.append((n, min(xs), min(ys), max(xs) + 1, max(ys) + 1))
    out.sort(reverse=True)
    return out


def anchor_of(cu, cv, u0, u1, v0=0.0, v1=0.0, span=0.45):
    """Nearest edge, plus a size mode per axis.

    Thirds were wrong. On this cabinet the screen and the control deck sit a
    little above mid-height, so a thirds rule called them "middle" and let them
    float with the centre -- meaning a taller cabinet would drift them down
    away from the marquee they belong to. Every one of them hangs off the TOP
    assembly at a fixed drop while the plain lower panel takes the change, and
    "nearest edge" says so directly.

    Horizontally these fittings SPAN the cabinet, so a point anchor is the
    wrong idea: a marquee on a wider cabinet is wider. It gets a 1D nine-slice
    instead -- ends fixed, middle stretched -- which is the trim case, and the
    same reason nano_atlas.py insists a tile's border sit on the image edge.
    """
    # symmetric on both axes: a fitting that spans an axis is trim on that
    # axis and gets a 1D nine-slice; one that does not is anchored to the
    # nearer edge at a fixed real size. The cabinet's side rails span the
    # HEIGHT, so without the vertical case a taller cabinet grew a body its
    # own edging no longer reached.
    ax = "span" if (u1 - u0) >= span else ("left" if cu <= 0.5 else "right")
    ay = "span" if (v1 - v0) >= span else ("top" if (1 - cv) <= cv else "bottom")
    mu = "slice" if ax == "span" else "fixed"
    mv = "slice" if ay == "span" else "fixed"
    return ax, ay, mu, mv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--dilate", type=int, default=2)
    ap.add_argument("--quantile", type=float, default=0.55,
                    help="share of rows treated as plain panel")
    ap.add_argument("--tol", type=int, default=60,
                    help="colour distance from the base panel that counts as a fitting")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    ob, _ = object_crop(d / f"{args.face}.png")
    q, base = base_colour(ob)
    qp = q.load()
    runs = bands_of_detail(ob, args.quantile)
    # mine the plain gaps for column-localised fittings (the coin door)
    extra, prev = [], 0
    for (a, b) in runs + [(ob.height, ob.height)]:
        if a - prev > 0.05 * ob.height:
            for (cx0, cx1) in cols_of_detail(ob, prev, a):
                extra.append((prev, a, cx0, cx1))
        prev = b
    kit = d / "fittings"
    kit.mkdir(exist_ok=True)
    out = []
    items = [(y0, y1, None, None) for (y0, y1) in runs] + extra
    for i, (py0, py1, cx0, cx1) in enumerate(items):
        if cx0 is None:
            px0, px1 = extent_of(ob, py0, py1, base, args.tol)
        else:
            px0, px1 = cx0, cx1
            # tighten the band to the feature's own rows
            pxl = ob.load()
            ys = [y for y in range(py0, py1)
                  if any(sum(abs(a - b) for a, b in zip(pxl[x, y], base)) > args.tol
                         for x in range(px0, px1, 2))]
            if ys:
                py0, py1 = ys[0], ys[-1] + 1
        if px1 - px0 < 4 or py1 - py0 < 4:
            continue
        # normalised to the FACE, with v measured up from the floor
        u0, u1 = px0 / ob.width, px1 / ob.width
        v0, v1 = 1 - py1 / ob.height, 1 - py0 / ob.height
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        ax, ay, mu, mv = anchor_of(cu, cv, u0, u1, v0, v1)
        # offset from the anchor, in units of the object's own height so the
        # number is a world size rather than a fraction of a changing face
        asp = ob.width / ob.height
        ou = {"left": u0, "right": 1 - u1, "span": u0, "center": cu - 0.5}[ax] * asp
        ov = {"bottom": v0, "top": 1 - v1, "span": v0, "middle": cv - 0.5}[ay]
        name = f"{args.face}_{i:02d}"
        ob.crop((px0, py0, px1, py1)).save(kit / f"{name}.png")
        out.append({
            "name": name, "face": args.face, "image": f"fittings/{name}.png",
            "anchor": [ax, ay], "mode": [mu, mv],
            "offset": [round(ou, 4), round(ov, 4)],
            "size": [round((u1 - u0) * asp, 4), round(v1 - v0, 4)],
            "area": round((px1 - px0) * (py1 - py0) / (ob.width * ob.height), 4),
            "_py0": py0, "_py1": py1, "_px0": px0, "_px1": px1,
        })

    # THE BASE TILE. Everything not in a detail band is plain panel, and the
    # renderer repeats it rather than stretching it, so the prop can grow on
    # any axis without the material smearing. Take the tallest plain gap.
    used = [(f["_py0"], f["_py1"], f["_px0"], f["_px1"]) for f in out]
    gaps, prev = [], 0
    for (a, b) in runs + [(ob.height, ob.height)]:
        if a - prev > 8:
            gaps.append((prev, a))
        prev = b
    base_png = None
    if gaps:
        g0, g1 = max(gaps, key=lambda g: g[1] - g[0])
        # inside that gap, take a column range no fitting occupies -- otherwise
        # the tile carries a coin door and every repeat stamps another one
        blocked = set()
        for (a, b, c, e) in used:
            if not (b <= g0 or a >= g1):
                blocked.update(range(max(0, c - 2), min(ob.width, e + 2)))
        free, run, start = [], None, None
        for x in range(ob.width):
            if x not in blocked and start is None:
                start = x
            elif x in blocked and start is not None:
                free.append((start, x)); start = None
        if start is not None:
            free.append((start, ob.width))
        c0, c1 = max(free, key=lambda r: r[1] - r[0]) if free else (0, ob.width)
        ob.crop((c0, g0, c1, g1)).save(d / "base.png")
        base_png = "base.png"
        print(f"  base tile: rows {g0}..{g1} x cols {c0}..{c1} "
              f"({c1-c0}x{g1-g0}px of plain panel) -> base.png")

    man = {"face": args.face, "aspect": round(ob.width / ob.height, 4),
           "base_tile": base_png,
           "base": "#%02x%02x%02x" % base, "fittings": out}
    (d / f"fittings_{args.face}.json").write_text(json.dumps(man, indent=1))
    print(f"{args.face}: object {ob.width}x{ob.height}, base {man['base']}, "
          f"{len(out)} fittings")
    print(f"  {'name':14} {'anchor':16} {'offset u,v':>16} {'size w,h':>16}")
    for f in out:
        print(f"  {f['name']:14} {f['anchor'][0]+'/'+f['anchor'][1]+' '+f['mode'][0]:16} "
              f"{f['offset'][0]:7.3f},{f['offset'][1]:7.3f} "
              f"{f['size'][0]:7.3f},{f['size'][1]:7.3f}")
    print(f"wrote {d / f'fittings_{args.face}.json'} and {kit}/")


if __name__ == "__main__":
    main()
