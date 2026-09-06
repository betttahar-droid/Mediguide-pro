#!/usr/bin/env python3
"""Split an elevation into a background layer and part layers.

    python3 tools/authoring/layer_build.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY. extract_fittings.py produced a 52x267 sliver of panel and tiled it
everywhere, which is why every judge described the lower cabinet as "blank
flat brown" -- one small patch repeated cannot carry a painted panel's
variation. And its parts were full-width strips, so reassembling them at a new
size mapped the coin door onto the control deck.

This keeps the whole elevation instead:

  BACKGROUND  the elevation with every part REMOVED and the hole filled from
              the nearest clean panel above or below it. Full size, so it
              nine-slices with all its grime and streaking intact rather than
              tiling one swatch.
  PARTS       cut at their measured boxes, each carrying its anchor and its
              resize rule.

The test that matters is that this is LOSSLESS at the original size: lay the
parts back on the background at their own coordinates and you must get the
reference image back. If that does not hold, nothing at any other size will.
"""
import argparse
import json
from pathlib import Path

from PIL import Image

from identify_parts import object_crop


def fill_from_panel(ob, boxes):
    """Paint out the parts using panel taken from directly above or below.

    A cabinet panel is vertically streaked -- wear runs down it -- so a column
    of panel is the honest thing to continue a column of hole with. For each
    hole row, copy the nearest row at the same x that no part covers.
    """
    W, H = ob.size
    out = ob.copy()
    px = out.load()
    src = ob.load()
    covered = [[False] * H for _ in range(W)]
    for (x0, y0, x1, y1) in boxes:
        for x in range(max(0, x0), min(W, x1)):
            for y in range(max(0, y0), min(H, y1)):
                covered[x][y] = True
    # SOURCE ROWS MUST BE PANEL, NOT MERELY UNCOVERED. Between two parts sits
    # dark trim, and it is uncovered -- so filling from "the nearest row no
    # part occupies" packed the holes with black. At scale 1 the parts sat on
    # top and hid it; the moment the background stretched, those fills came
    # out as black rectangles across the cabinet. Only rows that actually look
    # like the panel may be copied from.
    from collections import Counter as _C
    tally = _C()
    for x in range(0, W, 2):
        for y in range(0, H, 2):
            if not covered[x][y]:
                tally[src[x, y]] += 1
    base = tally.most_common(1)[0][0] if tally else (128, 128, 128)
    tol = 110

    def is_panel(c):
        return sum(abs(a - b) for a, b in zip(c, base)) < tol

    for x in range(W):
        clean = [y for y in range(H) if not covered[x][y] and is_panel(src[x, y])]
        if not clean:                      # this column is all trim or all part
            clean = [y for y in range(H) if not covered[x][y]]
        if not clean:
            continue
        for y in range(H):
            # ONLY the holes. Also repainting trim that no part covers scrubbed
            # detail the decomposition is supposed to keep, and recomposition
            # went from 0.00% to 7.04% different. Fill what the parts took out,
            # and take the fill from panel.
            if covered[x][y]:
                near = min(clean, key=lambda c: abs(c - y))
                px[x, y] = src[x, near]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    man = json.loads((d / f"parts_{args.face}.json").read_text())
    ob = object_crop(d / f"{args.face}.png")
    W, H = ob.size
    assert [W, H] == man["size"], f"size drift {W}x{H} vs {man['size']}"

    boxes = [p["px"] for p in man["parts"]]
    bg = fill_from_panel(ob, boxes)
    bg.save(d / f"bg_{args.face}.png")

    kit = d / "parts"
    kit.mkdir(exist_ok=True)
    out = []
    for p in man["parts"]:
        x0, y0, x1, y1 = p["px"]
        crop = ob.crop((x0, y0, x1, y1))
        crop.save(kit / f"{p['name']}.png")
        out.append({
            "name": p["name"], "image": f"parts/{p['name']}.png",
            "resize": p["resize"], "anchor": p["anchor"],
            # fractions of the ORIGINAL face; the renderer turns these into
            # world units that do not change when the prop resizes
            "u": [round(x0 / W, 5), round(x1 / W, 5)],
            "v": [round(1 - y1 / H, 5), round(1 - y0 / H, 5)],
        })

    # LOSSLESS CHECK. Lay the parts back on the background at their own
    # coordinates; it must reproduce the reference. If the background fill or
    # a box is wrong this is where it shows, not three stages later.
    check = bg.copy()
    for p, o in zip(man["parts"], out):
        x0, y0, x1, y1 = p["px"]
        check.paste(Image.open(kit / f"{p['name']}.png"), (x0, y0))
    a, b = ob.load(), check.load()
    diff = sum(1 for x in range(0, W, 2) for y in range(0, H, 2)
               if sum(abs(m - n) for m, n in zip(a[x, y], b[x, y])) > 12)
    tot = (W // 2) * (H // 2)
    check.save(d / f"_recomposed_{args.face}.png")

    man2 = {"face": args.face, "size": [W, H], "aspect": round(W / H, 5),
            "background": f"bg_{args.face}.png", "parts": out}
    (d / f"layers_{args.face}.json").write_text(json.dumps(man2, indent=1))
    print(f"{args.face}: {W}x{H}, {len(out)} parts, background written")
    print(f"  recomposition differs from the reference on "
          f"{100*diff/tot:.2f}% of sampled pixels")
    for o in out:
        print(f"  {o['name']:20} {o['resize']:6} {o['anchor']:7} "
              f"u {o['u'][0]:.3f}..{o['u'][1]:.3f}  v {o['v'][0]:.3f}..{o['v'][1]:.3f}")
    print(f"wrote {d / f'layers_{args.face}.json'}")


if __name__ == "__main__":
    main()
