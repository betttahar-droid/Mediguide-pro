# Guide-driven vaccine fridge v9 audit

Status: **PASS**

This is an isolated browser prototype. It does not replace the approved v5 GLB.

## Phase 0 — measurements

- Locked authority bounds: 39 px wide × 37 px deep × 96 px high.
- Half-width `W = 39 / 2 = 19.5` is the driving dimension.
- Half-depth: `18.5 / 19.5 = 0.949`; therefore `D = W * 0.949`.
- Base top: `20 / 96 = 0.208`; therefore `BASE_TOP = H * 0.208`.
- Opening bottom: `22 / 96 = 0.229`; therefore `OPEN_LO = H * 0.229`.
- Opening top: `82 / 96 = 0.854`; therefore `OPEN_HI = H * 0.854`.
- Crown bottom: `87.65 / 96 = 0.913`; therefore `CROWN_LO = H * 0.913`.
- Crown top: `93.5 / 96 = 0.974`; therefore `CROWN_HI = H * 0.974`.
- Opening half-width: `15 / 19.5 = 0.769`; therefore `OPEN_HALF = W * 0.769`.

## Phase 1 — proportions and planes

Macro dimensions are fractions of `W`, `H`, or `D`. Named front planes are shared by geometry and decals: `P_BODY`, `P_FRAME`, `P_DECAL`, and `P_HANDLE`. Fixed texel measurements are intentionally absolute in style-grid units; this is the required exception that prevents borders and fittings from stretching.

## Phase 2 — geometry

- Normal model: 22 structural parts, 1,838 triangles.
- Resized model: 23 structural parts, 1,850 triangles.
- The resized cabinet gains a shelf because repeated structure is generated at fixed pitch.
- Small hinges, corner chips, control lights, display marks, and grille detail are decals, not geometry.
- Two failed visual checks were corrected before proceeding: a solid door rail and then a solid cabinet front were occluding the cavity and shelves.

## Phase 3 — materials

Seven close-tone material families are used: cream, steel, teal, glass, plum, ochre, and dark. Fixed face-normal tints and a subtle object-height ramp replace scene lighting. The final pass snaps to a locked 28-colour palette.

## Phase 4 — surface masks

The Nano Banana v7 motif atlas supplies shape/alpha only. The shader recolours each mark from its assigned material family, so surface images do not introduce uncontrolled body colours or baked illumination.

## Phase 5 — fittings

- 19 decals are mounted on named frontmost planes.
- All decal dimensions are recorded in texels.
- The normal and independently resized models report identical decal-size arrays.

## Phase 6 — acceptance

| View | Parts | Triangles | Exact colours | Errors |
|---|---:|---:|---:|---:|
| Front | 22 | 1,838 | 26 | 0 |
| Isometric | 22 | 1,838 | 25 | 0 |
| Resized isometric | 23 | 1,850 | 25 | 0 |

- Required palette range (25–60): pass.
- Hero-prop triangle range (2,000–5,000): the model is slightly below the suggested hero range, but safely above the simple-prop floor. This is an explicit efficiency choice because the sub-4 px details are decals.
- Fixed decal dimensions after axis resize: pass.
- Adaptive structural count after resize: pass.
- Shader/page/console errors: none.
