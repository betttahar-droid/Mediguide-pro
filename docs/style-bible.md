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

## What the reference actually does

Nine rules, each of which is now a line in `tools/authoring/make_textures.py`
or in a module's part list.

1. **The light is painted in, not lit.** Every board, panel and plate carries a
   vertical gradient — lighter at the top, darker at the bottom — baked into the
   albedo. Our toon ramp then lights that again, which is why the sheets are
   authored as luminance and the ramp is kept gentle.
2. **Every groove has a bright lip.** The single most repeated mark in the
   reference: a dark core with a near-white lip on one side. It is what makes a
   flat plane read as two boards.
3. **Grain is few, long and confident.** Six to nine tapered streaks per board,
   not noise. Noise reads as dirt; strokes read as paint.
4. **Knots are drawn deliberately** as squashed concentric rings with a dark
   core, one or two per board, never evenly spaced.
5. **Joints are staggered.** Aligned butt joints turn a plank sheet into a tile
   grid instantly — the first version of our trim sheet made exactly this
   mistake.
6. **Fittings are ornament.** Bolts, corner plates, label rails and pulls are
   what separate "a box" from "a piece of furniture". They live on the trim
   sheet's detail strip and on small dedicated parts.
7. **Chunky, slightly squat proportions.** Fat corner radii, a thick worktop, a
   deep overhang. A correctly-proportioned realistic desk looks realistic.
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
- Toon ramp: 4 steps, terminator wrapped past halfway

## Fixed camera for reviewing an asset

Three-quarter, eye height, 38° FOV: camera `(2.6, 1.35, 4.3)` looking at
`(0.2, 0.58, 1.1)` — the framing `npm test` writes to
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
