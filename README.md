# Pharmacy Modular Builder

A browser game where you lay out a pharmacy from modular, resizable furniture,
rendered in a cute pixel-art low-poly style — and the modules fill themselves
with props as you grow them. Built against `CLAUDE CODE BRIEF — Pharmacy
Modular Builder`, Phases 0–6.

```bash
npm install
npm run dev        # http://localhost:5173

npm run build && npm run preview &
npm test           # headless acceptance checks, writes test/shots/
npm run portraits  # one framed shot per module, to compare against docs/concept/
```

Pick something from the **catalogue** on the left, click to place it. **Drag**
orbits · **R** rotates 45° · **X** deletes the selected module · **Esc** swaps
place and select mode. Sizes, save/load, the instancing stress test and every
look-dev knob are in the panel on the right.

## The catalogue

Nineteen modules on five shelves, grouped the way a pharmacy is laid out.

| Shelf | Modules |
| --- | --- |
| **Dispensary** | Dispensing bench · Dispensary racking · CD cabinet · Vaccine fridge · Sink unit · Waste & sharps |
| **Retail floor** | Gondola shelving · Wall shelving · OTC counter (stretch) · Till / POS · Basket stack · Offers dump bin · Queue barrier · Stock boxes |
| **Consultation** | Consultation booth · Consultation chair |
| **Staff** | Staff lockers · Filing cabinet |
| **Signage** | Pharmacy cross · Aisle sign |

Definitions live in `src/modules/catalogue/`, one file per area. A module is
pure data — form, resize behaviour, sockets and decor slots — so adding one is
a part list and a few numbers, not code.

Every one of them was rebuilt from its concept sheet in `docs/concept/`, and
the sheets turned out to agree on one thing above all: **a light frame around
darker panels** — proud corner posts, stiles, rails and a tray-like top cap in
the pale colour, with the body set back between them. The staff lockers had it
exactly backwards and inverting them is the whole finding in one object. The
fittings that recur on nearly every sheet — corner studs, vent stacks, label
plates, keypads — live in `catalogue/fittings.js`, so a part list says what the
object *is* and calls one function for the ornament. See `docs/style-bible.md`.

## Phases

| Phase | Status |
| --- | --- |
| 0 — Scaffold | Vite, three r185, lil-gui, stats, orbit controls |
| 1 — Look development | toon ramp, warm key + cool fill, rim, palette module, faceted normals, all three vertex mask channels with their six ramps in the UI |
| 2 — Nine-slice | margins as uniforms, normals corrected by the inverse-transpose, `capMask` varying, both §5.2 guards asserted at load |
| 3 — Hybrid material | 128² pixel-art trim sheet, 128² atlas, Tier A/B blend on `capMask`, Tier C triplanar for floor and walls |
| 4 — Outlines and hatching | normal-depth prepass sharing the vertex stage, Roberts cross on linearised depth, tinted ink, surface-locked cross-hatching — **built, and off by default**: the flat pixel look does not want ink |
| 5 — Module system | registry, sockets, both resize modes, socket + surface snapping, raycast placement, seeded decor slots, save/load |
| 6 — Instancing | `InstancedMesh` with `aTargetScale` / `aMargins` instanced attributes |

`npm test` drives the built app in headless Chromium and checks thirteen things,
including the acceptance tests that can be made objective:

- **Phase 2** — the cap crop is *pixel-identical* from 1.0× to 4.0× (mean
  channel difference 0.00/255), with the camera anchored to the cap.
- **Phase 3** — moving the triplanar floor half a texture period shifts the
  pattern; moving it a whole period does not. The texture is carried by the
  panel, which is what "object space, not world space" buys.
- **Phase 4** — with the pass switched on for the measurement, ink covers
  roughly 8% of the frame at 3m and 3% at 30m: the lines hold their weight
  instead of flooding.
- **Phase 5** — raising a gondola from 4 to 6 shelves gives six shelf meshes,
  not four taller ones; a gondola snaps into a flush run; save → clear → load
  round-trips identically.
- **Phase 6** — 200 modules (399 unit instances) cost one extra draw call.
- **§8.4 decor** — growing a desk from 2 bays to 5 adds props without touching
  a single one of the originals, and shrinking back restores exactly the same
  set. The test asserts the identities, not the counts.

It also asserts the authored sheets actually loaded, so a missing PNG fails
loudly instead of quietly rendering flat colour.

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
├── art/                 palette · ramps · bakeMasks · trimLayout · textures · shadow
├── modules/
│   ├── catalogue/       the modules themselves, one file per shelf
│   │   └── fittings.js  studs · vents · plates · keypads · caps · posts
│   ├── registry.js      merge point, schema docs, load-time validation
│   └── geometry · ModuleInstance · resize · decor · InstancedBatch
├── ui/                  catalogue panel · lil-gui look-dev
├── build/               snapping · placement · serialize
public/textures/         the authored sheets: trim · atlas · tiling · hatch
tools/authoring/         one-off asset authoring, run by hand (§11)
src/generated/           the img2threejs factory — reconstruction, not renderer
docs/img2threejs/        its spec, intake analysis and blockout review
docs/style-bible.md      palette, fixed light, fixed camera, the reference rules
docs/concept-prompts.md  the concept-sheet prompt and how to run it
docs/concept/            the generated sheets — reference only, never loaded
test/smoke.mjs           headless acceptance checks
test/portraits.mjs       a framed shot per module, for judging by eye
```

Nothing outside `src/shaders/` contains a line of GLSL, constructs a
`ShaderMaterial`, or touches a render target. The UI drives look-dev through
`setSharedUniform` / `setSharedVector` / `setToonRampSteps`.

### The decisions the brief flags as load-bearing

- **Repeat beats stretch.** The dispensing desk makes the argument literally:
  its length is a `repeat` axis of fully detailed 0.90 m bays, so no texel is
  ever distorted, and only its depth is 9-sliced. The `serving_counter` is kept
  beside it as the brief's continuous version of the same furniture — the two
  standing next to each other are §1 in one screenshot.
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
- **Hard edges, flat faces.** `EDGE_SOFTNESS` is 0.3. A wide chamfer was tried
  and abandoned: it read friendly but also soft and inflated, where the
  reference props are square-cornered. The rim fresnel is the only shading term
  that varies *across* a face, so it is nearly off; the vertex masks darken the
  crease and leave the face alone. Separation comes from adjacent faces sitting
  at clearly different flat values, which is how the reference does it.
- **Ink is not black** — when it is on at all. The shipped look has outlines off
  and separates forms three other ways instead: hemisphere ambient (cool from
  above, warm bounce from the floor), a tinted rather than merely darker shadow,
  and a small lift on upward faces. See `docs/style-bible.md`.
- **More geometry means less mask, not more.** Rebuilding the catalogue from
  the concept sheets roughly doubled every module's part count, which multiplied
  how much of each surface the cavity mask covers. A cool crevice tint that was
  right on a plain box turned the whole room lilac on a detailed one, so
  `uCavityStrength` came down and both cool tints warmed. The same change made
  the AO bake's cost matter: it raycast every vertex against every triangle, so
  `bakeMasks` now buckets triangles into a grid the size of one ray and tests
  only the 3×3×3 block around each vertex — provably every triangle a ray could
  reach, and nothing else.
- **A seeded hash must avalanche, and FNV-1a alone does not.** Slot keys differ
  by one character (`s0`, `s1`, `s2`), and raw FNV values for eight sequential
  keys landed inside a band 0.027 wide — so every slot in a module cleared or
  failed its chance roll *together*, decided only by the seed. A 0.85 chance
  fired 80.7% of the time and prop counts swung between runs. A murmur3
  finalizer takes the spread to 0.5–0.9 and the rate to 85.4%.
- **A part says what it is MADE OF.** The trim sheet carries twelve material
  strips — paint, panel, wood, steel, grille, screen, glass, paper, fabric —
  and a part declares one. It used to carry a single generic "surface" strip
  that everything sampled, which meant a computer screen was textured like
  rock, and so were the glass and the paper labels. A screen is now a
  near-black field with a hard diagonal reflection staircase, which is what a
  display is in the reference. `validateRegistry()` rejects an unknown material
  at load, because a typo's failure mode is silent: it lands on whichever strip
  happens to sit at that V.
- **A tiling sheet must have no direction** — with exactly one exception.
  `wood` has grain, because it is only ever used on parts that really are
  timber. Every other strip is isotropic, because anything linear in a sheet
  sampled by everything becomes a stripe on every object in the room.
  The joinery lines still come from the geometry, which already has rails,
  stiles and drawer fronts as separate parts.
- **Decor is declared, not placed.** A module's `decor(params)` returns slots;
  the contents are a pure function of a saved seed and the slot key, so growth
  adds props without disturbing the ones already there — and a save reloads
  identically. See `docs/style-bible.md`.

## What is not the brief's, and why

- **The textures are authored by script, not by a painter.** They are real
  committed files in `public/textures/` — the app only loads them — and they
  follow the reference rules in `docs/style-bible.md`: bright lip on every
  groove, long confident grain, deliberate knots, staggered joints. But a person
  did not paint them, and taste in mark-making is exactly what §11.3 says the
  pipeline cannot supply. `tools/authoring/make_textures.py` regenerates them;
  it is an authoring tool, never a build, CI or runtime dependency, and deleting
  it does not affect the game.
- **The concept sheets are generated, and they are reference.**
  `tools/authoring/concept_sheet.py` drives Nano Banana 2 (§11.1 step 2) from a
  style block and a set of local reference images, and writes `docs/concept/`.
  Nothing in there is loaded, sampled or imported: what returns to the build is
  the numbers read off a sheet. §11 is explicit that the generation service is a
  desktop authoring tool and never a build, CI or runtime dependency, and this
  keeps to that — the key lives in a gitignored `.env` that only the script
  reads. The output also carries a SynthID watermark and C2PA credentials
  (§11.2), which is fine for reference you never ship.
- **No normal maps, so no UDN blending.** §6.2's UDN blend exists to fix
  triplanar normal maps. This project authors albedo only and puts AO in vertex
  colours (§6.3), so there is nothing to blend yet. The note is in
  `chunks/triplanar.glsl.js`.
- **Snapping stops at rule 2.** Socket-to-socket and surface are implemented;
  edge alignment (smart guides) is not.
- **Decor is not batched, and the seeded shop feels it.** Each prop is its own
  mesh, so the twenty-module starting scene runs around 250–290 draw calls. That
  is fine on a real GPU and wrong in principle. Props are fixed-size and already
  share geometry and material per type, which is exactly the shape
  `createInstancedBatch()` wants — batching decor is the clear next win and the
  one thing I would do before adding more modules.
- **Wall mounting is a `hover` height, not a wall socket.** Signs and wall
  shelving float at a declared height and you position them against a wall by
  eye. Real wall sockets on the room panels would be better.
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

**The look still needs your eye**, and `npm run portraits` is now how you use
it: it shoots every module at one framing so you can put the result beside its
sheet in `docs/concept/` and see the disagreements. That is how the dispensary
racking was caught with cream shelf boards where its sheet has oak ones — a
thing no amount of reading the part list would have surfaced.

`docs/style-bible.md` holds the palette,
one fixed light, one fixed review camera, the nine rules read off the reference
boards, and the desk's proportions as a table of numbers. That is the §11.1
artefact the brief wants — but it was assembled from reference by me, not
judged by a pharmacist looking at their own dispensary. Phase 1 says landing the
style takes several rounds; the concept sheets and this rebuild are round two.
Change the numbers in that table and in `src/modules/catalogue/` and the engine
does not care.

Everything the brief says to tune by eye is in the **Look dev** folder:
lighting, the six mask ramps, texturing density, hatching, and the outline
thresholds.
