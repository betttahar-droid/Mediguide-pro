# Pharmacy Modular Builder

A browser game where you lay out a pharmacy from modular, resizable furniture,
rendered in a stylised low-poly hand-painted style. Built against `CLAUDE CODE
BRIEF — Pharmacy Modular Builder`, Phases 0–6.

```bash
npm install
npm run dev        # http://localhost:5173

npm run build && npm run preview &
npm test           # headless acceptance checks, writes test/shots/
```

Controls: **click** place · **drag** orbit · **R** rotate 45° · **Esc** toggle
place/select · **X** delete selected. Sizes, save/load, the instancing stress
test and every look-dev knob are in the lil-gui panel.

## Phases

| Phase | Status |
| --- | --- |
| 0 — Scaffold | Vite, three r185, lil-gui, stats, orbit controls |
| 1 — Look development | toon ramp, warm key + cool fill, rim, palette module, faceted normals, all three vertex mask channels with their six ramps in the UI |
| 2 — Nine-slice | margins as uniforms, normals corrected by the inverse-transpose, `capMask` varying, both §5.2 guards asserted at load |
| 3 — Hybrid material | 1024² trim sheet, 512² atlas, Tier A/B blend on `capMask`, Tier C triplanar for floor and walls |
| 4 — Outlines and hatching | normal-depth prepass sharing the vertex stage, Roberts cross on linearised depth, tinted ink, surface-locked cross-hatching in the beauty pass |
| 5 — Module system | registry, sockets, both resize modes, socket + surface snapping, raycast placement, detail props, save/load |
| 6 — Instancing | `InstancedMesh` with `aTargetScale` / `aMargins` instanced attributes |

`npm test` drives the built app in headless Chromium and checks eleven things,
including the acceptance tests that can be made objective:

- **Phase 2** — the cap crop is *pixel-identical* from 1.0× to 4.0× (mean
  channel difference 0.00/255), with the camera anchored to the cap.
- **Phase 3** — moving the triplanar floor half a texture period shifts the
  pattern; moving it a whole period does not. The texture is carried by the
  panel, which is what "object space, not world space" buys.
- **Phase 4** — ink covers ~6% of the frame at 3m and ~2.5% at 30m: the lines
  hold their weight instead of flooding.
- **Phase 5** — raising a gondola from 4 to 6 shelves gives six shelf meshes,
  not four taller ones; a gondola snaps into a flush run; save → clear → load
  round-trips identically.
- **Phase 6** — 200 modules (399 unit instances) cost one extra draw call.

Chromium here is software-rendered, so the suite proves the shaders compile and
the systems behave — not the frame rate. Set `CHROMIUM_PATH` if Playwright's own
browser is not installed.

## How the pieces fit

```
src/
├── main.js              scene, room, input, the build loop
├── shaders/             the ONLY GLSL in the project
│   ├── index.js         sole public entry point
│   ├── chunks/
│   │   ├── vertexStage.glsl.js   the one vertex stage, shared by both passes
│   │   ├── deform.glsl.js        slice1D and the normal correction
│   │   ├── triplanar.glsl.js     Tier C
│   │   ├── toonLighting.glsl.js  ramp, key/fill, rim
│   │   └── masks.glsl.js         the §4.3 ramps
│   ├── AdaptiveMaterial.js       all three tiers + hatching
│   ├── NormalDepthMaterial.js    the prepass twin
│   └── OutlinePass.js            prepass target + Roberts composite
├── art/                 palette · ramps · bakeMasks · textures · shadow
├── modules/             registry · geometry · ModuleInstance · resize · InstancedBatch
├── build/               snapping · placement · serialize
└── ui/                  gui
test/smoke.mjs           headless acceptance checks
```

Nothing outside `src/shaders/` contains a line of GLSL, constructs a
`ShaderMaterial`, or touches a render target. The UI drives look-dev through
`setSharedUniform` / `setSharedVector` / `setToonRampSteps`.

### The decisions the brief flags as load-bearing

- **Repeat beats stretch.** Five axes across the catalogue are `repeat`, three
  are `stretch`, the rest fixed. The gondola is the canonical repeat × repeat ×
  stretch case.
- **One vertex stage, not two.** `chunks/vertexStage.glsl.js` is the whole
  vertex shader for both the beauty pass and the prepass, and
  `createNormalDepthMaterial({ share })` reuses the beauty material's *uniform
  objects* by reference. The two passes cannot drift apart, so the outline
  cannot trace a mesh the player can't see.
- **`COLOR_0` holds the three masks, not the margins.** Margins are a per-mesh
  constant, so they are uniforms in Phases 2–5 and instanced attributes in
  Phase 6 — exactly the path baking them per-vertex would have closed.
- **Margins are zero on axes that do not stretch.** A margin on a fixed axis
  classifies its outer band as "cap" and hands the whole module to Tier A;
  `validateRegistry()` rejects it with the module named.
- **Object-space triplanar, post-deform.** World space swims; sampling the
  original position smears under stretch.
- **Ink is not black.** It is the palette's shadow tone (§7.3).

## What is not the brief's, and why

- **The textures are procedural, not hand-painted.** `src/art/textures.js`
  generates the trim sheet, the atlas, the tiling surface and the hatch on a
  canvas at load. They carry the brief's strip layout and the right tiling
  behaviour, so the material system is exercised for real, but they are
  placeholders for `public/textures/`. They are authored as luminance detail
  around mid-grey and tinted by `palette.js` at sample time, which is what keeps
  the palette consistent across the catalogue; painted albedo sheets would
  replace that multiply.
- **No normal maps, so no UDN blending.** §6.2's UDN blend exists to fix
  triplanar normal maps. This project authors albedo only and puts AO in vertex
  colours (§6.3), so there is nothing to blend yet. The note is in
  `chunks/triplanar.glsl.js`.
- **Snapping stops at rule 2.** Socket-to-socket and surface are implemented;
  edge alignment (smart guides) is not.
- **Instancing is an API, not the whole scene.** `createInstancedBatch()` builds
  the batched path and the stress test drives it; placed modules still use one
  mesh per unit so they stay individually selectable and resizable. Converting
  placement to batches is a scheduling decision, not a missing capability.
- **Contact shadows are blobs.** The toon ramp is the shading model and a shadow
  map would fight it; `src/art/shadow.js` grounds the modules the way the
  reference art does.
- **Three r185, not r184.** r185 is npm's current release; r184 is still
  available if you want the brief's exact pin.

## The part that is still yours

**The look is not signed off, and cannot be from here.** §11.1 is explicit that
proportions come off an orthographic concept sheet, read as numbers, before any
modelling — and Phase 1 is explicit that landing the style takes several rounds
with your eye on it. The numbers in `src/modules/registry.js` are placeholders I
chose: the dispensing desk is a 0.95 worktop on a 0.72 carcass with a 0.06
overhang, a 0.10 recessed kick, and a drawer band on the trim sheet's detail
strip. Replace them from a real concept sheet and the engine does not change.

Everything the brief says to tune by eye is in the **Look dev** folder:
lighting, the six mask ramps, texturing density, hatching, and the outline
thresholds.
