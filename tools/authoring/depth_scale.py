#!/usr/bin/env python3
"""How far a part really stands off the body, measured against the side view.

    python3 tools/authoring/depth_scale.py --props 12
    python3 tools/authoring/depth_scale.py --props 12 --scales 0.2,0.4,0.6,1.0

Authoring tool. NOT a build, CI or runtime dependency. Needs the dev server up.

WHY. `geometry_audit` renders the model from three axes and scores each outline
against its elevation, and the front is excellent -- median IoU 0.985 across 98
props, nothing below 0.93. The SIDE is not: median 0.966, nineteen props below
0.95, the worst at 0.76. That is the axis the reference cannot show directly,
so it is the axis where an error can hide.

WHICH HALF IS WRONG IS MEASURABLE, and it is not the half I expected. Rendering
the body with no parts on it at all (`?only=` pointed at a name that does not
exist) and scoring the same silhouette:

    prop                   side, with parts    side, body alone
    v8_arcade_cabinet             0.898              0.993
    v51_pinball                   0.851              0.973
    v44_pinball                   0.883              0.969
    v48_arcade_cabinet            0.916              0.992
    v52_jukebox                   0.932              0.996

Nine of twelve improve by 0.06 to 0.12 with the parts taken off. The LOFT IS
RIGHT -- it is traced from the side elevation and it matches it almost exactly.
What is wrong is how far the parts stand proud of it: a `deep` part stands
0.055 of the prop's height off the face, which on a cabinet 0.45 deep is an
extra 12% of depth that the side drawing does not show.

SO THE STAND-OFF IS FITTED RATHER THAN CHOSEN. `?pd=` scales every depth class
at once; this sweeps it and reports the side and top IoU at each value. The
right scale is the one that maximises the outline agreement, which is the
objective itself and not a proxy for it.

AND THE PROXY HERE IS A TRAP, WHICH IS WHY IOU IS SCORED AND NOT PROPORTIONS.
`geometry_audit` also reports an aspect ratio, and driving THAT to 1.0 by
scaling the body's depth converges beautifully -- side 1.144 -> 1.022 -> 1.002
on v8_arcade_cabinet -- while the outline IoU it is supposed to serve gets
steadily WORSE, 0.898 -> 0.886 -> 0.881. A prop can have exactly the right
proportions and the wrong shape. CLAUDE.md's rule, met head on: the measure
that improves while the thing gets worse is a measure, not the goal.

AND THE SWEEP ITSELF IS THE SAME TRAP, WHICH IS WHY `pd` IS NOT DRIVEN TO 0.
Re-swept over the eight worst and the eight best props after the loft, the
footprint and the bezel were fixed, summing front+side+top:

    pd      worst 8    best 8
    0.00     2.9096     2.9832
    0.50     2.8965     2.9804
    1.00     2.8825     2.9773
    1.50     2.8691     2.9735

Monotone decreasing in `pd` for BOTH groups -- and the earlier sweep, where
the good props preferred some relief, no longer holds. It is tempting to read
that as "the stand-off is simply wrong" and set it to zero. It is not, and the
reason is geometric rather than empirical:

    A SIDE ELEVATION TRACES THE FRONTMOST POINT AT EACH HEIGHT.

So the body's front wall ALREADY CONTAINS the deck, the bezel and the coin
door -- they were in the drawing the loft was traced from. A part standing
proud of that wall is not adding depth the drawing omitted; it is counting the
same depth twice, and the outline objective is right to dock it. The objective
is therefore blind in exactly one direction: it can see the double-count and
it cannot see the flattening, because a prop whose every button is a sticker
scores perfectly from all three axes. `A BUTTON IS A CAP, NOT A TILE` in
`parts_view/index.html` is the constraint the arithmetic cannot supply, and
this monotone slope is what it looks like from the arithmetic's side.

What follows is NOT "pd=0". It is that a part's stand-off should be measured
against what the elevation already accounts for, per part, rather than scaled
globally -- which is `part_bulge.py`, and which finds the handful of parts that
genuinely protrude past their own body (legs, arch columns, a control deck)
instead of docking every cap on every prop.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
import geometry_audit as ga                                  # noqa: E402

WORK = ROOT / "tools" / "img2threejs-work"


def score(d, extra="", out=None):
    """(side, top, front) outline IoU for one prop at one setting."""
    out = out or (d / "_depth")
    qs = [f"dir=/{d.relative_to(ROOT)}&audit=1&{q}{extra}"
          for q, _ in ga.VIEWS.values()]
    shots = ga.shoot(out, qs)
    fl = ga.flips(d)
    got = {}
    for (name, (q, elev)), qq in zip(ga.VIEWS.items(), qs):
        f, src = shots.get(qq), d / f"{elev}.png"
        if f and src.exists():
            got[name] = ga.compare(f, src, flip_x=fl[name][0],
                                   flip_y=fl[name][1])[0]
    return got


def worst_props(n):
    """The props whose side or top outline agrees least, from the last audit."""
    rows = []
    for f in sorted(WORK.glob("*/geometry_audit.json")):
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        v = [j[k]["iou"] for k in ("side", "top") if k in j]
        if v:
            rows.append((min(v), f.parent))
    rows.sort()
    return [d for _, d in rows[:n]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--props", type=int, default=12)
    ap.add_argument("--scales", default="0,0.25,0.5,0.75,1.0")
    ap.add_argument("--only", default=None, help="one prop directory")
    args = ap.parse_args()

    props = ([Path(args.only).resolve()] if args.only
             else worst_props(args.props))
    scales = [float(s) for s in args.scales.split(",") if s.strip()]
    print(f"{len(props)} prop(s) x {len(scales)} scale(s)\n")
    print("  " + "prop".ljust(24)
          + "".join(f"pd={s:<5g}".rjust(14) for s in scales))
    tot = {s: [] for s in scales}
    for d in props:
        cells = []
        for s in scales:
            g = score(d, f"&pd={s:g}")
            side, top = g.get("side"), g.get("top")
            if side is not None:
                tot[s].append((side, top or 0.0))
            cells.append(f"{side or 0:.3f}/{top or 0:.3f}".rjust(14))
        print("  " + d.name.ljust(24) + "".join(cells))

    print("\n  mean over the props above:")
    for s in scales:
        v = tot[s]
        if not v:
            continue
        ms = sum(a for a, _ in v) / len(v)
        mt = sum(b for _, b in v) / len(v)
        print(f"    pd={s:<5g}  side {ms:.4f}   top {mt:.4f}   "
              f"sum {ms + mt:.4f}")


if __name__ == "__main__":
    main()
