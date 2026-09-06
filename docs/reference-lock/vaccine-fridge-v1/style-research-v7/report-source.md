# Retro Pixel-Model Style Research — Vaccine Fridge v7

Audience: Mediguide procedural-asset implementation  
Date: 2026-09-05  
Scope: the five user-supplied reference images, the accepted v5 vaccine-fridge model, and scale-safe geometry/material implementation in Blender, glTF, and Three.js.

## Executive answer

The references do not get their character from dense texture noise. They combine a construction-readable stack of chunky boxes with a deliberately small number of large, hard-edged color clusters. The current fridge already has the right broad proportions and functional silhouette. Its remaining mismatch is that secondary construction layers and material marks are too thin, faint, or evenly quiet. The v7 target should preserve v5, strengthen stepped relief and side-panel hierarchy, and replace the subtle v6 decal pass with larger Nano-authored semantic clusters compiled onto a fixed-size padded atlas.

## Primary visual evidence

The supplied references are the style authority. Automated measurements are recorded in `reference-measurements.json`; the GIF was sampled at frames 0, 211, and 421. Before measurement, every frame was median-cut to 24 colors so JPEG noise was not misclassified as intentional detail.

- Across the still references, the median same-color run is 3 px horizontally and 3–4 px vertically; the 75th percentile is 5–8 px. The GIF uses larger 5 px median clusters and 9–11 px 75th-percentile runs.
- Large faces remain mostly quiet. Contrast is concentrated into borders, corners, seams, handles, vents, window reflections, and small identity marks.
- Curves are either absent or converted into stair steps and short chamfers. Broad machine surfaces remain planar.
- Every object is readable first as 3–6 nested masses, then as panels, then as pixel clusters. Fine detail never substitutes for the massing.
- Face colors use short material ramps: a dark edge/shadow, a body color, and one or two highlights. Highlights form rectangular clusters rather than gradients.

These are observations and inferences from the supplied images, not claims about a named commercial style.

## Geometry checklist

1. **Chunky primary mass.** Keep the fridge's locked 39 × 37 × 96 model-pixel envelope; it already matches the tall appliance family in `inspo 2`.
2. **Three-level construction hierarchy.** Maintain primary body zones (crown, cabinet, base), secondary frames (door rail, cavity, side panel), and tertiary hardware (handle mounts, hinges, shelf lips, grille bars).
3. **Nested relief, not painted depth.** Structural borders, shelves, vents, hinges, rails, and seam lips must be real geometry. A front view should show at least four depth planes.
4. **Stepped corners.** Use one- or two-model-pixel chamfers/notches and square corner caps; avoid smooth multi-segment bevels. Blender's bevel modifier physically creates new edge geometry, while flat shading keeps planar faces visually uniform ([Blender Bevel Modifier](https://docs.blender.org/manual/en/4.4/modeling/modifiers/generate/bevel.html), [Blender flat shading](https://docs.blender.org/manual/en/4.4/scene_layout/object/editing/shading.html)).
5. **Thick readable bands.** Important rails should be 1–2 model pixels thick; small fittings should occupy at least 2 × 2 model pixels. Hairline geometry disappears at the intended camera scale.
6. **Functional repetition.** Shelf lips, grille slots, cooling slots, and hinge plates use measured templates and loops, not hand-painted repetition.
7. **Controlled asymmetry.** Use a small number of side- or corner-anchored fittings so the model feels authored without becoming noisy.
8. **Orthographic audit.** Judge silhouette and pixel rhythm with a three-quarter orthographic camera. Orthographic projection keeps apparent size independent of camera distance ([Three.js OrthographicCamera](https://threejs.org/docs/pages/OrthographicCamera.html)).

## Texturing checklist

1. **Three-to-five colors per material family.** Each material gets a dark, body, mid-light, and optional catch color; colors are quantized before export.
2. **Hard square sampling.** Blender's `Closest` interpolation is explicitly intended for pixel art ([Blender Image Texture node](https://docs.blender.org/manual/en/4.2/render/shader_nodes/textures/image.html)). glTF supports `NEAREST` for both magnification and minification ([Khronos glTF 2.0 sampler specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)); the exported model must use 9728 for both.
3. **One stable logical texel scale.** Repeating material fields remain mapped in model-pixel/world space. Scaling adds or removes repeats; it never enlarges the motif.
4. **Quiet center, marked perimeter.** Target 75–90% quiet base area on broad panels. Concentrate marks around corners, seams, sockets, and transition zones.
5. **Cluster hierarchy.** Primary marks are 2–8 model pixels long and 1–3 pixels thick; isolated single pixels are reserved for fasteners or indicator lights.
6. **Directional ramps.** Light catches favor top/left; dark bands favor bottom/right. This is a palette rule, not a blurred baked-light layer.
7. **Material-specific motifs.** Steel uses short seams and corner catches; enamel uses chips/notches; teal/glass uses stair-step reflections; grille areas use repeated dark slots and warm frame accents.
8. **Fixed decals for identity.** Labels, displays, fasteners, corner chips, and reflection clusters remain fixed-size and anchor to named sockets.
9. **Tiled nine-slice for scalable panels.** Corners remain constant while edges and centers tile. Unity documents this exact invariant for tiled nine-slice sprites ([Unity `SpriteDrawMode.Tiled`](https://docs.unity3d.com/kr/2022.2/ScriptReference/SpriteDrawMode.Tiled.html)).
10. **Protected atlas margins.** Every decal receives transparent internal breathing room plus an atlas gutter. Filtering and coarse mip levels can sample neighboring atlas regions, causing color bleed ([NVIDIA GPU Gems, texture filtering artifacts](https://developer.nvidia.com/gpugems/gpugems2/part-v-image-oriented-computing/chapter-37-octree-textures-gpu)). For this deliberately crisp asset, decal mipmaps are disabled and the gutter is still retained.
11. **Correct color space.** PNG/JPEG color textures are treated as sRGB; Three.js warns that a wrong assignment changes apparent brightness and color ([Three.js color management](https://threejs.org/manual/en/color-management.html)).
12. **No generic dirt.** Reject random speckle, gradients, broad cloudy wear, and uniform edge outlining. Each mark must explain material, construction, orientation, or identity.

## v7 implementation decisions

- Preserve `vaccine-fridge-source-true.glb` as the accepted baseline.
- Build `vaccine-fridge-style-fit-v7.glb` separately.
- Add real side-panel rails, three lower service slots, and compact hinge/corner hardware from proportional model-pixel templates.
- Generate a new Nano Banana motif sheet using all five references, the locked turnaround, and the v5 render.
- Deterministically key magenta, quantize to the locked palette, reject tiny/noisy components, enforce 3 px internal transparent margins and 4 px atlas gutters, and store each source cell in an audit manifest.
- Place motifs at fixed model-pixel size on named corners/sockets. Do not scale them with cabinet width or height.
- Export glTF samplers as `NEAREST`/`NEAREST`, preserve sRGB color semantics, and keep the orthographic render path unchanged for A/B comparison.

## Acceptance audit

Geometry passes only if: the original envelope and door/shelf proportions remain locked; all new depth-bearing details are geometry; repeated slots are loop-generated; no smooth bevel is introduced; and the accepted v5 file is untouched.

Texture passes only if: each decal has at least 3 px internal transparency and 4 px atlas gutter; no connected mark exceeds 8 × 10 logical pixels; broad panels remain at least 75% quiet; samplers are nearest-neighbor without mipmaps; colors belong to the locked ramps; and no random isolated speckle is introduced.

Visual fit passes only if: the render reads as the same vaccine fridge before close inspection, has visibly stronger construction hierarchy and deliberate pixel clusters than v5/v6, retains quiet material fields, and introduces no stretched corners, sliding details, blended pixels, or doubled geometry.

## Claim-to-source ledger

- Nearest-neighbor/Closest preserves discrete source texels: Blender Manual, Image Texture Node, updated 2026-08-12; https://docs.blender.org/manual/en/4.2/render/shader_nodes/textures/image.html
- glTF sampler enum 9728 is `NEAREST`: Khronos Group, glTF 2.0 Specification; https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- Texture atlas filtering can bleed outside an island, especially through mip levels: GPU Gems 2, Chapter 37, NVIDIA; https://developer.nvidia.com/gpugems/gpugems2/part-v-image-oriented-computing/chapter-37-octree-textures-gpu
- Nine-slice tiled mode preserves corners and tiles other regions: Unity Technologies, `SpriteDrawMode.Tiled`, 2022.2; https://docs.unity3d.com/kr/2022.2/ScriptReference/SpriteDrawMode.Tiled.html
- Orthographic projection keeps apparent size independent of distance: Three.js documentation, OrthographicCamera; https://threejs.org/docs/pages/OrthographicCamera.html
- Color textures require sRGB annotation: Three.js manual, Color Management; https://threejs.org/manual/en/color-management.html
- Flat shading uses constant face normals; bevel creates edge geometry: Blender Manual, Shading and Bevel Modifier; https://docs.blender.org/manual/en/4.4/scene_layout/object/editing/shading.html and https://docs.blender.org/manual/en/4.4/modeling/modifiers/generate/bevel.html

## Limitations and stopping rule

The supplied JPEGs and GIF are presentation renders rather than source meshes or palettes, so exact original texel density and material colors cannot be recovered. Measurements therefore describe rendered cluster rhythm, not hidden authoring resolution. Research stopped when the visual rule categories had direct image evidence, every consequential runtime technique had primary documentation, and additional generic “low-poly style” articles were unlikely to alter the implementation decision.
