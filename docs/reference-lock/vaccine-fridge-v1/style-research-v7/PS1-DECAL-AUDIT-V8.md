# PS1 Decal/Geometry Audit — v8

Overall result: **PASS**

- Small-detail geometry from v7: removed.
- Replacement hinges/catches/service marks: six fixed decals.
- Macro hull vertices: 204 → 136 (33.3% reduction).
- Coarse silhouette profile rings: 10.
- Detail threshold: features below four model pixels become decals.
- Texture sampler: `[{"magFilter": 9728, "minFilter": 9728}]`.

- PASS — `styleVersionEight`
- PASS — `fourPixelGeometryThreshold`
- PASS — `smallDetailPolicyIsDecals`
- PASS — `tenCoarseMacroProfileRings`
- PASS — `smallV7GeometryRemoved`
- PASS — `sixReplacementFittingDecals`
- PASS — `replacementDetailsCarryDecalPolicy`
- PASS — `replacementDetailsRemainFixedScale`
- PASS — `macroHullVertexCountReduced`
- PASS — `nearestSamplerWithoutMipmaps`
- PASS — `renderExists`
