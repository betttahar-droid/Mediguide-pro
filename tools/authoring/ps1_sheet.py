#!/usr/bin/env python3
"""One generation, all the angles: let the image model hold the turnaround.

    python3 tools/authoring/ps1_sheet.py "arcade cabinet" --out work/ps1

Authoring tool. NOT a build, CI or runtime dependency.

TWO CORRECTIONS TO WHAT CAME BEFORE.

1. THE REFERENCE MUST NOT BE PIXEL ART. nano_views.STYLE opens with "16-bit
   pixel art, hard-edged chunky pixels", so every reference generated so far
   was a sprite -- and then the measurement stage read TEXELS as if they were
   geometry, and the part list inherited a look main.js already applies in the
   shader (palette snap, dither, outline). Pixelation is a post effect. Ask
   for it in the source and you bake it in twice.

   A PlayStation-era prop is a different thing: a low-polygon mesh with
   visible flat facets, carrying a small low-resolution hand-painted TEXTURE.
   The geometry is chunky and the detail lives in the texture.

2. THE MODEL SHOULD DRAW THE TURNAROUND, NOT THE HARNESS. nano_views.py makes
   one call per view and chains each to the last as a reference, which leaves
   the FIRST view anchored to nothing -- and that is the one that came back
   three-quarter, 40% wider than the back, and sent the carver a grid 2.81x
   too wide. b8a7f61 added a gate to catch it after the fact.

   Asking for all the views in ONE image removes the failure instead of
   detecting it: every view is drawn in the same pass, at the same scale, on
   the same baseline, because the model is composing them together. That is
   what multi-view consistency means for an image model, and it is the one
   thing PARTS.md says it is genuinely built for.

The sheet is then split on its background gaps, which is deterministic.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402

PS1_STYLE = (
    "Rendered as a late-1990s PlayStation 1 game asset. LOW POLYGON COUNT: "
    "visible flat angular facets, hard straight edges, no smooth shading, no "
    "bevels, no subdivision, no rounded corners. Surfaces carry LOW-RESOLUTION "
    "HAND-PAINTED TEXTURES -- coarse visible texels, with shading, panel lines, "
    "labels and grime PAINTED INTO THE TEXTURE rather than modelled -- in a "
    "muted, slightly desaturated palette. "
    "A CRISP CLEAN RENDER. This is NOT pixel art and NOT a sprite: no "
    "dithering, no black outline, no posterisation, no halftone, no scanlines."
)

LAYOUT = (
    "Draw FOUR orthographic elevations of the SAME object, side by side in a "
    "single row, evenly spaced, in this order: FRONT, LEFT SIDE, BACK, TOP.\n"
    "- STRICT ORTHOGRAPHIC PROJECTION in every view: dead on, no perspective, "
    "no foreshortening, no vanishing point, no three-quarter angle. Each view "
    "shows ONE face only.\n"
    "- All four are the SAME object at the SAME scale. Front, side and back "
    "share one baseline and one height. Front and back are the same width. "
    "The top view's width matches the front and its depth matches the side.\n"
    "- Wide clear gaps of flat background between the views, and none of them "
    "touching the image edge.\n"
    "- Absolutely flat single-colour background, one colour edge to edge. NO "
    "drop shadow, NO ground plane, NO reflection, NO gradient.\n"
    "- Exactly one object per view and nothing else in the frame: no extra "
    "props, no annotations, no labels, no text, no arrows, no watermark."
)

NAMES = ["front", "side", "back", "top"]


def split(path, out_dir, min_width=40):
    """Cut the sheet on its background gaps. Deterministic; no model involved."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    cols = [any(not is_bg(px[x, y]) for y in range(0, h, 2)) for x in range(w)]
    runs, start = [], None
    for x, f in enumerate(cols):
        if f and start is None:
            start = x
        elif not f and start is not None:
            if x - start >= min_width:
                runs.append((start, x))
            start = None
    if start is not None and w - start >= min_width:
        runs.append((start, w))

    out = []
    for i, (a, b) in enumerate(runs):
        x0, x1 = max(0, a - 6), min(w, b + 6)
        # DROP THE CAPTION. The sheet comes back labelled FRONT / LEFT SIDE /
        # BACK / TOP however firmly the prompt asks for no text, and the
        # caption sits under its view separated by a band of background -- so
        # it lands inside the column and inflates the object's height by the
        # gap plus the lettering. Keep only the TALLEST vertical run of
        # foreground in the column, which is the object; the caption is a
        # short run below it.
        rows = [any(not is_bg(px[x, y]) for x in range(x0, x1, 2)) for y in range(h)]
        vruns, s = [], None
        for y, f in enumerate(rows):
            if f and s is None:
                s = y
            elif not f and s is not None:
                vruns.append((s, y)); s = None
        if s is not None:
            vruns.append((s, h))
        if vruns:
            y0, y1 = max(vruns, key=lambda r: r[1] - r[0])
            y0, y1 = max(0, y0 - 6), min(h, y1 + 6)
        else:
            y0, y1 = 0, h
        sub = im.crop((x0, y0, x1, y1))
        name = NAMES[i] if i < len(NAMES) else f"view{i}"
        p = Path(out_dir) / f"{name}.png"
        sub.save(p)
        out.append((name, p, sub.size))
    return out, runs


def measure(paths):
    """Object box per view, so the four can be checked against each other."""
    dims = {}
    for name, p, _ in paths:
        im = Image.open(p).convert("RGB")
        w, h = im.size
        px = im.load()
        bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1],
                      px[w - 1, h - 1]]).most_common(1)[0][0]

        def is_bg(c):
            return sum(abs(a - b) for a, b in zip(c, bg)) < 40

        xs = [x for x in range(w) if any(not is_bg(px[x, y]) for y in range(0, h, 2))]
        ys = [y for y in range(h) if any(not is_bg(px[x, y]) for x in range(0, w, 2))]
        if xs:
            dims[name] = (xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1)
    return dims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset")
    ap.add_argument("--subject", default=None,
                    help="extra description; default is the bare noun")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    subject = args.subject or f"a {args.asset}"
    prompt = f"{PS1_STYLE}\n\nSubject: {subject}\n\n{LAYOUT}"
    (out / "prompt.txt").write_text(prompt)

    sheet = out / "sheet.png"
    print(f"generating one turnaround sheet for '{args.asset}' ...", flush=True)
    generate_image(prompt, sheet, load_key())
    print(f"  wrote {sheet} {Image.open(sheet).size}")

    paths, runs = split(sheet, out)
    print(f"  split into {len(paths)} views on background gaps: "
          f"{[(n, s) for n, _, s in paths]}")
    dims = measure(paths)
    print("\n  object boxes:")
    for n, d in dims.items():
        print(f"    {n:6} {d[0]:4} x {d[1]:4}")
    if "front" in dims and "back" in dims:
        fw, bw = dims["front"][0], dims["back"][0]
        print(f"\n  front vs back width: {fw} vs {bw} "
              f"({100*abs(fw-bw)/max(fw,bw):.1f}% apart)")
    if all(k in dims for k in ("front", "side", "top")):
        want = dims["side"][0] / dims["front"][0]
        got = dims["top"][1] / dims["top"][0]
        print(f"  footprint from front+side 1:{want:.2f}  vs top view 1:{got:.2f}")
    json.dump({k: list(v) for k, v in dims.items()}, open(out / "dims.json", "w"), indent=1)


if __name__ == "__main__":
    main()
