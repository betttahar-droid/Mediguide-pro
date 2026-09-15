#!/usr/bin/env python3
"""Which part is making the prop the wrong shape, by name.

    python3 tools/authoring/part_bulge.py --worst 20
    python3 tools/authoring/part_bulge.py --only tools/img2threejs-work/v8_arcade_cabinet

Authoring tool. NOT a build, CI or runtime dependency. Needs the dev server up.

WHY. `geometry_audit` says a prop's side outline is 0.889 against its own
elevation. That is a number about the whole machine, and CLAUDE.md's second rule
is "identify the object before theorising about the cause" -- so this renders the
body ALONE, then the body plus each part in turn, and scores each render against
the elevation. What comes out is a list of parts with what each one does to the
agreement, which is as specific as it gets.

It found the case it was written for on the first run: v8_arcade_cabinet's
`joystick_left`, which by itself cost 0.086 of the side outline. Its box turned
out to be 0.556 of the prop's width -- the segmenter had boxed most of the
control panel and called it a joystick, and the renderer had dutifully built it
as an upright standing off a sloped deck. Correcting that one field took the
prop's side outline from 0.889 to 0.975 and its top from 0.909 to 0.963.

READ IT AS A POINTER, NOT A VERDICT. A negative score says a part makes its prop
look less like its own drawing, and that is a question rather than a fault --
the answer is usually either "that part's box is wrong" or "that part's motion
is wrong", and both are cheap to check once you have the name.

IT IS SLOW ON PURPOSE. One render per part, from the axis you name. That is
minutes for a prop with eighty parts, which is why it takes a --worst list off
the last audit rather than sweeping everything.

WHAT IT FOUND, AND WHAT CAME OF IT. Over the fourteen worst side outlines it
listed 25 parts costing more than 0.01, and they were not scattered: TWENTY ran
to an EDGE of the face, u within 0.04 of 0 or 1, against a base rate of 39% for
all 1760 parts in the corpus. They were legs, base trims, arch columns, feet and
control decks -- the parts standing where the body stops being flat. Three
changes came out of that and they closed almost all of it: the seat became a
median rather than one sample, the stand-off is measured against what the
elevation already draws, and a part's mesh follows the wall instead of
approximating it. v13_jukebox's arch columns went from -0.057 and -0.070 to
nothing at all.

AND NOW READ THE REST OF THIS BEFORE ACTING ON A SMALL NEGATIVE NUMBER.

What is left is mostly NOT a fault, and the tool cannot tell you that, so this
has to. On a prop whose front is flat -- a vending machine, a plain cabinet --
`body gave 0.0000` in the ?fit=1 log, meaning the lofted wall carries no relief
at those rows, and a control deck standing 0.010 proud of a body 0.50 deep is 2%
of depth that the side elevation genuinely does not show. It is also a control
deck. `depth_scale.py` has the sweep: the outline objective is monotone in the
stand-off and would end with every button a sticker, because it can see a
double-count and cannot see a flattening.

So a small negative score on a part whose wall is flat under it is the OBJECTIVE
being blind, not the prop being wrong. What IS worth acting on:

  - more than about 0.03, which is usually a box or a motion that is wrong
    rather than relief that is right -- v8_arcade_cabinet's `joystick_left` at
    -0.086 was most of the control panel built as an upright
  - a ?fit=1 line showing `body gave` well above the part's own depth class, or
    a `range` above 0.40D, which means the surface under it is not a wall
  - a part that costs its prop on BOTH the side and the top

A recess is the clearest case of the blindness: its bezel stands proud by
construction -- there is no hole in the body to sink into -- so from directly
above it is a bump the plan does not draw. v7_vending_machine's `price_display`
adds eight pixels of depth to a 338-pixel plan and costs 0.030, because the
score tight-crops before it compares and one local bump rescales everything
else. Nothing about that part is wrong.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))

WORK = ROOT / "tools" / "img2threejs-work"
AXIS = {"side": "yaw=90&pitch=0", "front": "yaw=0&pitch=0",
        "top": "yaw=0&pitch=89.9"}


ELEV = {"side": "side", "front": "front", "top": "top"}


def bulges(d, axis="side"):
    """[(IoU change, part name)], most harmful first.

    SCORED AGAINST THE ELEVATION, NOT AGAINST THE BARE BODY. The first version
    of this measured the pixels a part adds beyond the body, and it is worth
    saying why that is wrong, because it looked right and found a real fault on
    its first run. A part is SUPPOSED to add pixels -- that is what relief is --
    and a part that stands clear of the body entirely adds all of itself. It
    ranked v51_pinball's `leg_right` at 15.3%, top of the corpus, for the crime
    of being a leg: the body's silhouette is the cabinet, the legs hang below
    it, and of course they are all new. Nothing was wrong with that prop.

    So each part is scored by what it does to the number that matters -- the
    outline agreement with the prop's own elevation. Render the bare body and
    score it; render the body plus this one part and score that; the difference
    is what the part contributes. A part that makes the prop look more like its
    drawing scores positive, and only a NEGATIVE score is a fault. A leg now
    scores positive, because the drawing has legs in it too.
    """
    import geometry_audit as ga
    lj = d / "layers_front.json"
    src = d / f"{ELEV[axis]}.png"
    if not lj.exists() or not src.exists():
        return []
    names = [p["name"] for p in json.loads(lj.read_text()).get("parts", [])]
    if not names:
        return []
    out = d / "_bulge"
    # `__none__` matches no part, so the first render is the bare body.
    qs = [f"dir=/{d.relative_to(ROOT)}&audit=1&fixcam=1&{AXIS[axis]}&only={n}"
          for n in ["__none__"] + names]
    got = ga.shoot(out, qs)
    # NO RENDER IS NOT NO FAULT. This used to skip a missing PNG and carry on,
    # so a run with no browser reported "every part earns its place" for every
    # prop in the corpus -- the most confident possible way to say nothing.
    if len(got) < len(qs):
        raise RuntimeError(f"{d.name}: {len(qs) - len(got)} of {len(qs)} "
                           f"renders never arrived (is the dev server up?)")
    fl = ga.flips(d)[axis]
    base = None
    rows = []
    for n, q in zip(["__none__"] + names, qs):
        iou = ga.compare(got[q], src, flip_x=fl[0], flip_y=fl[1])[0]
        if n == "__none__":
            base = iou
            continue
        rows.append((iou - base, n))
    rows.sort()
    return rows


def worst(n, axis):
    rows = []
    for f in sorted(WORK.glob("*/geometry_audit.json")):
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        if axis in j:
            rows.append((j[axis]["iou"], f.parent))
    rows.sort()
    return [d for _, d in rows[:n]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worst", type=int, default=12)
    ap.add_argument("--axis", default="side", choices=sorted(AXIS))
    ap.add_argument("--only", default=None)
    ap.add_argument("--show", type=int, default=3)
    ap.add_argument("--bar", type=float, default=0.01,
                    help="only report parts costing more than this much IoU")
    args = ap.parse_args()

    props = ([Path(args.only).resolve()] if args.only
             else worst(args.worst, args.axis))
    print(f"{len(props)} prop(s), {args.axis} view. A part is listed when "
          f"adding it costs more than {args.bar:g} of outline agreement with "
          f"the prop's own elevation.\n")
    flagged = 0
    for d in props:
        rows = [r for r in bulges(d.resolve(), args.axis) if r[0] < -args.bar]
        if not rows:
            print(f"  {d.name:26} -- every part earns its place")
            continue
        flagged += 1
        head = ", ".join(f"{n} {dv:+.3f}" for dv, n in rows[:args.show])
        print(f"  {d.name:26} {head}")
    print(f"\n{flagged} of {len(props)} props have a part that costs more "
          f"than {args.bar:g}")


if __name__ == "__main__":
    main()
