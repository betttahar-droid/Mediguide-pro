# Semantic freezer v3 — adaptive texture audit

Status: **PASS**. V3 keeps the reviewed v2 paintover art and replaces accidental
scaling with four explicit behaviors: `fixed`, `repeat`, `expand`, and
`count-adaptive`.

## Runtime behavior

| Changed axis | Fixed elements | Adaptive result |
| --- | --- | --- |
| Width 1.45x | 28 decals and five handle pieces unchanged | rear coil rails 8 → 13 |
| Depth 1.50x | 28 decals and five handle pieces unchanged | side panel columns 1 → 2 |
| Height 1.30x | 28 decals and five handle pieces unchanged | panel rows 2 → 3, shelves 4 → 5, coil runs 8 → 13 |

The combined resize remains inside the hero-prop budget at 2,632 triangles.
Normal size is 2,498 triangles.

## Surface classification

- `fixed`: labels, displays, warnings, product graphics, fan graphic, corner
  wear, SDF border widths, and the handle assembly.
- `repeat`: reviewed material microfields sampled in physical world texels.
- `expand`: flat base-color centers and the length of solid panel seams.
- `count-adaptive`: side panel divisions, shelves, rear coil runs, and rails.

The vertex shader derives each model-axis length from `modelMatrix`. Local face
positions and face spans are multiplied by those lengths before SDF or material
sampling. This closes the transform-scale loophole in addition to supporting
the generator's W/H/D rebuild path.

## Reference-style measurement

| View | V3/reference hard-edge density |
| --- | ---: |
| Front isometric | 0.468 |
| Right side | 0.434 |
| Rear isometric | 0.454 |

The side view increased from v2's 0.401 to 0.434 because meaningful panel
divisions are now count-adaptive. The remaining visual gap is authored fitting
and mechanical detail, not texture scaling.

## Evidence policy

- Measured geometry and visible authority style: `direct`.
- Existing geometry-aligned paintovers: `reconstructed`.
- Unsupported hidden structure: `excluded`.
- A later Nano Banana alternate-view paintover can replace a reconstructed
  region without changing any runtime scaling rule.

Detailed results: `adaptive-audit-v3.json`, `spatial-audit-v3.json`, and
`runtime/audit.json`.
