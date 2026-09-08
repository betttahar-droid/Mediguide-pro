#!/usr/bin/env python3
"""Redraw the prop's SMALL FITTINGS at a resolution worth modelling.

    python3 tools/authoring/detail_sheet.py work/ps1 --asset "arcade cabinet"
    python3 tools/authoring/detail_sheet.py work/ps1 --apply     # no API calls

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Everything this tool makes descends from one turnaround sheet, and the
sheet is 1408 by 768 for four elevations -- so the front of a cabinet is about
250 pixels wide, and every fitting is cut out of that. Measured across four
cabinets: twenty-seven of one prop's thirty-nine fittings have a side under 24
pixels. A coin slot is 9 by 13. A start button is 10 by 13. An INSERT COIN
strip is 80 by 10.

That is the fidelity ceiling, and no amount of care downstream lifts it. The
atlas cannot sharpen a 9-pixel slot; the geometry cannot give relief to a shape
it only knows to a tenth of its own size; the judges read the consequence off
every render -- "unreadable decal", "smeared graphics", "mangled". They were
describing thirteen pixels being asked to be a coin slot.

WHAT RAISES IT IS ASKING FOR THE FITTING ITSELF, at the size it deserves. Which
is the same move material_atlas made for materials and decal_sheet made for
graphics: stop carving the thing out of a picture of the whole prop, and ask
for the thing. A model that can draw a cabinet can draw its coin door, and it
draws it into a whole canvas instead of into thirteen pixels.

THE MODEL SUPPLIES INTERIOR DETAIL; ARITHMETIC KEEPS THE SHAPE. That division
is the one this repo runs on, and here it is unusually clean. A fitting's
OUTLINE is load-bearing -- the geometry is built from its measured box, its
mask cuts the hole in the background, its placement and its bays are all in
those coordinates -- so none of it may move. Its INTERIOR is just texels, and
texels are what is missing. So the redraw is resized to the part's own aspect
and masked with the part's own alpha: the silhouette is bit-for-bit what it
was, and the inside gains an order of magnitude of detail. A redraw that comes
back as the wrong object cannot corrupt the geometry -- at worst it is refused
by the colour check and the original stands.

VERIFIED, NOT TRUSTED, like everything else here:

  looks     shrunk to the crop's own size, the redraw must still look like the
            crop. This is also how cells are matched to fittings: the model
            does not draw the grid it was asked for, so which cell is which is
            settled by the pictures rather than by counting.
  colour    its median must sit near the crop's, or it is a different object
            drawn confidently.
  palette   the top tenth of its saturation must sit near the crop's, in
            either direction. A median agrees with far too much: a grey deck
            redrawn with orange and blue striping averages out grey.
  not flat  it must not be nearly blank. Note that "grainier than the crop
            upscaled" is NOT the test: a blurry upscale spreads a difference
            across every pixel, while crisp artwork has flat regions with hard
            edges between them and scores lower on mean neighbour difference
            while carrying far more. Measured that way, two properly louvred
            grilles came in under the smears they replaced.

CACHED, because the loop rebuilds the parts every round and the redraws must
not be re-bought each time. The sheet is drawn once; --apply re-lays it.
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
from material_atlas import cells, grain_px  # noqa: E402
from region_parts import annotate  # noqa: E402

# A SINGLE ROW, BECAUSE THAT IS A LAYOUT THE MODEL ACTUALLY DRAWS. Asked for
# three by two it drew one by two, two by four and three by two on three
# consecutive sheets -- cells() measures the gutters rather than trusting the
# request, which is right, and it leaves six fittings chasing however many
# cells turned up. Whichever ones lose are then paired with a blank and
# refused, so half the sheet is wasted and the fittings that most need the
# help are as likely to be the losers as not. A row of three is unambiguous
# left to right, costs twice as many calls and yields far more than twice as
# much, and keeps the palette consistent within each group of three.
COLS, ROWS = 3, 1
PER_SHEET = COLS * ROWS

PROMPT = """A FITTINGS SHEET for a {asset}, in the style of the attached
reference elevation.

Draw a SINGLE ROW of exactly {cols} square panels side by side on a pure white
background, with a wide white gutter between the panels and a wide white margin
around the whole row. Exactly {cols} panels, left to right, no more and no less.

Each panel is ONE FITTING of this {asset}, drawn LARGE and filling its panel
edge to edge, exactly as it appears on the reference, in this order:

{listing}

EVERY PANEL MUST BE:

  - THE SAME FITTING as the reference shows, in the same shape, the same
    proportions, the same colours and the same state of wear. This is the same
    object drawn bigger, not a new design of it.
  - FLAT ORTHOGRAPHIC FRONT VIEW. No perspective, no angle, no thickness seen
    from the side, no drop shadow, no glow.
  - FILLING ITS PANEL. The fitting's own edges touch the panel's edges. Do not
    draw the cabinet around it, do not leave a border of panel colour, do not
    add a frame.
  - DETAILED AT THIS SIZE. Now that it is large, draw what it actually has:
    the moulding round a coin slot, the bevel and the highlight on a button,
    the lettering on a plate, the mesh of a grille, the screwheads, the scuffs
    and the dirt in its corners.

Hand-painted PlayStation-era look, low resolution, muted palette taken from the
reference. Do not label the panels. Do not draw the whole {asset}.
"""


def wants_detail(q, W, H, small=48):
    """Is this fitting too small on the sheet to carry its own detail?

    Measured on the SHORTER side, because that is what limits it: a strip 80 by
    10 has plenty of pixels and none of them where it needs them. Anything
    already big enough is left alone -- a screen or a marquee is drawn at a
    size the sheet can afford and redrawing it would only risk changing it.
    """
    x0, y0, x1, y1 = q["px"]
    w, h = x1 - x0, y1 - y0
    return min(w, h) < small and w >= 4 and h >= 4


def target(w, h, want=64, cap=6.0, most=320):
    """How much bigger to draw it: enough to matter, not enough to be silly.

    The prop is about six hundred texels tall as drawn, so a thirteen-pixel
    button is thirteen texels. Four to six times that is the difference between
    a smear and a fitting; beyond it the atlas grows for detail no one at
    arm's length can see, and this is a period prop.
    """
    s = max(1.0, min(cap, want / max(1, min(w, h))))
    s = min(s, most / max(1, max(w, h)))
    return max(1, int(round(w * s))), max(1, int(round(h * s)))


def trim(cell, tol=34):
    """The fitting inside its panel, without the paper around it.

    The prompt asks for the fitting to fill its panel edge to edge and the
    model leaves a margin anyway -- which is fair enough, it is drawing a
    picture. cells() insets a few pixels off the gutter, which is enough to
    stop a cell carrying its neighbour and nowhere near enough to stop it
    carrying white: two fittings came back as white rectangles bolted to the
    cabinet, because the part's alpha is its measured box and the box was
    filled with paper.

    What is wanted is the drawn thing, and the drawn thing is what is not the
    colour of the border. Same question object_crop asks of an elevation,
    asked of one cell.
    """
    im = cell.convert("RGB")
    W, H = im.size
    px = im.load()
    edge = [px[x, 0] for x in range(0, W, max(1, W // 16))] \
        + [px[x, H - 1] for x in range(0, W, max(1, W // 16))] \
        + [px[0, y] for y in range(0, H, max(1, H // 16))] \
        + [px[W - 1, y] for y in range(0, H, max(1, H // 16))]
    bg = [sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3)]
    xs, ys = [], []
    for x in range(W):
        for y in range(H):
            if sum(abs(a - b) for a, b in zip(px[x, y], bg)) / 3 > tol:
                xs.append(x)
                ys.append(y)
    if len(xs) < 16:
        return cell
    x0, x1 = min(xs), max(xs) + 1
    y0, y1 = min(ys), max(ys) + 1
    if (x1 - x0) < 8 or (y1 - y0) < 8:
        return cell
    return cell.crop((x0, y0, x1, y1))


def resemblance(cell, crop):
    """How much this drawing looks like the fitting it claims to be. 0 is a
    perfect match, 1 is unrelated, 2 is anti-correlated or featureless.

    Median colour and aspect were what matched cells to fittings, and they are
    too weak: this sheet's two speaker grilles -- 2.4:1, dark, louvred -- were
    handed two flat dark squares, which agree on both counts and on nothing
    else. Every stage after a bad pairing is measuring the wrong picture.

    So compare the pictures. Put both at the same small size and correlate
    them. Correlation is the right form and mean-subtraction alone is not: a
    BLANK cell has no variance, so differencing it against a low-contrast crop
    gives a small number and every blank cell on the sheet scored best in the
    room. Dividing by each side's own spread is what makes the comparison about
    pattern rather than level, and it makes a featureless cell score worst
    instead of first, which is what it deserves.
    """
    n = (max(16, min(64, crop.width)), max(16, min(64, crop.height)))
    pa = list(crop.convert("L").resize(n, Image.LANCZOS).getdata())
    pb = list(cell.convert("L").resize(n, Image.LANCZOS).getdata())
    ma, mb = sum(pa) / len(pa), sum(pb) / len(pb)
    da = [x - ma for x in pa]
    db = [y - mb for y in pb]
    va = sum(x * x for x in da)
    vb = sum(y * y for y in db)
    if va <= 1e-6 or vb <= 1e-6:
        return 2.0
    r = sum(x * y for x, y in zip(da, db)) / ((va ** 0.5) * (vb ** 0.5))
    return 1.0 - r


def sat_p90(im):
    """How colourful this fitting's most colourful tenth is.

    A median colour agrees with far too much. The model redrew this cabinet's
    grey control deck with vivid orange and blue striping and its joystick as a
    blue and orange blob, and both passed a median test comfortably -- the
    average of a bright stripe and a grey panel is a greyish panel. What
    changed was the PALETTE, and the ninetieth percentile of saturation is what
    a palette change moves: 34.6 to 188.5 on the joystick, 32.3 to 63.8 on the
    door, while every honest redraw stayed within a fifth of where it started.

    Two-sided, because losing colour is the same fault mirrored: a redraw of a
    bright marquee legend came back at a fifth of its saturation, which is not
    that legend either.
    """
    im = im.convert("RGBA")
    px = im.load()
    v = []
    for x in range(im.width):
        for y in range(im.height):
            p = px[x, y]
            if p[3] < 128:
                continue
            mx, mn = max(p[:3]), min(p[:3])
            v.append(0.0 if mx == 0 else 255.0 * (mx - mn) / mx)
    if not v:
        return 0.0
    v.sort()
    return v[int(0.9 * (len(v) - 1))]


def median_rgb(im):
    im = im.convert("RGBA")
    px = im.load()
    ch = [[], [], []]
    for x in range(im.width):
        for y in range(im.height):
            p = px[x, y]
            if p[3] < 128:
                continue
            for c in range(3):
                ch[c].append(p[c])
    if not ch[0]:
        return None
    return [sorted(v)[len(v) // 2] for v in ch]


def shape_like(cell, crop):
    """The model's interior, the measured outline. Neither borrows the other.

    Resized to the part's own aspect and given the part's own alpha, so nothing
    the geometry depends on can move however the redraw came out.
    """
    tw, th = target(crop.width, crop.height)
    out = cell.convert("RGB").resize((tw, th), Image.LANCZOS).convert("RGBA")
    a = crop.convert("RGBA").split()[3].resize((tw, th), Image.NEAREST)
    out.putalpha(a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="prop")
    ap.add_argument("--apply", action="store_true",
                    help="re-lay the cached redraws, no API calls")
    ap.add_argument("--redraw", action="store_true",
                    help="draw the sheets again even if cached")
    ap.add_argument("--sheets", type=int, default=6)
    ap.add_argument("--colour-bar", type=float, default=58.0)
    # the look score's job is MATCHING, not judging: a redraw is a different
    # rendering of the same thing, so even a perfect pairing correlates only
    # loosely. It is bounded here only to throw out an anti-correlated pair;
    # what actually catches a bad cell is the colour distance and the flatness
    # test, both of which put every blank cell on these sheets far outside.
    ap.add_argument("--look-bar", type=float, default=1.30)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    kit = d / "parts"
    det = d / "detail"
    det.mkdir(parents=True, exist_ok=True)
    man = json.loads((d / f"parts_{args.face}.json").read_text())
    W, H = man["size"]

    # --apply is the loop's path: the parts are rebuilt every round and the
    # redraws have to go back on, but they must not be bought again.
    if args.apply:
        # FROM THE RECORD, NOT FROM THE FOLDER. Listing detail/ re-applied
        # every redraw ever written there, including ones a later pass refused
        # -- the checks had thrown out a garish repaint and the cache handed it
        # straight back, which is worse than never having checked. What was
        # accepted is written down; that is what gets laid.
        try:
            keep = json.loads((d / "detail.json").read_text()).get("redrawn", {})
        except Exception:
            keep = {}
        n = 0
        for name in keep:
            cached, src = det / f"{name}.png", kit / f"{name}.png"
            if not (cached.exists() and src.exists()):
                continue
            crop = Image.open(src).convert("RGBA")
            out = shape_like(Image.open(cached).convert("RGBA"), crop)
            out.save(src)
            n += 1
        print(f"  re-laid {n} redrawn fitting(s)")
        return

    want = [q for q in man["parts"] if wants_detail(q, W, H)]
    want.sort(key=lambda q: -((q["px"][2] - q["px"][0])
                              * (q["px"][3] - q["px"][1])))
    want = want[:args.sheets * PER_SHEET]
    if not want:
        print("  no fitting is small enough to need redrawing")
        return
    print(f"  {len(want)} of {len(man['parts'])} fittings are under 48px on a "
          f"side -- redrawing them large")

    ob = object_crop(d / f"{args.face}.png").convert("RGB")
    key = load_key()
    got = {}
    for s0 in range(0, len(want), PER_SHEET):
        group = want[s0:s0 + PER_SHEET]
        idx = s0 // PER_SHEET
        sheet = d / f"_detail_{args.face}_{idx}.png"
        ref = d / f"_detail_ref_{args.face}_{idx}.png"
        annotate(ob, [q["px"] for q in group]).save(ref)
        listing = "\n".join(
            f"  {i}. the one marked {i} on the reference -- "
            f"{q['name'].replace('_', ' ')}"
            for i, q in enumerate(group, 1))
        if args.redraw or not sheet.exists():
            try:
                generate_image(
                    PROMPT.format(asset=args.asset, cols=COLS, rows=ROWS,
                                  listing=listing),
                    sheet, key, refs=[ref])
            except Exception as e:
                print(f"  sheet {idx}: not drawn ({type(e).__name__})")
                continue
        try:
            cut = [trim(c) for c in cells(sheet, COLS, ROWS)]
        except Exception as e:
            print(f"  sheet {idx}: not splittable ({type(e).__name__})")
            continue
        # WHICH CELL IS WHICH IS MEASURED, NOT COUNTED OFF. The sheet is asked
        # for as three by two and this model drew one by two, two by four and
        # three by two on three consecutive sheets -- cells() reads the gutters
        # rather than trusting the request, which is right, and it means the
        # nth cell is not the nth fitting. Pairing them by position quietly
        # handed a coin slot the drawing of a vent; one such pair came back at
        # a colour distance of 223 and was refused, which is the check doing
        # its job and not a reason to keep guessing.
        #
        # A fitting and its drawing agree about two things no numbering is
        # needed for: the colour they are and the shape of their box. Matching
        # on those, best pair first, gets the assignment from the pictures
        # themselves.
        pool = list(enumerate(cut))
        pairs = []
        rank = []
        for gi, q in enumerate(group):
            src0 = kit / f"{q['name']}.png"
            if not src0.exists():
                continue
            c0 = Image.open(src0).convert("RGBA")
            for ci, cell in pool:
                rank.append((resemblance(cell, c0), gi, ci))
        rank.sort()
        used_g, used_c = set(), set()
        for _cost, gi, ci in rank:
            if gi in used_g or ci in used_c:
                continue
            used_g.add(gi)
            used_c.add(ci)
            pairs.append((group[gi], dict(pool)[ci], _cost))

        for q, cell, look in pairs:
            src = kit / f"{q['name']}.png"
            if not src.exists():
                continue
            crop = Image.open(src).convert("RGBA")
            want_rgb = median_rgb(crop)
            new = shape_like(cell, crop)
            got_rgb = median_rgb(new)
            if not want_rgb or not got_rgb:
                continue
            dist = sum(abs(a - b) for a, b in zip(want_rgb, got_rgb)) / 3
            # AND IT HAS TO BE MORE THAN THE THING IT REPLACES -- but "more"
            # is not "grainier than the same crop upscaled". A blurry upscale
            # spreads a difference across every pixel; crisp artwork has flat
            # regions with hard edges between them, and scores LOWER on mean
            # neighbour difference while carrying far more. Measured that way
            # a pair of properly louvred grilles came in under the smears they
            # replaced. What has to be caught is a redraw that is nearly
            # blank -- a white cell, a plain rectangle -- so the bar is an
            # absolute floor and a fraction of the crop's own grain at its own
            # scale, neither of which a real drawing ever fails.
            g_own = grain_px(crop.convert("RGB"))
            g_new = grain_px(new.convert("RGB"))
            flat = g_new < max(0.8, 0.25 * g_own)
            s_own, s_new = sat_p90(crop), sat_p90(new)
            repaint = not (0.45 * s_own - 10 <= s_new <= 1.6 * s_own + 10)
            ok = (look <= args.look_bar and dist <= args.colour_bar
                  and not flat and not repaint)
            print(f"    {q['name']:22} {crop.width}x{crop.height} -> "
                  f"{new.width}x{new.height}  looks {look:5.1f}  "
                  f"colour {dist:5.1f}  grain {g_own:5.2f}->{g_new:5.2f}  "
                  f"sat {s_own:5.1f}->{s_new:5.1f}  "
                  f"{'KEPT' if ok else 'refused'}")
            if ok:
                new.save(det / f"{q['name']}.png")
                new.save(src)
                got[q["name"]] = [new.width, new.height]

    for stale in det.glob("*.png"):
        if stale.stem not in got:
            stale.unlink()
    (d / "detail.json").write_text(json.dumps(
        {"face": args.face, "redrawn": got}, indent=1))
    print(f"  {len(got)} fitting(s) redrawn large -> {d / 'detail.json'}")


if __name__ == "__main__":
    main()
