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
  a convex corner lightens and a crevice darkens in the albedo itself, so forms
  separate by value rather than by line. The strengths are 0.34 and 0.34 — they
  were higher, and came down when the catalogue's part counts doubled and the
  masks started covering most of every surface.
  `Look dev → Outlines → enabled` puts the ink back.

## The frame rule

The twenty sheets in `docs/concept/` were generated from one prompt prefix, and
what they turned out to share is more useful than any single one of them:

> **A light frame around darker panels.** Corner posts, stiles, rails and a
> tray-like top cap in the pale colour, standing *proud*; the body panels
> darker and set back between them.

Nothing else moved as many objects as far. The staff lockers had it exactly
backwards — mint carcass, dark doors flush with it — and inverting them is the
whole finding in one module. The CD cabinet is a grey box until it becomes a
pale steel cage with near-black panels dropped into it.

The same handful of fittings recurs on nearly every sheet, so they live in
`catalogue/fittings.js` and a part list calls them rather than retyping them:

| Fitting | What it does |
| --- | --- |
| `studs` | four corner bolts on a face — the mark that says a panel is *fixed to* a frame |
| `vents` | a stack of slots; says manufactured steel rather than box |
| `plate` | a pale window in a darker surround: labels, readouts, notices |
| `keypad` | a plate with three key rows — three read as a keypad, twelve read as noise |
| `capTray` | a light rim with the body inset: a lid sitting on a carcass |
| `posts` | the four proud corner posts, i.e. the frame rule itself |
| `worktop` | a top with a darker band under its front lip |

Two of those deserve their reasoning written down. **The keypad is three rows,
not twelve keys**, because at 1.5 cm a key is one texel. **The worktop band**
does the job the outline pass used to: it separates the top plane from the
carcass front by value, at exactly the line where the two meet.

A module's `colors` block fills five slots — body, frame, accent, dark, glass —
and the discipline is that each slot does *one* job in that module, so the frame
never drifts into the panels. The slot *names* are the usual role, not a law:
the gondola spends its "dark" slot on warm oak shelf boards and says so.

### What it cost, and what paid for it

Every module roughly doubled its part count. Two things had to move with it:

- **The AO bake stopped being quadratic.** It raycast every vertex against every
  triangle, so twice the parts meant four times the work. Rays are at most
  `radius` long, so `bakeMasks` now buckets triangles into a grid of exactly
  that cell size and only tests the 3×3×3 block around each vertex — provably
  every triangle a ray could reach, and nothing else.
- **The cavity tint came down.** A cool crevice tint that looked right on a
  plain box turned the whole room lilac once the geometry carried five times as
  much occlusion. `uCavityStrength` went 0.5 → 0.34 and both cool tints warmed.
  More geometry means less tint, not more.

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
| paper | `#f9efdc` | the light frame, nearly everywhere |
| wall | `#aed6c2` | walls — the room's cool half |
| bone | `#ecdcc0` | the stretched middle under paper |
| putty | `#d3c3a4` | — |
| oak | `#dda265` | drawer fronts, shelf boards, worktops |
| oakDark | `#b0763e` | the stretched middle under oak |
| walnut | `#835531` | booth frame, corner posts, dark bands |
| mint / teal / tealDeep | `#9ad9b8` `#57a98d` `#356f5e` | locker doors, price rails, plinths |
| signal | `#f5804f` | the one properly saturated accent; a few pixels at a time |
| steel / steelDark | `#b0bcbd` `#77868a` | steel frames, fittings, shadow bands |
| glass | `#d2e8e4` | fridge door, lit faces, label windows |
| floorTile | `#c9c2b2` | floor — the room's warm half |
| ink | `#413353` | outlines, hatching, the darkest fittings — never black |

## Shading

Four things carry the look, in order of how much they do. All of them live in
`shaders/chunks/toonLighting.glsl.js`.

1. **Hemisphere ambient.** Fill light is not one colour: cool `#d6e6f4` from
   above, warm `#f6e2c4` bounced off the floor, mixed on the world normal. One
   `mix()`, and every upward face picks up sky while every downward face picks
   up the room. It is the cheapest thing that stops flat shading looking flat.
2. **Coloured shadow.** The dark end of the ramp is tinted `#9c90a6`, not just
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
| Dispensing bench | Proud steel posts, oak drawer fronts, teal pulls, label holders, banded worktop |
| Dispensary racking | A cream label strip with a window on **every** shelf front, bay dividers |
| CD cabinet | Pale cage over near-black panels, three barrel hinges, keypad, warning plate |
| Vaccine fridge | Oak sides in a steel cage, glass in a pale surround, readout above the door, oak grille |
| Sink unit | A real basin *well* inside a raised rim, square mixer column and square spout |
| Waste & sharps | A cream belt across a mint body, front grille, pedal tray with the linkage rod visible |
| Staff lockers | Cream frame, deep-green doors set into it, vents, number plates, sloped crown |
| Filing cabinet | A fat cream pull block on each drawer with a dark label slot cut into it |
| Consultation booth | Walnut posts and door surround, cream infill under full glazing, mint skirting |
| Pharmacy cross | Three layers — steel rim, teal body, lit face inset — so the rim reads as glow |
| Till / POS | A fat CRT in a steel shell with an oak bezel, keypad, receipt slot, card reader |
| Offers dump bin | A pallet, not a plinth, under a deep-teal rimmed box |
| Queue barrier | Cream posts with teal insets, oak caps and plinths, two rails not one |
| Gondola shelving | End posts standing proud of cream panels, oak boards, a teal price rail |
| Wall shelving | A teal price rail with cream label windows punched along it |
| Aisle sign | An oak panel set deep into a steel frame, lettering band across it |
| Consultation chair | Fat tan cushions proud of a steel frame, piped, on visible brackets |
| Basket stack | Teal panels, cream rim rails, walnut corner posts |
| OTC counter | Cream carcass, oak top banded in dark oak, projecting customer shelf |

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
