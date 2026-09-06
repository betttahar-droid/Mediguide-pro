# Semantic freezer v2 audit

Status: **PASS as an experimental v2 branch**. Geometry is unchanged from the
accepted model; only surface authoring, fittings, and shader behavior changed.

## Source and compilation

- Nano Banana 2 was attempted through the configured Gemini authoring path but
  returned HTTP 429 repeatedly. The built-in GPT image editor was therefore
  used to make geometry-aligned paintovers from the raw renders plus the three
  authority images.
- Paintover silhouettes are never used. The compiler takes only selected
  internal material regions and semantic fittings.
- Broad material fields repeat in fixed world texels with alternating mirror
  phase. Their influence is low in face interiors and stronger only in hard,
  fixed-width edge and bottom bands.
- Labels, displays, warnings, fan art, medicine labels, and wear clusters are
  fixed-size decals on named mounting planes. Transparent wear extraction
  prevents rectangular sticker backgrounds.

## Proportion check

- Envelope: 44 px wide, 104 px high. `44 / 104 = 0.423` overall width/height.
- Depth: 43 px against 44 px width. `43 / 44 = 0.977`.
- Door opening half-width: `22 * 0.795 = 17.49 px`; total opening is 34.98 px.
- Body/header bands: `104 * 0.837 = 87.05 px` and
  `104 * 0.971 = 100.98 px`.
- Door-frame thickness is 3.2 texels; it is structural. Handle pieces and all
  fittings intentionally use fixed texel dimensions so axis resizing cannot
  stretch them.

## Resize audit

- Normal: 2,492 triangles, 103 parts, 28 decals, 4 shelves.
- Axis-resized: 2,564 triangles, 109 parts, 28 decals, 5 shelves.
- Rigid handle dimensions: identical.
- Fixed fitting/decal dimensions: identical.
- Result: `runtime/audit.json` = **PASS**.

## Reference-style audit

Object crops are normalized to 256 x 384 and quantized to 32 colors before
measurement. This isolates spatial material/detail density from the already
accepted silhouette.

| View | v2/reference hard-edge ratio | top-5 color share delta | Result |
| --- | ---: | ---: | --- |
| Front isometric | 0.470 | +0.063 | PASS |
| Right side | 0.401 | +0.365 | PASS |
| Rear isometric | 0.485 | +0.256 | PASS |

The v2 result is materially closer than the previous flat render, but it is not
a pixel-identical reconstruction. It currently carries about 40-49% of the
reference's measured hard-edge density. The remaining difference is mostly
small authored chips, cable detail, interior shelf construction, and back-unit
mechanical density—not a missing whole-face texture.

## Technique audit

- Whole-face color texture stretching: **NO**.
- Repeating material used at full strength: **NO**.
- Semantic edge/bottom bands measured in world texels: **YES**.
- Fixed decals anchored to named planes: **YES**.
- Handle and bought-in parts remain unstretched: **YES**.
- Meaningful small details modeled as extra geometry: **NO**; they are decals.
- Repeated depth-bearing coils/shelves remain geometry: **YES**.
- Shader/page errors: **NONE**.

Detailed measurements are in `spatial-audit-v2.json`; runtime invariance is in
`runtime/audit.json`.
