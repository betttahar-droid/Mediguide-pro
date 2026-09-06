#!/usr/bin/env python3
"""Drive a part list toward the reference with a measured error signal.

    python3 tools/authoring/refine_parts.py "arcade cabinet" \
        --reference tools/img2threejs-work/arcade_v2 --rounds 8

Authoring tool. NOT a build, CI or runtime dependency.

WHY. The critique loop asked a vision model "what is wrong with this?" and got
prose. Prose cannot say whether a change HELPED, so the loop had no gradient
and stopped after two rounds by fiat.

project_score.py supplies the gradient: it projects the part list onto the
front plane and scores it against the measured reference, per region, in grid
coordinates. That turns feedback from

    "the marquee looks a bit small"

into

    region x 7..33 z 84..91 wants #57a3b5, you put #1e191a on 14% of it

which names the box to move and the colour to give it. Each round feeds the
worst regions back, keeps the best-scoring list seen so far, and stops when
the score stops improving.

The scorer never renders, so a round costs one model call and about a second,
and the loop can afford to be long.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, _openrouter_key, AUTHOR_MODEL  # noqa: E402
from author_prop import GRID_RULES, validate  # noqa: E402
from reference_regions import regions, depth_profile  # noqa: E402
from project_score import score, cell_report  # noqa: E402


def build_prompt(asset, grid, rects, prof, pal, previous=None, misses=None, s=None):
    head = f"""Build a 3D part list for a low-poly "{asset}" on a {grid[0]} x {grid[1]} x {grid[2]}
voxel grid, matching a measured reference elevation as closely as possible.

FRONT RECTANGLES, measured from the reference. x and z are VOXEL INDICES on
this grid already -- use them directly, do not rescale. z is up from the floor.
{json.dumps(rects, indent=1)}

DEPTH PROFILE from the side, floor first; y is a fraction of depth, y=0 front.
{json.dumps(prof, indent=1)}

PALETTE. Use ONLY these hex values:
{json.dumps(pal, indent=1)}"""

    if previous is None:
        return head + f"""

Every front rectangle must become at least one box with those exact x and z
extents and that colour. Choose y from the depth profile: surface detail is
shallow and starts at y=0, the body is deep. Add a back panel and a top cap.

{GRID_RULES}

Reply with JSON only: {{"grid": [W,D,H], "boxes": [{{"name","min","max","hex"}}]}}"""

    return head + f"""

YOUR PREVIOUS PART LIST:
{json.dumps(previous, indent=1)}

It was projected onto the front plane and compared with the reference.
Overall match {100*s['overall']:.1f}%; silhouette {100*s['iou']:.1f}%;
colour agreement inside the overlap {100*s['agree']:.1f}%.

THESE CELLS ARE WRONG. The front plane is tiled and each row is one tile in
VOXEL coordinates: what the reference mostly is there, what your list actually
put there, and how much of the tile already agrees. "empty" means nothing is
drawn there -- if the reference wants a colour and you are empty, a box is
MISSING; if you have a colour and the reference is empty, a box is TOO BIG.
Fix each by moving, resizing, recolouring or adding a box.
{json.dumps(misses, indent=1)}

Anything not listed already scores well -- do not disturb it. Keep the same
part names where a part survives.

{GRID_RULES}

Reply with JSON only: {{"grid": [W,D,H], "boxes": [{{"name","min","max","hex"}}]}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--grid", default="40,46,96")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--worst", type=int, default=18, help="cells fed back per round")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    grid = [int(v) for v in args.grid.split(",")]
    W, D, H = grid
    rd = Path(args.reference)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    key = _openrouter_key()

    rects, _, _ = regions(rd / "front.png")
    rects = [r for r in rects if r["fill"] >= 0.80]
    pal = sorted({r["colour"] for r in rects})
    prof = depth_profile(rd / "side.png")
    # hand over VOXEL extents, so the model has no arithmetic to get wrong
    vrects = [{"colour": r["colour"],
               "x": [int(r["x"][0] * W), max(int(r["x"][0] * W) + 1, int(r["x"][1] * W))],
               "z": [int(r["z"][0] * H), max(int(r["z"][0] * H) + 1, int(r["z"][1] * H))],
               "area": r["area"]} for r in rects]
    print(f"reference: {len(vrects)} rectangles, {len(pal)} colours, grid {grid}")

    best = (-1, None)
    previous, misses, s = None, None, None
    for rnd in range(args.rounds):
        prompt = build_prompt(args.asset, grid, vrects, prof, pal, previous, misses, s)
        try:
            spec = as_json(glm([{"role": "user", "content": prompt}], AUTHOR_MODEL,
                               key, max_tokens=30000))
        except SystemExit as e:
            print(f"round {rnd}: model failed -- {str(e)[:120]}")
            continue
        spec.setdefault("grid", grid)
        good, bad = validate(spec)
        if not good:
            print(f"round {rnd}: nothing valid ({len(bad)} rejected)")
            continue
        p = out / f"parts_r{rnd}.json"
        p.write_text(json.dumps({"grid": spec["grid"], "boxes": good}, indent=1))
        s = score(p, rd / "front.png")
        rows = cell_report(s)
        mark = ""
        if s["overall"] > best[0]:
            best = (s["overall"], p)
            mark = "  <-- best"
        print(f"round {rnd}: {len(good):3} parts ({len(bad)} rejected)   "
              f"match {100*s['overall']:6.2f}%   silhouette {100*s['iou']:5.1f}%   "
              f"colour {100*s['agree']:5.1f}%{mark}")
        for r in rows[:4]:
            print(f"           {100*r['score']:5.1f}% want {r['want']} got {r['got']} "
                  f"x{r['x'][0]}..{r['x'][1]} z{r['z'][0]}..{r['z'][1]} ({r['px']}px)")
        misses = [{"x": r["x"], "z": r["z"], "reference_is": str(r["want"]),
                   "you_put": str(r["got"]), "agree": round(r["score"], 2)}
                  for r in rows[:args.worst] if r["score"] < 0.95]
        previous = [{k: b[k] for k in ("name", "min", "max")} | {"hex": b["colour"]}
                    for b in good]
        if not misses:
            print("  nothing left below 95% -- stopping")
            break

    print(f"\nBEST {100*best[0]:.2f}%  ->  {best[1]}")


if __name__ == "__main__":
    main()
