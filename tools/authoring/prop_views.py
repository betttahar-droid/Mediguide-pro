#!/usr/bin/env python3
"""Generate a MEASURABLE orthographic reference for one prop.

    python3 tools/authoring/prop_views.py home_fridge
    python3 tools/authoring/prop_views.py --list

Authoring tool. NOT a build, CI or runtime dependency.

This is phase 0.3 of docs/making-a-prop.txt: every new prop needs a reference
you can measure band by band, and the style bible only settles the STYLE. The
sheet it writes is not meant to be pretty — it is meant to be measurable, which
imposes three things a nice illustration would get wrong:

  MAGENTA GROUND      the silhouette has to be unambiguous. Measuring an earlier
                      render against a cream ground silently classified a cream
                      door frame AS ground and reported a frame three times
                      thinner than it is.
  STRICT ORTHOGRAPHIC no perspective, no foreshortening — the whole point is to
                      read fractions of width and height straight off pixels.
  FRONT AND SIDE      side by side at the SAME height, so depth can be measured
                      as a fraction of width rather than guessed.

The reference set in docs/reference/ is attached so the prop comes back in the
kit's style rather than a generic one.

Output carries an invisible SynthID watermark and C2PA credentials.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from concept_sheet import generate_image, load_key  # noqa: E402

OUT = ROOT / "docs" / "style-bible" / "props"
REFS = ROOT / "docs" / "reference"

SUBJECTS = {
    # A deliberate contrast with the vaccine fridge: solid doors instead of
    # glass, two compartments instead of one, heavy rounded corners instead of
    # square ones. It exercises the parts of the system the first prop did not —
    # strong bevels, a taper, a door split, long handles.
    # A commercial upright vaccine fridge, from a reference set of four
    # isometric pixel-art views. Grittier than the other two: heavily weathered
    # steel, a full-height glass door with stock behind it, industrial labels,
    # and a big square vent low on the flank.
    "med_freeze": (
        "a tall single-door commercial vaccine refrigerator, about twice as "
        "tall as it is wide, in weathered pale grey-green painted steel with "
        "dark grimy mottling over it. It has: a full-height glass door taking "
        "most of the front, showing four wire shelves of small vaccine boxes "
        "and vials inside; a slim vertical steel handle on the door's left "
        "edge; a control band across the top of the front carrying a small "
        "blue medical-cross logo at the left, a tiny green indicator lamp, and "
        "a dark rectangular digital temperature display at the right; a small "
        "white rating label low on the side panel; a large square louvred vent "
        "grille low down on the right side panel; a recessed dark kick plinth "
        "at the bottom on four small feet"),
    # A pharmacy till computer, from docs/reference/03-retro-computers — the
    # chunky voxel monitors in that sheet are exactly this object's ancestors.
    # Deliberately UNLIKE the three fridges: wide rather than tall, an assembly
    # of several small masses rather than one cabinet, and its biggest feature
    # is a dark recessed rectangle rather than an opening. It exercises the
    # parts of the system the cabinets never touch.
    "pos_terminal": (
        "a chunky retro pharmacy point-of-sale computer terminal, WIDER than "
        "it is tall, in pale grey-cream moulded plastic yellowed with age. It "
        "has: a deep boxy monitor with a very thick square bezel and a large "
        "dark recessed screen, standing on a short square neck; a wide flat "
        "base plinth under the neck that the monitor slightly overhangs; a row "
        "of small ventilation slots along the top of the monitor; a small dark "
        "power button and a tiny green indicator lamp low on the bezel; a slim "
        "raised keypad panel of small square keys on the base in front of the "
        "monitor; a horizontal receipt printer slot with a short paper tail on "
        "the base beside the keypad; a short stalk carrying a small angled "
        "card reader with a dark display; small rubber feet under the base"),
    "home_fridge": (
        "a chunky retro 1950s domestic refrigerator with two solid doors — a "
        "short freezer door on top and a taller fridge door below, separated by "
        "a horizontal gap — heavily ROUNDED corners on the body and on both "
        "doors, a long slim vertical chrome handle on each door mounted near "
        "the door's opening edge, a small rectangular badge on the upper door, "
        "a recessed kick plinth at the bottom, and short stubby feet. The body "
        "is a soft pale mint green, the handles and trim are pale steel, the "
        "plinth is dark"),
}

STYLE = (
    "Flat 2D orthographic technical elevation, drawn in a chunky low-poly "
    "voxel game-prop style: hard-edged blocky forms, flat shading with NO "
    "gradients, a limited muted palette, crisp pixel edges, and only a few "
    "large features. "
    "STRICT ORTHOGRAPHIC PROJECTION: no perspective, no foreshortening, no "
    "vanishing point, no drop shadow, no ground plane, no reflection. "
    "The background is PURE MAGENTA #ff00ff, completely flat, everywhere that "
    "is not the object. "
    "No text, no labels, no dimensions, no annotations, no watermark."
)

# THE SIDE VIEW IS THE HARD ONE, and it fails silently. Asked for "its LEFT
# SIDE elevation" on a terminal with a screen, the model drew the monitor from
# BEHIND on a base drawn from the side — a coherent-looking picture in two
# different projections, from which the depth measures to a plausible number
# that is not the object's depth. A wrong drawing that measures cleanly is
# worse than an obviously wrong one.
#
# So the right-hand view is now specified by what must NOT be visible in it,
# which is the only form of the instruction the model cannot half-satisfy.
LAYOUT = (
    "Draw the SAME object TWICE, side by side on the magenta background, well "
    "separated: on the LEFT its FRONT elevation seen dead on, on the RIGHT its "
    "LEFT SIDE elevation seen dead on. "
    "The RIGHT drawing is the object turned exactly 90 degrees, so you are "
    "looking straight at its left flank. In that drawing you must NOT be able "
    "to see the front of the object at all: no screen, no door, no controls, "
    "no front panel, no keypad face — only the flat side of the object, its "
    "depth from front to back, and whatever is mounted on that flank. Both "
    "drawings show the WHOLE object, and every part visible in the front view "
    "must also appear in the side view, seen edge-on. "
    "Both drawings must be EXACTLY THE SAME HEIGHT and must line up "
    "horizontally, so the side view's width can be read as the object's depth. "
    "Nothing else in the image."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--like", nargs="*", default=[],
                    help="approved prop sheets to add as style references")
    args = ap.parse_args()
    if args.list or not args.name:
        print("subjects:", ", ".join(sorted(SUBJECTS)))
        return
    if args.name not in SUBJECTS:
        sys.exit(f"unknown subject {args.name!r}; try --list")

    OUT.mkdir(parents=True, exist_ok=True)
    refs = sorted(REFS.glob("crop-*.png")) or sorted(REFS.glob("*.png"))
    # --like feeds an ALREADY APPROVED prop sheet back in as an extra style
    # reference. docs/reference/ is where the style came FROM; the sheets in
    # docs/style-bible/props/ are where it has GOT TO, and after three props
    # those are not the same thing — the palette, the texel size and the
    # presentation have all been settled since. A new prop should match the
    # latter. This is concept_sheet.py's own rule ("feed the approved sheets
    # back in for every module after") applied to a per-prop reference.
    for name in args.like:
        sheet = OUT / f"{name}.png"
        if not sheet.exists():
            sys.exit(f"no approved sheet {sheet.relative_to(ROOT)}; try --list")
        refs.append(sheet)
    prompt = f"{STYLE}\n\nSubject: {SUBJECTS[args.name]}.\n\n{LAYOUT}"
    print(f"generating {args.name} — style refs: "
          + ", ".join(r.name for r in refs), flush=True)
    out = generate_image(prompt, OUT / f"{args.name}.png", load_key(), refs=refs)
    print(f"wrote {Path(out).relative_to(ROOT)}")
    print("next: measure it band by band before writing any geometry "
          "(docs/making-a-prop.txt phase 0.3)")


if __name__ == "__main__":
    main()
