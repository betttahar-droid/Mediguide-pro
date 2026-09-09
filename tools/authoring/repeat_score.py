#!/usr/bin/env python3
"""Measure whether resizing a prop DUPLICATED anything, from the renders alone.

    python3 tools/authoring/repeat_score.py tools/img2threejs-work/v48_arcade_cabinet

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Of 306 blocking faults across three judged runs, 181 were one sentence in
different words: "a tiling seam, repeat, smear or band a player could point
at". It is the fault this whole growth-band machinery exists to avoid, it is
the one the judges report most, and it is the one they are worst at.

They scored a cabinet with FIVE ARCADE marquees stacked down its front at two
blocking faults -- exactly what they gave the fixed cabinet beside it. They
passed a pinball standing on stilts at zero. Both graders, both runs. A
grader that cannot separate those is not measuring this class, and no amount
of prompting will make a language model count copies of a sign reliably.

Arithmetic can. A repeat is PERIODICITY, and periodicity is the thing
autocorrelation was invented for. Take the row-luminance profile of the prop
in the render -- one number per scanline, over the prop's own pixels -- and
autocorrelate it. A cabinet with one marquee has no strong period. The same
cabinet with the marquee laid down five times has a peak at the spacing
between them, and it is not subtle: 0.87 against 0.24 on the pair above.

CONTROLLED AGAINST THE PROP'S OWN 1x RENDER, which is the whole trick. Props
are periodic by nature -- a vending machine has shelves, a jukebox has title
strips, and a bare autocorrelation score punishes them for being what they
are. What is a fault is periodicity the ORIGINAL DID NOT HAVE. So the same
measurement runs on the 1x render and only the RISE counts. A machine drawn
with three shelves and resized to six has gained a period it always had; a
cabinet drawn with one marquee and resized to five has gained one it never
had, and only the second is a bug.

AND FLATNESS IS THE OTHER HALF. The opposite failure is not a repeat, it is a
blank: the growth band blows the renderer's copy bound, falls back to the
carcass tile, and the prop grows a dead grey slab. That is periodicity's
mirror image -- a long run of scanlines with almost no variation, where the
original had detail -- and it is measured on the same profile in the same
pass.

Neither number is a taste call and neither needs a model. Both are free,
both are deterministic, and both run on renders the loop has already made.

TRIED AND REVERTED: THE SAME MEASURE AS A LICENCE RATHER THAN A VETO. A
growth band is refused unless its rows are bare, and that is too strict on
its face -- some material is periodic to begin with and repeating THAT is
invisible. A speaker grille is slats, a vent is louvres, a radiator is fins,
and laying down more of one is what a taller one of the object has. The
jukebox is the motivating case: its front is grille edge to edge, every place
it named was refused for having the grille in it, and the blind fallback grew
a dead grey slab under the cabinet instead.

So: let a band repeat if it is bare OR already a repeat, using this same
autocorrelation on the elevation's own rows.

It does not work, and the failure is worth keeping because the idea will
occur again. At a minimum period of 3 scanlines everything scores high --
including the ARCADE marquee at 0.80 -- because what is being measured there
is the texel grid, not slats. Raised to 8 and then 12, the separation does
not appear; it inverts. The jukebox's GRILLE, the one band this was written
to license, scores lowest of every case tried (0.27, then 0.18) while the
marquee that must never repeat scores 0.55 and 0.29 above it.

The reason is that a diamond mesh has no vertical period in its ROW MEANS at
all -- averaging across the width of a grille gives very nearly a constant,
which reads as flat rather than as periodic. The row profile is the right
signal for finding a repeat that spans the prop's width and the wrong one for
finding texture that repeats within it. Measuring it properly would mean
2-D autocorrelation on the band's pixels, which is a different tool; a
threshold on this one would license the marquee.
"""
import argparse
import json
import re
from pathlib import Path

from PIL import Image

# A prop is not periodic below this fraction of its height (that is texture)
# nor above it (that is the prop's own top-to-bottom composition).
LAG_LO, LAG_HI = 0.04, 0.45


def profile(path):
    """Row-mean luminance over the prop's pixels only, plus its extent.

    The renders are the prop on a flat grey field with a caption bar burned in
    at the top and a ruler at the bottom, so both have to go: they are the same
    in every image and would dominate any correlation.
    """
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    bg = px[4, H // 2]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 24

    rows, ys = [], []
    for y in range(30, H - 30):
        s = n = 0
        for x in range(0, W, 2):
            c = px[x, y]
            if is_bg(c):
                continue
            s += 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
            n += 1
        if n >= 8:                      # a scanline that actually crosses it
            rows.append(s / n)
            ys.append(y)
    return rows, (ys[0], ys[-1]) if ys else (0, 0)


def autocorr_peak(rows):
    """The strongest self-similarity in ANY window about three periods long.

    MEASURED OVER A WINDOW, NOT THE WHOLE PROP, and that is the difference
    between a measure that works and one that reads backwards. Correlating the
    entire profile mixes the region that repeats with the region that does not,
    and a prop has plenty of the second: the cabinet with five stacked ARCADE
    marquees scored 0.42 against 0.60 for its own drawn self, because four
    fifths of it is an ordinary cabinet and the stack was averaged away.

    A repeat is local. Sliding a window of about three periods and keeping the
    best score asks the question the fault actually poses -- "is anything,
    anywhere on this prop, laid down over and over" -- and on the same pair it
    gives 0.55 against 0.31.
    """
    n = len(rows)
    if n < 60:
        return 0.0, 0
    best, at = 0.0, 0
    for lag in range(max(4, int(LAG_LO * n)), max(5, int(LAG_HI * n))):
        w = min(n, lag * 3)
        if w <= lag + 4:
            continue
        for s in range(0, n - w + 1, max(1, w // 6)):
            seg = rows[s:s + w]
            m = sum(seg) / len(seg)
            a = [v - m for v in seg]
            denom = sum(v * v for v in a) or 1e-9
            # normalised by the OVERLAP, not by the window: without this a long
            # lag scores low simply for having fewer terms, and the measure
            # stops looking at exactly the spacings a stacked sign uses
            c = (sum(a[i] * a[i + lag] for i in range(len(a) - lag))
                 / (denom * (len(a) - lag) / len(a)))
            if c > best:
                best, at = c, lag
    return best, at


def flat_run(rows, tol=1.5):
    """The longest run of scanlines that barely change, as a fraction.

    A dead slab is not a repeat and reads just as broken. Measured on the same
    profile: consecutive rows whose luminance moves less than `tol` out of 255
    are carrying no detail at all.
    """
    n = len(rows)
    if n < 20:
        return 0.0
    run = best = 0
    for i in range(1, n):
        if abs(rows[i] - rows[i - 1]) <= tol:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best / n


SCALE = re.compile(r"-w-(\d+(?:-\d+)?)-h-(\d+(?:-\d+)?)-")


def scales(name):
    m = SCALE.search(name)
    return (tuple(float(g.replace("-", ".")) for g in m.groups())
            if m else None)


def shots(round_dir):
    """The as-drawn render and the two enlarged ones, told apart by value."""
    base = big = None
    out = []
    for p in sorted(round_dir.glob("*.png")):
        sc = scales(p.name)
        if sc is None:
            continue
        w, h = sc
        if w == 1 and h == 1:
            base = base or p
        else:
            out.append((f"{w:g}x wide" if w > 1 else f"{h:g}x tall", p))
    return base, out


def judge(round_dir, rise=0.22, flat_rise=0.14):
    base, bigs = shots(Path(round_dir))
    if not base or not bigs:
        return None
    b_rows, _ = profile(base)
    b_peak, _ = autocorr_peak(b_rows)
    b_flat = flat_run(b_rows)
    faults, rows = [], []
    for label, p in bigs:
        r, _ = profile(p)
        peak, lag = autocorr_peak(r)
        fl = flat_run(r)
        rows.append({"size": label, "peak": round(peak, 3), "lag": lag,
                     "flat": round(fl, 3)})
        # ONLY THE RISE OVER THE PROP'S OWN 1x RENDER. See the note at the top:
        # a shelved machine is periodic before anything is resized.
        if peak - b_peak >= rise:
            faults.append({
                "part": "background", "severity": "blocking",
                "fault": f"At {label} the prop has gained a repeat it did not "
                         f"have when drawn: its row profile self-correlates "
                         f"{peak:.2f} at a period of {lag} scanlines, against "
                         f"{b_peak:.2f} at the drawn size. Something is being "
                         f"laid down more than once."})
        if fl - b_flat >= flat_rise:
            faults.append({
                "part": "background", "severity": "blocking",
                "fault": f"At {label} the prop has gained a dead band: "
                         f"{100*fl:.0f}% of its height is scanlines that do "
                         f"not change, against {100*b_flat:.0f}% when drawn. "
                         f"The growth is filling with flat material."})
    return {"base": {"peak": round(b_peak, 3), "flat": round(b_flat, 3)},
            "sizes": rows, "faults": faults}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir")
    ap.add_argument("--round", default=None,
                    help="round folder name, default the newest with renders")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = Path(args.prop_dir)
    if args.round:
        rounds = [d / args.round]
    else:
        rounds = sorted([p for p in d.glob("r[0-9]*") if p.is_dir()],
                        key=lambda p: int(p.name[1:] or 0), reverse=True)
    for r in rounds:
        v = judge(r)
        if not v:
            continue
        if args.json:
            print(json.dumps(v, indent=1))
        else:
            print(f"{d.name} {r.name}: drawn peak {v['base']['peak']:.2f}, "
                  f"flat {100*v['base']['flat']:.0f}%")
            for s in v["sizes"]:
                print(f"   {s['size']:>10}  peak {s['peak']:.2f} "
                      f"(period {s['lag']})  flat {100*s['flat']:.0f}%")
            for f in v["faults"]:
                print(f"   BLOCKING: {f['fault']}")
        return
    print("no rendered round found")


if __name__ == "__main__":
    main()
