# Pharmacy Modular Builder — test build

A browser game where you lay out a pharmacy from modular, resizable furniture.
This repository is a **quick test build** against `CLAUDE CODE BRIEF — Pharmacy
Modular Builder`: a vertical slice that proves the engine's load-bearing ideas
run end to end, not the phase-by-phase delivery the brief asks for.

```bash
npm install
npm run dev        # http://localhost:5173

npm run build && npm run preview &
npm test           # headless smoke test, writes test/shots/
```

Controls: **click** place · **drag** orbit · **R** rotate 45° · **Esc** toggle
place/select · **X** delete selected. Sizes, save/load and every look-dev knob
are in the lil-gui panel.

## What is built

| Brief | Status |
| --- | --- |
| §2 stack — Three.js, Vite, lil-gui, `WebGLRenderer` | yes (three r185 — npm's current release; r184 is available if you want the brief's exact pin) |
| §2 shader boundary — all GLSL under `src/shaders/`, imported only via `src/shaders/index.js` | yes, strictly |
| §4.3 vertex-baked masks (cavity / edge / up) in `COLOR_0` | yes, baked in JS at load |
| §4.4 toon ramp, warm key + cool fill, rim, palette module, faceted normals | yes |
| §5 nine-slice deform, normal correction, both `H < m` and `m > h` guards | yes |
| §8.1 module schema and registry | yes, six modules |
| §8.2 both resize modes — `stretch` (GPU 9-slice) and `repeat` (CPU instancing) | yes |
| §8.3 snapping — socket-to-socket and surface | partly: 1 and 2, not edge alignment |
| §8.4 detail props | two (medicine box, till) |
| §8.5 save format + localStorage, pure serializer | yes |

## What is not built

Deliberately, and in the brief's own priority order:

- **Textures.** There is no atlas and no trim sheet, so Tier A and Tier B are
  stood in by flat palette colours plus a procedural one-axis seam pattern. The
  region blend on `capMask` is real and wired; only the sampling is a stand-in.
- **Tier C triplanar (§6).** The floor uses the same adaptive material with a
  flat colour. Nothing else in the project needs it yet.
- **Outlines and hatching (§7, Phase 4).** No normal-depth prepass, no
  `EffectComposer`. `chunks/deform.glsl.js` is already the shared chunk the
  prepass will import, which is the part that is expensive to retrofit.
- **Instancing (Phase 6).** Margins and target scale are uniforms, as §5.3
  prescribes for Phases 2–5, so the move to `InstancedBufferAttribute` is open.
- **§11 asset pipeline.** Out of the codebase by design. No `scripts/`.

**The look is not signed off, and cannot be from here.** §11.1 is explicit that
proportions come off a concept sheet read as numbers, and Phase 1 is explicit
that it takes several rounds with the user's eye. The numbers in
`src/modules/registry.js` are placeholders I chose; they are the first thing to
replace once a concept sheet exists. Every ramp and light parameter the brief
says to tune by eye is in the **Look dev** folder of the panel.

## Layout

```
src/
├── main.js              scene, input, the build loop
├── shaders/             the ONLY GLSL in the project
│   ├── index.js         sole public entry point
│   ├── chunks/          deform · toonLighting · masks
│   └── AdaptiveMaterial.js
├── art/                 palette · ramps · bakeMasks
├── modules/             registry · geometry · ModuleInstance · resize
├── build/               snapping · placement · serialize
└── ui/                  gui
test/smoke.mjs           headless acceptance checks
```

`src/shaders/index.js` also exposes `setSharedUniform` / `setSharedVector` /
`setToonRampSteps`, so the UI can drive look-dev without importing GLSL. No file
outside `src/shaders/` constructs a `ShaderMaterial` or contains a line of GLSL.

## Notes on two brief decisions

- **`COLOR_0` holds the three masks, not the margins** (§4.3, §5.3). Margins are
  per-mesh constants and live in uniforms, which keeps the Phase 6 instanced
  path open.
- **Repeat beats stretch.** Of the six modules, five axes are `repeat`, three
  are `stretch`, and the rest are fixed. The gondola is the canonical
  repeat × repeat × stretch case, and `npm test` asserts that raising it from 4
  to 6 shelves gives six shelf meshes rather than four taller ones.

## Smoke test

`npm test` drives the built app in headless Chromium (SwiftShader, so it proves
the shaders compile and the module system behaves — not the frame rate) and
checks: no shader errors, repeat instancing, stretch driving `uTargetScale`,
param clamping, mask bake signal, socket snapping into a flush run, and a
save → clear → load round trip. Set `CHROMIUM_PATH` if Playwright's own browser
is not installed.
