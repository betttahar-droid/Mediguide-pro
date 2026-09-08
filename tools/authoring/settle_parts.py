#!/usr/bin/env python3
"""Drop the fittings that are another fitting listed twice.

    python3 tools/authoring/settle_parts.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Whichever way the part list is arrived at -- the model's colour map or
the measured flat cells -- nothing downstream ever asks whether two of its
boxes are the same thing. The cabinet's list has ten fittings called button
and four of them are duplicates:

    button    91,384..110,406   the top-left pad
    button_2  96,388..106,401   the same pad's inner face
    button_4 114,392..133,406   the top-right pad
    button_3 120,388..130,401   the same pad's inner face
    button_8  90,462..153,490   the top of the coin door
    coin_door 82,468..149,551
    button_9 173,485..210,504   the same panel as
    coin_slot 171,485..205,502

Each of those pairs becomes two boxes of geometry standing on the same spot,
which is what the render shows: a deck of fittings intersecting each other,
with the smaller one's edges poking through the larger one's face. It is also
why the small-fittings flatten rule existed -- flattening them to decals hid
the intersections instead of removing them, at the cost of every button on the
prop having no relief at all.

THE MEASUREMENT THAT SEPARATES A DUPLICATE FROM A RIDER IS NOT AREA. A button
sits inside the instruction panel and a decal sits inside the screen; both are
wholly contained and both are perfectly legitimate. Area ratio nearly works
and then does not: the marquee's lettering is 48% of the marquee, and a pad's
inner face is 31% of the pad, so no threshold on it separates them.

What separates them is WHERE the small box sits. A fitting's own inner face is
CONCENTRIC in it -- the rim is the same width all the way round, because that
is what a rim is. A rider is placed: the lettering hugs the left of the
marquee, the decal hugs the right of the screen, the button sits high on the
panel. So a contained box whose margins match on both axes is the same fitting
drawn twice, and one that hugs an edge is a rider, whatever their sizes.

For boxes that overlap without either containing the other, no such question
arises: two boxes that share most of the smaller one and stick out of each
other cannot be a fitting mounted on a fitting.

WHICH ONE SURVIVES IS THE LARGER, always. In every case seen it is the right
one: the pad rather than its inner face, the coin door rather than the strip
across its top, the panel rather than the slot drawn inside it. And it is the
safe direction regardless -- the union of the two is closer to the larger, so
keeping it leaves less of the artwork unclaimed.

WHAT THIS DOES NOT DO is decide whether a fitting is there at all. The
cabinet's right-hand panel carries a vent, a coin slot and two buttons over
what is, in the elevation, blank wall. That is a real fault and a different
one: measured four ways -- the step across each of the box's four sides, the
interior's mean and spread against a ring around it, and the edge energy
inside against outside -- no statistic separates those four from the speaker
grilles and the coin door, because a real fitting can be flush, low-contrast
and bounded by its neighbours. A threshold picked anyway would delete real
fittings, so nothing is thresholded and the phantoms stand.
"""
import argparse
import json
from pathlib import Path


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def overlap(a, b):
    return (max(0, min(a[2], b[2]) - max(a[0], b[0]))
            * max(0, min(a[3], b[3]) - max(a[1], b[1])))


def concentric(small, big, tol=0.25):
    """Are the small box's margins the same on both sides, on both axes?

    That is the shape of a rim: an inner face drawn inside a fitting sits in
    the middle of it, and a rider mounted on a fitting sits somewhere.

    MEASURED AGAINST THE MARGINS, NOT AGAINST THE HOST. Allowing a quarter of
    the host's WIDTH called a 13-pixel button concentric in a 238-pixel
    control deck -- which it is, in the sense that a coin dropped on a table
    is in the middle of the table. A rim is the same width all the way round,
    so the question is whether the two margins match EACH OTHER.
    """
    for lo, hi, s0, s1 in ((big[0], big[2], small[0], small[2]),
                           (big[1], big[3], small[1], small[3])):
        a, b = s0 - lo, hi - s1
        if abs(a - b) > tol * max(1, a + b):
            return False
    return True


def duplicate(a, b, share=0.55, inside=0.60, scale=0.15):
    """Are these two boxes one fitting? a and b in either order.

    The size floor is what keeps a rider a rider. A joystick covers 61% of
    itself with the deck it stands on and sticks out over the deck's top edge,
    so it is not contained and cannot be judged on where it sits -- but it is
    a fourteenth of the deck's area, and a fitting drawn twice is drawn at
    roughly the same size both times. Below the floor the pair is left alone
    whichever way it overlaps.
    """
    ov = overlap(a, b)
    small, big = (a, b) if area(a) <= area(b) else (b, a)
    if area(small) < 1 or ov < share * area(small):
        return False
    # two boxes that share half of everything they cover between them are the
    # same fitting and no further question is worth asking. The coin slot and
    # the button drawn over it agree on 74% of their union and differ by two
    # pixels at one edge -- near enough contained to fail a containment test
    # and near enough identical that where the smaller one "sits" is noise.
    if ov >= inside * (area(a) + area(b) - ov):
        return True
    if area(small) < scale * area(big):
        return False
    if all(s >= g for s, g in zip(small[:2], big[:2])) \
            and all(s <= g for s, g in zip(small[2:], big[2:])):
        # the small one is inside the big one -- a rider unless it sits
        # concentrically, in which case it is the big one's own face
        return concentric(small, big)
    # overlapping without containment: neither can be mounted on the other
    return True


def settle(parts):
    """The list with each fitting once, largest box of each kept."""
    order = sorted(range(len(parts)),
                   key=lambda i: -area(parts[i]["px"]))
    keep, dropped = [], []
    for i in order:
        b = parts[i]["px"]
        hit = next((k for k in keep if duplicate(parts[k]["px"], b)), None)
        if hit is None:
            keep.append(i)
        else:
            dropped.append((parts[i]["name"], parts[hit]["name"]))
    return [parts[i] for i in sorted(keep)], dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    f = d / f"parts_{args.face}.json"
    man = json.loads(f.read_text())
    kept, dropped = settle(man["parts"])
    for name, host in dropped:
        print(f"    {name:22} is {host} listed twice -- dropped")
    print(f"  {len(kept)} of {len(man['parts'])} fittings are distinct")
    if dropped and not args.dry_run:
        man["parts"] = kept
        f.write_text(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
