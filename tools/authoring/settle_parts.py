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

TRIED AND REVERTED: DROPPING THE STRIP THAT TRACES ITS HOST'S OWN RIM.

Two of the three parts the acceptance gate still calls gross outliers look, in
the drawing, like the edge of the thing they sit inside rather than a fitting on
it: v50_vending_machine's `push_bar_slot` is 155x8 along the top rim of the
delivery flap, and v26_arcade_cabinet's `screen_bezel_bottom` is 187x28 along
the bottom of the screen. `concentric()` above lets both through on purpose,
because a box hugging an edge is how this file tells a RIDER from a duplicate --
and a rim strip is the one kind of rider that is neither.

The rule that separates them reads well: contained, thin against the host,
spanning nearly all of it, and flush to one edge. Swept over the 624 parts in
the work tree that lie inside a larger part, at thin<=0.30, span>=0.85,
hug<=0.12, it matches seven:

  v25_vending_machine  price_strip_row3    in display_window    REAL
  v5_arcade_cabinet    control_deck        in screen_bezel      a containment
                                                                error, not a rim
  v50_vending_machine  push_bar_slot       in delivery_flap     the target
  prop_vending_machine coin_slot_label     in coin_slot_panel   REAL
  v26_arcade_cabinet   coin_return_tray    in coin_door_panel   REAL
  v17_arcade_cabinet   marquee             in decal_1           REAL
  v52_jukebox          title_board_header  in dome_window       REAL

Five real fittings deleted to remove one spurious box, and `screen_bezel_bottom`
-- half the reason for writing it -- does not even match. A price strip across a
vending machine's shelf, a label across a coin panel and a marquee across a
decal are all exactly "thin, spanning, flush to an edge", because that is what a
strip of lettering on a panel IS.

No threshold in that family survives, for the reason the docstring below gives
about phantom fittings: the geometry of a rim and the geometry of a caption are
the same geometry. The two boxes stand, and the gate naming them is the right
outcome -- it is a question for whoever segments, not a number to tune here.

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


def duplicate(a, b, share=0.55, inside=0.60, scale=0.30):
    """Are these two boxes one fitting? a and b in either order.

    The size floor is what keeps a rider a rider. A joystick covers 61% of
    itself with the deck it stands on and sticks out over the deck's top edge,
    so it is not contained and cannot be judged on where it sits -- but it is
    a fourteenth of the deck's area, and a fitting drawn twice is drawn at
    roughly the same size both times. Below the floor the pair is left alone
    whichever way it overlaps.

    A FIFTEENTH WAS NOT ENOUGH OF A FLOOR. Run across every prop in the work
    tree it took a jukebox's two coin slots -- 110 by 46 boxes straddling the
    top edge of a 278 by 68 deck, which is a coin mech mounted at the back of
    the deck and not the deck drawn again. At three tenths they survive, along
    with a start-button panel, two decals sitting on a speaker grille and a
    coin door's lower panel, while every pair that was checked by eye against
    the artwork is still caught: a pad's inner face at 0.31, a strip across a
    coin door at 0.32, a pad boxed twice at 0.49. Losing a duplicate costs one
    flat box standing where another box already stands; losing a rider deletes
    a fitting the prop has. The floor is set where the second cannot happen.
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


# A part this thin, flush against that same side of the sheet, is the edge of
# the drawing rather than something drawn on it.
#
# NOT A SIZE FLOOR, AND THE DIFFERENCE IS THE WHOLE POINT. This file's own
# docstring and CLAUDE.md both record what a size floor did here: 0.15, fitted
# on the arcade cabinet where it was right, swept across the work tree and it
# deleted a jukebox's two coin slots, a start-button panel and a coin door's
# lower panel. A bare thinness test would do it again -- v51_pinball has a real
# decal 56x2 and v32_arcade_cabinet one 2x64, and both are in the middle of
# their props where a player can see them.
#
# The conjunction is what makes it safe. Thin AND flush to that same edge is a
# column or row of the image itself, which cannot be a fitting because there is
# no prop outside it to mount on. Swept over all 3465 part records in the work
# tree it matches FIVE, being three parts on two props, every one of them named
# `decal` and every one of them one pixel wide at the last column of its sheet:
#
#   v25_arcade_cabinet  decal     1x177 @ x=234  sheet 235 wide
#   v25_arcade_cabinet  decal_2   1x220 @ x=234  sheet 235 wide
#   v43_arcade_cabinet  decal_7   1x107 @ x=261  sheet 262 wide
#
# and it leaves all four of the thin interior decals alone. Those three are
# also three of the seven parts `feature_intent`'s acceptance gate calls gross
# outliers, at 7.1x, 8.8x and 4.3x outside their role's aspect band -- so the
# gate had already named them from a completely different direction.
EDGE_THIN = 2


def edge_sliver(px, sheet):
    """Which side of the drawing this box IS, or None if it is a fitting."""
    if not sheet:
        return None
    sw, sh = sheet
    x0, y0, x1, y1 = px
    if x1 - x0 <= EDGE_THIN and (x0 <= 1 or x1 >= sw - 1):
        return "left" if x0 <= 1 else "right"
    if y1 - y0 <= EDGE_THIN and (y0 <= 1 or y1 >= sh - 1):
        return "top" if y0 <= 1 else "bottom"
    return None


def settle(parts, sheet=None):
    """The list with each fitting once, largest box of each kept.

    @param sheet (w, h) of the drawing these boxes are measured in. Without it
      the edge test cannot run and is skipped rather than guessed -- a part
      list with no `size` is one this cannot answer for, and inventing a sheet
      size to have something to compare against is how a check comes to reject
      real work.
    """
    order = sorted(range(len(parts)),
                   key=lambda i: -area(parts[i]["px"]))
    keep, dropped, edges = [], [], []
    for i in order:
        b = parts[i]["px"]
        side = edge_sliver(b, sheet)
        if side:
            edges.append((parts[i]["name"], side))
            continue
        hit = next((k for k in keep if duplicate(parts[k]["px"], b)), None)
        if hit is None:
            keep.append(i)
        else:
            dropped.append((parts[i]["name"], parts[hit]["name"]))
    return [parts[i] for i in sorted(keep)], dropped, edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    f = d / f"parts_{args.face}.json"
    man = json.loads(f.read_text())
    kept, dropped, edges = settle(man["parts"], man.get("size"))
    for name, host in dropped:
        print(f"    {name:22} is {host} listed twice -- dropped")
    for name, side in edges:
        print(f"    {name:22} is the {side} edge of the drawing, "
              f"{EDGE_THIN}px or thinner and flush to it -- dropped")
    print(f"  {len(kept)} of {len(man['parts'])} fittings are distinct")
    if (dropped or edges) and not args.dry_run:
        man["parts"] = kept
        f.write_text(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
