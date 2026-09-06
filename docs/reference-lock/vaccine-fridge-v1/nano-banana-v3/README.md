# Nano Banana microtexture pipeline v3

Nano Banana 2 is used as a texture art director and source painter, not as a geometry or atlas authority.

## Inputs

- `style-references/`: five user-supplied examples of the target low-resolution voxel language.
- `vaccine-fridge-turnaround-v1.png`: locked fridge design and palette.
- `authority-1door-pixel-v6.png`: previous geometry-preserving render used only as the style-transfer target.

The exact generation prompts are saved next to the outputs. `nano-style-target-v3.jpg` establishes the desired frequency, contrast, face-value steps, and trim language. It is not used as geometry. `nano-microtexture-kit-v3.jpg` supplies material colors and motif evidence.

## Deterministic compiler

Run:

```powershell
npm.cmd run build:fridge-nano-materials
```

The compiler:

- crops only fixed 4x4 source cells;
- derives a limited Nano palette per material;
- places one-model-pixel accents on an exact 16x16 logical grid;
- rejects accent clusters larger than two pixels;
- forces a base-color periodic perimeter;
- uses a sparse 32x32 period for large steel panels;
- emits front/side/top value variants without changing motif coordinates;
- records all source and style-reference hashes in the audit.

Identity-bearing display and grille pixels remain locked source crops. Door edge bands, shelf-lip bands, seams, and fasteners use fixed model-pixel dimensions and named per-bay anchors. A wider fridge repeats complete door modules; no decal, corner, or texel is stretched.
