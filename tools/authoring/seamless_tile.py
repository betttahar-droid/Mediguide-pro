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
from collections import Counter
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]


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


def per_strip(d, args):
    """A tile for every band, cut from that band's own material.

    One tile for the whole face cannot be right on a prop made of more than one
    material. This cabinet is grey above and wood below: cutting the tile from
    the wood made a taller cabinet grow correctly and a WIDER one grow wooden
    flanks either side of its grey upper body. Each strip knows which rows it
    owns, so each gets its own tile and grows in the material it is made of.
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "tools" / "authoring"))
    from identify_parts import object_crop as _oc
    src = _oc(d / f"{args.face}.png").convert("RGB")
    strips = json.loads((d / f"strips_{args.face}.json").read_text())["strips"]
    cov = _covered_mask(d, args.face, src.size)
    W0, H0 = src.size

    # THE CARCASS IS ONE MATERIAL. A band across the marquee has almost no body
    # panel in it, so the best "material" it can offer is the vent beside the
    # title -- and a widened cabinet grew ribbed dark chequerwork either side of
    # its marquee. What a prop is MADE of is a property of the prop, not of the
    # band, so a strip whose own material does not look like the carcass borrows
    # the carcass instead.
    px0 = src.load()
    tally = Counter()
    for x in range(0, W0, 2):
        for y in range(0, H0, 2):
            if cov[x][y]:
                continue
            c = px0[x, y][:3]
            if 28 < 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] < 232:
                tally[c] += 1
    body = tally.most_common(1)[0][0] if tally else (128, 128, 128)
    bx, by, bw, bh = _patch_in(src, (0, H0), cov)
    print(f"  carcass {body}, patch {bw}x{bh} at ({bx},{by})")

    out = []
    for i, st in enumerate(strips):
        y0, y1 = st["px"]
        if y1 - y0 < 12:
            out.append(None)
            continue
        x0, py0, pw, ph = _patch_in(src, (y0, y1), cov)
        mean = [0, 0, 0]
        n = 0
        for xx in range(x0, x0 + pw, 2):
            for yy in range(py0, py0 + ph, 2):
                c = px0[xx, yy][:3]
                mean = [m + v for m, v in zip(mean, c)]
                n += 1
        mean = [m / max(1, n) for m in mean]
        far = sum(abs(a - b) for a, b in zip(mean, body)) / 3
        if far > 26 or min(pw, ph) < 12:
            x0, py0, pw, ph = bx, by, bw, bh
            print(f"  strip {i}: own material is {far:.0f} from the carcass "
                  f"-- borrowing the carcass")
        size = max(16, min(args.size, min(pw, ph)))
        k = max(4, size // 5)
        crop = src.crop((x0, py0, x0 + pw, py0 + ph)).resize(
            (size + k, size + k), Image.LANCZOS)
        tile = make_seamless_overlap(flatten(crop), size, size, k)
        name = f"tile_{args.face}_{i}.png"
        tile.save(d / name)
        wv, wh = tile_seam_ratio(tile)
        cv, ch = cross_seam_ratio(tile)
        out.append({"tile": name, "size": size, "patch_px": [pw, ph],
                    "worst_seam": round(max(wv, wh, cv, ch), 3),
                    "rows": [y0, y1]})
        print(f"  strip {i} rows {y0:4}..{y1:4}  patch {pw}x{ph} -> {size}px  "
              f"seam {max(wv, wh, cv, ch):.2f}")
    (d / f"tiles_{args.face}.json").write_text(json.dumps({"tiles": out}, indent=1))
    print(f"wrote {sum(1 for t in out if t)} strip tiles")


def _covered_mask(d, face, size):
    """Which pixels belong to a fitting, so material is never cut from one."""
    W, H = size
    cov = [[False] * H for _ in range(W)]
    try:
        man = json.loads((d / f"parts_{face}.json").read_text())
    except Exception:
        return cov
    for q in man.get("parts", []):
        x0, y0, x1, y1 = q["px"]
        mp = None
        if q.get("mask") and (d / q["mask"]).exists():
            mp = Image.open(d / q["mask"]).convert("L").load()
        for x in range(max(0, x0), min(W, x1)):
            for y in range(max(0, y0), min(H, y1)):
                if mp is None or mp[x - x0, y - y0] > 128:
                    cov[x][y] = True
    return cov


def _patch_in(bg, band, cov=None):
    """The largest chunky run of the dominant mid-tone inside one row band."""
    from collections import Counter
    W, _ = bg.size
    y0, y1 = band
    px = bg.load()
    # MATERIAL IS WHAT THE FITTINGS SIT ON, NOT THE FITTINGS. Cutting from the
    # elevation avoids the circular grey problem, but the elevation still has
    # the artwork in it -- so the marquee's band offered its own cream border as
    # "material" and a widened cabinet grew cream chequerwork either side of its
    # title. Pixels a part covers are not eligible.
    tally = Counter()
    for x in range(0, W, 2):
        for y in range(y0, y1, 2):
            if cov is not None and cov[x][y]:
                continue
            c = px[x, y][:3]
            if 28 < 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] < 232:
                tally[c] += 1
    base = tally.most_common(1)[0][0] if tally else (128, 128, 128)

    def ok(x, y):
        if cov is not None and cov[x][y]:
            return False
        return sum(abs(a - b) for a, b in zip(px[x, y][:3], base)) < 70

    best, bw, bh, score = None, 0, 0, 0
    for sy in range(y0, y1, 4):
        for sx in range(0, W, 4):
            if not ok(sx, sy):
                continue
            ex = sx
            while ex + 1 < W and ok(ex + 1, sy):
                ex += 1
            ey = sy
            while ey + 1 < y1 and all(ok(x, ey + 1) for x in range(sx, ex + 1, 3)):
                ey += 1
            w, h = ex - sx + 1, ey - sy + 1
            if min(w, h) < 8:
                continue
            sc = w * h * (min(w, h) / max(w, h))
            if sc > score:
                best, bw, bh, score = (sx, sy), w, h, sc
    if best is None:
        return 0, y0, min(W, 32), min(32, y1 - y0)
    return best[0], best[1], bw, bh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--rows", default="",
                    help="y0,y1 -- cut the tile from this band only")
    ap.add_argument("--per-strip", action="store_true",
                    help="one tile per strip, each from its own material")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    if args.per_strip:
        return per_strip(d, args)
    patch_meta = d / f"panel_patch_{args.face}.json"
    bg = Image.open(d / f"bg_{args.face}.png").convert("RGB")
    # CUT THE TILE FROM THE BAND THAT WILL BE FILLED WITH IT. The patch was
    # chosen anywhere on the face, and on a cabinet with a grey upper half and a
    # wood lower half it landed on the grey -- so making the prop taller
    # inserted a flat grey band into the middle of the woodwork, which both
    # judges called out as untextured body. The strip that absorbs the height is
    # known by the time this runs, so the material is taken from there.
    band = None
    if args.rows:
        try:
            a, b = (int(v) for v in args.rows.split(","))
            band = (max(0, a), min(bg.size[1], b))
        except ValueError:
            band = None
    if band and band[1] - band[0] > 24:
        # FROM THE ORIGINAL, NOT FROM THE FILLED BACKGROUND. Taking it from the
        # background is circular: the holes there were already filled with the
        # PREVIOUS tile, so a grey tile makes the band grey, which makes the
        # next tile grey. The elevation still has the prop's real material.
        import sys as _s
        _s.path.insert(0, str(ROOT / "tools" / "authoring"))
        from identify_parts import object_crop as _oc
        srcim = _oc(d / f"{args.face}.png").convert("RGB")
        if srcim.size != bg.size:
            srcim = srcim.resize(bg.size)
        x0, y0, pw, ph = _patch_in(srcim, band,
                                   _covered_mask(d, args.face, srcim.size))
        bg = srcim
        print(f"  tile cut from the elevation, rows {band[0]}..{band[1]}")
    elif patch_meta.exists():
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
    # THE TILE CARRIES THE GRAIN; THE PANEL DECIDES THE COLOUR. flatten() lifts
    # the low-frequency gradient off so the tile can repeat at all, and that is
    # the same operation that throws away where the panel sits on the colour
    # wheel. On this cabinet the patch landed near the left edge and the tile
    # came out dusty pink at (150,121,126) against a body whose panel is
    # (71,77,83) -- so a widened cabinet grew pink. Which patch the search
    # happens to pick is a lottery worth not depending on: put the tile's
    # median back onto the panel's median and the fill matches whatever it is
    # standing next to, however the cut went.
    tp = tile.load()
    ob_pix = [tp[x, y] for x in range(size) for y in range(size)]
    face = Image.open(d / f"bg_{args.face}.png").convert("RGBA")
    fp = face.load()
    FW, FH = face.size
    panel = [fp[x, y] for x in range(0, FW, 2) for y in range(0, FH, 2)
             if fp[x, y][3] > 200]
    if panel:
        def med(vals):
            v = sorted(vals)
            return v[len(v) // 2]
        for c in range(3):
            want = med([q[c] for q in panel])
            have = med([q[c] for q in ob_pix])
            k2 = 0 if have <= 0 else min(3.0, want / have)
            for x in range(size):
                for y in range(size):
                    q = list(tp[x, y])
                    q[c] = max(0, min(255, int(round(q[c] * k2))))
                    tp[x, y] = tuple(q)
        print(f"  tile recoloured to the panel: median now "
              f"{tuple(med([tp[x, y][c] for x in range(size) for y in range(size)]) for c in range(3))}")
    # GRAIN REPEATS AS MATERIAL; A BLOB REPEATS AS WALLPAPER. With the colour
    # right, the fill was clean except for one thing: a small light mark in the
    # patch tiled across the whole added panel as a faint regular motif, which
    # is exactly the "repeat a player could point at" this tile exists to
    # avoid. The difference between grain and a feature is amplitude, not
    # frequency -- so clamp each texel to within a fixed multiple of the tile's
    # own median absolute deviation. Fine variation passes through untouched
    # and only the outliers, which are the things the eye latches onto, are
    # pulled back. Damping everything was tried once and made an enlarged prop
    # read as a flat slab; this keeps the material and removes the pattern.
    tp2 = tile.load()
    for c in range(3):
        vals = sorted(tp2[x, y][c] for x in range(size) for y in range(size))
        med = vals[len(vals) // 2]
        mad = sorted(abs(v - med) for v in vals)[len(vals) // 2] or 1
        lim = 2.0 * mad
        for x in range(size):
            for y in range(size):
                q = list(tp2[x, y])
                q[c] = int(round(med + max(-lim, min(lim, q[c] - med))))
                tp2[x, y] = tuple(max(0, min(255, v)) for v in q)
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
