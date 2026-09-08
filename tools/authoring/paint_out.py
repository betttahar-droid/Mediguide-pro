#!/usr/bin/env python3
"""Ask the image model for the prop with its fittings taken off.

    python3 tools/authoring/paint_out.py work/ps1 --asset "vending machine"

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Every fitting is cut out of the elevation into its own layer, and the hole
it leaves has to be filled with whatever the prop is made of, because the
background is what shows when the prop is stretched. That fill was arithmetic:
find the largest rectangle of clean material anywhere on the face, make it
tile, and lay it over every hole.

Which is the tool AUTHORING texture, and this repo's whole division of labour
says it should not. The model draws; arithmetic measures and verifies. A patch
of panel tiled over a coin door is a guess about what is behind the coin door,
and it looks like one: at the drawn size the fittings sit back on top and hide
it, and the moment anything grows it is all you can see. Black rectangles
across a display case, grey slabs where a control deck widened, corrugated
banding down a flank.

A model that can draw the cabinet can draw the cabinet with its coin door
taken off. That is one call, it is the same question a texture artist answers
with a clone brush, and it needs no clean rectangle to exist anywhere.

WHAT KEEPS IT HONEST is that only the HOLES are taken. The reply is composited
into the original through the hole mask, so every pixel outside a hole is the
original's own pixel, bit for bit -- the model cannot redraw the prop, move a
fitting, change the palette or lose the silhouette, because none of that is
inside a hole. It can only answer the question it was asked. This is the same
bargain shape_like strikes in detail_sheet: the model supplies interior, and
the outline is not its to touch.

AND THEN THE FILL IS MEASURED, per hole:

  covered   the reply must actually put something there. A model that returns
            the input unchanged leaves the fitting in the hole, which would
            reinstate the very thing being removed.
  material  the fill's colour must sit near the material AROUND that hole --
            not near the prop's modal colour, which is what the arithmetic
            version got wrong on a machine whose exterior is dark and whose
            display case is pale.
  not flat  it must have grain. A hole filled with one flat colour is the
            slab this exists to stop.

A hole whose fill fails goes back to the arithmetic patch, so a bad reply
costs nothing. CACHED, because the loop rebuilds the layers every round and
this must not be re-bought each time.

TRIED AND REVERTED: THE SAME THING FOR THE SIDE AND BACK. The growth band is
measured on the front and applied to every face, so a cabinet bare across some
rows at the front and carrying a rocket across the same rows on its FLANK
stacks that rocket down a taller prop -- both judges, every round. The obvious
extension is to paint the graphics off the side too.

It does not work, for two reasons that are worth writing down.

There is no parts_side.json, so there are no holes to composite through and
none of the safety that gives. The tightest honest scope is the rows the body
actually repeats -- everything else is untouched -- and compositing a band of
the reply into the original puts a SEAM at each end of it. The reply is a
different rendering of the same material, close enough to pass a colour check
at a distance of 20 and plainly a different grey up against the original: the
cabinet came back with two dark stripes ruled across its rocket, which is a
worse fault than the one being fixed and a more obvious one.

And the model did not remove the rocket in any case. Asked to take off decals
and graphics it took off lettering and kept the artwork, which is a defensible
reading -- a painted-on rocket is the cabinet's paint.

What this needs is not a better prompt. It needs the side's graphics to be
LIFTED, the way the front's fittings are, so there are holes to composite
through and so the decals can be drawn back as their own planes. decal_sheet
already extracts them; what it does not record is where they were.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402
from identify_parts import object_crop  # noqa: E402

PROMPT = """The attached image is the front elevation of a {asset}, drawn flat
and straight on.

Redraw it EXACTLY as it is, with one change: every fitting has been taken off
the {asset} and the bare body is showing where each one was.

Take off the doors, panels, buttons, slots, grilles, signs, screens, shelves,
handles and labels. Leave the {asset}'s own BODY: its outline, its panels, its
seams, its paint, its dirt, its wear, its shading.

Where a fitting was, draw what is behind it -- the same painted material as the
body immediately around that spot, continuing through: the same colour, the
same grain, the same streaks and grime running the same way, the same
brightness. As though the fitting had been unbolted and the surface behind it
had always been plain.

  - SAME SIZE, SAME POSITION, SAME ANGLE. The body must not move, resize or
    turn by a single pixel. Its outline must be identical.
  - SAME PALETTE and the same lighting. Do not clean it up, do not brighten it,
    do not add new detail or new panel lines.
  - DO NOT leave holes, blanks, flat patches, white areas or shadows where the
    fittings were, and do not draw the fittings faintly or in outline. Draw the
    material.

Hand-painted PlayStation-era look, same resolution and same style as the
attached image."""


def holes_of(d, face, parts, W, H, grow=2):
    """Which pixels a fitting covers, from the masks the segmenter measured."""
    m = [[False] * H for _ in range(W)]
    for p in parts:
        x0, y0, x1, y1 = p["px"]
        mk = mw = mh = None
        if p.get("mask") and (d / p["mask"]).exists():
            try:
                mi = Image.open(d / p["mask"]).convert("L")
                # A MASK IS NOT ALWAYS ITS BOX. segment_sheet writes the mask at
                # the region's size and a later pass may have moved or merged
                # the box, so indexing it by the box's own extent walks off the
                # end. Where they disagree the box is the authority -- it is
                # what every other coordinate in the pipeline is measured in.
                mw, mh = mi.size
                mk = mi.load()
            except Exception:
                mk = None
        for x in range(max(0, x0), min(W, x1)):
            for y in range(max(0, y0), min(H, y1)):
                if mk is None:
                    m[x][y] = True
                    continue
                mx, my = x - x0, y - y0
                if 0 <= mx < mw and 0 <= my < mh and mk[mx, my] > 128:
                    m[x][y] = True
    if grow <= 0:
        return m
    # A HOLE'S OWN EDGE IS STILL THE FITTING. A mask is a boundary and the
    # pixel just outside it carries the fitting's shadow and its antialiasing,
    # which is what left a fitting-shaped tracery in the background before.
    out = [[False] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            if not m[x][y]:
                continue
            for dx in range(-grow, grow + 1):
                nx = x + dx
                if not 0 <= nx < W:
                    continue
                for dy in range(-grow, grow + 1):
                    ny = y + dy
                    if 0 <= ny < H:
                        out[nx][ny] = True
    return out


def grain(im, box):
    """Mean neighbour difference in one region -- flat fill scores near zero."""
    x0, y0, x1, y1 = box
    px = im.convert("RGB").load()
    n = s = 0
    for x in range(max(0, x0), min(im.width - 1, x1)):
        for y in range(max(0, y0), min(im.height - 1, y1)):
            a, b = px[x, y], px[x + 1, y]
            c = px[x, y + 1]
            s += (sum(abs(u - v) for u, v in zip(a, b))
                  + sum(abs(u - v) for u, v in zip(a, c))) / 6
            n += 1
    return s / max(1, n)


def mean_rgb(im, box, want, skip=None):
    px = im.convert("RGB").load()
    acc, n = [0, 0, 0], 0
    for x in range(max(0, box[0]), min(im.width, box[2])):
        for y in range(max(0, box[1]), min(im.height, box[3])):
            if skip is not None and skip[x][y] != want:
                continue
            c = px[x, y]
            acc = [a + v for a, v in zip(acc, c)]
            n += 1
    return [a / n for a in acc] if n else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--ring", type=int, default=10,
                    help="how far around a hole counts as its surroundings")
    ap.add_argument("--colour-bar", type=float, default=46.0)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    face = args.face
    man = json.loads((d / f"parts_{face}.json").read_text())
    parts = man["parts"]
    # IN THE COORDINATES EVERY PART IS MEASURED IN. The elevation on disk has
    # sheet around it; object_crop is what layer_build works in and what every
    # part's box refers to. Reading front.png raw made this silently useless --
    # the plate was the right picture at the wrong size, the size check failed,
    # and layer_build went on tiling its patch without a word.
    src = object_crop(d / f"{face}.png").convert("RGB")
    W, H = src.size
    if list(src.size) != list(man.get("size", src.size)):
        print(f"  size drift {src.size} vs {man.get('size')} -- not painting")
        return
    ref = d / f"_plate_ref_{face}.png"
    src.save(ref)
    if not parts:
        print("  no fittings to take off")
        return

    plate = d / f"_plate_{face}.png"
    if args.redraw or not plate.exists():
        try:
            generate_image(PROMPT.format(asset=args.asset), plate, load_key(),
                           refs=[str(ref)])
        except Exception as e:
            print(f"  plate not drawn ({type(e).__name__}) -- arithmetic fill "
                  f"stands")
            return
    try:
        got = Image.open(plate).convert("RGB")
    except Exception:
        print("  plate unreadable -- arithmetic fill stands")
        return
    # THE REPLY IS RESAMPLED TO THE ELEVATION, NOT TRUSTED TO MATCH IT. The
    # model returns whatever size it likes; the coordinates every hole is
    # measured in are the elevation's.
    if got.size != (W, H):
        got = got.resize((W, H), Image.LANCZOS)

    hole = holes_of(d, face, parts, W, H)
    out = src.copy()
    op = out.load()
    gp = got.load()
    # WHICH HOLES THE PLATE ANSWERED FOR, AS A MASK. A refused hole keeps the
    # original's pixels, which are the FITTING -- so a consumer that took the
    # composite as the fill source everywhere would copy a coin door into the
    # hole where the coin door was, which is worse than any tiled patch. The
    # mask says where the plate may be believed; everywhere else the arithmetic
    # fill is still the answer.
    okmask = Image.new("L", (W, H), 0)
    mp = okmask.load()
    kept = refused = 0
    for p in parts:
        x0, y0, x1, y1 = p["px"]
        r = args.ring
        ring = (x0 - r, y0 - r, x1 + r, y1 + r)
        # the material AROUND this hole, which is what the fill has to match --
        # not the prop's modal colour, which is a different question and the
        # one the arithmetic fill answered wrongly
        near = mean_rgb(src, ring, False, hole)
        new = mean_rgb(got, (x0, y0, x1, y1), True, hole)
        if near is None or new is None:
            refused += 1
            continue
        dist = sum(abs(a - b) for a, b in zip(near, new)) / 3
        g = grain(got, (x0, y0, x1, y1))
        ok = dist <= args.colour_bar and g >= 0.6
        print(f"    {p['name']:22} {x1-x0:3}x{y1-y0:<3}  colour {dist:5.1f}  "
              f"grain {g:5.2f}  {'PAINTED' if ok else 'refused'}")
        if not ok:
            refused += 1
            continue
        for x in range(max(0, x0), min(W, x1)):
            for y in range(max(0, y0), min(H, y1)):
                if hole[x][y]:
                    op[x, y] = gp[x, y]
                    mp[x, y] = 255
        kept += 1

    if not kept:
        print("  nothing usable in the plate -- arithmetic fill stands")
        return
    out.save(d / f"_painted_{face}.png")
    okmask.save(d / f"_painted_{face}_mask.png")
    print(f"  {kept} fitting(s) painted out by the model, {refused} left to "
          f"the arithmetic fill -> {d / f'_painted_{face}.png'}")


if __name__ == "__main__":
    main()
