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
from side_profile import simplify  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--tol", type=float, default=0.006)
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

    # the two edges are different curves -- a cabinet can be square one side
    # and stepped the other -- so they are simplified independently
    left = simplify([(a, b) for a, b, _ in rows], args.tol)
    right = simplify([(a, c) for a, _, c in rows], args.tol)

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
    print(f"front profile: {len(left)} + {len(right)} points, "
          f"widest {span:.3f}" + (f", narrowest {waist:.3f}" if waist else ""))
    print(f"wrote {d / f'front_profile_{args.face}.json'}")


if __name__ == "__main__":
    main()
