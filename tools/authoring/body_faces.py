#!/usr/bin/env python3
"""Turn the sheet's other elevations into the body's other faces.

    python3 tools/authoring/body_faces.py work/ps1

Authoring tool. NOT a build, CI or runtime dependency.

WHY. ps1_sheet.py already gets four true elevations out of Nano Banana in one
pass, and until now three of them were thrown away: the renderer textured the
front and painted the sides, back and top a flat brown. On a straight-on shot
nobody notices; the moment the prop is turned to show that its parts are
separate objects, two thirds of what you can see is a solid colour. The sheet
paid for those views, so use them.

It also settles the DEPTH, which was a guess. The side elevation is the same
prop at the same height, so its width IS the prop's depth in the same units --
no model has to estimate it and S14.0 is not troubled, because this is
measurement rather than reading proportions off a picture.

The far side is the near side mirrored. That is not a shortcut for its own
sake: a game prop's two sides are the same art, and mirroring is what an
artist would do too.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from identify_parts import object_crop  # noqa: E402
from layer_build import silhouette  # noqa: E402


def clamp_to_silhouette(im):
    """Push the prop's own colour out into the sheet showing past its outline.

    A prop is not a rectangle and an elevation crop is, so an arcade cabinet's
    side view arrives with pale sheet in the corner above its sloped back. Laid
    on a box face that read as two grey slabs bolted to the cabinet -- which is
    the first thing you see once the prop is turned.

    The body is a box, so the honest thing for a face to show past the profile
    is more of the same panel: extend the nearest real pixel outwards, which
    carries the panel's own shading with it rather than inventing a flat fill.
    Making the face TRANSPARENT there instead would be wrong -- you would see
    straight through the cabinet -- and reshaping the box to the profile is a
    different job from texturing it.
    """
    W, H = im.size
    inside = silhouette(im, erode=1)
    px = im.load()
    out = im.copy()
    op = out.load()
    for y in range(H):
        run = [x for x in range(W) if inside[x][y]]
        if not run:
            continue
        lo, hi = run[0], run[-1]
        for x in range(W):
            if inside[x][y]:
                continue
            op[x, y] = px[min(max(x, lo), hi), y]
    # a row entirely outside the prop (above a dome, below a plinth) has no
    # neighbour to borrow from, so take the nearest row that did have one
    rows = [y for y in range(H) if any(inside[x][y] for x in range(W))]
    if rows:
        for y in range(H):
            if y in (rows[0], rows[-1]) or (rows[0] <= y <= rows[-1]
                                            and any(inside[x][y] for x in range(W))):
                continue
            src_y = min(rows, key=lambda r: abs(r - y))
            for x in range(W):
                op[x, y] = op[x, src_y]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    args = ap.parse_args()
    d = Path(args.sheet_dir)

    front = object_crop(d / "front.png")
    FW, FH = front.size
    out = {"front_size": [FW, FH], "aspect": round(FW / FH, 5)}

    for face in ("side", "back", "top"):
        src = d / f"{face}.png"
        if not src.exists():
            print(f"  no {face}.png -- skipping")
            continue
        im = clamp_to_silhouette(object_crop(src))
        # THE VIEWS MUST AGREE ON HEIGHT, OR THE DEPTH IS A LIE. side and back
        # are elevations of the same prop, so resampling them to the front's
        # height costs nothing and makes the box's faces line up exactly.
        if face in ("side", "back"):
            w = max(1, round(im.width * FH / im.height))
            im = im.resize((w, FH))
        else:                       # the top is seen from above: its width is
            out["top_ratio"] = im.height / im.width   # depth / width, measured
            im = im.resize((FW, im.height))   # the front's, its height the depth
        im.save(d / f"body_{face}.png")
        out[face] = {"image": f"body_{face}.png", "size": list(im.size)}
        print(f"  {face}: {im.size[0]}x{im.size[1]}")

    # depth in the renderer's units, where the front face is `aspect` wide and
    # exactly 1 tall. Prefer the side elevation; the top view is the check.
    depth = None
    if "side" in out:
        depth = out["side"]["size"][0] / FH
    if "top_ratio" in out:
        # the top view's height IS the depth, in units of its width, and its
        # width is the prop's width -- which is FW/FH once the front is 1 tall
        by_top = out.pop("top_ratio") * (FW / FH)
        out["depth_from_top"] = round(by_top, 4)
        if depth is None:
            depth = by_top
        elif abs(by_top - depth) / max(depth, 1e-6) > 0.35:
            print(f"  ! side says depth {depth:.3f}, top says {by_top:.3f}"
                  f" -- trusting the side elevation")
    out["depth"] = round(depth if depth else 0.34, 4)
    (d / "body.json").write_text(json.dumps(out, indent=1))
    print(f"depth {out['depth']} (front {FW}x{FH}) -> {d / 'body.json'}")


if __name__ == "__main__":
    main()
