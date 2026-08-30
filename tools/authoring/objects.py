#!/usr/bin/env python3
"""
The object briefs — one record per module, and the single source they all come
from.

Authoring tool. NOT a build, CI or runtime dependency.

    python3 tools/authoring/objects.py briefs              # write docs/object-briefs.md
    python3 tools/authoring/objects.py views dispensing_desk
    python3 tools/authoring/objects.py views --all --ref docs/reference/crop-*.png

WHY THIS EXISTS. Two details got into the catalogue that have no logic behind
them: a cream RAIL between the dispensing bench's two drawers, and WOOD on the
sides of a vaccine fridge. Both came from the same mistake — the concept sheets
share a "light frame around darker panels" rule, and it was applied mechanically
instead of being asked to justify itself per object. A bright bar between two
drawers of one carcass is not a thing that exists. A fridge that has to be
wiped down is not made of oak.

So every record here carries a WHY for each material and each fitting, and the
rule is: if you cannot write the why, it does not go on the model. That test is
the whole point of the file.

The same record also writes the image prompt, so the reference views and the
built model are asking for the same object rather than drifting apart — which
is how the fridge ended up wooden in the first place. And it records what the
module does when RESIZED, because that is half of what these objects are: they
are not props, they are furniture that grows.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concept_sheet import MODEL, generate_image, load_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VIEWS_DIR = ROOT / "docs" / "concept" / "views"

# The style block for MULTI-VIEW reference. Deliberately different from the hero
# sheet in concept_sheet.py: this one asks for orthographic elevations a person
# can measure, at LOW RESOLUTION, because the target is a low-poly retro game
# object and a beautifully rendered 4K sheet invites detail the engine cannot
# hold and the style does not want.
VIEW_STYLE = """\
Presentation: THREE VIEWS of the same object in one image, side by side on a \
plain flat background, evenly spaced, all three at exactly the same scale — \
FRONT elevation, SIDE elevation, and a three-quarter view. Straight-on \
orthographic for the two elevations, no perspective.

Style: low-poly retro video-game object, LOW RESOLUTION pixel art. Large \
visible pixels — the whole object should be readable at about 64 pixels tall. \
Hard square corners, no bevels, no rounded edges, no smooth curves. Every face \
is ONE FLAT COLOUR: no gradients, no soft shading, no highlights, no baked \
lighting, no drop shadow. Faces separate from each other by a clean step in \
value only — a lighter top, a mid front, a darker side.

Detail: a SMALL number of large shapes plus only the fittings named below. Do \
not add panel lines, screws, rivets, vents, labels or wear that are not named. \
Every mark must be something the object actually has.

Colour: use only this palette — cream #f9efdc, bone #ecdcc0, warm oak #dda265, \
dark oak #b0763e, walnut #6b4426, mint #9ad9b8, teal #57a98d, deep teal \
#24544a, coral #f5804f, steel #b0bcbd, dark steel #68777c, charcoal #39424a, \
pale glass #d2e8e4.

No text or lettering, no logos, no watermarks, no people, no background \
scenery, no props other than the object itself. Do NOT draw a user interface, \
a phone screen, a browser window, buttons or a website."""


def O(label, what, form, materials, fittings, resize, pops=None):
    return dict(label=label, what=what, form=form, materials=materials,
                fittings=fittings, resize=resize, pops=pops)


# materials:  part -> (material, why it is that material)
# fittings:   (name, why it earns its place)
# resize:     axis -> what physically happens
OBJECTS = {
    "dispensing_desk": O(
        "Dispensing bench",
        "The bench a pharmacist assembles a prescription on. It is the busiest "
        "surface in the building and it gets wiped down constantly.",
        "a pharmacy dispensing bench, one bay: a rectangular carcass on a "
        "recessed plinth, a thick worktop oversailing it on three sides, one "
        "deep drawer above one shallow drawer in the front, and a low upstand "
        "along the back edge",
        {
            "carcass and worktop": ("painted steel, cream", "it is wiped down "
                "many times a day; timber would not survive it and is not what "
                "dispensary furniture is made of"),
            "drawer fronts": ("warm oak", "the one warm surface, and the only "
                "part a hand touches all day — real dispensary benches use a "
                "timber front on a steel carcass for exactly that reason"),
            "pulls": ("deep teal painted metal", "the single saturated colour "
                "on the object, put on the thing you actually grab"),
        },
        [
            ("two drawers of different depths", "deep for boxes, shallow for "
                "labels and paperwork — the depth difference is the object "
                "telling you what goes where"),
            ("long bar pulls", "you open a drawer with a full hand, not a knob"),
            ("label holders", "every drawer in a dispensary is labelled, "
                "because picking the wrong drawer is a dispensing error"),
            ("recessed plinth", "your toes go there when you stand at it"),
            ("rear upstand", "stops a bottle rolling off the back"),
        ],
        {"x": "bays REPEAT — a run is built from 0.9 m carcasses, so a longer "
              "bench is more carcasses, never a stretched one",
         "y": "fixed — worktop height is ergonomic, not a choice",
         "z": "depth STRETCHES between 0.85 and 1.4, and only the middle of "
              "the carcass moves; the worktop lip and the drawer fronts stay "
              "the size they were authored"},
        "Work appears on the worktop as it grows: paper, a mug, a clipboard, "
        "scales, a mortar. At three bays or more it earns the equipment a short "
        "bench does not have — a terminal, a plant, a desk lamp.",
    ),
    "fridge_cabinet": O(
        "Vaccine fridge",
        "A pharmacy fridge holding vaccines between 2 and 8 °C. Getting that "
        "wrong destroys the stock, which is why it has a readout on the front.",
        "an upright vaccine fridge: a plain rectangular cabinet on a low "
        "plinth, a full-height glass door in a pale surround, a slim vertical "
        "handle, a small dark digital readout above the door, and a condenser "
        "grille across the bottom",
        {
            "body and door surround": ("painted steel, pale", "a medical fridge "
                "is a wipe-clean steel box — it had OAK SIDES, which was the "
                "frame rule applied without thinking and is simply not a thing"),
            "door": ("glass", "you check stock without opening it and warming it"),
            "readout": ("dark screen with a lit face", "a temperature display "
                "is a display, not a printed label"),
            "grille and plinth": ("dark steel", "the condenser is the one part "
                "that is bare metal, and it sits where the heat goes"),
        },
        [
            ("full-height glass door", "the identifying feature — you can see "
                "the stock, which is the whole point of a pharmacy fridge"),
            ("temperature readout", "the legal reason this cabinet exists "
                "rather than a cupboard"),
            ("condenser grille", "it has to reject heat somewhere"),
            ("slim vertical handle", "opened one-handed, many times a day"),
        ],
        {"x": "sections REPEAT — a bigger fridge is more cabinets side by side",
         "y": "fixed", "z": "fixed"},
        None,
    ),
    "cd_cabinet": O(
        "CD cabinet",
        "A controlled-drugs cabinet. Its shape is dictated by law: steel, "
        "fixed to the structure, double-locked, no glass.",
        "a small floor-standing steel security cabinet on a plinth: one solid "
        "door with no window, three heavy hinges down one side, a keypad, a "
        "short vertical handle, and a small plate near the top",
        {
            "body and door": ("near-black steel", "a security cabinet is heavy "
                "gauge steel and reads dark against everything around it"),
            "frame and cap": ("pale steel", "the cage the panels sit in"),
            "keypad keys": ("coral", "the only lit thing on a deliberately "
                "boring object"),
        },
        [
            ("three heavy hinges", "the legal giveaway — a CD cabinet is hung "
                "on more iron than a cupboard needs"),
            ("keypad", "double-locked is the requirement"),
            ("no glass anywhere", "an absence that identifies it as strongly "
                "as any fitting"),
            ("warning plate", "it is labelled because it has to be"),
        ],
        {"x": "cabinets REPEAT", "y": "fixed", "z": "fixed"},
        None,
    ),
    "sink_unit": O(
        "Sink unit",
        "Where measuring equipment gets washed. Wet all day.",
        "a stainless dispensary sink unit: a cabinet with two cupboard doors, "
        "a pressed steel top with one rectangular basin recessed into it, and "
        "a tall square mixer tap with a single lever",
        {
            "worktop, basin and tap": ("stainless steel", "one pressed piece — "
                "a seam at a wet joint is where water gets in"),
            "doors": ("painted steel", "wipe-clean, like the bench"),
        },
        [
            ("a real recessed basin", "a well with a rim, not a plate on top — "
                "water has to go somewhere"),
            ("square mixer column and lever", "elbow-operated; you do not "
                "touch a tap with contaminated hands"),
        ],
        {"x": "bays REPEAT", "y": "fixed", "z": "depth STRETCHES"},
        None,
    ),
    "waste_station": O(
        "Waste & sharps",
        "Clinical waste and a sharps box. Hands-free, because the contents are "
        "hazardous.",
        "a pedal-operated clinical waste bin: a squat body with a thick lid, a "
        "foot pedal on a projecting tray at the base with a visible linkage rod "
        "running up the back corner to the lid, a hazard plate on the front, "
        "and a small separate sharps box sitting on the lid",
        {
            "body": ("moulded plastic, mint", "it is a bin — moulded, not built"),
            "sharps box": ("cream plastic", "sharps boxes are a different, "
                "brighter colour on purpose so nobody confuses the two streams"),
            "pedal and linkage": ("dark steel", "the only mechanism on it"),
        },
        [
            ("foot pedal and a visible linkage rod", "hands-free is the reason "
                "this bin costs more than a bin, so the mechanism should show"),
            ("hazard plate", "clinical waste is labelled by law"),
            ("a separate sharps box", "sharps and soft waste never share a "
                "container"),
        ],
        {"x": "fixed", "y": "fixed", "z": "fixed"},
        None,
    ),
    "dispensary_shelving": O(
        "Dispensary racking",
        "The racking a dispensed item is picked from. Shallow so nothing hides "
        "behind anything, and labelled on every shelf.",
        "one bay of shallow open shelving: a simple frame of two uprights and "
        "a back panel, several shelf boards, a label strip along the front edge "
        "of every shelf, and one divider standing on each shelf",
        {
            "carcass and shelves": ("warm oak", "picking racking is joinery, "
                "not a wipe-down surface — it never gets wet"),
            "label strips": ("cream card in a holder", "paper labels, changed "
                "when the stock changes"),
        },
        [
            ("a label strip on EVERY shelf", "the identifying feature; an "
                "unlabelled dispensary shelf is a dispensing error waiting"),
            ("shallow depth", "one item deep so nothing is hidden behind"),
            ("dividers", "stops a row collapsing sideways when you pick from it"),
        ],
        {"x": "bays REPEAT", "y": "shelves REPEAT — add a shelf and you get "
              "another whole shelf, not a taller one",
         "z": "depth STRETCHES"},
        "Each shelf stocks itself with dispensing packs, amber bottles and "
        "totes as bays and shelves are added.",
    ),
    "serving_counter": O(
        "OTC counter",
        "The counter a customer stands at. The calm object in the room — the "
        "working furniture behind it carries the colour.",
        "an over-the-counter serving counter: a long plain carcass on a "
        "plinth, a thick timber worktop oversailing it, a row of drawer bays "
        "across the front each with its own pull, and a lower shelf projecting "
        "toward the customer",
        {
            "carcass": ("painted steel, cream", "calm, so the customer looks "
                "at the products and not the furniture"),
            "worktop and customer shelf": ("warm oak with a dark oak edge", "the "
                "one thing a customer touches; the dark edge is what separates "
                "the top plane from the front by value"),
        },
        [
            ("one pull per drawer bay", "a rail crossing four independently "
                "moving drawers is not a handle — each drawer gets its own, and "
                "a longer counter is more bays, not a stretched one"),
            ("a projecting customer shelf", "where a bag gets put down — it is "
                "the difference between a counter and a desk"),
        ],
        {"x": "bays SNAP in steps (1-4) — the drawer fronts, pulls and the "
              "reveals between them are rebuilt per step, while the worktop, "
              "shelf and plinth are cut longer; nothing stretches",
         "y": "fixed", "z": "depth STRETCHES"},
        "Props space themselves one every 0.55 m along the top, so a longer "
        "counter fills rather than spreading the same few items further apart.",
    ),
    "gondola_shelf": O(
        "Gondola shelving",
        "Free-standing retail shelving on the shop floor, open both sides.",
        "one bay of free-standing retail shelving: two slim end posts standing "
        "proud of the carcass, a back panel, flat shelf boards, and a price "
        "rail along the front edge of each shelf",
        {
            "carcass and back panel": ("painted steel, cream", "shop fittings "
                "are painted steel; cream keeps the products loudest"),
            "shelf boards": ("warm oak", "a warm ground for the stock to sit on"),
            "price rail": ("teal", "shop signage is meant to be seen"),
        },
        [
            ("end posts standing proud", "what stops a long run reading as one "
                "extruded slab — you can see where one bay ends"),
            ("a price rail per shelf", "retail law and retail practice: every "
                "facing has a price"),
        ],
        {"x": "bays REPEAT", "y": "shelves REPEAT", "z": "depth STRETCHES"},
        "Every shelf stocks itself with boxes and bottles as it grows.",
    ),
    "wall_shelving": O(
        "Wall shelving",
        "A bracketed wall run, at eye height.",
        "one bay of wall-mounted shelving: a single board on two triangular "
        "brackets hung from a slim wall rail, with a price rail along the front",
        {
            "board": ("warm oak", "matches the gondolas it faces"),
            "brackets and wall rail": ("steel", "it is carrying weight off a wall"),
            "price rail": ("teal with cream label windows", "the only saturated "
                "thing on it, and it reads across the room"),
        },
        [
            ("visible brackets", "wall shelving that appears to float reads as "
                "a mistake"),
            ("cream label windows punched along the price rail", "the identity: "
                "a run of little labels is what a shop shelf edge looks like"),
        ],
        {"x": "bays REPEAT", "y": "shelves REPEAT", "z": "fixed"},
        None,
    ),
    "till_block": O(
        "Till / POS",
        "The point of sale. A deliberately retro terminal, because the style is "
        "16-bit and a modern tablet till would have nothing to draw.",
        "a retro point-of-sale terminal: a low base with a keypad, a fat CRT "
        "monitor on a short neck tilted back slightly, a receipt slot in the "
        "front of the base, and a small card reader on a stalk beside it",
        {
            "monitor shell and base": ("cream plastic", "beige-box era plastic"),
            "bezel and receipt slot": ("warm oak-brown plastic", "the two-tone "
                "plastic of period hardware"),
            "screen": ("dark glass with a hard diagonal reflection", "a display "
                "is a dark rectangle with a reflection drawn on it, not a "
                "textured surface — this is the test case for the whole "
                "material system"),
        },
        [
            ("a fat CRT, not a flat panel", "depth is what makes it read as "
                "retro at all"),
            ("a real keypad", "the thing that says till rather than computer"),
            ("a receipt slot", "till roll has to come out somewhere"),
            ("card reader on its own stalk", "it faces the customer, so it is "
                "a separate thing pointing the other way"),
        ],
        {"x": "fixed", "y": "fixed", "z": "fixed — it sits on a counter"},
        None,
    ),
    "basket_stack": O(
        "Basket stack",
        "Shopping baskets by the door.",
        "a stack of nesting plastic shopping baskets, open topped, with a "
        "folding handle bar across the top one",
        {
            "baskets": ("moulded plastic, teal", "injection-moulded, so no "
                "joinery anywhere"),
            "rim rails": ("cream", "the moulded lip, which is what you see when "
                "they are stacked"),
        },
        [
            ("a visible rim on every basket", "when they nest, the rims are "
                "the only thing you can see — they ARE the object"),
            ("a folding handle bar on the top one", "how you pick one off"),
        ],
        {"x": "fixed", "y": "baskets REPEAT — a taller stack is more baskets",
         "z": "fixed"},
        None,
    ),
    "promo_bin": O(
        "Offers dump bin",
        "Stock dumped on the shop floor at a price. Deliberately temporary.",
        "a free-standing promotional dump bin: a square open-topped bin with a "
        "thick rim, standing on a wooden pallet, with one post at the back "
        "carrying a header card above it",
        {
            "bin": ("printed card and painted steel", "it is a display bin, not "
                "furniture"),
            "pallet": ("raw timber", "the reason it reads as temporary — it "
                "arrived like this and it will leave like this"),
            "rim": ("deep teal", "caps the open box so the eye stops at the rim"),
        },
        [
            ("a real pallet with slats and feet", "not a plinth. This is the "
                "single detail that makes it read as stock dumped this morning "
                "rather than as fitted furniture"),
            ("a header card on a post", "what makes it a promotion rather than "
                "a crate"),
        ],
        {"x": "bins REPEAT", "y": "fixed", "z": "fixed"},
        "The bin fills with stock as it widens.",
    ),
    "queue_barrier": O(
        "Queue barrier",
        "Steers the queue away from the consultation room door.",
        "a queue barrier: two square posts on square base plinths with caps on "
        "top, one timber rail between them near the top and one slimmer steel "
        "rail below it",
        {
            "posts": ("painted steel, cream", "shop furniture"),
            "caps, plinths and top rail": ("warm oak", "the parts a hand rests "
                "on, and the warmth that stops it reading as a bollard"),
            "lower rail": ("dark steel", "structural, so it stays quiet"),
        },
        [
            ("two rails rather than one", "one rail reads as a prop; two reads "
                "as something manufactured"),
            ("heavy base plinths", "a barrier that could be knocked over is "
                "not a barrier"),
        ],
        {"x": "spans REPEAT", "y": "fixed", "z": "fixed"},
        None,
    ),
    "consultation_booth": O(
        "Consultation booth",
        "A private room for a conversation that cannot happen at the counter.",
        "a small free-standing consultation booth: two solid walls meeting at a "
        "corner with large glazed panels above waist height, heavy timber "
        "corner posts and a door surround on the open side, a flat roof, a "
        "skirting band at the base, and a sign panel over the door",
        {
            "posts and door surround": ("dark timber", "heavy frame is what "
                "makes it read as a room you would go into rather than a "
                "shower cubicle"),
            "lower panels": ("painted cream", "waist height, so nobody outside "
                "sees who is sitting down"),
            "upper glazing": ("pale glass", "privacy for the conversation, "
                "safety for the pharmacist — you can be seen but not heard"),
            "roof": ("dark steel with vents", "a sealed room needs air"),
        },
        [
            ("glazing only ABOVE waist height", "the whole privacy logic of "
                "the object in one decision"),
            ("a sign over the door", "people have to know what it is for"),
            ("roof vents", "a small sealed room gets stuffy"),
        ],
        {"x": "width STRETCHES", "y": "fixed", "z": "depth STRETCHES — both "
              "plan axes, because a room has to fit the space it is in; every "
              "fitting sits in the 9-slice caps so none of it smears"},
        None,
    ),
    "consult_chair": O(
        "Consultation chair",
        "Two of these face each other in the booth.",
        "a simple chair: a padded seat and a padded back held in a slim steel "
        "frame, on four square legs with a stretcher between the front pair",
        {
            "cushions": ("fabric, tan", "the one soft thing in the building"),
            "frame and legs": ("steel", "contract furniture is a steel frame"),
        },
        [
            ("cushions standing proud of the frame", "what makes it look sat-on "
                "rather than moulded"),
            ("a stretcher between the front legs", "how a light chair stays rigid"),
        ],
        {"x": "fixed", "y": "fixed", "z": "fixed"},
        None,
    ),
    "locker_bank": O(
        "Staff lockers",
        "Where staff leave their coats and phones. Back of house.",
        "one bay of a two-tier steel staff locker: a cream frame of stiles and "
        "rails with a deep green door in each tier, three vent slots near the "
        "top of each door, a short handle and a number plate on each, a plinth "
        "at the base and a sloped top",
        {
            "frame": ("cream painted steel", "the cage"),
            "doors": ("deep green painted steel", "the panels set into it — "
                "this is the frame rule where it genuinely applies, because a "
                "locker really is a frame with doors hung in it"),
        },
        [
            ("vent slots", "a closed locker with damp clothes in it has to "
                "breathe"),
            ("a number plate per door", "lockers are allocated"),
            ("a sloped top", "so nobody stores anything up there — that is "
                "exactly why real lockers have one"),
        ],
        {"x": "bays REPEAT", "y": "fixed", "z": "fixed"},
        None,
    ),
    "filing_cabinet": O(
        "Filing cabinet",
        "Paperwork. Back of house, and things accumulate on top of it.",
        "a four-drawer steel filing cabinet: a plain body, four equal drawer "
        "fronts each with a fat handle block that has a label slot in it, a "
        "plinth at the base and a flat top",
        {
            "body and drawers": ("grey steel", "it is a grey steel filing "
                "cabinet; that is the whole visual identity"),
            "handle blocks": ("cream", "the only light thing on it, which is "
                "why they carry the whole object"),
        },
        [
            ("a fat pull block with a label slot", "one fitting doing two jobs, "
                "handle and label holder — and the only reason four identical "
                "grey rectangles read as a filing cabinet"),
        ],
        {"x": "fixed", "y": "fixed", "z": "fixed"},
        "Paperwork accumulates on the top.",
    ),
    "green_cross": O(
        "Pharmacy cross",
        "In most of Europe this is the single thing that says pharmacy from "
        "across the street.",
        "a wall-mounted illuminated pharmacy cross: an equal-armed cross with a "
        "pale lit face inset into a deep green body, a steel rim standing proud "
        "all the way round, on a square back plate held off the wall by a stalk",
        {
            "body": ("deep green", "the colour IS the sign"),
            "rim": ("pale steel", "a pale edge round a dark body is what makes "
                "it read as illuminated with no emissive term in the renderer"),
            "face": ("pale glass", "the lit panel"),
        },
        [
            ("a proud rim", "the glow, done with geometry"),
            ("a stalk holding it off the wall", "an illuminated sign is a box "
                "that stands off the wall, not a sticker"),
        ],
        {"x": "fixed", "y": "fixed", "z": "fixed — hangs at fascia height"},
        None,
    ),
    "aisle_sign": O(
        "Aisle sign",
        "Hangs over an aisle so a customer can find the cough and cold shelf.",
        "a hanging aisle sign: a panel set deep into a steel frame with a pale "
        "lettering band across the middle, hung from two drop rods",
        {
            "frame": ("dark steel", "deep enough to cast a line of shadow "
                "across the panel from above"),
            "panel": ("warm oak", "warm against the cool room"),
            "lettering band": ("cream", "the readable part"),
        },
        [
            ("a deep frame, not a flat panel", "the shadow line the depth casts "
                "is what makes it read as a hung object"),
            ("two drop rods", "one rod would spin"),
        ],
        {"x": "panels REPEAT", "y": "fixed", "z": "fixed"},
        None,
    ),
    "medicine_box": O(
        "Stock boxes",
        "A run of dispensing cartons. Mostly here for the instancing test.",
        "a small white cardboard dispensing carton with a printed label panel",
        {"carton": ("printed card", "it is a cardboard box and should look "
                    "like one — flat, matte, no sheen")},
        [("a label panel", "an unmarked white box is not a medicine box")],
        {"x": "boxes REPEAT", "y": "fixed", "z": "fixed"},
        None,
    ),
}


def prompt_for(key):
    o = OBJECTS[key]
    fittings = "\n".join(f"  - {name}" for name, _ in o["fittings"])
    materials = "\n".join(f"  - {part}: {mat}" for part, (mat, _) in o["materials"].items())
    return (
        f"Three views of {o['form']}.\n\n"
        f"The object has these fittings and NOTHING ELSE:\n{fittings}\n\n"
        f"Materials:\n{materials}\n\n"
        f"{VIEW_STYLE}"
    )


def write_briefs(path):
    lines = [
        "# Object briefs",
        "",
        "Generated by `tools/authoring/objects.py briefs` — do not edit by hand;",
        "edit `OBJECTS` in that file and regenerate.",
        "",
        "One record per module, and the same record writes the reference-view",
        "prompt in `docs/concept/views/`. That is the point: the image the object",
        "is modelled from and the description it is modelled to cannot drift apart.",
        "",
        "**The rule every fitting has to pass: if you cannot write down why it is",
        "there, it does not go on the model.** Two details failed that test and are",
        "why this file exists — a cream rail between the dispensing bench's two",
        "drawers, and wood on the sides of a vaccine fridge. Both came from applying",
        "the concept sheets' light-frame-around-dark-panels rule mechanically instead",
        "of asking it to justify itself per object.",
        "",
    ]
    for key, o in OBJECTS.items():
        lines += [f"## {o['label']}  <sub>`{key}`</sub>", "", o["what"], "",
                  "**Materials**", ""]
        for part, (mat, why) in o["materials"].items():
            lines.append(f"- **{part}** — {mat}. {why}.")
        lines += ["", "**Fittings, and why each is there**", ""]
        for name, why in o["fittings"]:
            lines.append(f"- **{name}** — {why}.")
        lines += ["", "**Resizing**", ""]
        for axis, what in o["resize"].items():
            lines.append(f"- `{axis}` — {what}.")
        if o["pops"]:
            lines += ["", "**What pops in**", "", o["pops"]]
        lines.append("")
    path.write_text("\n".join(lines))
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Object briefs and multi-view references.")
    ap.add_argument("command", choices=["briefs", "views", "prompt"])
    ap.add_argument("object", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ref", nargs="*", default=[])
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    if args.command == "briefs":
        out = write_briefs(ROOT / "docs" / "object-briefs.md")
        print(f"{out.relative_to(ROOT)}  {len(OBJECTS)} objects")
        sys.exit(0)

    names = list(OBJECTS) if args.all else args.object
    if not names:
        ap.error("name an object, or pass --all")
    unknown = [n for n in names if n not in OBJECTS]
    if unknown:
        ap.error(f"unknown object {unknown[0]!r} — choose from {', '.join(OBJECTS)}")

    if args.command == "prompt":
        for n in names:
            print(f"=== {n} ===\n{prompt_for(n)}\n")
        sys.exit(0)

    key = load_key()
    failed = False
    for n in names:
        try:
            path = generate_image(prompt_for(n), VIEWS_DIR / f"{n}.png", key,
                                  refs=args.ref, model=args.model)
            print(f"  {n:22s} -> {path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")
        except Exception as exc:
            print(f"  {n:22s} -> FAILED: {exc}", file=sys.stderr)
            failed = True
    sys.exit(1 if failed else 0)
