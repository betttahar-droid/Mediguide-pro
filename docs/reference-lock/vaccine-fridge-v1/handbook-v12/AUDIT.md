# Vaccine fridge handbook v12 audit

This pass applies `BUILDINGAPROP.txt` to the accepted low-poly fridge geometry. The v11 Nano paintover remains a visual study only; it is no longer used as a full-face runtime texture.

## Output

- Runtime front: `runtime/view-front.png`
- Runtime isometric: `runtime/view-iso.png`
- Non-uniform resize: `runtime/view-iso-sx-1_65-sy-1_35-sz-1_22.png`
- Nano Banana source: `surface-masks-v12-source-guided.png`
- Deterministic compiled mask preview: `surface-masks-v12-compiled-preview.png`
- Machine audits: `surface-masks-v12.audit.json`, `runtime/audit.json`

## Authoring result

Nano Banana 2 (`gemini-3.1-flash-image`) was called only through `tools/authoring/concept_sheet.py`. Two earlier generations were rejected because their panel shapes were inconsistent. The guided generation produced five disconnected panels with mutually consistent source ratios (0.7214–0.7286). The deterministic cutter therefore normalized all five equally to the kit's 20×20 logical texel grid; it did not infer a different crop for each design.

The source is reduced to exactly three neutral mask values: 0, 128, and 255. Runtime colors come only from named material families. `vent` is the only repeat-middle mask; the other four stretch only their quiet centers while preserving their measured 2–4 texel caps.

## Geometry and placement list

- STRETCH: shell walls, base, crown, roof, door frame, and cavity opening.
- REPEAT: shelves are produced by a fixed-pitch loop; the resized model gains one shelf instead of stretching shelf spacing.
- ANCHOR: the handle is two mounts, one grip, one catch highlight, and one return, all recorded in fixed texel sizes.
- ANCHOR: control bezel and caution plate are the only atlas decals. Both use fixed dimensions and fixed corner offsets, with face-size guards.
- ANCHOR: seven status lamps are fixed purchased parts. Their two added colors are measured from `inspo 3.gif` and `inspo 1.jpg`.
- Glass: the door opening is true cavity geometry. There is no transparent pane, reflection material, or reflection decal.

## Texture and material list

- No UV unwrap, triplanar projection, color texture map, baked shadow, or baked lighting.
- Surface atlas carries placement/structure only as three-level tone masks.
- Per-face lighting comes from the shader normal and the named material ramps.
- Surface coordinates are reconstructed from local box position and half extents.
- Nine-slice marks are expressed in `STYLE.texel` units and gated when a face cannot contain both fixed caps and a center.
- Final nearest-palette snap keeps each view inside the measured PS1-style palette budget.

<SELF_AUDIT>

Proportions calculated: canonical measured grid is 39 px wide × 96 px high. Half-width = 39 / 2 = 19.5. Base top = 20 / 96 = 0.208. Crown start = 87.65 / 96 = 0.913. Crown end = 93.5 / 96 = 0.974. Door opening half-width = 15 / 19.5 = 0.769. Half-depth = 18.51 / 19.5 = 0.949. Frame border is a fixed kit mark of 3 texels, not a proportional placement.

Absolute numbers used? NO unclassified absolute geometry sizes. Macro bands are measured fractions. Literal values passed through `tx()` are deliberately classified fixed world/texel marks, pitches, or purchased fitting dimensions.

UVs/Textures/Baked lighting used? NO standard UV unwrap, color texture map, or baked lighting. The permitted three-tone structure mask and two semantic fitting regions are sampled by analytic face coordinates/fixed decal quads.

Structural depth faked with textures? NO. Shelves are real boxes in a fixed-pitch loop. The vent mask describes a surface grille and does not pretend to change the silhouette.

Fittings anchored to fixed corners? YES. Control and caution fittings use named front mounting planes, fixed texel offsets, and face-size guards. Handle components keep identical recorded dimensions under resize.

</SELF_AUDIT>

## Acceptance

| Check | Normal | Resized | Result |
|---|---:|---:|---|
| Triangles | 2,140 | 2,152 | PASS (hero range 2,000–5,000) |
| Parts | 34 | 35 | PASS (repeat count adapts) |
| Decals | 2 | 2 | PASS (semantic fittings only) |
| Palette, front | 25 | — | PASS |
| Palette, isometric | 28 | 28 | PASS |
| Fixed decal dimensions | exact | exact | PASS |
| Fixed handle/lamp dimensions | exact | exact | PASS |
| Shader/page errors | 0 | 0 | PASS |

Overall: **PASS**.
