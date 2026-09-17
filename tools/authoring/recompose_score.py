#!/usr/bin/env python3
"""Does the decomposition put the reference back together? It does.

    python3 tools/authoring/recompose_score.py work/ps1
    python3 tools/authoring/recompose_score.py --sweep

Authoring tool. NOT a build, CI or runtime dependency. NOT a gate -- read the
last section before adding one.

WHY IT EXISTS. layer_build's docstring names one invariant and calls it the
test that matters: "lay the parts back on the background at their own
coordinates and you must get the reference image back. If that does not hold,
nothing at any other size will." It computes that number, prints it, saves
`_recomposed_<face>.png` beside the prop -- and nothing reads either. The tool's
own stated correctness property had been advisory since it was written, which is
mistake #1's shape exactly.

WHAT THE PRINTED NUMBER WAS ACTUALLY MEASURING. Two things, neither of them the
decomposition.

FIRST, THE SHEET. It sampled the whole bounding box, and a prop is not a
rectangle: the sheet shows through beside a jukebox's dome and between a
pinball's legs, the background layer fills its box to the corners, and the two
disagree everywhere outside the silhouette. That is compositing working.

    v49_pinball        25.80%  ->   0.89%   restricted to the silhouette
    v49_jukebox        12.66%  ->   2.58%
    v44_pinball        34.53%  ->   7.42%

SECOND, ITS OWN DILATION RING. What is left sits within a few pixels of a part
boundary, and it is put there on purpose: fill_from_panel dilates what counts as
covered by R = 2 so a fitting's outline does not survive in the background --
"the background kept a thin dark tracery of the door", in its own note. Those
pixels are meant to differ, and the part sits back on top of them at render
time. Excluding a four-pixel margin round every part box, and four pixels of the
silhouette's own outline, the residual is:

    89 of 90 props            0.00%
    v25_vending_machine       7.25%   (an outer frame line, and an old prop)

SO THE INVARIANT HOLDS, and that is the result. It is not a gate waiting for a
threshold; there is nothing to block on.

WHAT WAS BUILT AND REVERTED, because the numbers are worth keeping. A first
version attributed the residual per part and named any part whose own box
disagreed three times worse than its prop, which fired on 203 of 1700 parts.
Every one was an artefact: 180 of the 203 are under 1500 pixels, median 400 --
tiny decals whose masks have soft edges -- and parts are CUT FROM the reference
at their own boxes, so pasting them back is exact by construction. A per-part
residual can only measure a redraw or a mask edge, never a wrong box, and the
finding text it wrote ("its box or its mask is wrong") was wrong about the half
that matters.

SO THE USE OF THIS FILE IS AS A REGRESSION CHECK WITH A REAL ZERO. If a change
to segmentation, paint-out or compositing breaks the invariant, `--sweep` says
so against a baseline of 0.00% rather than against a number that was 26% when
everything was fine.
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Pixels within this many of a part's box are fill_from_panel's dilation ring,
# which is meant to differ and is covered by the part at render time.
PART_MARGIN = 4
# And this much of the silhouette's own outline is the prop's edge, where a
# one-pixel disagreement about where the object stops is not a decomposition
# fault. `silhouette` already erodes; this is its parameter.
EDGE = 4


def score(prop_dir, face="front"):
    """Residual where it can mean something, plus the two contaminated figures.

    Returns None when there is nothing to compare. All three numbers come back
    so the difference between them stays visible -- that difference is the
    finding this file exists to record.
    """
    import numpy as np
    from PIL import Image
    from identify_parts import object_crop
    from layer_build import silhouette

    d = Path(prop_dir)
    rec = d / f"_recomposed_{face}.png"
    if not rec.exists():
        return None
    try:
        ob = object_crop(d / f"{face}.png").convert("RGB")
        rc = Image.open(rec).convert("RGB")
        pj = json.loads((d / f"parts_{face}.json").read_text())
    except Exception:
        return None
    if rc.size != ob.size:
        return None
    W, H = ob.size
    a = np.asarray(ob).astype(int)
    b = np.asarray(rc).astype(int)
    # the same tolerance layer_build uses, so only the DOMAIN changes
    diff = np.abs(a - b).sum(axis=2) > 12

    def as_mask(sil):
        return np.array([[sil[x][y] for x in range(W)] for y in range(H)], bool)

    box = as_mask(silhouette(ob, erode=0))
    inner = as_mask(silhouette(ob, erode=EDGE))
    if int(box.sum()) < 100:
        return None
    cov = np.zeros((H, W), bool)
    for p in pj.get("parts", []):
        x0, y0, x1, y1 = p["px"]
        cov[max(0, y0 - PART_MARGIN):min(H, y1 + PART_MARGIN),
            max(0, x0 - PART_MARGIN):min(W, x1 + PART_MARGIN)] = True
    free = inner & ~cov
    n = int(free.sum())
    return {
        "whole_box": round(float(diff.mean()), 5),
        "silhouette": round(float((diff & box).sum() / box.sum()), 5),
        "free": round(float((diff & free).sum() / n), 5) if n >= 200 else None,
        "free_px": n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--face", default="front")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        work = Path(__file__).resolve().parents[1] / "img2threejs-work"
        rows = []
        for rec in sorted(work.glob(f"*/_recomposed_{args.face}.png")):
            s = score(rec.parent, args.face)
            if s and s["free"] is not None:
                rows.append((s["free"], s["silhouette"], s["whole_box"],
                             rec.parent.name))
        if not rows:
            print("no props with a recomposition on disk")
            return
        rows.sort(reverse=True)
        bad = [r for r in rows if r[0] > 0.002]
        print(f"{len(rows)} props")
        print(f"   clean (residual under 0.2% where it can mean anything): "
              f"{len(rows) - len(bad)}")
        print(f"   {'free':>7} {'silhouette':>11} {'whole box':>10}   prop")
        for fr, si, wb, name in rows[:10]:
            print(f"   {100*fr:6.2f}% {100*si:10.2f}% {100*wb:9.2f}%   {name}")
        print("\n   'free' excludes a 4px margin round every part box "
              "(fill_from_panel's\n   dilation ring, covered by the part at "
              "render time) and 4px of the\n   silhouette's own outline. "
              "'whole box' is what layer_build used to print.")
        return

    s = score(Path(args.prop_dir), args.face)
    if not s:
        print("nothing to compare: no recomposition on disk")
        return
    print(f"recomposition residual")
    print(f"   whole bounding box   {100*s['whole_box']:6.2f}%   "
          f"(mostly sheet outside the prop)")
    print(f"   inside the silhouette{100*s['silhouette']:6.2f}%   "
          f"(mostly the dilation ring)")
    if s["free"] is None:
        print(f"   away from every part -- too few pixels to say "
              f"({s['free_px']})")
    else:
        print(f"   away from every part {100*s['free']:6.2f}%   "
              f"over {s['free_px']} px  <- the one that means something")


if __name__ == "__main__":
    main()
