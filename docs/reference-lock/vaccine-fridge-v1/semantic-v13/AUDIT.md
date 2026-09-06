# Vaccine fridge semantic-face v13

## Result

This is the first working pilot of the per-part/per-face semantic texture compiler. It keeps the accepted geometry while separating three behaviors that v12 incorrectly tried to encode in one generic mask:

- Border and perimeter structure: fixed-cap nine-slice face programs.
- Repeating structure: fixed-density middle fields.
- Unique marks: fixed-size, socket-anchored semantic decals.

## Visual outputs

- `runtime/view-front.png`
- `runtime/view-iso.png`
- `runtime/view-iso-sx-1_65-sy-1_35-sz-1_22.png`
- `semantic-faces-v13-source.png`
- `semantic-faces-v13-compiled-preview.png`
- Diagnostic geometry: `diagnostics/`

## Nano generation audit

Nano Banana 2 received exact raw front/isometric renders, a part-ID render, a face-orientation render, the fridge authority, and all five style references. It was asked for eight face-role masks.

The authored designs were useful, but the requested layout failed: Nano returned a 3×3 arrangement rather than 4×2, with one extra quiet cell and two detached decorative bars. The compiler records `generationLayoutAccepted: false`, rejects those three regions explicitly, and compiles only the eight reviewed face roles. No failed region silently enters runtime.

The deterministic atlas is 256×32 pixels: eight 32×32 tiles using exactly five indexed tone roles (32, 96, 128, 192, 240). Runtime material families supply all actual colors.

## Runtime mapping

| Role | Runtime behavior |
|---|---|
| `roofTop` | top face, fixed perimeter + stretch center |
| `crownFront` | front face, fixed vertical caps + horizontal repetition |
| `shelfLip` | shelf front, horizontal repetition |
| `baseFront` | front face, fixed perimeter + stretch center |
| `ventField` | front face, repeated middle |
| `doorSocket` | four fixed 2×2-texel corner decals |
| `serviceStripe` | two fixed 8×3-texel side decals |
| `shelfPatch` | one fixed 4×3-texel top decal per generated shelf |

Semantic masks operate on a half-model-texel grid. This makes authored marks smaller than the v12 material cells while preserving the common world grid.

## Bugs found during the pilot

1. Nano ignored the guide layout. Fixed by explicit reviewed cell selection and a rejection ledger.
2. The first shader integration accidentally enabled semantic sampling on every unassigned face because `THREE.Vector4()` defaults `w` to `1`. All role uniforms now initialize with `new THREE.Vector4(0, 0, 0, 0)`, and the regression test locks this.
3. Full-face nine-slice stretched interior service marks. Those marks were removed from face programs and reintroduced as fixed anchored decals.
4. The initial semantic decals were still too large. Unique mark placements now use half-scale physical dimensions consistent with the semantic grid.

## Acceptance

| Check | Normal | Resized | Result |
|---|---:|---:|---|
| Triangles | 2,160 | 2,174 | PASS |
| Parts | 34 | 35 | PASS |
| Semantic/identity decals | 12 | 13 | PASS |
| Generated shelf patches | 4 | 5 | PASS |
| Palette, front | 28 | — | PASS |
| Palette, isometric | 34 | 33 | PASS |
| Fixed fitting dimensions | exact | exact | PASS |
| Handle/lamp dimensions | exact | exact | PASS |
| Shader/page errors | 0 | 0 | PASS |

## Honest limitation

This proves the representation and resizing behavior, but it is not yet an exact perceptual match to the authority render. The semantic placement is more coherent than generic atlas scattering, while the overall surface-transition density remains lower than the authority. The next art pass should add reviewed face roles for cavity walls and cabinet seams rather than adding random decals.

Overall technical pilot: **PASS**.
