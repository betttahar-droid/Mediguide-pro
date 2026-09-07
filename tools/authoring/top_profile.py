#!/usr/bin/env python3
"""Trace the prop's PLAN from the top elevation: its shape seen from above.

    python3 tools/authoring/top_profile.py work/ps1 --asset "arcade cabinet"

Authoring tool. NOT a build, CI or runtime dependency.

WHY. The body is now the intersection of the front and side silhouettes, which
fixed the width at every height -- front outline agreement went from 96% to
99.6%. But a two-view hull can only ever produce a RECTANGULAR cross-section,
because a rectangle is what one width crossed with one depth is. The audit says
so plainly: the plan still disagrees by about ten percent, and it is the same
ten percent on every prop.

The sheet has a third drawing and it is the one nobody was reading. The top
elevation IS the cross-section: it says the prop is rounded at the back, or
chamfered at its front corners, or waisted in the middle. Scaling that outline
into the rectangle that the other two views define gives a body that satisfies
all three at once, which is the whole of what "accurate from every angle" can
mean from three drawings.

The plan is stored the same way the side profile is -- two walls as functions
of position across the width -- because a plan is a silhouette like any other,
and the renderer already knows how to loft between two walls.

WHICH EDGE IS THE FRONT is asked, not assumed, for the same reason it is asked
of the side elevation: get it backwards and the prop's nose becomes its tail.
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


def relief(rows, W):
    """How much each boundary wanders: the busier one is the front."""
    if len(rows) < 8:
        return 0.0

    def smooth(a, k=3):
        return [sum(a[max(0, i - k):i + k + 1]) / len(a[max(0, i - k):i + k + 1])
                for i in range(len(a))]

    def tv(a):
        a = smooth(a)
        return sum(abs(a[i + 1] - a[i]) for i in range(len(a) - 1)) / max(1, W)

    lo = tv([r[1] for r in rows])
    hi = tv([r[2] for r in rows])
    if lo + hi < 0.05:
        return 0.0
    return (lo - hi) / (lo + hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--tol", type=float, default=0.008)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    src = d / "top.png"
    if not src.exists():
        raise SystemExit("no top.png -- nothing to trace")
    ob = object_crop(src)
    W, H = ob.size
    inside = silhouette(ob, erode=0)

    # for every column across the width, where the plan starts and ends
    cols = []
    for x in range(W):
        run = [y for y in range(H) if inside[x][y]]
        if run:
            cols.append((x / W, run[0] / H, (run[-1] + 1) / H))
    if len(cols) < 4:
        raise SystemExit("top elevation has no silhouette")

    # WHICH IMAGE EDGE IS THE PROP'S FRONT. The boundary that wanders is the
    # front, exactly as on the side elevation -- a control deck juts, a back
    # panel does not -- and the vision model settles a plan that is a plain
    # rectangle, where the answer does not matter but must still be made.
    r = relief(cols, W)
    said = None
    try:
        from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL
        tmp = d / "_top_obj.png"
        ob.save(tmp)
        ask = (f"This is a {args.asset} seen from directly ABOVE, in plan.\n\n"
               "Which edge of this image is the prop's FRONT -- the side a "
               "person stands at? The opposite edge is its back.\n\n"
               'JSON only: {"front": "top"} or {"front": "bottom"}')
        got = as_json(glm([{"role": "user", "content": [
            {"type": "text", "text": ask},
            {"type": "image_url", "image_url": {"url": data_uri(tmp)}}]}],
            CRITIC_MODEL, _openrouter_key(), max_tokens=4000, temperature=0.0))
        v = str(got.get("front", "")).strip().lower()
        if v in ("top", "bottom"):
            said = v
    except Exception as e:
        print(f"  front-edge call failed ({type(e).__name__}), using the relief")
    by_relief = "top" if r > 0 else "bottom" if r < 0 else None
    front_top = ((by_relief or said or "bottom") == "top" if abs(r) >= 0.15
                 else (said or by_relief or "bottom") == "top")

    # depth fraction: 1 at the prop's nose, 0 at its tail
    def frac(v):
        return 1 - v if front_top else v

    near = simplify([(u, frac(a)) for u, a, _ in cols], args.tol)
    far = simplify([(u, frac(b)) for u, _, b in cols], args.tol)
    front_wall = near if front_top else far
    back_wall = far if front_top else near

    out = {
        "front_edge": "top" if front_top else "bottom",
        "front_edge_said": said, "relief": round(r, 4),
        # u runs across the prop's width, 0 at its left; the value is how far
        # forward that wall is, 0 at the very back and 1 at the very front
        "front_wall": [[round(u, 5), round(max(0.0, min(1.0, f)), 5)]
                       for u, f in sorted(front_wall)],
        "back_wall": [[round(u, 5), round(max(0.0, min(1.0, f)), 5)]
                      for u, f in sorted(back_wall)],
    }
    (d / "top_profile.json").write_text(json.dumps(out, indent=1))
    depth_var = max(f for _, f in out["front_wall"]) - min(f for _, f in out["front_wall"])
    print(f"plan: front edge = {out['front_edge']}  "
          f"[model {said or '-'}, relief {r:+.3f}]")
    print(f"  {len(out['front_wall'])} + {len(out['back_wall'])} points, "
          f"front wall varies by {depth_var:.3f} "
          f"({'shaped' if depth_var > 0.06 else 'essentially straight'})")


if __name__ == "__main__":
    main()
