# Part-by-part build record

The rule: **no part gets modelled or textured until its analysis is written
here.** Every earlier pass on this object failed the same way — I built the
whole cabinet from a general impression, then chased symptoms across twenty
boxes at once (a bevel on every face, then no bevel anywhere, then a grille
that moiréd, then a back that showed the cavity). Analysing one part at a
time and finishing it is slower per part and far faster overall, because a
mistake is contained to the part that caused it.

Sources, and nothing else:
- **Geometry** — the reference's FRONT / SIDE / BACK / ISO views, plus the
  FINAL IMMUTABLE COORDINATE TABLE where the two agree. Where they disagree
  the drawn views win, and the disagreement gets recorded.
- **Texture** — the atlas only. If a part needs a mark the atlas does not
  have, the atlas gains it; the part never gets a bespoke material.

Render the same four views with `?view=front|side|back|iso` and compare.

---

## The adaptive texture toolset

Every surface declares how it survives a size change. These are the only
tools; a part that needs something else means the toolset is missing a mode,
which is a change to `main.js`, not a special case in the part.

| tool | manifest | what it does | use for |
|---|---|---|---|
| **nine-slice** | `corner: N` | outer N texels of the patch are FIXED at every size; the middle fills the rest | every panel: the outline, catch, inset plate and corner bolts stay native |
| **tile** | `tile: [1,1]` | the middle repeats | fields that should grow more of themselves |
| **clamp** | `tile: [1,0]` etc. | the middle holds ONE line, no repeat | an axis whose pattern must not recur — a plain band, the grille's fixed slot rows |
| **crop / decal** | no `corner` | patch maps 1:1 in texels, never repeats; `decalBox()` sizes the geometry FROM the atlas | display, bolts — things with a true pixel size |
| **plate off** | `panel=False` in the atlas | outline + catch only, no inset frame | parts too small or too thin to be a pressed plate |

Two constraints fall out of this and are not negotiable:

1. On an axis that **clamps or does not tile**, the patch's pixel size *is*
   the part's world size (`px / texelsPerUnit`).
2. **Texel density must match render density.** The sheet is 8 texels/unit and
   the renderer draws 8 px/unit. Break this and fine detail aliases.

---

## Part index

Built bottom-up, the way the object stacks. Status: ☐ not started ·
◐ analysed · ☑ built and checked against the reference.

| # | part | status |
|---|---|---|
| P01 | Feet | ☑ |
| P02 | Plinth strip | ☑ |
| P03 | Condenser base | ☑ |
| P04 | Condenser grille | ☑ |
| P05 | Base corner blocks | ☑ |
| P06 | Carcass sides | ☐ |
| P07 | Back panel | ☐ |
| P08 | Corner posts | ☐ |
| P09 | Cavity liner | ☐ |
| P10 | Shelves | ☐ |
| P11 | Door outer frame | ☐ |
| P12 | Door inner frame | ☐ |
| P13 | Glass | ☐ |
| P14 | Handle | ☐ |
| P15 | Crown | ☐ |
| P16 | Display | ☐ |

---

## P01 — Feet (×4)

**Geometry.** FRONT shows two dark purple blocks at the extreme bottom
corners, each roughly a sixth of the cabinet width and standing about 4 units
tall; ISO confirms four of them, one per corner, and that they are the only
thing touching the floor. They sit *proud of the base on both plan axes* —
in ISO the foot's outer face is flush with the base's outer face, not inset.
SIDE shows the same two-per-side arrangement, so they are corner blocks and
not a front rail.

Extents: `x` 6 units in from each end, `y` 5 units deep at each end,
`z` −1.5 → 3.5.

**Texture.** Surface `plinth`. Nine-slice; at 6×5 units (48×40 texels) both
axes are entirely inside the 20-texel ring, so the whole foot is "corner" —
outline and catch on every face and no tiling at all. Correct: a foot is too
small to be a pressed plate.

**Adapts.** The feet *move* with width, they never scale. Their offset from
each end is a constant, so a wider cabinet gets the same four feet further
apart — which is what a real cabinet does.

## P02 — Plinth strip

**Geometry.** A thin purple band running the full width between the feet,
visible in FRONT as a continuous line and in ISO as a shallow step under the
teal base. It is inset from the base's face, so the base overhangs it.

Extents: `x` ±(H−2), `y` ±13, `z` 0 → 4.

**Texture.** Surface `plinth`. `tile: [1, 0]` — it tiles along its length so
a longer cabinet grows more band, and **clamps** vertically because at 4
units tall a repeating vertical pattern would show a seam mid-band.

**Adapts.** Length tiles; height is fixed by the object.

## P03 — Condenser base

**Geometry.** The mid-teal block the cabinet stands on, from the plinth up to
the carcass. FRONT and ISO agree it is about 15% of total height. Its front
face carries the grille (P04) and its top corners carry the cream blocks
(P05). BACK shows a plain teal panel with a recessed rectangle — the same
inset plate the atlas already draws, so no extra geometry is needed for it.

Extents: `x` ±(H−2), `y` ±14, `z` 4 → 18.

**Texture.** Surface `teal`, full nine-slice, `tile: [1, 0]`. Tiles on
length; clamped vertically so the inset plate reads as ONE plate the height
of the base rather than a stack of repeats.

**Adapts.** Width tiles, so the plate frame stays a constant border and the
field between grows.

## P04 — Condenser grille

**Geometry.** A tan louvred panel inset into the base's front face, spanning
most of the width and centred. FRONT shows continuous horizontal slots with
tan end caps; the kit sheet confirms "END CAPS (FIXED) + SLOTS (TILEABLE
HORIZONTAL)".

Extents: `x` ±(H−7), `y` −15.2 → −14, `z` 8 → 11.

**Texture.** Surface `grille`, `tile: [1, 0]`. The patch is 48×24 px, so at 8
texels/unit the part **must** be 3 units tall — constraint 1 above. Slots run
through the corner ring so they join across tiles into continuous lines.

**Adapts.** A wider base gets MORE slot length, with the end caps unmoved.
Height cannot change without re-authoring the patch.

## P05 — Base corner blocks (×4)

**Geometry.** Small cream blocks capping the base's top corners, clearly in
FRONT (two pale squares either side above the grille) and ISO. They are what
stops the base reading as a plain slab the cabinet stands on.

Extents: 3 units in `x`, 4 in `y`, `z` 13 → 18.

**Texture.** Surface `cream`, all-corner like the feet.

**Adapts.** Move with width; never scale.
