# Style bible

§11.1 step 1. Every texture and every module's proportions are judged against
this page. It is deliberately short: a fixed palette, a fixed light, a fixed
camera, and a small set of rules read off reference.

## Reference

Boards surveyed for "low poly hand painted desk / furniture / wood". Links
only — none of these images are redistributed in this repo.

- <https://www.pinterest.com/thehobbyhaus/low-poly/>
- <https://www.pinterest.com/kayjammi/hand-painted-assets/>
- <https://www.pinterest.com/emmasmith92/low-poly-and-handpainted/>
- <https://www.pinterest.com/jennelljaquays/hand-painted-3d-game-styles/>
- <https://www.pinterest.com/kennethtaylor3964/wood-texture-stylized/>
- <https://www.pinterest.com/xsbharp/textures-stylized-wood/>
- <https://www.pinterest.com/loquaciouslit/texture-low-poly-ref/>

Then surveyed again for "low poly retro pixelated models":

- <https://www.pinterest.com/blobman605/ps1-graphics/>
- <https://www.pinterest.com/themaxp12345/ps1-aesthetic/>
- <https://www.pinterest.com/alexdelker/ps1-style-graphics/>
- <https://www.pinterest.com/ryoung13/low-poly-ps1/>

Two clusters matter. The WoW / Albion / Aetherlight family gave the chunky
forms, warm woods and painted metal fittings. The isometric-room dioramas in the
retro boards gave three things the first pass had missed:

- **Props sit in clusters, not evenly spaced.** A mug beside a stack of paper,
  two bottles together. Evenly spaced single objects read as a showroom.
  `resolveDecor` now spawns a companion prop next to a slot's main one.
- **The floor stays quiet.** In every diorama that reads well the ground is a
  near-flat field and the furniture carries the detail. Our floor tiles were
  0.5 m and busy; they are 0.73 m now.
- **Very limited palette, one or two saturated accents**, everything else
  desaturated pastel.

Then a set of five images supplied directly as the style target: hard-edged
isometric voxel props where the pixel texture carries the detail and the
geometry is close to a plain box. Those live in `docs/reference/` — gitignored,
because they are not this project's work to redistribute — and they are what
`tools/authoring/concept_sheet.py` feeds the image model. They moved two things:

- **The detail belongs to the texture, not the silhouette.** The server tower in
  that set is a box; everything that makes it read is painted on. Our answer to
  that is the trim sheet's detail strip plus small dedicated fitting parts, not
  more chamfer.
- **The room is a colour, not an absence of one.** Every diorama that reads well
  commits: cool walls against a warmer floor, warm furniture against both. The
  walls were paper `#e4d9c1` — near enough to the worktops that a bench dissolved
  into the wall behind it — and are now mint `#aed6c2`, with the floor moved warm
  to `#c9c2b2`. The mint is pushed harder than it looks like it should be,
  because a 0.72 warm key washes a pale cool out.

## The look: pixel art, not painted

The style target is **cute pixelated low-poly** — Minecraft-ish texel density,
chunky forms with soft bevelled corners, **no ink outlines**, warm pastel
colour, and enough small props that a scene reads as lived in. That drives five
things:

- **Sheets are tiny.** 128² trim and atlas, 64² floor and hatch. A texel lands
  near 2 cm in world space. Combined with `NearestFilter` on magnification,
  texels read as texels.
- **No blur, no antialiasing, no gradients.** Value steps and 4×4 Bayer
  dithering. A groove is one dark pixel with one bright pixel beside it.
- **Soft corners.** `EDGE_SOFTNESS` in `modules/geometry.js` scales every
  chamfer. It sat at 0.4 for a hard voxel edge and is now **0.85**: a visible
  bevel that catches the edge highlight. Rounded corners are most of what makes
  an object read as friendly rather than as a crate, and the wider chamfer gives
  the §4.3 mask bake a much stronger convex signal — which matters with no ink.
- **Flat lighting.** A 3-step ramp, a weak rim, no cross-hatching by default.
  Pixel art gets its detail from texels; a soft shading gradient over them just
  muddies the palette.
- **No outlines.** The Phase 4 ink pass is built and correct, and it is off. In
  this style the texels already carry the detail and a line around every box
  competes with them. What replaces the ink is the vertex-mask work of §4.3:
  cavity and edge strengths are pushed up (0.55 and 0.42) so a convex corner
  lightens and a crevice darkens in the albedo itself. Forms separate by value,
  not by line. `Look dev → Outlines → enabled` puts the ink back.

## What the reference actually does

Nine rules, each of which is now a line in `tools/authoring/make_textures.py`
or in a module's part list.

1. **The surface strip is a MATERIAL, not a structure.** This is the rule that
   replaced three earlier ones, and it is the most important on the page. The
   sheet used to draw four hard plank bands with near-black grooves and
   near-white lips; mapped across a part's height that reads as loud horizontal
   stripes on every object in the room. The joinery lines are the geometry's job
   — rails, stiles and drawer fronts are already separate parts — so the strip
   now carries low-contrast mottling, isotropic speckle and a whisper of a board
   edge at about a fifth of the old contrast. Everything in it sits within
   roughly ±22 of mid grey.
2. **Texture should have no direction.** Anything linear in a tiling sheet
   becomes a stripe on every object that uses it. Mottling is round; speckle is
   single pixels; grain is short broken dashes, never a run across the sheet.
   The metal cell lost its brushed lines for the same reason.
3. **Keep the deliberate marks deliberate.** Bolts, the label rail and the floor
   grout stay crisp, because those are structure and you want to see them. Only
   the *material* went quiet.
4. **Knots are drawn deliberately** — at this size, an eight-pixel ring around a
   two-pixel core, now at low contrast. One per board at most.
5. **Fittings are ornament.** Bolts, corner plates, label rails and pulls are
   what separate "a box" from "a piece of furniture". They live on the trim
   sheet's detail strip and on small dedicated parts.
6. **Chunky, slightly squat proportions.** A thick worktop, a deep overhang,
   heavy pulls. A correctly-proportioned realistic desk looks realistic.
7. **Narrow hue range, and the value range lives in the lighting.** The sheets
   are greyscale and `palette.js` supplies the colour; the contrast that used to
   be painted into the texture now comes from the shading model instead, where
   it can respond to the form.
8. **When there is ink, it is a drawn line, not a filter** — dark, tinted
   toward the palette's shadow tone, never black. This project ships with it
   off; the rule stands for anyone who turns it on.

## Palette

One source of truth: `src/art/palette.js`. No hex literals anywhere else.

| Role | Hex | Used on |
| --- | --- | --- |
| paper | `#f2e6d2` | gondola carcass, desk frame |
| wall | `#aed6c2` | walls — the room's cool half |
| bone | `#ded0b6` | worktops, upstands |
| putty | `#c4b294` | — |
| oak | `#c98f4e` | dispensing desk carcass and drawers |
| oakDark | `#9a6531` | desk trim middle |
| walnut | `#6b4325` | desk pulls, kick, queue barrier |
| mint / teal / tealDeep | `#7fbfa4` `#3f8a76` `#27594c` | serving counter, accents |
| signal | `#e0704a` | medicine boxes — the one warm signal colour |
| steel / steelDark | `#9aa6a8` `#5e6b6e` | till, fridge carcass, fittings |
| glass | `#bfd8d6` | fridge door |
| floorTile | `#c9c2b2` | floor — the room's warm half |
| ink | `#2b1f33` | outlines, hatching — never black |

## Shading

Four things carry the look, in order of how much they do. All of them live in
`shaders/chunks/toonLighting.glsl.js`.

1. **Hemisphere ambient.** Fill light is not one colour: cool `#d6e6f4` from
   above, warm `#f6e2c4` bounced off the floor, mixed on the world normal. One
   `mix()`, and every upward face picks up sky while every downward face picks
   up the room. It is the cheapest thing that stops flat shading looking flat.
2. **Coloured shadow.** The dark end of the ramp is tinted `#8d85b0`, not just
   darkened. Shadows with a hue read as chosen; grey shadows read as an absence
   of light.
3. **The ramp.** Three flat steps, terminator wrapped past halfway.
4. **Up-face lift.** +9% on upward faces, −9% on downward ones, independent of
   the key. The classic voxel trick: it separates a worktop from the carcass
   front under it even in full light, and it does the job the outline pass used
   to.

The fixed key stays: warm `#fff3de` at azimuth 37°, elevation 53°, intensity
0.72; cool fill from behind-left at 0.18; rim at 0.14, suppressed on upward
faces; hemisphere strength 0.33. Hatching off — it fights the texels.

## Decor: things pop in when a module grows

§8.4's detail props, made systemic. A module declares **slots** as a function of
its parameters, so making it bigger fills the new space instead of stretching
the emptiness:

- A gondola gets three slots per bay per tier. Add a shelf and it stocks itself.
- The desk gets three slots per bay, plus a fourth "hero" slot that only unlocks
  at three bays or more — that is where the terminal, the plant and the basket
  live, so a long bench earns equipment a short one does not have.
- The stretch counter has no bays, so its slots are spaced by length instead:
  one every 0.55 m.

What each slot holds is a pure function of the module's saved seed and the
slot's key, which buys two things worth more than the randomness itself:

1. **Adding a bay never reshuffles the bays already there.** Resize 2 → 5 → 2
   and you get exactly the props you started with. `npm test` asserts this.
2. **A saved scene reloads identically**, because the seed is serialised with
   the module.

Props are fixed-size, so one geometry and one material serve every copy.

A slot can also spawn a **companion** — a second prop tucked against the first
at a small offset, derived from the same seed and key. Clustering costs nothing
in stability: the companion appears and disappears with its parent slot. Slots
on a shelf, where the spacing is already tight, set `pair: 0` and stay single.

## Before you change a module's shape

Generate a concept sheet first and read the numbers off it — §11.1 in order.
`docs/concept-prompts.md` explains the prompt and the flags;
`tools/authoring/concept_sheet.py` runs it; `docs/concept/` holds the generated
set, one sheet per module plus a props row.

The sheet is reference, never an asset. Nothing in `docs/concept/` is loaded,
sampled or imported by the game — what comes back into the build is the numbers
you read off it and the fittings you decide are worth a part.

## Believable detail, per object

The rule for every module in `catalogue/`: **detail earns its place by naming
what the object is for.** A box with a bevel is a box. The same box with three
hinges, a keypad and a warning plate is a controlled-drugs cabinet, and a
pharmacist reads it as one instantly.

So each module carries the two or three fittings that identify it:

| Module | What makes it that thing |
| --- | --- |
| Dispensing bench | Kick recess, stiles and rails, two drawer depths, label holders, rear upstand, socket block |
| Dispensary racking | Shallow shelves, a label strip on every one, bay dividers |
| CD cabinet | Three heavy hinges, keypad, warning plate, no glass |
| Vaccine fridge | Glass door, head and foot rails, temperature readout, condenser grille |
| Sink unit | Basin well and rim, mixer column, lever, two cupboard doors |
| Waste & sharps | Yellow lid, flap, hazard plate, foot pedal and linkage, sharps box on top |
| Staff lockers | Three vent slots per door, stubby handle, number plate, plinth |
| Filing cabinet | Four drawers, pull and label holder on each, a top things get left on |
| Consultation booth | Glazed upper panels with beads, door post and head, skirting, sign over the door |
| Pharmacy cross | Two bars, a lit face inset, a wall stalk |

Fittings go on the trim sheet's **detail strip** when they repeat along a run
(bolts, label rails) and on their own small parts when they are positional (a
keypad, a temperature readout). That split is what §4.1 means by tiers.

## Fixed camera for reviewing an asset

Three-quarter, eye height, 38° FOV: camera `(2.5, 1.72, 4.0)` looking at
`(0.2, 0.72, 1.1)` — the framing `npm test` writes to
`test/shots/03-desk.png`. Judge every module change against that shot before
anything else.

## The dispensing desk, as numbers

§11.1 step 3. One 0.90 m bay, repeated. All metres.

| | |
| --- | --- |
| bay width | 0.90 |
| worktop top | 0.95 |
| worktop | 0.055 thick, 0.94 × 0.70, 0.06 front overhang, bullnose lip 0.032 |
| carcass | 0.805 tall, 0.62 deep |
| kick | 0.09 tall, recessed 0.05 |
| stiles | 0.055 wide, full height |
| rails | 0.05 / 0.045 / 0.05 |
| drawers | 0.30 deep and 0.22 shallow |
| pulls | 0.30 × 0.030, standing 0.05 proud |
| label holders | 0.15 × 0.038 |
| upstand | 0.10 tall at the back |
| depth | 0.66 at scale 1.0, stretchable 0.85–1.4 |

Length is a **repeat** axis, not a stretch one: real dispensing furniture is
built from carcasses, and a repeated bay never distorts a texel (§1).
