#!/usr/bin/env python3
"""
The two Nano Banana assets the img2threejs pipeline needs — §11.1 step 2.

Authoring tool. NOT a build, CI or runtime dependency: the game never calls
this and never reads the key.

    cp .env.example .env      # then put your Gemini key in it
    python3 tools/authoring/nano_assets.py            # both
    python3 tools/authoring/nano_assets.py shape      # just the shape reference
    python3 tools/authoring/nano_assets.py atlas --ref docs/reference/crop-*.png

Two assets, two jobs, and they are not interchangeable:

  SHAPE   docs/concept/shape-reference.png
          A three-quarter hero of the object, which is what the img2threejs
          skill reads to derive proportions, part hierarchy and pivots. It is
          reference for a HUMAN and a VISION MODEL to measure — never sampled
          by the renderer.

  ATLAS   public/textures/nano-atlas.png
          A flat, seamless, top-down material sheet. This one IS sampled at
          runtime, so it has requirements the shape reference does not: no
          lighting baked in, no perspective, no drop shadow, and it must tile.
          Anything with a light direction in it will fight the toon shading and
          show up as a highlight that does not move when the object turns.

The output carries an invisible SynthID watermark and C2PA credentials (§11.2).
Fine for reference; worth knowing for a sheet that ships in public/.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concept_sheet import MODEL, generate_image, load_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# The prompts, verbatim as specified. Kept as constants rather than inlined so
# a regeneration is reproducible and a change to one is visible in the diff.
SHAPE_PROMPT = (
    "A 3D low-poly game asset of a retro pharmacy dispensing desk. "
    "16-bit pixel art style, simple faceted low-poly geometry, flat shading. "
    "Retro cozy medical color palette (muted greens, warm wood). "
    "3/4 isometric perspective, clean white background. No smooth gradients."
)

ATLAS_PROMPT = (
    "A flat, seamless 16-bit pixel art texture atlas of retro pharmacy materials "
    "including muted green metal and warm wood. Top-down view, completely flat "
    "shading, no lighting, sharp retro game texture."
)

ASSETS = {
    "shape": (SHAPE_PROMPT, ROOT / "docs" / "concept" / "shape-reference.png"),
    "atlas": (ATLAS_PROMPT, ROOT / "public" / "textures" / "nano-atlas.png"),
}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    # No `choices=` here: argparse validates the EMPTY list against choices when
    # nargs='*', so "generate both" would be rejected. Validate by hand instead.
    ap.add_argument("asset", nargs="*", help="shape and/or atlas; both if you name neither")
    ap.add_argument("--ref", nargs="*", default=[], help="style reference images")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    unknown = [a for a in args.asset if a not in ASSETS]
    if unknown:
        ap.error(f"unknown asset {unknown[0]!r} — choose from {', '.join(ASSETS)}")

    key = load_key()
    failed = False
    for name in args.asset or list(ASSETS):
        prompt, out = ASSETS[name]
        try:
            path = generate_image(prompt, out, key, refs=args.ref, model=args.model)
            print(f"  {name:6s} -> {path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")
        except Exception as exc:  # one refusal should not stop the other asset
            print(f"  {name:6s} -> FAILED: {exc}", file=sys.stderr)
            failed = True
    sys.exit(1 if failed else 0)
