#!/usr/bin/env python3
"""Synthesise a genuinely seamless panel tile, and prove the seam is gone.

    python3 tools/authoring/seamless_tile.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY. make_prop.py's judge stalled for five rounds on one complaint and it was
right every time: "hard seams and banding where the background tiles", "the
smeared dark patches cut off with hard seams". Mirroring the repeats softened
it and could not remove it, because a mirror join is still a join -- the
gradient reverses at it, which reads as a crease.

A painted panel will not tile as-is for two separate reasons, and both have to
be dealt with:

  LOW FREQUENCY  the panel is darker at its edges and grimier at the bottom.
                 That gradient cannot tile at any size: butt two copies
                 together and the dark edge lands against the light middle.
                 Dividing out a heavily blurred copy removes it and leaves
                 the grain, which is the part that CAN tile.
  THE JOIN       even flat grain has a discontinuity where the crop wraps.
                 The standard fix is to cross-blend the tile with copies of
                 itself shifted half a period, weighted so the contributions
                 swap over exactly at the edge. Then T(0,y) and T(w,y) are the
                 same pixel by construction, and there is nothing to see.

The gradient is not thrown away: it belongs to the prop, not the material, so
the renderer keeps it in the nine-slice CAPS, which never repeat.

VERIFIED, NOT ASSUMED. tile_seam_ratio() butts two copies together and
compares the mean gradient across the join against the mean gradient inside
the tile. A seamless tile scores about 1.0; the raw crop scores far higher,
and that number is what says whether this worked.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageFilter


def flatten(im, radius_frac=0.25):
    """Remove the low-frequency gradient, keep the grain."""
    w, h = im.size
    r = max(2, int(min(w, h) * radius_frac))
    blur = im.filter(ImageFilter.GaussianBlur(r))
    bp, sp = blur.load(), im.load()
    # the mean of the blur is the level we normalise back to
    n = 0
    acc = [0, 0, 0]
    for x in range(0, w, 2):
        for y in range(0, h, 2):
            c = bp[x, y]
            acc = [a + v for a, v in zip(acc, c)]
            n += 1
    mean = [a / max(1, n) for a in acc]
    out = Image.new("RGB", (w, h))
    op = out.load()
    for x in range(w):
        for y in range(h):
            s, b = sp[x, y], bp[x, y]
            op[x, y] = tuple(
                max(0, min(255, int(s[i] - b[i] + mean[i]))) for i in range(3))
    return out


def damp(im, keep=0.72):
    """Pull the grain toward its own mean, a little.

    flatten() removes the gradient but leaves the grime at full strength, and a
    strong mark repeated nine times across a widened panel is legible as a
    repeat however seamless the joins are. Softening the deviation trades some
    of the panel's character for a material that does not announce its period.
    Not so far that it goes flat: "blank flat brown" was the complaint this
    whole path exists to answer.
    """
    w, h = im.size
    px = im.load()
    n = 0
    acc = [0, 0, 0]
    for x in range(0, w, 2):
        for y in range(0, h, 2):
            c = px[x, y]
            acc = [a + v for a, v in zip(acc, c)]
            n += 1
    mean = [a / max(1, n) for a in acc]
    out = Image.new("RGB", (w, h))
    op = out.load()
    for x in range(w):
        for y in range(h):
            c = px[x, y]
            op[x, y] = tuple(
                max(0, min(255, int(mean[i] + (c[i] - mean[i]) * keep)))
                for i in range(3))
    return out


def make_seamless(im, feather=0.18):
    """Roll by half, then repair the seam that move puts in the middle.

    The four-corner cross-blend tried first is not a seamless construction and
    the measurement said so -- it took the horizontal seam ratio from 7.3 to
    14.3, worse than the raw crop. Its two edges resolve to DIFFERENT source
    pixels, so there was never a reason for them to match.

    Rolling does work, and by construction rather than by blending: after a
    half-period roll the new left edge is old[w/2] and the new right edge is
    old[w/2 - 1], which were neighbours in the source. The wrap is therefore
    exactly as continuous as the middle of the original was.

    What the roll does is MOVE the discontinuity to a cross through the centre,
    where it is interior and can be repaired without touching the wrap. The
    repair blends across it with a feathered mix of the two sides.
    """
    w, h = im.size
    src = im.load()
    hw, hh = w // 2, h // 2
    rolled = Image.new("RGB", (w, h))
    rp = rolled.load()
    for x in range(w):
        for y in range(h):
            rp[x, y] = src[(x + hw) % w, (y + hh) % h]

    # REPAIR BY BLENDING TOWARD THE ORIGINAL, NOT TOWARD A MIRROR. Mirroring
    # across the join leaves the two sides as different content meeting at a
    # line, and the measurement said so: the cross seam stayed at 5.0 against
    # an interior of 1.0. But the UNROLLED image is continuous exactly where
    # the rolled one is broken, so fade to it at the seam and back to the
    # rolled copy before the edges -- the wrap keeps the roll's continuity
    # (t is 0 there) and the middle keeps the original's.
    out = rolled.copy()
    op = out.load()
    kx, ky = max(2, int(w * feather)), max(2, int(h * feather))
    # AND THE REPAIR MUST VANISH AT THE BORDER. The horizontal seam band runs
    # the full width, so at x=0 and x=w-1 it was pulling in the ORIGINAL's own
    # edges -- which are exactly the discontinuity the roll existed to hide.
    # That put the wrap back up to 2.07/2.71 while fixing the cross. Windowing
    # the blend to zero at every border keeps both.
    def window(i, n, k):
        return max(0.0, min(1.0, i / k, (n - 1 - i) / k))

    for x in range(w):
        tx = max(0.0, 1 - abs(x - hw) / kx)
        ex = window(x, w, kx)
        for y in range(h):
            ty = max(0.0, 1 - abs(y - hh) / ky)
            t = max(tx, ty) * ex * window(y, h, ky)
            if t <= 0:
                continue
            a, b = rp[x, y], src[x, y]
            op[x, y] = tuple(
                max(0, min(255, int(a[i] * (1 - t) + b[i] * t))) for i in range(3))
    return out


def make_seamless_overlap(src, W, H, k):
    """Tile W x H cut from a (W+k) x (H+k) source, with the overlap blended in.

    Roll-and-repair gets the WRAP to 0.6 and cannot get the interior cross
    below about 3.4 -- a wider feather made it worse, not better, because the
    blend only spreads the discontinuity rather than removing it. This has no
    interior seam at all, because it never creates one.

    The trick is that the source is BIGGER than the tile, so column W exists
    and is genuinely adjacent to column W-1. Ramping the first k columns from
    S(x+W) at x=0 back to S(x) at x=k makes the tile's left edge equal to the
    source's column W -- which butts against column W-1, the tile's right edge,
    exactly as it did in the source. Continuous by construction on both axes,
    at the cost of a soft cross-fade in one corner strip.
    """
    sp = src.load()
    sw, sh = src.size
    # defensive: a caller asking for a tile the source cannot cover should get
    # a slightly worse seam, never an IndexError that ends an unattended run
    gx = lambda x: min(x, sw - 1)
    gy = lambda y: min(y, sh - 1)
    out = Image.new("RGB", (W, H))
    op = out.load()
    for x in range(W):
        ax = 1 - x / k if x < k else 0.0
        for y in range(H):
            ay = 1 - y / k if y < k else 0.0
            base = sp[x, y]
            if ax <= 0 and ay <= 0:
                op[x, y] = base
                continue
            # blend in the far side on each axis that is inside the overlap
            r = list(base)
            if ax > 0:
                q = sp[gx(x + W), gy(y)]
                r = [r[i] * (1 - ax) + q[i] * ax for i in range(3)]
            if ay > 0:
                q2 = sp[gx(x), gy(y + H)]
                if ax > 0:
                    q2 = [q2[i] * (1 - ax) + sp[gx(x + W), gy(y + H)][i] * ax
                          for i in range(3)]
                r = [r[i] * (1 - ay) + q2[i] * ay for i in range(3)]
            op[x, y] = tuple(max(0, min(255, int(v))) for v in r)
    return out


def cross_seam_ratio(im):
    """The roll moves the discontinuity to the middle; measure THAT too, or the
    repair is unverified and a clean wrap can still look creased."""
    w, h = im.size
    px = im.load()
    def g(p, q):
        return sum(abs(a - b) for a, b in zip(p, q)) / 3
    hw, hh = w // 2, h // 2
    cv = sum(g(px[hw - 1, y], px[hw, y]) for y in range(h)) / max(1, h)
    ch = sum(g(px[x, hh - 1], px[x, hh]) for x in range(w)) / max(1, w)
    inv = sum(g(px[x, y], px[x + 1, y])
              for x in range(0, w - 1, 3) for y in range(0, h, 3))
    inv /= max(1, len(range(0, w - 1, 3)) * len(range(0, h, 3)))
    inh = sum(g(px[x, y], px[x, y + 1])
              for x in range(0, w, 3) for y in range(0, h - 1, 3))
    inh /= max(1, len(range(0, w, 3)) * len(range(0, h - 1, 3)))
    return (cv / max(0.01, inv), ch / max(0.01, inh))


def tile_seam_ratio(im):
    """Gradient across the wrap join, over gradient inside. ~1.0 = seamless."""
    w, h = im.size
    px = im.load()
    def g(p, q):
        return sum(abs(a - b) for a, b in zip(p, q)) / 3
    join_v = sum(g(px[w - 1, y], px[0, y]) for y in range(h)) / max(1, h)
    join_h = sum(g(px[x, h - 1], px[x, 0]) for x in range(w)) / max(1, w)
    in_v = sum(g(px[x, y], px[x + 1, y])
               for x in range(0, w - 1, 3) for y in range(0, h, 3))
    in_v /= max(1, len(range(0, w - 1, 3)) * len(range(0, h, 3)))
    in_h = sum(g(px[x, y], px[x, y + 1])
               for x in range(0, w, 3) for y in range(0, h - 1, 3))
    in_h /= max(1, len(range(0, w, 3)) * len(range(0, h - 1, 3)))
    return (join_v / max(0.01, in_v), join_h / max(0.01, in_h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--size", type=int, default=96)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    patch_meta = d / f"panel_patch_{args.face}.json"
    bg = Image.open(d / f"bg_{args.face}.png").convert("RGB")
    if patch_meta.exists():
        x0, y0, pw, ph = json.loads(patch_meta.read_text())["patch"]
    else:                       # fall back to the middle of the lower panel
        W, H = bg.size
        pw = ph = min(W, H) // 3
        x0, y0 = (W - pw) // 2, int(H * 0.72)
        ph = min(ph, H - y0)
    # DO NOT UPSCALE THE PATCH. A 39x38 patch blown up to a 96px tile magnifies
    # every grime blob two and a half times, and the middle band then repeats
    # that five to nine times across a widened prop -- which is exactly what the
    # judge kept reporting as "dark grime smears repeat in obvious vertical
    # columns". Repeating FINE grain many times reads as a material; repeating
    # magnified blobs reads as tiling. Build the tile at the panel's own
    # resolution and the repeat stops announcing itself.
    size = max(24, min(args.size, min(pw, ph)))
    if size != args.size:
        print(f"  patch is {pw}x{ph}: building a {size}px tile rather than "
              f"upscaling to {args.size}px")
    best = None
    for k in (16, 24, 32):
        src = bg.crop((x0, y0, x0 + pw, y0 + ph)).resize(
            (size + k, size + k), Image.LANCZOS)
        # LIGHTLY DAMPED ONLY. This tile is now what every growth region is filled
        # with, so it is the entire surface of an enlarged prop -- damped hard it
        # reads as "a huge blank smeared slab with no detail", which is a fault
        # in its own right. It needs to keep its grain; it is the repeat, not the
        # contrast, that had to go.
        # NOT DAMPED. Damping existed to make a repeat less legible, and this tile
        # no longer repeats artwork -- every detail is lifted off as a decal, so
        # what is left is material and its grain is the only thing standing
        # between an enlarged prop and "a flat dark panel with no grime". The
        # judge is right that a bigger cabinet is not a cleaner cabinet.
        tile = make_seamless_overlap(flatten(src), size, size, k)
        wv, wh = tile_seam_ratio(tile)
        cv, ch = cross_seam_ratio(tile)
        worst = max(wv, wh, cv, ch)
        if best is None or worst < best[0]:
            best = (worst, k, tile, (wv, wh, cv, ch))
    worst, k, tile, (wv, wh, cv, ch) = best
    raw = bg.crop((x0, y0, x0 + pw, y0 + ph)).resize((size, size),
                                                     Image.LANCZOS)
    rv, rh = tile_seam_ratio(raw)
    tile.save(d / f"tile_{args.face}.png")
    print(f"panel patch {pw}x{ph} at ({x0},{y0}) -> {size}px tile, overlap k={k}")
    print(f"  raw crop   wrap v {rv:5.2f}  h {rh:5.2f}")
    print(f"  tile       wrap v {wv:5.2f}  h {wh:5.2f}   cross v {cv:5.2f}  h {ch:5.2f}")
    print(f"  {'SEAMLESS' if worst < 1.8 else 'STILL SEAMED'} (worst {worst:.2f})"
          f"  -> {d / f'tile_{args.face}.png'}")
    (d / f"tile_{args.face}.json").write_text(json.dumps(
        {"tile": f"tile_{args.face}.png", "size": size, "k": k,
         "worst_seam": round(worst, 3), "patch_px": [pw, ph]}))


if __name__ == "__main__":
    main()
