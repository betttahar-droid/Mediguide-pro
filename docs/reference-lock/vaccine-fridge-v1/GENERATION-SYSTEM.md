# Vaccine fridge generation system

This directory owns the visual and dimensional authority for every vaccine-fridge variant.

## Authority chain

1. `vaccine-fridge-turnaround-v1.png` is the locked visual source and its SHA-256 is recorded in `geometry-authority.json`.
2. `geometry-authority.json` owns all geometry, feature coordinates, part classifications and adaptive rules. No builder-local dimensions are allowed.
3. `vaccine-fridge-source-atlas.png` is extracted directly from the locked raster at one texture pixel per model pixel.
4. `vaccine-fridge-adaptive-source-atlas.png` is a deterministic derivative. Fixed details are removed from repeatable layers and emitted as separate 1:1 decals.
5. The five files in `style-references/` are the texture-style authority. Their hashes are recorded in the Nano audit.
6. Nano Banana 2 creates `nano-style-target-v3` and `nano-microtexture-kit-v3`. They own appearance direction only; they cannot supply dimensions, UV coordinates, geometry, or identity graphics.
7. `build_nano_fridge_materials.py` compiles the generated board into exact 16x16 logical material fields and a sparse 32x32 large-panel field. It enforces one model pixel per texel, equal periodic edges, and a maximum two-pixel accent cluster.
8. `build_fridge_authority_variants.py` translates fixed end caps, repeats complete 32px door bays and expands only parts classified as `spanWidth`.

Full orthographic illustrations must never be layered over modeled parts. The front is assembled from real frame, door, shelf, handle and base geometry; only genuinely graphical features such as the display, grille and glass reflection remain image surfaces.

The accepted export no longer uses full-view source skins on the front, side, back, or top. Cream, steel, and teal structure use audited Nano tiles in model-pixel UV space. Large side/back faces use a low-density 32px field plus sparse fixed-size corner/fastener decals and paired semantic seams. Door frames and shelf lips receive fixed-width light/dark strips repeated with each complete bay. This restores pixel character without allowing baked structural errors back into the model.

AI-generated part sheets are advisory only. A proposed measurement or texture must be reviewed and explicitly entered into the authority file before it can affect an exported model.

The reusable axis and socket contract lives in `src/production/adaptiveAssembly.js`. It is a 3D extension of nine-slice resizing: each axis is independently classified as fixed-near, fixed-center, fixed-far, protected-end span, or proportional. Fixed decals are rejected if any axis asks for proportional or stretch behavior.

## Texture policies

- Door bays: repeat the complete measured 32px bay. Never stretch it.
- End caps and side panels: translate only. Their source-pixel scale stays fixed.
- Display, grille and glass reflections: independent fixed-resolution surfaces.
- Handles: three-part geometry (grip plus two mounts); no baked handle slab.
- Shelves: real body and front lip only; no second illustrated shelf surface.
- Grille: one fixed 26×11px source-derived decal per door bay.
- Crown and top: preserve both ends and fill only the inserted neutral centre using source pixels.
- Sampling: nearest-neighbour with mipmaps disabled.
- Ordinary material fields: 16x16 texels over 16x16 model pixels; individual accents remain one model pixel.
- Large panel fields: 32x32 texels over 32x32 model pixels; only two accents per period.
- Face values: front, side, and top use palette-preserving value variants with the same motif coordinates.
- Corners, displays, logos, handles and wear accents: attach to named sockets with scale `(1,1,1)`; recompute only their position after a resize.
- Functional repetition: insert complete doors, shelves, grille units, or bays. Never create a fractional functional module by stretching it.

## Required workflow

Run:

```powershell
npm.cmd run build:fridge-source
npm.cmd run gate:fridge-source
npm.cmd run build:fridge-nano-materials
npm.cmd run test:fridge-adaptive
npm.cmd run build:fridge-variants
npm.cmd run gate:fridge-variants
```

The source gate checks front, side and back silhouettes against the locked turnaround. The variant gate verifies authority hashes, measured dimensions, semantic part counts, absence of the rejected legacy atlas, and exact rendered parity between the generated one-door asset and the accepted source-true asset. It also writes isolated 1/2/3-door inspection renders to `variants/`.

## Acceptance rules

A generation is rejected if any of these are true:

- a dimension exists only in a builder script;
- an authority part is missing from the adaptive rule partition;
- one-door rendered parity is not exact;
- a source silhouette drops below its recorded threshold;
- a texture feature stretches rather than repeating or remaining fixed 1:1;
- a fixed decal uses a proportional or stretch axis policy;
- a generated tile has unequal opposite edges;
- a generated identity decal changes a counted feature or locked glyph;
- a full-view source skin overlaps an explicitly modeled front component;
- the inspection render contains a detached surface, duplicated fixed display, invented detail or inconsistent bay.

The current accepted widths are 38.75px, 70.75px and 102.75px. Depth remains 36.75px and height remains 96px for all three.
