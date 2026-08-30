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
it. Ours was five boards on two thin uprights, which read as flimsy and
threw no interior shadow. The consultation booth had the same problem more
severely — no front wall at all, and then, once it had one, full-height
opaque walls that hid their own glazing on the inner face.

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

Everything below is applied and re-rendered. Status is kept because the
*reason* is the useful part — it says what the sheet was asking for.

### Dispensing bench
The sheet's carcass sides are a cool grey against the oak drawer fronts;
ours were warm on warm, so the drawers never separated from the box they sit
in. Its plinth is dark walnut where ours was teal — on a warm object the
plinth is the shadow the whole thing stands in, and a saturated colour down
there competes with the pulls for the one accent the object gets. Carcass to
`steelDark` on the new NEUTRAL slot, plinth to `espresso`.

### Vaccine fridge
All wood removed earlier; steel body, steel cap, dark grille. The door then
still read as opaque grey metal where the sheet shows a *pale* glass you see
stock through — the glass slot was too dark for a lit interior, and is now
mint. The readout moved to the door head, at eye level, where you would
actually read it. And the grille is now a bold louvred band across the whole
foot: on the sheet it is the second-strongest mark on the object after the
door, where ours was a modest inset two-thirds the width.

### CD cabinet
Read as one near-black mass. The sheet contrasts a **pale** cap and pale
feet against the dark body, and that contrast is what makes it a safe rather
than a fridge — the cage is now `paper`. The keypad was a 10 cm plate of
1.6 cm bands, i.e. invisible; it is now four coral squares you can count
across the room.

### Consultation chair
Reproportioned earlier. The identifying feature was still missing: in the
sheet there is an **open gap between the seat and the back**, the back
floating on its posts. Ours had the back cushion sitting straight down on the
seat, which reads as an armchair. The back now starts 9 cm higher.

### Consultation booth
The weakest match in the set, and it took two goes. It had no front wall at
all, so it was open on the side you look at it from and read as a canopy on
legs. Adding the wall was not enough: all four walls were full-height opaque
with a glass panel stuck on the *inner* face, which from outside is
invisible, so it then read as a solid shed. The walls are now **split** —
solid infill to waist height, glazing above — which is the object's entire
privacy logic and has to be on the faces people see. And there is a door
leaf: there had been a door post, a door head and two hinges hung on nothing.

### Dispensary racking
The sheet draws a carcass — solid oak gables full depth with the shelves
living inside it. Ours was two thin cream posts, so it read as an open cage
with boards floating in it and threw no interior shadow. Gables now, in the
same timber as the shelves, because it is one piece of joinery.

### OTC counter
The sheet is a display counter with three levels you can count: oak top, a
dark band under it, an oak customer shelf projecting well out in front. Ours
had all three, but the shelf was 4.5 cm thick and barely cleared the carcass,
so it read as a flat lid on a cream box. Thicker, and standing 22 cm proud.

### Gondola shelving
Gables and posts to cream (they were steel grey); the teal price rail now
runs the full bay width with four cream windows dashed along it, where it was
a short stub with two.

### Wall shelving
Fat board and brackets earlier. The teal band — the loudest thing on the
object in the sheet — was thin and short and lost against the board above it;
same full-width dashed treatment as the gondola.

### Till / POS
Shells to beige-box cream (steel grey made a modern machine out of a
deliberately retro one). The keypad is coral function keys, a green enter and
dark number rows: on the sheet the keypad is where every saturated colour
lives and it is what says *till* rather than *computer*. Base and CRT were
both a size small against a sheet that draws a machine dominating its
counter, and are now bigger.

### Basket stack
On the sheet a basket is wide and deep — the stack ends up broader than it is
tall — where ours was narrow enough to read as a pile of trays. And the
handle is a **cream arch on two struts**, not a coral bar laid across the top;
it is the part that reads first.

### Offers dump bin
Cream tub with a teal rim on an oak pallet. It had been an oak tub, so the
pallet and the bin were the same material and the object had no parts. Its
header card is cream, not oak.

### Queue barrier
Heavier caps, plinths and rails; the drawn shadow line and the paper notice
removed. The 56 cm teal stripe down each post is now the small dark window
the sheet has — the stripe was a second saturated colour competing with the
oak, on an object whose whole job is to be ignored.

### Pharmacy cross
The back plate was 0.78 m behind a 0.80 m cross, so from every angle but
head-on it read as a dark square with a cross on it; it now hides behind the
arms. The pale glow surround had also eaten most of the face, leaving a thin
green edge — narrower now, so the deep green border reads.

### Staff lockers
Doors to `teal`; they were `tealDeep` and rendering black. The vent stacks
and number plates were drawn at the size a real locker has them, which at
playing distance is nothing — both are now sized to be read, on a heavier
dark plinth.

### Filing cabinet
A 16 mm reveal between drawers is invisible, so the cabinet read as one grey
box with handles stuck on it. The reveal is the seam that does the
identifying and now has the width to do it.

### Aisle sign
The panel had been sliced into four horizontal stripes — a shadow bead, a
lettering band, a detail band and two coral marks — which at any distance
reads as a venetian blind. The sheet is an oak panel with a single wide cream
band and one coral mark at the end of the line.

### Stock boxes
The module declared **no accent colours at all**, so its label fell through to
a default and rendered white. It now has a palette and a printed mint panel
with coral marks across most of the front face.

### Sink unit
Doors to teal — grey doors under a grey top collapsed into one slab. The tap
was a stub where the sheet draws a tall gooseneck, which is the thing that
says *sink* from across the room: a column, a long arm out over the basin and
a drop at the end. The well was `ink`, a purple-black that read as a void
punched through the worktop, and is now a pale pressed recess.

### Waste & sharps
The sheet has a single clean cream sharps box sitting square on the lid; ours
was a box plus a dark capped aperture offset to one side, reading as two
half-objects.

---

## Three bugs the pass turned up in the systems themselves

None of these are art. All three have the same shape: **a change that
silently does not happen.**

- **The accent chain aliased out-of-range indices.** The shader picks an
  accent with a descending chain of comparisons, so an index past the top
  slot landed on the top slot rather than failing. I wrote `accent: 5`
  before the fifth slot existed and got a plausible wrong colour, not an
  error.
- **`rotZ` was never read.** `buildParts` handled `rotX` only. The basket's
  angled handle struts were written and simply did not rotate.
- **The catalogue needed a fifth colour.** Two sheets want a cool grey that
  is neither the frame nor a shadow — a bench carcass behind warm drawer
  fronts, a pressed steel sink well — and four slots could not express it.

So: `NEUTRAL` (slot 5) added through the shader and every call site; `rotY`
and `rotZ` added to `buildParts`; and `validateRegistry` now rejects an
out-of-range accent by number, a NEUTRAL used without an `accent5`, and any
part key it does not recognise. That last one is the general fix — the
unknown-material check already existed for exactly this reason, and these
were the same failure wearing different clothes.

## What this changes about how the catalogue is built

Two rules to add to the one already in `object-briefs.md` ("if you cannot
write down why it is there, it does not go on the model"):

1. **Pick colours that survive the dark end of the ramp.** Check a saturated
   colour on a face turned away from the key before committing it.
2. **Print is a big flat area, not small geometry.** If the sheet carries
   information as print, model it at the scale the sheet draws it — full
   width, most of the face — or leave it off.
