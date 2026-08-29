# Concept sheet prompts

§11.1 step 2. Ready-to-paste prompts for generating orthographic concept sheets
before a module is modelled or revised.

**These are for you to run, not the build.** Per §11 the generation service is a
desktop authoring tool: never a build, CI or runtime dependency, and the only
thing that comes back into the repo is a decision written down as numbers. The
brief names Nano Banana 2 (`gemini-3.1-flash-image`) for this because its
reference-consistency across many objects is what keeps a catalogue coherent —
feed the approved sheet for the dispensing bench back in as a reference image
for every module after it.

## How to use the output

1. Generate front, side and three-quarter views.
2. Judge **shape only**. Proportion is what a concept sheet is for; texture and
   colour are already settled by `style-bible.md`.
3. **Read the numbers off the sheet** — height, depth, overhang, kick recess,
   rail widths — and write them into the module's table in `style-bible.md`.
4. Rebuild parametrically: edit the `build()` part list in
   `src/modules/catalogue/`. The generated image is never imported.

Nano Banana output carries an invisible SynthID watermark and C2PA credentials
(§11.2). Not a problem for reference images you never ship, but know it is there.

## The style block

Every prompt below is prefixed with this. Do not paraphrase it between modules —
consistency across the catalogue comes from the prefix being identical.

```
Orthographic front, side and three-quarter views of {SUBJECT}, laid out in a row
on a plain flat background, evenly spaced, all three at the same scale.

Style: cute pixelated low-poly game asset. Chunky, slightly squat proportions.
Softly bevelled corners, not sharp and not rounded — a visible small chamfer.
Low texel density, so surfaces read as visible pixels. Simple readable
silhouette with a small number of large forms plus two or three small identifying
fittings.

Flat lighting, albedo only, no shadows, no baked highlights, no ambient
occlusion, no outlines.

Palette, use only these: cream #f9efdc, bone #ecdcc0, warm oak #dda265,
dark oak #b0763e, walnut #835531, mint #9ad9b8, teal #57a98d, deep teal #356f5e,
coral #f28b60, steel #b0bcbd, dark steel #77868a, pale glass #d2e8e4,
plum #413353.

No text, no labels, no logos, no watermarks, no people, no props other than the
subject itself.
```

## Per module

Substitute for `{SUBJECT}`. The identifying fittings are listed because they are
what the sheet must resolve — the rest of the shape is a box and needs no help.

### Dispensary

| Module | `{SUBJECT}` |
| --- | --- |
| Dispensing bench | a single pharmacy dispensing bench bay, 0.9 m wide, with a thick overhanging worktop with a rounded front lip, a low back upstand, two stacked drawers of different depths with long horizontal pull handles and small label holders, framed by vertical side stiles and horizontal rails, on a recessed kick plinth |
| Dispensary racking | one bay of shallow pharmacy dispensary shelving, open-fronted, with a thin label strip running along the front edge of each shelf and a small vertical divider at the back |
| CD cabinet | a small steel controlled-drugs cabinet, floor standing on a plinth, one solid door with no glass, three heavy barrel hinges down one side, a keypad lock, a stubby vertical handle and a small warning plate near the top |
| Vaccine fridge | an upright pharmacy vaccine fridge with a full-height glass door, a slim vertical handle, horizontal rails top and bottom of the door, a small digital temperature readout above the door, and a condenser grille along the bottom |
| Sink unit | a stainless dispensary sink unit, one recessed rectangular basin set into a worktop, a tall mixer tap column with a single lever, two cupboard doors below, a recessed kick |
| Waste & sharps | a pedal-operated clinical waste bin with a coloured lid, a foot pedal and visible linkage rod at the base, a hazard plate on the front, and a small separate sharps box sitting on the lid |

### Retail floor

| Module | `{SUBJECT}` |
| --- | --- |
| Gondola shelving | one bay of free-standing retail gondola shelving, open both sides, a flat shelf board, two slim end posts, a back panel, and a price rail along the front edge of the shelf |
| Wall shelving | one bay of wall-mounted retail shelving, a single shelf board on two small triangular brackets, a slim back rail, and a price strip on the front edge |
| OTC counter | a pharmacy over-the-counter serving counter, a plain carcass with a thick overhanging worktop, a horizontal drawer band with a continuous pull rail across the front, a lower customer shelf projecting from the front face, on a recessed kick plinth |
| Till / POS | a small retail point-of-sale unit, a flat base, an angled screen on a short neck, a keypad on the base, and a small card reader on a short stalk beside it |
| Basket stack | a stack of five nesting plastic shopping baskets, open topped, with a folding handle bar across the top of the topmost basket |
| Offers dump bin | a free-standing retail promotional dump bin, a square open-topped bin with a thick rim, on a low base, with two slim posts at the back carrying a rectangular header card above it |
| Queue barrier | a retail queue barrier, two square posts with small square feet and one horizontal rail between them near the top |

### Consultation

| Module | `{SUBJECT}` |
| --- | --- |
| Consultation booth | a small free-standing pharmacy consultation booth, two solid walls meeting at a corner with a glazed upper panel in each, a door opening on the third side with a heavy door post and a header, a flat roof cap, a skirting at the base, and a small sign panel above the door |
| Consultation chair | a simple consultation chair, a padded seat and padded back with piping around the edges, on four slim square steel legs with a stretcher between the front pair |

### Staff

| Module | `{SUBJECT}` |
| --- | --- |
| Staff lockers | one bay of a two-tier steel staff locker, an upper and a lower door, three horizontal vent slots near the top of each door, a stubby vertical handle and a small number plate on each door, a plinth at the base, and a sloped crown on top |
| Filing cabinet | a four-drawer steel filing cabinet, each drawer with a recessed horizontal pull and a small label holder, a plinth at the base and a thin top cap |

### Signage

| Module | `{SUBJECT}` |
| --- | --- |
| Pharmacy cross | a wall-mounted illuminated pharmacy cross sign, a thick equal-armed cross on a square back plate, an inset lit face on the front of each arm, and a short stalk behind holding it off the wall |
| Aisle sign | a hanging retail aisle sign, a rectangular panel with a lettering band across it, a top rail, and two slim drop rods above it |

## Props

Props are small enough that a single sheet covering the set is more useful than
one each. Same style block, then:

```
{SUBJECT}: a row of small pharmacy counter props, evenly spaced, all at the same
scale, each shown three-quarter: a stack of loose paper; a clipboard with a
metal clip; a mug with a handle; a pot of pens; a roll of till paper with a
paper tail; a small counter weighing scale with a display; a pestle and mortar;
a stapled paper prescription bag; an angled desk lamp; a stack of ring binders;
a white cardboard dispensing pack with a printed label panel; an amber glass
bottle with a white cap and a label; a stacking plastic tote.
```

## When the sheet disagrees with the build

The sheet wins on proportion; the numbers table in `style-bible.md` is the
record of the decision. If a sheet asks for something the part system cannot
express — a curve, a taper, a genuinely non-boxy form — that is worth knowing
too: it is the signal to either simplify the design or extend `geometry.js`,
and §11.1 is explicit that a shape you cannot describe numerically is the one
case where image-to-3D earns its place.
