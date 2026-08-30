# Reference gap: every object against its own concept sheet

Each module in the catalogue has a multi-view sheet in `docs/concept/views/`
and a written record in `docs/object-briefs.md`. This file is the third
thing: a side-by-side reading of the **rendered** object against the sheet
it was modelled from, asking one question per object — *why does it not
look like the reference, and what changes?*

Method: `npm run portraits` renders one framed shot per module; each is set
beside its sheet at matched height and read for silhouette first, then
value, then colour, then detail.

---

## The four faults that account for most of the twenty

Read individually, each object looks like a separate problem. Read
together, the same four things keep happening.

### 1. Colour drains out between the sheet and the render

This is the big one, and it was silently affecting a third of the
catalogue. The sheets are built from saturated flats — teal cupboard
doors, green locker doors, a cream tub, a beige-box CRT. In the renders
those same objects came out grey, black, orange and grey respectively.

Two causes, and they compound:

- **The module declared the wrong colour.** The sink unit had `steelDark`
  doors under a `steel` worktop, where the sheet is unambiguously teal
  doors under a pale top. Grey on grey collapses into one slab and the
  sink stops being the thing the object is named for.
- **Dark saturated colours land on the ramp's bottom step and go to
  black.** The locker doors were `tealDeep`, which on any face turned away
  from the key reads as black, not green. The sheet's doors are green on
  every face. `teal` survives the ramp; `tealDeep` does not.

The rule that comes out of it: **a colour that only reads on the lit face
is the wrong colour.** Pick the value that still says green in shadow.

### 2. Open frames where the sheet draws closed boxes

The sheets are built from solid volumes with things set *into* them. Several
modules were built as skeletons instead — posts and shelves with air
between them. The dispensary racking is the clearest: the sheet shows a
carcass with solid gables, a solid back and a top, shelves living inside
it. Ours is five boards on two thin uprights, which reads as flimsy and
throws no interior shadow. The consultation booth has the same problem more
severely — with no reading infill panels it looks like a canopy on legs
rather than a room you would go into.

### 3. Silhouette contaminated by parts behind the object

The pharmacy cross was a 0.78 m dark square plate sitting behind a 0.80 m
cross. Head-on it read correctly; from any other angle — which is every
angle the game is played at — the plate showed past the arms and the object
read as a dark square with a cross on it. The silhouette *is* the entire
job of that sign. The plate is now small enough to hide behind the arms.

### 4. Printed graphics modelled as geometry, at the wrong scale

The sheets carry a lot of information as flat print: a big label panel
across most of a carton's face, a dashed row of price windows the full
width of a shelf edge, a keypad where every saturated colour on the object
lives. Ours reproduced these as small geometry — a 7 cm speck on the
carton, two short windows on a shelf, four identical cream bars for a
keypad. At playing distance, print at the wrong scale is invisible; the
object loses the one feature that identifies it.

The stock box was the worst case and had a real bug behind it: the module
declared **no accent colours at all**, so its label fell through to a
default and rendered white.

---

## Object by object

Status key: **[fixed]** applied and re-rendered · **[open]** diagnosed, not
yet applied.

### Dispensing bench
Closest match in the set. The sheet's carcass sides are a cool grey against
the oak drawer fronts; ours are warm on warm, so the drawers do not separate
from the box they sit in. Its plinth is teal where the sheet's is dark
walnut. **[open]** Carcass sides to steel-grey, plinth to `espresso`.

### Vaccine fridge
**[fixed]** All wood removed; steel body, steel cap, dark grille at the foot.
**[open]** The door still reads as opaque grey metal where the sheet shows a
*pale* glass you can see stock through — the `glass` accent is too dark and
too reflective for a lit interior. The sheet also puts the temperature
readout at the top-left of the door, high and visible; ours sits low on the
surround. And the sheet's grille is a bold black louvred band across the
whole foot, where ours is a modest inset.

### CD cabinet
Reads as one near-black mass with a purple cast. The sheet contrasts a
**pale** cap and pale feet against the dark body — that contrast is what
makes it read as a safe rather than a fridge — and puts four coral keypad
squares in a 2×2 big enough to see. **[open]** Lift the cap and feet to
`paper`, enlarge the keypad, add the three visible hinge blocks the sheet
draws down the left edge.

### Consultation chair
**[fixed]** Reproportioned to the sheet's chunk. **[open]** One thing still
missing and it is the identifying feature: in the sheet there is an **open
gap between the seat and the back rest** — the back floats on the posts.
Ours has the back cushion sitting directly on the seat, which reads as an
armchair, not a contract chair.

### Consultation booth
The weakest match. The sheet is a solid little room: dark timber corner
posts, cream infill below waist height, big pale glazing above, a flat dark
roof with two vent boxes standing on it, and a full dark timber door.
Ours reads as an open canopy on legs, because the glazing is nearly
invisible and the infill panels do not hold. **[open]** Thicken and opaque
the lower panels on all four sides, give the glass a visible pale-cyan
value, add a real door leaf, stand the vent boxes on the roof.

### Dispensary racking
**[open]** Needs enclosure — see fault 2. Solid gables, back and top; the
shelves then sit *in* something. Label strips are already right.

### OTC counter
The sheet is a display counter: a big oak top with a deep overhang, an oak
customer shelf **projecting at the front** below it, dark bands separating
the levels, coral price marks. Ours reads as a flat oak lid on a cream box —
the projecting shelf and the bands are present but too small to register.
**[open]** Scale both up until the counter has three visible levels.

### Gondola shelving
**[fixed]** Gables and posts to cream (they were steel grey); the teal price
rail now runs the full bay width with four cream windows dashed along it,
where it was a short stub with two.

### Wall shelving
**[fixed]** Fat board and brackets. **[open]** The teal band on the front
edge still does not read, and in the sheet it is the loudest thing on the
object. Same full-width treatment as the gondola.

### Till / POS
**[fixed]** Shells to beige-box cream (they were steel grey, which made a
modern machine out of a deliberately retro one); the keypad is now coral
function keys, a green enter and dark number rows — on the sheet the keypad
is where every saturated colour lives and it is what says *till* rather than
*computer*. **[open]** Base unit and CRT are both a size small against the
sheet's proportions.

### Basket stack
**[open]** Proportion is wrong in plan: the sheet's basket is wide and deep —
the stack is wider than it is tall — where ours is narrow enough to read as
a stack of trays. The handle is a **cream arch** on two diagonal struts, not
a coral bar. **[fixed]** the wooden corner posts on a plastic shell.

### Offers dump bin
**[fixed]** Cream tub with a teal rim on an oak pallet. It had been an oak
tub, so the pallet and the bin were the same material and the object had no
parts.

### Queue barrier
**[fixed]** Heavier caps, plinths and rails; drawn shadow line and paper
notice removed. **[open]** The teal inset panel on each post is not on the
sheet — the sheet has a small dark window there instead.

### Pharmacy cross
**[fixed]** Back plate shrunk to hide behind the arms; the silhouette is a
cross from every angle now. **[open]** The face is paler than the sheet's,
which keeps a strong dark green border all the way round the lit panel.

### Staff lockers
**[fixed]** Doors to `teal`; they were `tealDeep` and rendering black.
**[open]** The number plates and vent slots are smaller than the sheet's and
do not read; the dark plinth under the carcass is missing.

### Filing cabinet
Body colour and sloped-lighter top are right. What is missing is the
**seams**: the sheet separates four drawers with dark reveals, so it reads
as four drawers. Ours is one grey box with pull blocks on it. **[open]** Add
the reveals, widen the label plates.

### Aisle sign
The sheet is a deep dark tray with an oak panel set well inside it and
**one** wide cream lettering band across the middle. Ours chops the panel
into horizontal stripes — a shadow band, a lettering band, a detail band and
two coral marks — so it reads as a venetian blind. **[open]** Delete the
extra bands, make the lettering band tall and full width.

### Stock boxes
**[fixed]** The module declared no accent colours, so the label rendered
white by fallback. It now has a proper palette and a printed mint panel with
coral marks across most of the front face. **[open]** The panel could still
go larger; the sheet's covers nearly the whole face.

### Sink unit
**[fixed]** Doors to teal. **[open]** The tap is a stub where the sheet
draws a tall gooseneck — a vertical column with a horizontal spout, and it
is the thing that says *sink* from across the room. The basin well is `ink`
purple where the sheet's is a pale steel recess.

### Waste & sharps
Good match. **[open]** The sheet puts a single clean cream box on top;
ours splits it into two blocks with dark caps.

---

## What this changes about how the catalogue is built

Two rules to add to the one already in `object-briefs.md` ("if you cannot
write down why it is there, it does not go on the model"):

1. **Pick colours that survive the dark end of the ramp.** Check a saturated
   colour on a face turned away from the key before committing it.
2. **Print is a big flat area, not small geometry.** If the sheet carries
   information as print, model it at the scale the sheet draws it — full
   width, most of the face — or leave it off.
