# Adaptive geometry and texture system

## Decision

Do not resize an assembled GLB with transform scale. Rebuild it from semantic modules. The reusable model is a **3D nine-slice plus repeatable bays and fixed decal sockets**.

This separation is the important part:

1. Geometry authority owns measurements and topology.
2. Material fields own repeatable surface character.
3. Trim owns fixed end caps and a repeatable neutral middle.
4. Decals own identity details at a fixed model-pixel size.
5. A resize recipe owns where modules move, repeat, or expand.

Nano Banana can propose an appearance target and clean material source art. It does not own measurements, module counts, UV rectangles, identity graphics, or acceptance. Generated content enters the runtime only after deterministic extraction and gates.

## Resize vocabulary

Every part declares a policy independently on `x`, `y`, and `z`:

| Policy | Position behavior | Size behavior | Typical use |
| --- | --- | --- | --- |
| `fixed_min` | follows the near/min edge | unchanged | left/bottom/front corner |
| `fixed_center` | follows axis center | unchanged | centered display or logo |
| `fixed_max` | follows the far/max edge | unchanged | right/top/back corner |
| `nine_slice_span` | protected ends translate; safe center expands | center only changes | rail, crown, panel frame |
| `proportional` | affine remap | scales | allowed only for explicitly scale-safe invisible structure |

Combining these policies across three axes creates the spatial equivalent of 27 box-slice zones. A corner can be fixed on all axes; an edge can span one axis and remain fixed on two; a face center can span two axes and remain fixed in depth.

Functional elements use a separate discrete rule: `repeat_per_module`. Doors, shelf cassettes, grille units, hinges, and handles are inserted as complete measured modules. Continuous extra length is absorbed only by designated filler panels.

## Texture layers

### Layer 0: base material fields

Cream enamel, painted steel, teal enamel, and glass are seamless tiles sampled at model-pixel/world scale. Geometry growth allocates more repetitions; it never enlarges existing texels. Pixel-art sampling uses nearest filtering and no mipmaps.

The accepted Nano Banana tiles are:

- `public/textures/vaccine-fridge-nano-cream-microtile-v3.png`
- `public/textures/vaccine-fridge-nano-steel-microtile-v3.png`
- `public/textures/vaccine-fridge-nano-teal-microtile-v3.png`
- `public/textures/vaccine-fridge-nano-glass-microtile-v3.png`

Their 16x16 outputs are deterministic derivatives of the generated board. Motifs occupy literal one-model-pixel cells, no connected accent can exceed two cells, and a base-color perimeter makes opposite edges identical. Large side/back faces use a separate 32x32 tile with only two accents. This prevents both earlier failures: oversized cloudy patches and dense polka-dot repetition.

The material compiler also emits reference-measured top and side value variants. Door edges, shelf lips, roof inset bands, panel seams, corner notches, and short rectangular panel marks are semantic fixed-width strips or decals. They carry most of the reference style; the repeatable material center deliberately stays quiet.

### Layer 1: trims and protected borders

A trim is a one-dimensional three-slice: fixed start cap, tiled middle, fixed end cap. A framed panel is a two-dimensional nine-slice. Geometry and texture use the same protected-border values so a corner pixel cannot drift away from its corner mesh.

### Layer 2: fixed decals

Displays, labels, logos, wear corners, highlight marks, and grille faces live on separate planes or shallow meshes attached to named sockets. The socket is repositioned after rebuild, while decal size and scale remain unchanged. Do not project a decal across a hard corner; use one planar socket per face.

Generated grille and display attempts are never trusted as identity sources. Runtime keeps:

- `public/textures/vaccine-fridge-grille.png`
- `public/textures/vaccine-fridge-display.png`

This is expected behavior, not a failed pipeline: the gate prevented a small generative error from becoming a production error.

### Layer 3: optional wear

Wear is a sparse transparent decal or procedural mask, seeded by stable part ID. Keep it away from atlas island boundaries and do not bake object-scale lighting into the base tile. The fridge uses fixed-size reference-derived corner notches, roof bands, panel marks, and a semantic side-panel seam; these move with their anchors but never scale.

## Runtime resize sequence

1. Quantize the requested size to model pixels.
2. Resolve discrete functional counts such as door or shelf bays.
3. Build/instance complete repeated modules.
4. Resolve fixed caps, corners, rails, and filler bounds with per-axis policies.
5. Recompute socket positions from anchors.
6. Attach fixed decals with scale `(1,1,1)`.
7. Set tiled material density from model pixels, not transform scale.
8. Validate bounds, module counts, socket sizes, tile seams, and atlas gutters.

The asset root should remain at scale `(1,1,1)` after the rebuild. If an editor exposes a scale gizmo, convert that interaction into requested dimensions and rebuild; do not retain the scale transform as the final state.

## Why this approach

- Unity's 9-slicing model preserves corner regions and either stretches or tiles centers. Its documentation also distinguishes changing the sliced size from ordinary transform scaling: https://docs.unity3d.com/cn/2018.4/Manual/9SliceSprites.html
- glTF's `KHR_texture_transform` can address atlas subregions with offset and scale, but baking final UVs remains the most portable fallback: https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_texture_transform/README.md
- Three.js exposes repeat, offset, wrap, and nearest filtering on textures: https://threejs.org/docs/pages/Texture.html
- Three.js warns that projected decals distort around corners, supporting separate planar face sockets: https://threejs.org/docs/pages/DecalGeometry.html
- Repeated identical modules should remain instances until per-instance editing is required: https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/instances/instance_on_points.html
- In Three.js, `InstancedMesh` reduces draw calls for repeated geometry/material pairs: https://threejs.org/docs/pages/InstancedMesh.html

## Source assets and audit

- Geometry guide: `docs/reference-lock/vaccine-fridge-v1/gpt-image/gpt-image-geometry-decomposition-v1.png`
- Style target: `docs/reference-lock/vaccine-fridge-v1/nano-banana-v3/nano-style-target-v3.jpg`
- Texture board: `docs/reference-lock/vaccine-fridge-v1/nano-banana-v3/nano-microtexture-kit-v3.jpg`
- Texture audit: `docs/reference-lock/vaccine-fridge-v1/nano-banana-v3/nano-microtexture-kit-v3.audit.json`
- Style references: `docs/reference-lock/vaccine-fridge-v1/style-references/`
- Generic resolver: `src/production/adaptiveAssembly.js`
- Accepted isolated render: `docs/reference-lock/vaccine-fridge-v1/variants/authority-1door-nano-v3.png`
- Accepted 1/2/3 comparison: `docs/concept/vaccine-fridge-voxel-variants-nano-v3.png`

Negative subtraction/CSG is reserved for real recesses and cut-outs. It is not the resize system: repeated booleans make topology and UVs less predictable, while semantic parts keep dimensions, sockets, and texture ownership explicit.
