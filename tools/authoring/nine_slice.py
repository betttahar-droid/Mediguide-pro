#!/usr/bin/env python3
"""Find where a prop can be stretched without smearing anything.

    python3 tools/authoring/nine_slice.py front.png --out slice.json

Authoring tool. NOT a build, CI or runtime dependency.

THE PROBLEM. A resizable prop cannot simply be scaled. AdaptivePropBase says
so in the strongest terms it has -- "length authored as a stretch axis" is a
CRITICAL failure -- because scaling a mesh drags its detail with it: a two-
texel trim line becomes a six-texel smear, a round button becomes an oval, and
a marquee stretched to twice the width stops being readable. The same is true
of the texture, and worse, because texels have no geometry to hide behind.

THE OBSERVATION. Stretching is only visible where the image CHANGES along the
stretch axis. A band of rows that are identical to each other can be padded
with as many copies as you like and nobody can tell -- duplicating a row that
equals its neighbour is a no-op. So the question is not "how much can this
stretch" but "WHERE is it already uniform", and that is measurable.

For each row, the mean absolute difference to the row below it. A long run of
near-zero difference is a band that stretches for free. Everything outside it
-- the marquee, the screen, the control panel, the plinth -- is a fixed cap
that keeps its size and simply moves. That is a nine-slice, with the margins
derived from the artwork instead of chosen by hand.

The same scan on columns gives the horizontal slice.

WHAT COMES OUT is two numbers per axis in 0..1 of the object's own box: the
start and end of the stretch band. Geometry and UVs both use them, so the mesh
and its texture stay locked together at any size.
"""
import argparse
import json
from pathlib import Path
from collections import Counter

from PIL import Image


def _object(im):
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    xs = [x for x in range(w) if any(not is_bg(px[x, y]) for y in range(0, h, 2))]
    ys = [y for y in range(h) if any(not is_bg(px[x, y]) for x in range(0, w, 2))]
    return im.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1))


def _runs(diff, thresh):
    """Longest run of consecutive indices whose difference is below thresh."""
    best = (0, 0, 0)
    s = None
    for i, d in enumerate(diff + [float("inf")]):
        if d <= thresh:
            if s is None:
                s = i
        else:
            if s is not None and i - s > best[0]:
                best = (i - s, s, i)
            s = None
    return best


def bands(path, quantile=0.35, min_frac=0.08, fallback=False, parts=None):
    """-> {"v": [z0, z1], "h": [x0, x1]} stretch bands, normalised 0..1.

    z runs UP from the floor to match the model, so the vertical band is
    reported in model coordinates rather than image ones.
    """
    ob = _object(Image.open(path).convert("RGB"))
    W, H = ob.size
    px = ob.load()

    rowdiff = []
    for y in range(H - 1):
        s = sum(abs(px[x, y][c] - px[x, y + 1][c])
                for x in range(0, W, 2) for c in range(3))
        rowdiff.append(s / max(1, (W // 2) * 3))
    coldiff = []
    for x in range(W - 1):
        s = sum(abs(px[x, y][c] - px[x + 1, y][c])
                for y in range(0, H, 2) for c in range(3))
        coldiff.append(s / max(1, (H // 2) * 3))

    def pick(diff, n, axis):
        """SMOOTH BEFORE THRESHOLDING. A hand-painted texture is never two
        identical rows -- the grime alone keeps every difference off zero --
        so an absolute threshold finds nothing and the first version reported
        "no uniform band" for a cabinet whose lower panel is obviously plain.
        What separates a plain panel from the marquee is not zero difference
        but an order of magnitude: 1-3 against 8-15 here. Averaging over a
        short window stops one grimy row from cutting a band in half."""
        if not diff:
            return [0.0, 1.0]
        k = max(1, n // 60)
        sm = [sum(diff[max(0, i - k):i + k + 1]) / len(diff[max(0, i - k):i + k + 1])
              for i in range(len(diff))]
        # THE THRESHOLD NEEDS AN ABSOLUTE FLOOR. A quantile is relative, so a
        # background with its parts already removed -- almost entirely plain
        # panel -- gets the same verdict as a busy one: the cut lands far down
        # its own distribution and only a sliver clears it. On a 0..255 scale
        # a row differing from its neighbour by under ~3 is uniform whatever
        # the rest of the image does, so take whichever is larger.
        srt = sorted(sm)
        thresh = max(srt[int(quantile * (len(srt) - 1))], 3.0)
        span, a, b = _runs(sm, thresh)
        if span >= min_frac * n:
            return [a / n, b / n]
        if not fallback:
            return None                    # nothing uniform enough to trust
        # THE BACKGROUND MUST ALWAYS HAVE A BAND. Returning None for it left
        # the renderer with a zero-width middle and unitW pinned to its floor,
        # so a widened prop asked for four thousand copies of a zero-width UV
        # slice -- the vertical streaking the judge reported on every enlarged
        # prop, round after round. A part may honestly refuse to stretch; a
        # background cannot, because something has to absorb the change. So
        # take the QUIETEST window of the required width instead of the empty
        # answer: it is the best this artwork can offer, and it is measured.
        k = max(2, int(min_frac * n))
        run = sum(sm[:k])
        bestv, besti = run, 0
        for i in range(1, len(sm) - k + 1):
            run += sm[i + k - 1] - sm[i - 1]
            if run < bestv:
                bestv, besti = run, i
        return [besti / n, (besti + k) / n]

    # A COLUMN A FITTING STANDS IN IS NOT SOMEWHERE TO INSERT WIDTH. The same
    # trap as the vertical band: the background is flat where a part was cut
    # out and its hole patched, so the quietest columns are often the coin
    # door's. Striking out the occupied columns first asks where the prop is
    # actually BARE, which is the only place more of it can go.
    if parts:
        try:
            man = json.loads(Path(parts).read_text())
            # WEIGHTED BY HOW MUCH OF THE COLUMN IS COVERED, not struck out on
            # first contact. Striking a column because ANY part touches it left
            # this cabinet with no free columns at all -- its deck and its
            # marquee each run the full width -- so the search fell through to
            # its fallback and returned a band spanning the whole face, which
            # is the stretch-everything behaviour the band exists to prevent.
            # A column under a full-height door is a bad place to insert width;
            # a column that clips one marquee corner is nearly fine. Coverage
            # says which is which, and adding it to the difference score lets
            # busy-ness and occupancy trade off instead of one vetoing.
            cov = [0] * len(coldiff)
            for q in man.get("parts", []):
                x0, y0, x1, y1 = q["px"]
                for x in range(max(0, x0 - 1), min(len(cov), x1 + 1)):
                    cov[x] += max(0, y1 - y0)
            span = max(1.0, max(cov)) if cov else 1.0
            scale = (sorted(coldiff)[int(0.9 * (len(coldiff) - 1))]
                     if coldiff else 1.0) * 2.0 + 1.0
            for x in range(len(coldiff)):
                coldiff[x] += scale * (cov[x] / span)
        except Exception:
            pass

    v = pick(rowdiff, H, "v")
    h = pick(coldiff, W, "h")
    out = {}
    # image y runs DOWN; the model's z runs UP
    out["v"] = [round(1 - v[1], 4), round(1 - v[0], 4)] if v else None
    out["h"] = [round(h[0], 4), round(h[1], 4)] if h else None
    out["size"] = [W, H]

    # THE FILL MATCHES WHAT IT BUTTS AGAINST, NOT THE PROP'S AVERAGE. One
    # global colour for the carcass works on a prop with one body material and
    # fails on one with two: this cabinet has brown panels below and a dark
    # bezel surround above, the median landed on the dark, and a widened
    # cabinet grew dark green out of brown sides. The band is known here, so
    # the colour of the artwork inside it is known too -- and that is exactly
    # the colour the new material will stand next to.
    def band_rgb(box):
        x0, y0, x1, y1 = box
        vals = [[], [], []]
        src = _object(Image.open(path).convert("RGBA"))
        sp = src.load()
        for x in range(max(0, x0), min(W, x1)):
            for y in range(max(0, y0), min(H, y1)):
                q = sp[x, y]
                if len(q) < 4 or q[3] > 200:
                    for c in range(3):
                        vals[c].append(q[c])
        if not vals[0]:
            return None
        return [sorted(v)[len(v) // 2] for v in vals]

    if h:
        out["h_rgb"] = band_rgb((int(h[0] * W), 0, int(h[1] * W), H))
    if v:
        # v is stored in model coordinates, so flip it back to image rows
        out["v_rgb"] = band_rgb((0, int((1 - out["v"][1]) * H),
                                 W, int((1 - out["v"][0]) * H)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--quantile", type=float, default=0.35,
                    help="share of rows counted as 'uniform enough'")
    ap.add_argument("--parts", default=None,
                    help="parts manifest: strike out the columns they occupy")
    ap.add_argument("--fallback", action="store_true",
                    help="never return null: use the quietest window instead")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    b = bands(args.image, args.quantile, fallback=args.fallback,
              parts=args.parts)
    print(f"{args.image}: object {b['size'][0]}x{b['size'][1]}")
    if b["v"]:
        print(f"  vertical   stretch band z {b['v'][0]:.3f}..{b['v'][1]:.3f}  "
              f"({100*(b['v'][1]-b['v'][0]):.0f}% of height)")
    else:
        print("  vertical   no uniform band -- do not stretch this axis")
    if b["h"]:
        print(f"  horizontal stretch band x {b['h'][0]:.3f}..{b['h'][1]:.3f}  "
              f"({100*(b['h'][1]-b['h'][0]):.0f}% of width)")
    else:
        print("  horizontal no uniform band -- do not stretch this axis")
    if args.out:
        json.dump(b, open(args.out, "w"), indent=1)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
