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

The cluster that matters is the WoW / Albion / Aetherlight family: chunky
forms, warm woods, painted metal fittings, ink outlines.

## The look: pixel art, not painted

The style target is **pixelated low-poly** — Minecraft-ish texel density, chunky
voxel forms, hard edges, strong ink outlines, and enough small props that a
scene reads as lived in. That decision drives four things:

- **Sheets are tiny.** 128² trim and atlas, 64² floor and hatch. A texel lands
  near 2 cm in world space. Combined with `NearestFilter` on magnification,
  texels read as texels.
- **No blur, no antialiasing, no gradients.** Value steps and 4×4 Bayer
  dithering. A groove is one dark pixel with one bright pixel beside it.
- **Hard edges.** `EDGE_SOFTNESS` in `modules/geometry.js` scales every chamfer
  down to about a texel. The chamfer stays because the vertex-mask bake needs
  convex edges to find and the trim sheet's edge strip needs somewhere to land,
  but it reads as a crisp corner, not a rounded bevel.
- **Flat lighting.** A 3-step ramp, a weak rim, no cross-hatching by default.
  Pixel art gets its detail from texels; a soft shading gradient over them just
  muddies the palette.

## What the reference actually does

Nine rules, each of which is now a line in `tools/authoring/make_textures.py`
or in a module's part list.

1. **The light is painted in, not lit.** Every board, panel and plate is lighter
   at the top and darker at the bottom in the albedo itself — as a dithered band
   at this resolution. The toon ramp then lights that again, which is why the
   sheets are authored as luminance and the ramp is kept to three flat steps.
2. **Every groove has a bright lip.** The single most repeated mark in the
   reference: a dark core with a near-white lip on one side. It is what makes a
   flat plane read as two boards.
3. **Grain is few, long and confident.** Two or three dashed lines per board,
   with real gaps — never solid, never per-pixel noise. Noise reads as dirt.
4. **Knots are drawn deliberately** — at this size, an eight-pixel ring around a
   two-pixel core. One per board at most, never evenly spaced.
5. **Joints are staggered.** Aligned butt joints turn a plank sheet into a tile
   grid instantly — the first version of our trim sheet made exactly this
   mistake.
6. **Fittings are ornament.** Bolts, corner plates, label rails and pulls are
   what separate "a box" from "a piece of furniture". They live on the trim
   sheet's detail strip and on small dedicated parts.
7. **Chunky, slightly squat proportions.** A thick worktop, a deep overhang,
   heavy pulls. A correctly-proportioned realistic desk looks realistic.
8. **Wide value range, narrow hue range.** The grooves go near-black and the
   lips near-white; the hue barely moves. This is why the sheets are greyscale
   and `palette.js` supplies the colour.
9. **Ink is a drawn line, not a filter.** Dark, tinted toward the palette's
   shadow tone, never black.

## Palette

One source of truth: `src/art/palette.js`. No hex literals anywhere else.

| Role | Hex | Used on |
| --- | --- | --- |
| paper | `#f2e6d2` | gondola carcass, walls |
| bone | `#ded0b6` | worktops, upstands |
| putty | `#c4b294` | — |
| oak | `#c98f4e` | dispensing desk carcass and drawers |
| oakDark | `#9a6531` | desk trim middle |
| walnut | `#6b4325` | desk pulls, kick, queue barrier |
| mint / teal / tealDeep | `#7fbfa4` `#3f8a76` `#27594c` | serving counter, accents |
| signal | `#e0704a` | medicine boxes — the one warm signal colour |
| steel / steelDark | `#9aa6a8` `#5e6b6e` | till, fridge carcass, fittings |
| glass | `#bfd8d6` | fridge door |
| floorTile | `#b6bdb2` | floor |
| ink | `#2b1f33` | outlines, hatching — never black |

## Fixed light

One direction for the whole project, so separately-authored modules agree.

- Key: warm `#fff0d6`, azimuth 37°, elevation 53°, intensity 0.68
- Fill: cool `#a9c0dd`, from behind-left, intensity 0.28
- Rim: `#ffd39b`, suppressed on upward faces
- Ambient: slightly cool, 0.26
- Toon ramp: 3 steps, terminator wrapped past halfway
- Hatching off by default — it fights the texels

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
