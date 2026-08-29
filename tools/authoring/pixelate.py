#!/usr/bin/env python3
"""
Re-pixelate a generated sheet: snap it to its true texel grid and quantise it.

Authoring tool. NOT a build, CI or runtime dependency.

    python3 tools/authoring/pixelate.py public/textures/nano-atlas.png --colors 32

WHY THIS EXISTS. The image API returns JPEG bytes regardless of the filename,
and JPEG is the wrong codec for pixel art: it is lossy in exactly the way that
destroys hard edges. The generated atlas came back with 49,698 unique colours
in a sheet that should carry about thirty, and a flat green panel measured 56
distinct values across a 40x40 patch. Every one of those is ringing around an
edge the model drew crisply.

That matters because of how the sheet is sampled. NearestFilter takes ONE texel
and shows it at ten times its size — so it magnifies the ringing instead of
averaging it away the way a linear filter would. Turning on the crisp-retro
filter settings over a JPEG makes the artefacts *more* visible, not less.

So before a generated sheet is usable it needs two passes:

  1. GET ONTO A TEXEL GRID. Ideally by detecting the one the art was drawn on.
     Measured on the generated atlas, though, there ISN'T one: edge energy falls
     on every candidate scale at exactly chance (share x scale = 0.95-1.06 for
     every scale from 2 to 12). The model rendered an ILLUSTRATION OF pixel art
     at native resolution rather than art on a pixel grid. So when no grid is
     found, one is imposed by integer downscale — which is the only way to make
     the sheet genuinely pixel-art rather than merely pixel-art-flavoured.
  2. QUANTISE. Snap what survives to a small palette, so flat regions are
     genuinely flat and the sheet reads as authored rather than as photographed.

The result is written back as a real PNG.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

from PIL import Image


def detect_texel(im, lo=2, hi=12):
    """The pixel scale the art was drawn at, found from where the EDGES land.

    Within-cell variance looks like the obvious measure and is a trap: a 1x1
    cell has zero variance by definition, so any normalisation you pick either
    lets scale 1 win outright or is an arbitrary fudge. Edges are the honest
    signal instead. Art drawn at 6x has its colour changes on multiples of 6,
    so summing the gradient per column and scoring each candidate by how much
    of that gradient falls on its multiples finds the scale without needing a
    penalty term at all.

    Returns 1 when nothing scores clearly — a sheet that really is 1:1, or one
    the JPEG has smeared past recognition.
    """
    g = im.convert('L')
    w, h = g.size
    px = g.load()

    def gradient_profile(n, along_x):
        prof = [0.0] * n
        step = max(1, (h if along_x else w) // 200)
        for i in range(1, n):
            acc = 0
            for j in range(0, (h if along_x else w), step):
                a = px[i, j] if along_x else px[j, i]
                b = px[i - 1, j] if along_x else px[j, i - 1]
                acc += abs(a - b)
            prof[i] = acc
        return prof

    best, best_score = 1, 0.0
    for prof in (gradient_profile(w, True), gradient_profile(h, False)):
        total = sum(prof) or 1.0
        for scale in range(lo, hi + 1):
            on = sum(v for i, v in enumerate(prof) if i % scale == 0)
            # share of edge energy on the grid, against the share expected by
            # chance (1/scale). A real grid beats chance by a wide margin.
            score = (on / total) * scale
            if score > best_score:
                best, best_score = scale, score
    return best if best_score > 1.35 else 1
def snap(im, texel):
    """Collapse each texel cell to its median colour, then scale back up."""
    w, h = im.size
    cols, rows = w // texel, h // texel
    src = im.convert('RGB').load()
    small = Image.new('RGB', (cols, rows))
    dst = small.load()
    for ry in range(rows):
        for rx in range(cols):
            cell = Counter(
                src[rx * texel + i, ry * texel + j]
                for j in range(texel) for i in range(texel)
            )
            dst[rx, ry] = cell.most_common(1)[0][0]
    return small


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Snap a generated sheet to its texel grid.")
    ap.add_argument("image")
    ap.add_argument("--colors", type=int, default=32, help="palette size after quantising")
    ap.add_argument("--texel", type=int, default=0, help="force a texel size instead of detecting")
    ap.add_argument("--downscale", type=int, default=4,
                    help="integer factor used to IMPOSE a grid when none is detected")
    ap.add_argument("--upscale", action="store_true",
                    help="write back at the original size instead of the texel grid")
    ap.add_argument("--out", default="", help="output path (default: overwrite in place)")
    args = ap.parse_args()

    path = Path(args.image)
    im = Image.open(path)
    before_fmt, before_colors = im.format, len(set(im.convert('RGB').getdata()))

    detected = args.texel or detect_texel(im)
    if detected > 1:
        # the art really is on a grid — collapse each cell to the colour that
        # dominates it, which is a colour that was actually in the art
        small = snap(im, detected)
        how = f"detected {detected}px grid"
    else:
        # no grid: impose one. BOX averages each block, which is right here —
        # we are RESAMPLING to a lower resolution, not recovering texels that
        # were already there, and averaging is what kills the JPEG ringing.
        f = args.downscale
        small = im.convert('RGB').resize((im.width // f, im.height // f), Image.BOX)
        how = f"no grid found, imposed one by /{f}"

    # MEDIANCUT with no dithering: dithering is how you fake colours you do not
    # have, and a pixel-art sheet wants the colours it actually has.
    small = small.quantize(colors=args.colors, method=Image.MEDIANCUT, dither=Image.NONE)
    out_img = small.convert('RGB')
    if args.upscale:
        out_img = out_img.resize(im.size, Image.NEAREST)

    out = Path(args.out or path)
    out_img.save(out, "PNG", optimize=True)
    after = len(set(out_img.getdata()))
    print(f"{path.name}: {before_fmt} {im.size} {before_colors:,} colours")
    print(f"  {how} -> {out_img.size}, {after} colours -> {out}")
    if before_fmt == "JPEG":
        print("  (input was JPEG under a .png name — lossy, which is why this pass is needed)")
