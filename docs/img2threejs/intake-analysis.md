# Intake analysis — `docs/concept/shape-reference.png`

img2threejs stage 1. Layers follow `grimoire/intake/image_analysis.md`; the
verdict follows `grimoire/intake/validation_rubric.md`. Observation is kept
separate from inference throughout, and inference is marked.

## Technical probe

`forge/stage1_intake/probe_image.py` → `technicalSuitability: pass`,
1408×768, aspect 1.83. **Reported type: JPEG**, despite the `.png` name — the
image API returns JPEG bytes whatever the file is called. Not disqualifying for
a shape reference (this one is measured, never sampled), but it is why the
sibling texture atlas needed `tools/authoring/pixelate.py` before use.

## Layer 1 — identification

Work type: **pharmacy dispensing counter assembly**. Broad classification:
*furnishing*. `primaryDomain`: `object`. Confidence 0.9.

Not a single atomic prop: it is a U-shaped counter run plus a back-wall
shelving unit plus loose props (till, lamp, stool, mortar, papers). That
distinction drives the verdict below.

## Layer 2 — overall form & silhouette

Bounding volume: a wide, shallow cuboid footprint with a tall thin cuboid
standing at the rear-left. Footprint is a **U** open toward the viewer's left
rear — three counter runs meeting at two right angles.

Symmetry: **asymmetric**. Shape language: **geometric**, entirely
axis-aligned boxes. No curve anywhere except the mortar bowl and the lamp
shade, both of which are props rather than structure.

Proportion: counter height reads ~0.95 m against the stool beside it; the back
shelving is roughly 2.2× counter height.

## Layer 3 — macro → meso → micro

- **macro**: counter run A (front, long) · counter run B (left return) ·
  counter run C (rear) · back shelving unit · loose props
- **meso** (per counter run): worktop slab · carcass · drawer bank · door
  bank · kick recess · fascia sign panel
- **micro**: drawer pulls · door pulls · panel seams · the green cross plaque ·
  the lettered fascia · shelf label strips

## Layer 4 — spatial relationships

- `<worktop, rests-on, carcass>` — overlap contact, oversailing on the front
  edge
- `<drawer bank, embedded-in, carcass>` — embed, flush front
- `<back shelving, attached-to, rear wall>` — butt; *inference*: free-standing
  against a wall rather than wall-hung, since a plinth is visible
- `<till, rests-on, worktop>` — butt
- `<cross plaque, embedded-in, front fascia>` — embed, proud by ~1 texel

## Layer 5 — materials & surface

| Part | Material | Notes |
| --- | --- | --- |
| carcass, doors, shelving frame | painted metal, muted green | dielectric, mid roughness, flat |
| worktop, drawer fronts, stool | warm wood | dielectric, visible plank direction |
| pulls | metal, warm brass-ish | small, low-value |
| jars / bottles | glass + paper labels | semi-translucent read, but drawn opaque |

No specular highlights are painted in; the sheet is albedo-only with flat
shading, which is what the prompt asked for and what makes it usable.

## Layer 6 — colour & finish

Two families, both mid-value and low-saturation: muted sage green (cabinetry)
and warm mid-brown (timber). Accents are small and few — a saturated green
cross, brass pulls, a handful of coloured bottle labels. Finish: **matte**
throughout. No gradients; values step.

## Layer 7 — identity-defining features

1. The **green cross plaque** on the front fascia — the single mark that says
   pharmacy from across a room.
2. The **lettered fascia panel** ("PHARMACY") on the front run.
3. The **stocked apothecary shelving** behind — rows of small jars.
4. The **mortar and pestle** on the worktop.

Each becomes a `detailInventory` entry; 1 and 2 are `featureReviewTargets`
because both are easy to get wrong and both are load-bearing for recognition.

## Layer 8 — uncertainty & single-image limits

- **hidden**: the entire back of the shelving unit; the inside faces of the two
  far counter runs; the underside of every worktop.
- **occluded**: the lower half of counter run C, behind run A.
- **uncertain**: whether the fascia lettering is painted or a mounted plate.
- **needs another view**: the right-hand end of run A leaves frame at the
  bevel — its return is not visible.

None of these blocks a reconstruction; all are inferable as boxes.

## Verdict — CONDITIONAL

Against the rubric it passes on every *Pass* criterion (one target, fills the
frame, strong silhouette, materials visible, procedurally approximable) except
one, and fails one *Reject* criterion partially:

> "photo is a scene, not an object reference"

It is an **assembly**, not a single object — counter runs plus shelving plus
loose props. Under `Conditional` it qualifies on "some occlusion but macro
shape is clear" and "fine surface detail can be represented with procedural
texture".

**Route taken:** reconstruct the *dispensing counter run* as the target object
and treat the shelving and loose props as out of scope for this factory. That
is the honest reading for this project, because the counter run is the thing
that needs to be modular and resizable, and the shelving and props already
exist as separate catalogue modules (`dispensary_shelving`) and decor props
(`mortar`, `terminal`, `desk_lamp`, `paper_stack`) that the spawner places.

Rebuilding the whole assembly as one rigid factory would produce an object
that cannot be resized meaningfully and would duplicate three modules that
already exist.
