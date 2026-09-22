#!/usr/bin/env python3
"""Trace how WIDE the prop is at every height, from the front elevation.

    python3 tools/authoring/front_profile.py work/ps1

Authoring tool. NOT a build, CI or runtime dependency.

WHY. The body is extruded from the SIDE profile, so its width is the same at
every height -- and the geometry audit put a number on what that costs. Seen
from above, the cabinet's plan came back a plain rectangle while the top
elevation's plan tapers: 89.9% outline agreement, with the model too wide down
both sides and too deep across the bottom. Nothing in the textured render says
so, which is exactly why it needed measuring.

A prop that domes, tapers, steps in at a plinth or flares at a hood is the wrong
width somewhere, always. The front elevation says what the width is at each
height, the side elevation says what the depth is, and the honest body is the
INTERSECTION of the two -- a stack of rectangles rather than one extrusion. That
is the visual hull from two views, built as clean low-poly rather than voxels,
and it makes the front, side and plan all correct together instead of trading
one against another.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from identify_parts import object_crop  # noqa: E402
from layer_build import silhouette  # noqa: E402
from side_profile import fit, pull_inside  # noqa: E402


# A FOURFOLD COLLAPSE IN ONE ROW IS NOT THE PROP.
#
# The trace took every row with any silhouette pixel in it, and the top and
# bottom rows of a crop are antialiasing, a drop shadow, or the single pixel at
# the apex of a dome. So the polyline's terminal point was a SLIVER, and the
# loft pinched to it: v49_arcade_cabinet's wall at the second-to-last row read
# +0.189..+0.192 where its silhouette is -0.206..+0.208, a gap of 95% of the
# prop's width. Five props had an end pinched that way, and it is visible in a
# three-quarter render as parts hanging in the air off a body that has tapered
# out from under them -- a jukebox's arch glass and base trim both at x=-0.246
# with no body there at all.
#
# NARROWNESS IS NOT THE TEST, and that is the whole difficulty: a domed jukebox
# really is one pixel wide at its apex, and v45_arcade_cabinet really is 20 px
# wide across its whole marquee top. What separates them is CONTINUITY. A real
# taper grows a couple of pixels a row -- prop_jukebox's crown runs 1, 14, 30,
# 44 -- while antialiasing gives one row against a full-width neighbour: 2 then
# 298, 5 then 326, 1 then 23.
#
# So: drop a terminal row only while the row just inside it is more than FOURFOLD
# wider. Swept over 100 props that trims nothing on 62, one row on 37 and two
# rows on one. At 3 it starts taking two rows off three props; at 6 it misses
# v5_vending_machine's drop shadow (299 against 65, a factor of 4.6).
# AND THE SAME RULE CATCHES A SPIKE IN THE MIDDLE, which is the same fault with
# a neighbour on both sides. v14_vending_machine has one row three pixels wide
# between two rows of 297 and 302 -- a band the silhouette lost, not a waist --
# and the polyline drawn through it sent the LEFT wall to +0.253, which is over
# on the RIGHT-hand side of the prop. The body got a one-row spike across its
# whole width. Swept over 100 props that rule fires on exactly one, twice.
JUMP = 4.0


def _smooth(rows, k=3, what="front"):
    """Median-filter each bracketing edge down the rows.

    A silhouette traced off PAINTED artwork is jagged wherever the prop's own
    edge is dark: on v11_vending_machine's right wall the trace runs 277, 256,
    276 on three consecutive rows, and does it ten times down the machine. That
    is the segmentation losing a column of dark trim, not a feature -- and no
    polyline can follow it, so `fit` spends its whole point budget failing to
    and settles twelve pixels away from a trace whose real shape is a straight
    line. The body then bulges past its own artwork and the renderer cuts the
    bulge away: 1.04% of that prop is see-through, the worst left in the corpus.

    `_trim_ends` below is the same idea for one spike, and it cannot see this
    one, because its test is on the prop's WIDTH and here only one edge moves --
    277 to 256 and back takes 21 pixels off the right and puts none on the left,
    so the width barely changes.

    TRIED, MEASURED THREE WAYS, AND NOT CALLED. Every version fixes the prop it
    was written for -- v11_vending_machine's front goes 0.957 to 0.971, its fit
    error 12.5px to 3.3px and its front holes close -- and none of them survives
    the corpus:

        window   all three >= 0.95   >= 0.97   better / worse
        none            97              77          --
        5 rows, front and side
                        95              74        21 / 22
        5 rows, front only
                        95              77        12 / 11
        3 rows, front only
                        96              77         8 /  8

    On the SIDE elevation it is worse than useless: `relief` decides which edge
    is the prop's FRONT off the same trace, and a median filter flips its sign
    on a prop whose two walls are nearly equally busy -- v11_vending_machine
    went from agreeing with the vision model to disagreeing with it.

    On the front it is a straight trade, one prop for another, which CLAUDE.md
    names as the signature of a fix that is not structural. The jagged trace is
    real and this is the wrong place to answer it: what makes v11's right wall
    jump 277, 256, 277 is the SEGMENTATION losing a column of dark trim, and it
    should be fixed where the silhouette is decided, not smoothed over here.

    Kept, with its numbers, so the next person does not re-derive it.
    """
    if len(rows) < k:
        return rows
    h = k // 2
    out, moved = [], 0
    for i, r in enumerate(rows):
        lo, hi = max(0, i - h), min(len(rows), i + h + 1)
        a = sorted(x[1] for x in rows[lo:hi])
        b = sorted(x[2] for x in rows[lo:hi])
        m = (r[0], a[len(a) // 2], b[len(b) // 2])
        if abs(m[1] - r[1]) > 1e-9 or abs(m[2] - r[2]) > 1e-9:
            moved += 1
        out.append(m)
    if moved:
        print(f"  {what} trace: {moved} of {len(rows)} rows had an edge that "
              f"disagreed with its neighbours and was taken from them instead")
    return out


def _trim_ends(rows, what="front"):
    """rows is [(height, left, right)] top-first, or any triple whose last two
    entries bracket the prop. Drop degenerate ends and interior spikes."""
    def width(r):
        return max(1e-6, abs(r[2] - r[1]))

    a, b = 0, len(rows)
    while b - a > 4 and width(rows[a + 1]) > JUMP * width(rows[a]):
        a += 1
    while b - a > 4 and width(rows[b - 2]) > JUMP * width(rows[b - 1]):
        b -= 1
    kept = rows[a:b]
    spikes = [i for i in range(1, len(kept) - 1)
              if width(kept[i]) * JUMP < min(width(kept[i - 1]),
                                             width(kept[i + 1]))]
    if spikes:
        kept = [r for i, r in enumerate(kept) if i not in set(spikes)]
    if a or b < len(rows) or spikes:
        print(f"  {what} trace: dropped {a} row(s) off the top, "
              f"{len(rows) - b} off the bottom and {len(spikes)} spike(s) -- "
              f"the width changes more than {JUMP:g}x in a single row there, "
              f"which is antialiasing, a shadow or a lost band, not the prop")
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--want", type=float, default=2.0,
                    help="how close the polyline must sit to the traced edge, "
                         "in pixels of the elevation")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    ob = object_crop(d / f"{args.face}.png")
    W, H = ob.size
    inside = silhouette(ob, erode=0)

    rows = []
    for y in range(H):
        run = [x for x in range(W) if inside[x][y]]
        if run:
            rows.append((1 - y / H, run[0] / W, (run[-1] + 1) / W))
    if not rows:
        raise SystemExit("front elevation has no silhouette")
    rows = _trim_ends(rows)

    # the two edges are different curves -- a cabinet can be square one side
    # and stepped the other -- so they are simplified independently
    # only as far as the shape survives: a fixed tolerance eats whatever is
    # SHORT, and what is short on a cabinet is its plinth step and its hood
    left, ltol, lerr = fit([(a, b) for a, b, _ in rows], args.want, H)
    right, rtol, rerr = fit([(a, c) for a, _, c in rows], args.want, H)
    # AND NEVER OUTSIDE THE ART -- see pull_inside(). Half of a symmetric
    # tolerance is body with no texture on it, and the renderer cuts that away.
    left, lp = pull_inside(left, [(a, b) for a, b, _ in rows], +1,
                            max(args.want, lerr) / H)
    right, rp = pull_inside(right, [(a, c) for a, _, c in rows], -1,
                             max(args.want, rerr) / H)
    if max(lp, rp) * W > 0.5:
        print(f"  front trace: pulled the walls in by up to "
              f"{max(lp, rp) * W:.1f}px so the body is nowhere wider than the "
              f"artwork that covers it")

    aspect = W / H
    out = {
        "aspect": round(aspect, 5),
        # x measured from the centre, in the renderer's units where the face is
        # `aspect` wide and exactly 1 tall
        "left_wall": [[round(y, 5), round((f - 0.5) * aspect, 5)] for y, f in left],
        "right_wall": [[round(y, 5), round((f - 0.5) * aspect, 5)] for y, f in right],
    }
    (d / f"front_profile_{args.face}.json").write_text(json.dumps(out, indent=1))
    span = max(f for _, f in right) - min(f for _, f in left)
    waist = min(r - l for (_, l), (_, r) in zip(left, right)) if len(left) == len(right) else None
    print(f"front profile: {len(left)} + {len(right)} points, within "
          f"{max(lerr, rerr):.1f}px of the drawing, "
          f"widest {span:.3f}" + (f", narrowest {waist:.3f}" if waist else ""))
    print(f"wrote {d / f'front_profile_{args.face}.json'}")


if __name__ == "__main__":
    main()
