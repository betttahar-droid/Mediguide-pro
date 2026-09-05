#!/usr/bin/env python3
"""Compare two orthographic images. TWO CHECKS A JUDGEMENT CANNOT MAKE.

    # does the render match the reference's proportions?
    python3 tools/authoring/compare.py --bands REFERENCE.png RENDER.png

    # did anything anchored move or grow when the prop was widened?
    python3 tools/authoring/compare.py --margins NARROW.png WIDE.png --strip 60

Authoring tool. NOT a build, CI or runtime dependency.

WHY. docs/BUILDING-A-PROP.txt phases 2, 6.5 and 6.7 all say "compare
numerically, not by eye", and then leave the comparing to you. That is the one
instruction in the whole file that assumes judgement, and it is the instruction
most likely to be skipped or faked. Both checks below are arithmetic.

--bands   walks up both silhouettes and prints, at each height, how wide each
          one is as a fraction of its own body width. Same object, same
          proportions, same numbers — whatever the two images' pixel sizes are.
          A band that differs by more than a couple of percent is a real
          proportion error, and it names the height to go and look at.

--margins is the resize test. Everything ANCHORED to an edge lives in a fixed
          strip along that edge, so if the two renders are aligned on their
          silhouettes, those strips must be IDENTICAL. A stretched frame
          section, a handle that scaled, a badge that drifted — all of them
          change the strip. Per-column difference counts are printed rather
          than a verdict.

          RENDER BOTH WITH ?dither=0. The Bayer pattern is keyed on
          gl_FragCoord, so two renders at different canvas widths get a
          different dither PHASE, and up to a third of every flat field lands
          on the other of two neighbouring palette entries. That produces a
          systematic, column-shaped difference indistinguishable from a part
          that really moved — 35% of a strip on a prop whose geometry was
          provably identical. With the dither off the same comparison came back
          at 0.7%.

          CHOOSING --strip: it must cover the region that should be IDENTICAL
          and stop before any REPEAT region. Point it at a frame and it is
          clean; run it 56 px deep on a glass-fronted cabinet and it reaches
          into the shelves, where more stock at the wider size is CORRECT, and
          it reports a difference that is not a bug. A flagged column inside a
          repeating region means your strip is too wide, not that the model is
          wrong.

          --zrange Z0 Z1 limits it to a height band. USE IT when a prop has
          parts anchored to its CENTRE rather than to an edge: a till's monitor
          is a bought-in part, so it is fixed-size and centred, and it
          therefore moves AWAY from the edge as the base widens. The strips
          then differ enormously and correctly. Restrict the check to the band
          where the edge-anchored parts actually live (--zrange 0 0.30 for that
          till's base) and measure the centred parts on their own.

          It cannot see a part anchored in the MIDDLE of a face. Nothing here
          can; measure those individually.
"""
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("needs Pillow:  pip install pillow")


def load(path):
    """-> (px, obj, x0, x1, y0, y1).

    THE GROUND IS ALWAYS COLLECTED FROM THE BORDER RING, magenta or not. A
    magenta-only test looks safer and is not: a screenshot can carry one stray
    row at the canvas edge (an off-by-one between the renderer's height and the
    capture's), and that row is then "object", so the bounding box is the whole
    image and every measurement downstream is quietly wrong. Whatever is in the
    outer ring is ground by definition. The magenta test is kept as well, so a
    generated sheet still works if its ring happens to clip the subject.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    ring = {px[x, y] for y in range(h) for x in range(w)
            if x < 3 or x >= w - 3 or y < 3 or y >= h - 3}
    c = px[0, 0]
    magenta = c[0] > 200 and c[2] > 200 and c[1] < 80

    def bg(p):
        return p in ring or (magenta and p[0] > 200 and p[2] > 200 and p[1] < 80)

    obj = [[not bg(px[x, y]) for x in range(w)] for y in range(h)]
    xs = [x for x in range(w) if any(obj[y][x] for y in range(h))]
    ys = [y for y in range(h) if any(obj[y][x] for x in range(w))]
    if not xs:
        sys.exit(f"{path}: nothing but ground")
    return px, obj, xs[0], xs[-1], ys[0], ys[-1]


def first_drawing(obj, x0, x1, h):
    """A reference sheet holds a front AND a side view. Take the first."""
    cols = [x for x in range(x0, x1 + 1) if any(obj[y][x] for y in range(h))]
    start = cols[0]
    for a, b in zip(cols, cols[1:]):
        if b - a > 1:
            return start, a
    return start, cols[-1]


def widths(obj, box, n):
    """Object width at n evenly spaced heights, as a fraction of the widest."""
    x0, x1, y0, y1 = box
    hp = y1 - y0 + 1
    out = []
    for i in range(n):
        zf = 1 - (i + 0.5) / n
        y = min(y1, max(y0, int(round(y1 - zf * hp))))
        out.append((zf, sum(1 for x in range(x0, x1 + 1) if obj[y][x])))
    widest = max(w for _, w in out) or 1
    return [(zf, w, w / widest) for zf, w in out]


def bands(a_path, b_path, n):
    pa, oa, ax0, ax1, ay0, ay1 = load(a_path)
    pb, ob, bx0, bx1, by0, by1 = load(b_path)
    ax0, ax1 = first_drawing(oa, ax0, ax1, len(oa))
    bx0, bx1 = first_drawing(ob, bx0, bx1, len(ob))
    ra = (ay1 - ay0 + 1) / (ax1 - ax0 + 1)
    rb = (by1 - by0 + 1) / (bx1 - bx0 + 1)
    print(f"A {Path(a_path).name}  {ax1-ax0+1} x {ay1-ay0+1} px   ratio 1:{ra:.3f}")
    print(f"B {Path(b_path).name}  {bx1-bx0+1} x {by1-by0+1} px   ratio 1:{rb:.3f}")
    print(f"RATIO DELTA {abs(ra-rb)/ra*100:.1f}%"
          + ("   <- over 2% is a real proportion error" if abs(ra - rb) / ra > 0.02 else ""))
    print()
    wa = widths(oa, (ax0, ax1, ay0, ay1), n)
    wb = widths(ob, (bx0, bx1, by0, by1), n)
    print("   z      A width   B width    delta")
    worst = (0, 0)
    for (zf, _, fa), (_, _, fb) in zip(wa, wb):
        d = fb - fa
        flag = "  <<<" if abs(d) > 0.03 else ""
        print(f"  {zf:.3f}   {fa:6.3f}    {fb:6.3f}   {d:+7.3f}{flag}")
        if abs(d) > abs(worst[1]):
            worst = (zf, d)
    print()
    print(f"worst band: z={worst[0]:.3f}, {worst[1]:+.3f} of the body width")
    print("Bands marked <<< differ by more than 3%. Go and measure that height")
    print("with measure.py --rows on BOTH images before changing anything.")


def margins(a_path, b_path, strip, zlo=0.0, zhi=1.0):
    pa, oa, ax0, ax1, ay0, ay1 = load(a_path)
    pb, ob, bx0, bx1, by0, by1 = load(b_path)
    ha, hb = ay1 - ay0 + 1, by1 - by0 + 1
    if ha != hb:
        print(f"NOTE heights differ ({ha} vs {hb} px). The resize test needs the")
        print("     SAME prop at two widths — if the height changed too, ?w= is a")
        print("     uniform scale and the test proves nothing. See phase 1.4.")
    rows = min(ha, hb)
    r0, r1 = int(rows * zlo), int(rows * zhi)
    print(f"A {Path(a_path).name}  body {ax1-ax0+1} px")
    print(f"B {Path(b_path).name}  body {bx1-bx0+1} px")
    print(f"comparing {strip}-px strips down each edge, rows z={zlo:.2f}..{zhi:.2f} "
          f"({r1 - r0} of {rows}), aligned on the silhouette\n")
    for side in ("left", "right"):
        diffs = []
        for c in range(strip):
            n = 0
            for r in range(r0, r1):
                if side == "left":
                    xa, xb = ax0 + c, bx0 + c
                else:
                    xa, xb = ax1 - c, bx1 - c
                ya, yb = ay1 - r, by1 - r
                if pa[xa, ya] != pb[xb, yb]:
                    n += 1
            diffs.append(n)
        span = max(1, r1 - r0)
        total = sum(diffs)
        heavy = [c for c, n in enumerate(diffs) if n > span * 0.25]
        print(f"{side.upper()} STRIP  {total} differing pixels "
              f"({total / (strip * span) * 100:.1f}% of the strip)")
        bar = "".join("#" if n > span * 0.25 else
                      "+" if n > span * 0.05 else
                      "." if n else " " for n in diffs)
        print(f"  col 0{' ' * max(0, strip - 12)}col {strip - 1}")
        print(f"  {bar}")
        if heavy:
            print(f"  COLUMNS {heavy[0]}..{heavy[-1]} differ on most rows.")
            print("  If those columns are FRAME, that is an edge that MOVED:")
            print("  something in the strip is a fraction and should be ANCHORED.")
            print("  If they are inside a REPEAT region (contents, slats, seams)")
            print("  they SHOULD differ — narrow --strip until it stops there.")
        else:
            print("  Scattered only — nothing anchored to this edge changed.")
        print()
    print("Reminder: this cannot see a part anchored in the MIDDLE of a face.")
    print("Measure those individually — see BUILDING-A-PROP.txt phase 6.7.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--bands", action="store_true")
    ap.add_argument("--margins", action="store_true")
    ap.add_argument("-n", type=int, default=24, help="bands to sample")
    ap.add_argument("--strip", type=int, default=60, help="edge strip width, px")
    ap.add_argument("--zrange", nargs=2, type=float, default=[0.0, 1.0],
                    metavar=("Z0", "Z1"),
                    help="limit --margins to this height band, 0 at the floor")
    x = ap.parse_args()
    if x.margins:
        margins(x.a, x.b, x.strip, x.zrange[0], x.zrange[1])
    else:
        bands(x.a, x.b, x.n)


if __name__ == "__main__":
    main()
