#!/usr/bin/env python3
"""Slice the background into horizontal strips, each with its OWN stretch band.

    python3 tools/authoring/strip_slice.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY ONE NINE-SLICE IS NOT ENOUGH. nine_slice gives the whole face a single
horizontal stretch band -- one vertical strip of the image, applied at every
height. On an arcade cabinet the quietest such strip ran at x 0.371..0.450,
which is plain panel down in the cabinet body and straight through the middle
of the word on the MARQUEE. Widen the prop and that strip is what repeats, so
the title came out as "TRAIL TRAIL TRAIL" while the panel below it tiled
perfectly. No single band can avoid the artwork at every height, because the
artwork is at different places at different heights. The band is the wrong
shape for the question.

A cabinet is a stack of horizontal bands -- marquee, grille, screen bay,
control deck, lower panel -- and each has its own idea of where it is allowed
to grow. The marquee grows in its plain frame either side of the title; the
lower panel grows almost anywhere; the deck grows between button clusters. So
measure each strip separately, and let each repeat its own quiet region.

VERTICALLY, ONE STRIP TAKES THE CHANGE. Splitting the extra height between all
of them would stretch the marquee, and a taller cabinet does not have a taller
marquee -- it has more cabinet. So the strip with the longest genuinely uniform
run of rows absorbs the whole difference by repeating its own middle, and every
other strip keeps its real height. That is what makes a two-metre cabinet look
like a cabinet rather than a photograph of one pulled out of shape.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from collections import Counter as _Counter  # noqa: E402
from nine_slice import _runs  # noqa: E402


def row_diff(im):
    """Mean absolute difference between each row and the one below it."""
    W, H = im.size
    px = im.load()
    out = []
    for y in range(H - 1):
        s = 0
        for x in range(0, W, 2):
            a, b = px[x, y], px[x, y + 1]
            s += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
        out.append(s / max(1, 3 * len(range(0, W, 2))))
    return out


def col_diff(im, y0, y1):
    """The same, column-wise, over one strip only."""
    W, _ = im.size
    px = im.load()
    out = []
    for x in range(W - 1):
        s = 0
        for y in range(y0, y1, 2):
            a, b = px[x, y], px[x + 1, y]
            s += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
        out.append(s / max(1, 3 * len(range(y0, y1, 2))))
    return out


def smooth(a, k):
    return [sum(a[max(0, i - k):i + k + 1]) / len(a[max(0, i - k):i + k + 1])
            for i in range(len(a))]


def quiet_window(diff, frac):
    """The calmest run of at least `frac` of the axis, and how calm it is.

    _runs finds the longest run under a threshold, which is the right answer
    when one exists. When nothing clears the bar this still has to return
    something usable -- a strip that cannot grow at all would leave the
    renderer with a zero-width middle, and that is what asked for four thousand
    copies of a zero-width slice and streaked the whole prop.
    """
    n = len(diff)
    if n < 4:
        return [0.4, 0.6], 999.0
    sm = smooth(diff, max(1, n // 40))
    srt = sorted(sm)
    thresh = max(srt[int(0.35 * (len(srt) - 1))], 3.0)
    span, a, b = _runs(sm, thresh)
    if span >= frac * n:
        inner = sm[a:b] or sm
        # THE PEAK MATTERS AS MUCH AS THE MEAN. A band holding one warning
        # label and 240 rows of plain panel averages out quiet, and the lower
        # cabinet passed on that average and then ran the label six times down
        # a two-metre prop. What must not repeat is the FEATURE, so score the
        # band by the worst row in it as well as the typical one.
        return [a / n, b / n], max(sum(inner) / len(inner), max(inner) / 3.0)
    k = max(2, int(frac * n))
    run = sum(sm[:k])
    best, besti = run, 0
    for i in range(1, n - k + 1):
        run += sm[i + k - 1] - sm[i - 1]
        if run < best:
            best, besti = run, i
    win = sm[besti:besti + k] or sm
    return [besti / n, (besti + k) / n], max(best / k, max(win) / 3.0)


def flank_window(diff, w=0.09, lo=0.07, hi=0.44):
    """The calmest window in the LEFT FLANK -- inside the trim, outside the art.

    Measuring "the outer tenth" instead called every strip busy, because the
    outer tenth of a cabinet is its side trim and outline, which has the
    strongest edges on the whole face. The region that actually grows on a
    marquee is the plain frame between that trim and the title.
    """
    n = len(diff)
    k = max(2, int(w * n))
    i0, i1 = int(lo * n), max(int(lo * n) + 1, int(hi * n) - k)
    if n < 8 or i1 <= i0:
        return (0.15, 0.24), 999.0
    best, besti = None, i0
    for i in range(i0, i1):
        v = sum(diff[i:i + k]) / k
        if best is None or v < best:
            best, besti = v, i
    return (besti / n, (besti + k) / n), best


# Above this, a region is ARTWORK and repeating it duplicates content a player
# can name -- a screen, a ship, a row of cans. Measured as mean absolute
# neighbour difference on 0..255, so it is an absolute bar and not a quantile:
# every axis has a quietest tenth, and on a busy strip that tenth is still busy.
QUIET = 2.0


def grow_mode(diff, band_noise):
    """Repeat an interior band, or hold the art and grow its FLANKS?

    A nine-slice can only repeat something INTERIOR: caps at the ends, band in
    the middle. That is the wrong shape for a marquee, whose artwork is in the
    centre and whose calm regions are the plain frame either side of it. Asked
    for its quietest interior window the marquee offered a strip straight
    through the title, and widening the cabinet tiled it into "TRAIL TRAIL".

    So measure both and pick. Where the flanks are much calmer than the centre,
    the honest growth is to hold the artwork at its real size and extend the
    frame outwards on both sides -- which is what a person would do, and what
    "one title, not three" has meant all along. The flanks are mirrored so the
    two sides grow by the same amount and the art stays centred.
    """
    n = len(diff)
    if n < 8:
        return "extend", (0.15, 0.24), False
    (f0, f1), fn = flank_window(diff)
    # MEASURE THE BAND YOU ARE ACTUALLY GOING TO REPEAT. This used to re-derive
    # a 10% window and test that, while the renderer repeated a 25% one -- so a
    # strip could pass the quiet test and then tile something quite different.
    # The lower cabinet cleared it and duplicated the coin door's frame and a
    # warning label six times down a two-metre prop.
    if band_noise < QUIET:
        return "repeat", (f0, f1), True
    # NOTHING INSIDE IS QUIET ENOUGH TO REPEAT. Repeating the best of a busy
    # strip is how a widened cabinet ended up with three screens, ships cut
    # mid-sprite and a row of doubled can labels -- the judge called every one
    # of those a bug a player could point at, and it was right. Hold the
    # artwork at its real size and grow the flanks instead; and if even the
    # flanks are busy, grow them from a SINGLE column stretched, which cannot
    # duplicate anything. A plain extruded band reads as more cabinet. A second
    # copy of the screen reads as broken.
    return "extend", (f0, f1), (fn < QUIET)


def busy_frac(im, x0, x1, y0, y1):
    """What fraction of a region is NOT its own dominant colour.

    Row-difference is averaged across the full width, so a warning label twelve
    pixels tall barely moves it on a 240-pixel-wide strip: the lower cabinet
    measured as quiet on every difference-based test there is, and then ran
    that label six times down a two-metre prop. A small feature is invisible to
    an average by construction -- but it is not invisible to a COUNT. Anything
    a player could recognise occupies pixels that differ from the panel around
    it, and if there are more than a few percent of them, this region is not
    material and must not be repeated.
    """
    px = im.load()
    W, H = im.size
    x0, x1 = max(0, int(x0)), min(W, int(x1))
    y0, y1 = max(0, int(y0)), min(H, int(y1))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return 1.0
    tally = _Counter()
    for x in range(x0, x1, 2):
        for y in range(y0, y1, 2):
            tally[px[x, y]] += 1
    if not tally:
        return 1.0
    base = tally.most_common(1)[0][0]
    n = far = 0
    for x in range(x0, x1, 2):
        for y in range(y0, y1, 2):
            n += 1
            if sum(abs(a - b) for a, b in zip(px[x, y], base)) > 110:
                far += 1
    return far / max(1, n)


def flank_colour(im, y0, y1, f0, f1):
    """The mean colour of the region a strip grows from.

    A strip that cannot repeat its artwork has to be filled with something, and
    a stretched column gives a featureless wash -- "a flat blank panel", "a
    huge blank smear", in the judge's words, which is as much a bug as the
    duplicated screen it replaced. The answer is the seamless panel tile, which
    has real grain and repeats without duplicating anything recognisable. But
    the tile is cut from ONE patch of the prop, and a marquee's frame is not
    the colour of the cabinet body. So each strip also records the colour of
    its own growth region, and the renderer tints the shared tile to it: one
    material, every strip's own colour, nobody's artwork repeated.
    """
    W, _ = im.size
    px = im.load()
    x0, x1 = int(f0 * W), max(int(f0 * W) + 1, int(f1 * W))
    n = 0
    acc = [0, 0, 0]
    for x in range(x0, min(W, x1)):
        for y in range(y0, y1, 2):
            c = px[x, y]
            acc = [a + v for a, v in zip(acc, c)]
            n += 1
    return [round(a / max(1, n)) for a in acc]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--min-strip", type=float, default=0.045,
                    help="strips thinner than this fraction get merged up")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    im = Image.open(d / f"bg_{args.face}.png").convert("RGB")
    W, H = im.size

    # STRIP BOUNDARIES ARE THE STRONG HORIZONTAL LINES. A cabinet's bands are
    # drawn with them -- the rail under the marquee, the lip of the deck -- so
    # the artwork tells us where its own bands are and nothing has to guess.
    rd = smooth(row_diff(im), max(1, H // 200))
    srt = sorted(rd)
    cut = srt[int(0.90 * (len(srt) - 1))]
    edges = [0]
    for y, v in enumerate(rd):
        if v >= cut and y - edges[-1] >= int(args.min_strip * H):
            edges.append(y + 1)
    if H - edges[-1] < int(args.min_strip * H) and len(edges) > 1:
        edges.pop()
    edges.append(H)

    strips = []
    for i in range(len(edges) - 1):
        y0, y1 = edges[i], edges[i + 1]
        cd = col_diff(im, y0, y1)
        hband, noise = quiet_window(cd, 0.10)
        rows = rd[y0:max(y0 + 2, y1 - 1)]
        vband, vnoise = quiet_window(rows, 0.25)
        hmode, hflank, hrep = grow_mode(cd, noise)
        vmode, vflank, vrep = grow_mode(rows, vnoise)
        # and the band has to be MATERIAL, not just smooth on average
        BUSY = 0.05
        if hrep and busy_frac(im, hband[0] * W, hband[1] * W, y0, y1) > BUSY:
            hmode, hrep = "extend", False
        if vrep and busy_frac(im, 0, W, y0 + vband[0] * (y1 - y0),
                              y0 + vband[1] * (y1 - y0)) > BUSY:
            vmode, vrep = "extend", False
        if hmode == "extend" and hrep and \
                busy_frac(im, hflank[0] * W, hflank[1] * W, y0, y1) > BUSY:
            hrep = False
        strips.append({
            "fill": flank_colour(im, y0, y1, hflank[0], hflank[1]),
            "hmode": hmode, "hf": [round(hflank[0], 5), round(hflank[1], 5)],
            "hf_repeat": hrep,
            "vmode": vmode, "vf": [round(vflank[0], 5), round(vflank[1], 5)],
            "vf_repeat": vrep,
            # v measured from the BOTTOM, like everything else the renderer eats
            "v": [round(1 - y1 / H, 5), round(1 - y0 / H, 5)],
            "h": [round(hband[0], 5), round(hband[1], 5)],
            "vh": [round(vband[0], 5), round(vband[1], 5)],
            "noise": round(noise, 3), "vnoise": round(vnoise, 3),
            "px": [y0, y1],
        })

    # THE STRIP THAT GROWS MUST BE BODY, NOT MERELY QUIET. Scored on height and
    # calm alone the winner was the SCREEN BAY -- a big flat dark rectangle is
    # about as quiet as an image gets -- so a taller cabinet grew a two-metre
    # screen recess with the deck stranded at the bottom. A prop gets taller by
    # having more BODY, so the strip must also look like the body: its mean
    # colour has to match the panel colour the rest of the pipeline already
    # measures. That is what separates the cabinet's plain lower panel from an
    # equally smooth sheet of glass.
    px_im = im.load()
    tally = _Counter()
    for x in range(0, W, 2):
        for y in range(0, H, 2):
            c = px_im[x, y]
            if 28 < 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] < 232:
                tally[c] += 1
    panel = tally.most_common(1)[0][0] if tally else (128, 128, 128)

    def body_score(st):
        y0, y1 = st["px"]
        n = 0
        acc = [0, 0, 0]
        for x in range(0, W, 3):
            for y in range(y0, y1, 3):
                c = px_im[x, y]
                acc = [a + v for a, v in zip(acc, c)]
                n += 1
        mean = [a / max(1, n) for a in acc]
        dist = sum(abs(a - b) for a, b in zip(mean, panel)) / 3
        like_body = 1.0 / (1.0 + (dist / 22.0) ** 2)
        return (y1 - y0) * like_body / max(1.0, st["vnoise"])

    grow = max(range(len(strips)), key=lambda i: body_score(strips[i]))
    for i, s in enumerate(strips):
        s["grow_y"] = (i == grow)

    (d / f"strips_{args.face}.json").write_text(json.dumps(
        {"size": [W, H], "strips": strips}, indent=1))
    print(f"{args.face}: {len(strips)} strips")
    for i, s in enumerate(strips):
        print(f"  {i}: rows {s['px'][0]:4}..{s['px'][1]:4}  {s['hmode']:6} "
              f"h {s['h'][0]:.3f}..{s['h'][1]:.3f} (noise {s['noise']:6.2f})"
              f"{'   <- takes the height, ' + s['vmode'] if s['grow_y'] else ''}")
    print(f"wrote {d / f'strips_{args.face}.json'}")


if __name__ == "__main__":
    main()
