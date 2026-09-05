#!/usr/bin/env python3
"""Measure an orthographic sheet or a render, band by band. PRINTS EVIDENCE.

    python3 tools/authoring/measure.py docs/style-bible/props/med_freeze.png
    python3 tools/authoring/measure.py <img> --rows 0.62 0.95
    python3 tools/authoring/measure.py <img> --view 1 --rows 0.10

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS EXISTS. Every proportion error in this kit read as "slightly off" and
none of them was ever caught by looking. This is the tool phase 0.3 and phase
6.7 of docs/BUILDING-A-PROP.txt both call for, and it was hand-rolled from
scratch three times before it was worth keeping.

IT PRINTS BANDS AND RUNS, NEVER A VERDICT. A tool that answers "is the margin
right?" can be confidently wrong and look clean doing it; three margin
definitions in a row were. A tool that prints "z=0.884 y=95 width=346
mean=#030806" cannot lie to you about what it saw.

GROUND DETECTION, which is the one thing it can get wrong and the one thing
that has bitten in both directions:
  - a magenta sheet uses the magenta test
  - anything else collects the ground from the OUTER MARGIN as a SET of
    colours, because ordered dither makes a render's background a set and not
    one value. Comparing every pixel to a single corner pixel once classified
    an entire frame as object.
"""
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("needs Pillow:  pip install pillow")


def load(path):
    """-> (px, obj, w, h, how). Ground is ALWAYS the border ring.

    A magenta-only test looks safer and is not: a screenshot can carry one stray
    row at the canvas edge, that row becomes "object", and the bounding box is
    then the whole image with every measurement downstream quietly wrong. The
    magenta test is kept as well, so a generated sheet still works if its ring
    happens to clip the subject. Ordered dither is why the ground has to be a
    SET rather than one value in the first place.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    ring = {px[x, y] for y in range(h) for x in range(w)
            if x < 3 or x >= w - 3 or y < 3 or y >= h - 3}
    corner = px[0, 0]
    magenta = corner[0] > 200 and corner[2] > 200 and corner[1] < 80

    def is_ground(c):
        return c in ring or (magenta and c[0] > 200 and c[2] > 200 and c[1] < 80)

    obj = [[not is_ground(px[x, y]) for x in range(w)] for y in range(h)]
    return px, obj, w, h, ("magenta + ring" if magenta else "ring")


def views(obj, w, h):
    """Split the sheet into separate drawings on their own columns."""
    cols = [any(obj[y][x] for y in range(h)) for x in range(w)]
    xs = [x for x in range(w) if cols[x]]
    if not xs:
        sys.exit("nothing but ground in this image")
    out, start = [], xs[0]
    for a, b in zip(xs, xs[1:]):
        if b - a > 1:
            out.append((start, a))
            start = b
    out.append((start, xs[-1]))
    res = []
    for (x0, x1) in out:
        ys = [y for y in range(h) if any(obj[y][x] for x in range(x0, x1 + 1))]
        res.append((x0, x1, ys[0], ys[-1]))
    return res


def vbands(px, obj, box, step):
    """One line per change in width or mean colour, top to bottom.

    z is measured from the BOTTOM, as a fraction of the view's height, because
    that is the direction a model is built in.
    """
    x0, x1, y0, y1 = box
    hp = y1 - y0 + 1
    prev = None
    for y in range(y0, y1 + 1):
        run = [x for x in range(x0, x1 + 1) if obj[y][x]]
        n = len(run)
        if n:
            r = sum(px[x, y][0] for x in run) // n
            g = sum(px[x, y][1] for x in run) // n
            b = sum(px[x, y][2] for x in run) // n
        else:
            r = g = b = 0
        key = (n // step, r // 24, g // 24, b // 24)
        if key != prev:
            print("  z=%.3f  y=%-4d width=%-4d mean=#%02x%02x%02x"
                  % (1 - (y - y0) / hp, y, n, r, g, b))
            prev = key


def row(px, obj, box, zf):
    """One line per change in colour along a horizontal cut."""
    x0, x1, y0, y1 = box
    wp, hp = x1 - x0 + 1, y1 - y0 + 1
    y = int(round(y1 - zf * hp))
    y = max(y0, min(y1, y))
    print("  --- z=%.3f (y=%d) ---" % (zf, y))
    prev = None
    for x in range(x0, x1 + 1):
        c = px[x, y]
        key = tuple(v // 20 for v in c)
        if key != prev:
            print("    x=%.3f  px=%-4d #%02x%02x%02x  %s"
                  % ((x - x0) / wp, x, c[0], c[1], c[2],
                     "" if obj[y][x] else "(ground)"))
            prev = key


def _binarise(px, obj, ax, bx, ay, by):
    """Region -> a boolean map of "off the dominant tone", plus the two tones."""
    from collections import Counter
    c = Counter(px[x, y] for y in range(ay, by) for x in range(ax, bx) if obj[y][x])
    if not c:
        return None, None, None, 0
    dom = c.most_common(1)[0][0]
    far = lambda p: sum((a - b) ** 2 for a, b in zip(p, dom)) >= 18 * 18
    B = [[(far(px[x, y]) if obj[y][x] else None) for x in range(ax, bx)]
         for y in range(ay, by)]
    n = sum(1 for r in B for v in r if v is not None)
    off = sum(1 for r in B for v in r if v)
    second = None
    for col, _ in c.most_common(12):
        if far(col):
            second = col
            break
    return B, dom, second, (off / n if n else 0)


def _checker_pitch(B):
    """The pitch of a checkerboard, PHASE-INDEPENDENTLY, or None.

    Sampling a grid at one stride and looking at (x+y) parity is phase
    dependent: land the samples on the cell boundaries and a perfect
    checkerboard scores 0.50, meaning "no pattern". That is what happened on a
    CRT screen that a 5x zoom shows is unmistakably checked. A checkerboard of
    pitch t instead satisfies two things at every phase — B(x,y) == B(x+2t,y)
    and B(x,y) != B(x+t,y) — so score both and sweep t.
    """
    h, w = len(B), len(B[0])
    best = (0.0, None)
    for t in range(1, min(24, w // 4, h // 4) + 1):
        same = diff = n1 = n2 = 0
        for y in range(0, h - 2 * t, max(1, t // 2)):
            for x in range(0, w - 2 * t, max(1, t // 2)):
                a = B[y][x]
                if a is None:
                    continue
                b, c2 = B[y][x + t], B[y][x + 2 * t]
                if b is not None:
                    n1 += 1; diff += (a != b)
                if c2 is not None:
                    n2 += 1; same += (a == c2)
        if n1 < 20 or n2 < 20:
            continue
        score = (diff / n1 + same / n2) / 2
        if score > best[0]:
            best = (score, t)
    return best


def texture(px, obj, box, rect, label, texel):
    """What KIND of texture a region carries, as numbers rather than a look.

    The style has four procedural patterns and they are not interchangeable:
    flecks are scattered single texels, a checker is an ordered 2-tone grid,
    perf is a dot grid, grain is directional runs. Choosing between them by eye
    is how a cabinet once ended up sprayed with 14% noise that read as grime.

    OFF-DOMINANT under about 6% means the region is FLAT and any pattern put on
    it is an invention. Above that, the checker score decides whether the
    variation is ORDERED (a dither, with a pitch) or not (a fleck).
    """
    x0, x1, y0, y1 = box
    wp, hp = x1 - x0 + 1, y1 - y0 + 1
    ax = int(x0 + rect[0] * wp); bx = int(x0 + rect[1] * wp)
    ay = int(y1 - rect[3] * hp); by = int(y1 - rect[2] * hp)
    B, dom, second, off = _binarise(px, obj, ax, bx, ay, by)
    if B is None:
        return print(f"  {label:16s} (no object pixels)")
    score, pitch = _checker_pitch(B)
    tone2 = ("#%02x%02x%02x" % second) if second else "-"
    verdict = ("FLAT" if off < 0.06 else
               f"CHECKER pitch {pitch}px" if score > 0.85 else
               f"weak order (pitch {pitch}px)" if score > 0.70 else
               "FLECK / noise")
    print(f"  {label:16s} {bx-ax:4d}x{by-ay:<4d}px | dom #{dom[0]:02x}{dom[1]:02x}{dom[2]:02x}"
          f" 2nd {tone2} | off {off*100:5.1f}%"
          f" | order {score:.2f}  -> {verdict}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--rows", nargs="*", type=float, default=[],
                    help="height fractions to cut across, 0 at the floor")
    ap.add_argument("--view", type=int, default=None,
                    help="which drawing on the sheet (default: all)")
    ap.add_argument("--step", type=int, default=6,
                    help="width change, in px, that starts a new band")
    ap.add_argument("--no-bands", action="store_true")
    ap.add_argument("--texel", type=int, default=0,
                    help="pixels per texel; 0 (default) sweeps 2..32 and keeps "
                         "the pitch that correlates best")
    ap.add_argument("--texture", nargs=5, action="append", default=[],
                    metavar=("X0", "X1", "Z0", "Z1", "LABEL"),
                    help="classify a region's texture: fractions of the drawing")
    a = ap.parse_args()

    p = Path(a.image)
    px, obj, w, h, how = load(p)
    vs = views(obj, w, h)
    print("%s  %dx%d  ground: %s  drawings: %d" % (p.name, w, h, how, len(vs)))
    for i, (x0, x1, y0, y1) in enumerate(vs):
        wp, hp = x1 - x0 + 1, y1 - y0 + 1
        print("\nDRAWING %d   x %d..%d  y %d..%d   %d x %d px   ratio 1:%.3f"
              % (i, x0, x1, y0, y1, wp, hp, hp / wp))
        if len(vs) > 1 and i > 0:
            w0 = vs[0][1] - vs[0][0] + 1
            print("            width / drawing 0's width = %.3f" % (wp / w0))
    print()

    todo = vs if a.view is None else [vs[a.view]]
    for i, box in enumerate(todo):
        idx = i if a.view is None else a.view
        if not a.no_bands:
            print("VERTICAL BANDS, drawing %d  (z=0 at the floor)" % idx)
            vbands(px, obj, box, a.step)
            print()
        if a.texture:
            print("TEXTURE, drawing %d" % idx)
            for t in a.texture:
                texture(px, obj, box, [float(v) for v in t[:4]], t[4], a.texel)
            print()
        for zf in a.rows:
            row(px, obj, box, zf)
        if a.rows:
            print()


if __name__ == "__main__":
    main()
