#!/usr/bin/env python3
"""Decompose a reference elevation into MEASURED coloured rectangles.

    python3 tools/authoring/reference_regions.py front.png --out regions.json

Authoring tool. NOT a build, CI or runtime dependency.

WHY. author_prop.py writes a part list from a noun and never sees the
reference, so the result does not resemble it -- a black cabinet with magenta
trim came back brown and teal. The obvious fix is to show the model the
picture, and docs/BUILDING-A-PROP.txt 14.0 is the standing objection to
exactly that: the moment anything reads a proportion off pixels, the pipeline
has lost the property it exists for.

So measure the picture instead, and hand over numbers.

A pixel-art elevation IS very nearly a rectangle list already -- flat regions
of a limited palette, drawn axis-aligned. This quantises to the palette the
image actually uses, finds connected regions per colour, and emits each one as
a box in NORMALISED coordinates (0..1 across the object's own bounding box, not
the frame's). The result reads like a 2D part list:

    marquee band   x 0.08..0.92  z 0.88..0.97   #38e0e0
    screen         x 0.18..0.82  z 0.55..0.85   #8a99a0

which a model can lift into 3D by giving each region a depth, rather than
inventing extents. The front view fixes x and z; the side view fixes y.

Nothing here guesses and nothing here is asked of a model.
"""
import argparse
import json
from collections import Counter

from PIL import Image


def object_box(im):
    """Crop to the object, so coordinates are fractions of IT, not the frame."""
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    xs = [x for x in range(w) if any(not is_bg(px[x, y]) for y in range(0, h, 2))]
    ys = [y for y in range(h) if any(not is_bg(px[x, y]) for x in range(0, w, 2))]
    if not xs:
        raise SystemExit("no object found")
    return (xs[0], ys[0], xs[-1] + 1, ys[-1] + 1), bg


def regions(path, colours=10, min_frac=0.004, step=2):
    im = Image.open(path).convert("RGB")
    box, bg = object_box(im)
    ob = im.crop(box)
    W, H = ob.size
    q = ob.quantize(colors=colours, method=Image.MEDIANCUT).convert("RGB")
    px = q.load()
    raw = ob.load()

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    w, h = W // step, H // step
    grid = [[px[x * step, y * step] for y in range(h)] for x in range(w)]
    solid = [[not is_bg(raw[x * step, y * step]) for y in range(h)] for x in range(w)]
    seen = [[False] * h for _ in range(w)]
    out = []
    for sx in range(w):
        for sy in range(h):
            if seen[sx][sy] or not solid[sx][sy]:
                continue
            col = grid[sx][sy]
            stack = [(sx, sy)]
            seen[sx][sy] = True
            xs, ys, n = [], [], 0
            while stack:
                x, y = stack.pop()
                xs.append(x); ys.append(y); n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = x + dx, y + dy
                    if 0 <= a < w and 0 <= b < h and not seen[a][b] \
                            and solid[a][b] and grid[a][b] == col:
                        seen[a][b] = True
                        stack.append((a, b))
            if n < min_frac * w * h:
                continue
            x0, x1 = min(xs) / w, (max(xs) + 1) / w
            # image y runs DOWN; the part list's z runs UP from the floor
            z0, z1 = 1 - (max(ys) + 1) / h, 1 - min(ys) / h
            out.append({"colour": "#%02x%02x%02x" % col,
                        "x": [round(x0, 3), round(x1, 3)],
                        "z": [round(z0, 3), round(z1, 3)],
                        "area": round(n / (w * h), 4),
                        "fill": round(n / max(1, (max(xs) - min(xs) + 1)
                                              * (max(ys) - min(ys) + 1)), 2)})
    out.sort(key=lambda r: -r["area"])
    return out, box, (W, H)


def accents(path, min_px=200, thresh=60):
    """Rescue the small saturated colours that area filters throw away.

    The arcade reference has a red joystick ball, a yellow button and a red
    button. None survives: the generator's anti-aliasing smears each across
    hundreds of near-identical shades -- 1776 distinct "reds" at about thirty
    pixels apiece -- so no single one clears a quantiser or an area threshold,
    and the palette came back with no red and no yellow in it. The match then
    scored 100% against a target that had lost them.

    Saturated accents are the cheapest identity an object has, and
    reference-gap.md fault 1 is the same lesson from the other end: colour that
    drains out between the sheet and the render. So select by CHROMA rather
    than by area -- bright and far from grey -- then cluster the shades and
    keep any cluster with enough pixels behind it.
    """
    im = Image.open(path).convert("RGB")
    box, bg = object_box(im)
    ob = im.crop(box)
    px = ob.load()
    chroma = Counter()
    for x in range(ob.width):
        for y in range(ob.height):
            c = px[x, y]
            if sum(abs(a - b) for a, b in zip(c, bg)) < 40:
                continue
            mx, mn = max(c), min(c)
            if mx > 110 and (mx - mn) > 70:
                chroma[c] += 1
    seeds = []
    for c, n in chroma.most_common():
        hit = next((s for s in seeds if sum(abs(a - b) for a, b in zip(s[0], c)) < thresh),
                   None)
        if hit is None:
            seeds.append([c, n])
        else:
            hit[1] += n
    return ["#%02x%02x%02x" % c for c, n in seeds if n >= min_px]


def depth_profile(path, bands=12, step=2):
    """Side elevation -> how DEEP the object is at each height.

    The side view is one dark silhouette, so splitting it by colour returns
    outline fragments rather than parts. What the front rectangles are missing
    is a y extent, and that is all this needs to supply: for each band of
    height, the near and far edge of the silhouette, normalised across the
    object's own depth. A stepped cabinet reads straight off it.
    """
    im = Image.open(path).convert("RGB")
    box, bg = object_box(im)
    ob = im.crop(box)
    W, H = ob.size
    px = ob.load()

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    out = []
    for b in range(bands):
        y0, y1 = int(H * b / bands), int(H * (b + 1) / bands)
        xs = [x for x in range(0, W, step)
              if any(not is_bg(px[x, y]) for y in range(y0, y1, step))]
        z0, z1 = 1 - y1 / H, 1 - y0 / H
        if not xs:
            out.append({"z": [round(z0, 3), round(z1, 3)], "y": None})
        else:
            out.append({"z": [round(z0, 3), round(z1, 3)],
                        "y": [round(xs[0] / W, 3), round((xs[-1] + 1) / W, 3)]})
    out.reverse()          # report top-down reads oddly; give floor-up
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--colours", type=int, default=10)
    ap.add_argument("--min-frac", type=float, default=0.004)
    ap.add_argument("--min-fill", type=float, default=0.80,
                    help="a region whose bounding box it does not fill is an "
                         "outline or a scatter, not a rectangle -- drop it")
    ap.add_argument("--profile", action="store_true",
                    help="side view: emit a depth-per-height profile instead")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.profile:
        prof = depth_profile(args.image)
        print(f"{args.image}: depth profile, floor first")
        for b in prof:
            y = b["y"]
            print(f"  z {b['z'][0]:.2f}..{b['z'][1]:.2f}   "
                  + (f"y {y[0]:.2f}..{y[1]:.2f}  (depth {y[1]-y[0]:.2f})" if y else "empty"))
        if args.out:
            json.dump({"source": args.image, "profile": prof}, open(args.out, "w"), indent=1)
            print(f"wrote {args.out}")
        return

    rs, box, size = regions(args.image, args.colours, args.min_frac)
    rs = [r for r in rs if r["fill"] >= args.min_fill]
    print(f"{args.image}: object {size[0]}x{size[1]} at {box}, {len(rs)} regions")
    print(f"  {'area':>6} {'fill':>5}  {'colour':9}  x            z")
    for r in rs[:26]:
        print(f"  {r['area']:6.3f} {r['fill']:5.2f}  {r['colour']:9}  "
              f"{r['x'][0]:.2f}..{r['x'][1]:.2f}   {r['z'][0]:.2f}..{r['z'][1]:.2f}")
    if args.out:
        json.dump({"source": args.image, "object_px": size, "regions": rs},
                  open(args.out, "w"), indent=1)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
