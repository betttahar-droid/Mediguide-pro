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

THE MODEL IS SHOWN THE FITTING, NOT JUST TOLD WHERE IT IS. The reference is
the elevation with the group outlined on it AND the same fittings cut out and
magnified beside it. Without the magnifier a 10 by 13 pad is being described
rather than shown, and the model draws what a fitting of that name usually
looks like: all seven of the cabinet's flat dark recessed pads came back as
bright red arcade buttons and every one was refused. With it they come back
the colour they are.

AND ASKED AGAIN WHEN REFUSED. The drawings vary enormously run to run -- the
same pad scored a colour distance of 10 on one sheet and 82 on the next from
an identical prompt and reference -- so a refusal is a verdict on one drawing,
not on the fitting. About half pass first time; three rounds of asking again
for only the failures costs one sheet per three of them.

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
  no paper  it must not have bare sheet in it. The deck came back drawn in
            perspective, a slab seen from above with its sloped top edge
            cutting across the panel, and the paper above and below the slab
            is INSIDE the content's bounding box where no trim can reach it.
            Forced into the part's rectangle it is a bar of blown-out white
            lying across the deck.
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
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402
from identify_parts import object_crop  # noqa: E402
from material_atlas import cells, grain_px  # noqa: E402
from region_parts import annotate  # noqa: E402

# THREE TO A SHEET, AND THE LAYOUT IS NOT THE REASON. Asked for three by two
# the model drew one by two, two by four and three by two on three consecutive
# sheets, and asked for a row of three it drew a column of four; the sheets it
# returns are read by cells(), which cuts on whatever gutters are actually
# there and does not care which way they run. What three buys is AREA: six
# fittings to a sheet gives each of them a quarter of what three do, and a
# quarter is most of the difference this whole tool exists to make. It also
# keeps the palette consistent within each group.
COLS, ROWS = 3, 1
PER_SHEET = COLS * ROWS

PROMPT = """A FITTINGS SHEET for a {asset}, in the style of the attached
reference.

THE REFERENCE has the {asset}'s elevation on the left with {cols} fittings
outlined and numbered on it, and on the right the SAME {cols} fittings cut out
and magnified, numbered to match. The magnified cut-outs are blocky because
they are only a few pixels across -- that is exactly why they are being
redrawn. They are the authority on what each fitting IS: its shape, its
colours, whether it is light or dark, raised or recessed.

Draw a SINGLE ROW of exactly {cols} square panels side by side on a pure white
background, with a wide white gutter between the panels and a wide white margin
around the whole row. Exactly {cols} panels, left to right, no more and no less.

Each panel is ONE FITTING of this {asset}, drawn LARGE and filling its panel
edge to edge, exactly as the reference shows it, in this order:

{listing}

EVERY PANEL MUST BE:

  - THE SAME FITTING as the numbered cut-out, in the same shape, the same
    proportions, the same colours and the same state of wear. This is that
    cut-out drawn bigger and sharper, not a new design of it and not what a
    fitting of that name usually looks like. If the cut-out is a dark grey
    recessed pad, draw a dark grey recessed pad -- not a red button.
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


def wants_detail(q, W, H, small=48, long_side=5.0):
    """Is this fitting too small on the sheet to carry its own detail?

    Measured on the SHORTER side, because that is what limits it: a strip 80 by
    10 has plenty of pixels and none of them where it needs them. Anything
    already big enough is left alone -- a screen or a marquee is drawn at a
    size the sheet can afford and redrawing it would only risk changing it.

    BUT NOT A STRIP LONGER THAN ABOUT FIVE TO ONE, whatever its short side.
    The panel it would be drawn into is square, and past about 5:1 the model
    stops drawing the fitting and starts drawing something that fits: the
    cabinet's control deck is 229 by 26, and what came back was a plain dark
    bar with a light grey band across it -- no joysticks, no buttons, nothing
    of the deck at all. Laid into the deck's box that band renders as a bar of
    near-white lying across the controls, which is how it was found.

    IT WAS NOT FOUND BY ANY CHECK, and not for want of trying. That pairing
    passed the colour distance (41.7 against a bar of 58), the palette check,
    the grain floor and the paper fraction, and five further measures were
    tried against the run's twenty-one accepted redraws before this rule was
    written: two-dimensional NCC at 64px (the bad pair scored 0.2, a good
    joystick 0.1); NCC of the row and column luminance profiles (bad 0.31/0.11,
    good grille -0.01/0.82); the top and bottom deciles of luminance (the bad
    one is DARKER than what it replaces on both); the median colour; and the
    saturation percentile. Not one separates them, because a redraw is a
    different rendering and the honest ones differ from their crop about as
    much as the wrong ones do. There is no statistic here to tune, so the
    answer is to stop asking for the drawing that cannot be made.

    A fitting this excludes keeps the artwork it was cut from, which for a
    strip that long is a good deal of artwork.
    """
    x0, y0, x1, y1 = q["px"]
    w, h = x1 - x0, y1 - y0
    return (min(w, h) < small and w >= 4 and h >= 4
            and max(w, h) <= long_side * max(1, min(w, h)))


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


def paper_frac(im, lo=228, grey=14):
    """How much of the drawing is bare sheet.

    The prompt asks for a flat orthographic fitting filling its panel, and
    what comes back is sometimes the fitting drawn in PERSPECTIVE -- the
    control deck as a slab seen from above and in front, with its sloped top
    edge cutting across the panel. Trimming to the content cannot help: the
    content's bounding box is the panel, and the paper is INSIDE it, above
    and below the slab. Squeezed into the part's rectangle that paper becomes
    what the render showed, a bar of blown-out white lying across the deck.

    A fitting that fills its panel has no bare sheet in it at all: of fifteen
    accepted redraws thirteen measured 0.0% and the other two 0.1% and 0.4%,
    while the deck measured 13.5% and a bad cell 28.6%.
    """
    px = im.convert("RGBA").load()
    n = w = 0
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            n += 1
            if min(r, g, b) >= lo and max(r, g, b) - min(r, g, b) <= grey:
                w += 1
    return w / max(1, n)


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


def reference(ob, group, kit, side=1000):
    """The elevation with the three marked on it, AND the three blown up.

    THE MARKED ELEVATION ALONE IS NOT A REFERENCE FOR A TEN-PIXEL PAD. It is
    the whole point of this tool that a 10 by 13 fitting carries almost no
    information, and the reference was handing the model exactly that
    information and asking for "the same colours, the same shape, the same
    wear". It did the only thing it could and drew what a button generally
    looks like: every one of the cabinet's seven button pads -- flat dark
    recessed rectangles -- came back as a bright red arcade button, and every
    one was refused on colour or on palette. The magnifier does not create
    detail, but it puts what detail there is where the model can see it, and
    it makes "these three, in these colours" a thing the picture says rather
    than a thing the prompt asserts.

    Nearest-neighbour, because the fitting's few pixels are the evidence and
    smoothing them is editorialising.
    """
    left = annotate(ob, [q["px"] for q in group])
    tiles, pad, num = [], 16, 1
    for q in group:
        src = kit / f"{q['name']}.png"
        c = (Image.open(src).convert("RGBA") if src.exists()
             else ob.convert("RGBA").crop(tuple(q["px"])))
        # onto white, so alpha does not read as part of the drawing
        flat = Image.new("RGB", c.size, (255, 255, 255))
        flat.paste(c.convert("RGB"), (0, 0), c.split()[3])
        k = max(1, min(24, (side // 2 - 2 * pad) // max(1, c.width),
                       (side // 3 - 2 * pad) // max(1, c.height)))
        tiles.append(flat.resize((c.width * k, c.height * k), Image.NEAREST))
    cw = max([t.width for t in tiles] + [1]) + 2 * pad
    ch = sum(t.height + 2 * pad for t in tiles)
    right = Image.new("RGB", (cw, max(ch, 1)), (255, 255, 255))
    dr = ImageDraw.Draw(right)
    y = pad
    for t in tiles:
        right.paste(t, ((cw - t.width) // 2, y))
        dr.rectangle([(cw - t.width) // 2 - 1, y - 1,
                      (cw + t.width) // 2, y + t.height], outline=(255, 0, 255))
        dr.rectangle([(cw - t.width) // 2 - 1, y - 1,
                      (cw - t.width) // 2 + 12, y + 14], fill=(255, 0, 255))
        dr.text(((cw - t.width) // 2 + 3, y + 2), str(num), fill=(255, 255, 255))
        num += 1
        y += t.height + 2 * pad
    H = max(left.height, right.height)
    out = Image.new("RGB", (left.width + right.width + pad, H), (255, 255, 255))
    out.paste(left, (0, (H - left.height) // 2))
    out.paste(right, (left.width + pad, 0))
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
    ap.add_argument("--sheets", type=int, default=14,
                    help="cap on sheets drawn; 14 covers a whole prop")
    ap.add_argument("--colour-bar", type=float, default=58.0)
    # the look score's job is MATCHING, not judging: a redraw is a different
    # rendering of the same thing, so even a perfect pairing correlates only
    # loosely. It is bounded here only to throw out an anti-correlated pair;
    # what actually catches a bad cell is the colour distance and the flatness
    # test, both of which put every blank cell on these sheets far outside.
    ap.add_argument("--look-bar", type=float, default=1.30)
    ap.add_argument("--paper-bar", type=float, default=0.04,
                    help="most of the redraw that may be bare sheet")
    ap.add_argument("--tries", type=int, default=3,
                    help="rounds of redrawing for the ones refused")
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

    # SMALLEST FIRST, BECAUSE THAT IS WHAT THE TOOL IS FOR. This sorted by
    # area DESCENDING, and the cabinet wants thirty-four fittings redrawn
    # against a budget of eighteen: the sixteen it dropped were every button
    # pad, both coin slots and six of the decals -- a ten by thirteen button
    # is exactly the thing that cannot carry its own detail, and it was being
    # skipped in favour of a control deck that already had two hundred and
    # twenty-nine pixels to work with. Ordered by the side that limits it, a
    # budget that does bite now falls on the fittings that least need the
    # help. The budget is also large enough now to cover a whole prop.
    want = [q for q in man["parts"] if wants_detail(q, W, H)]
    want.sort(key=lambda q: (min(q["px"][2] - q["px"][0],
                                 q["px"][3] - q["px"][1]),
                             (q["px"][2] - q["px"][0])
                             * (q["px"][3] - q["px"][1])))
    over = max(0, len(want) - args.sheets * PER_SHEET)
    want = want[:args.sheets * PER_SHEET]
    if not want:
        print("  no fitting is small enough to need redrawing")
        return
    print(f"  {len(want) + over} of {len(man['parts'])} fittings are under "
          f"48px on a side -- redrawing {len(want)} of them large"
          + (f" ({over} over budget)" if over else ""))

    ob = object_crop(d / f"{args.face}.png").convert("RGB")
    key = load_key()
    got = {}

    def run(todo, attempt):
        for s0 in range(0, len(todo), PER_SHEET):
            group = todo[s0:s0 + PER_SHEET]
            idx = s0 // PER_SHEET
            # KEYED ON WHAT IS ON IT, NOT ON WHERE IT CAME IN THE RUN. The cache
            # was `_detail_front_0.png` and so on, which is only correct while the
            # grouping never changes -- reorder the fittings, or add one, and
            # sheet 0 holds a drawing of three fittings that are no longer the
            # three this sheet is asking about, and the matcher pairs them anyway
            # because it pairs whatever it is given. The names on the sheet name
            # the sheet, so a regrouping simply misses the cache and redraws.
            tag = hashlib.sha1(
                (",".join(q["name"] for q in group)
                 + f"#{attempt}").encode()).hexdigest()[:8]
            sheet = d / f"_detail_{args.face}_{tag}.png"
            ref = d / f"_detail_ref_{args.face}_{tag}.png"
            reference(ob, group, kit).save(ref)
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
            #
            # ORDER IS STILL EVIDENCE, THOUGH, and it was being thrown away
            # entirely. The fittings are listed in the prompt in order, the
            # reference numbers them in that order, and cells() now returns
            # what it found top to bottom and then left to right -- which is
            # how a model lays out a numbered list whichever way it decides to
            # run it. That is worth nothing when the sheet came back with a
            # different number of drawings than were asked for, and worth a
            # tiebreak when it came back with exactly as many. The weight is
            # small on purpose: a clearly better resemblance still wins, and
            # order only decides pairs the pictures cannot.
            pool = list(enumerate(cut))
            ordered = len(cut) == len(group)
            pairs = []
            rank = []
            for gi, q in enumerate(group):
                src0 = kit / f"{q['name']}.png"
                if not src0.exists():
                    continue
                c0 = Image.open(src0).convert("RGBA")
                for ci, cell in pool:
                    bias = 0.15 * abs(gi - ci) if ordered else 0.0
                    look = resemblance(cell, c0)
                    rank.append((look + bias, look, gi, ci))
            rank.sort()
            used_g, used_c = set(), set()
            for _bias, look, gi, ci in rank:
                if gi in used_g or ci in used_c:
                    continue
                used_g.add(gi)
                used_c.add(ci)
                # the bar is checked against the resemblance itself; the order
                # bias picks the pairing and has no business in the verdict
                pairs.append((group[gi], dict(pool)[ci], look))

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
                pap = paper_frac(new)
                ok = (look <= args.look_bar and dist <= args.colour_bar
                      and not flat and not repaint and pap <= args.paper_bar)
                print(f"    {q['name']:22} {crop.width}x{crop.height} -> "
                      f"{new.width}x{new.height}  looks {look:5.1f}  "
                      f"colour {dist:5.1f}  grain {g_own:5.2f}->{g_new:5.2f}  "
                      f"sat {s_own:5.1f}->{s_new:5.1f}  paper {100*pap:4.1f}%  "
                      f"{'KEPT' if ok else 'refused'}")
                if ok:
                    new.save(det / f"{q['name']}.png")
                    new.save(src)
                    got[q["name"]] = [new.width, new.height]

    # A REFUSAL IS NOT A VERDICT ON THE FITTING, it is a verdict on one
    # drawing of it, and the drawings vary enormously run to run: the same
    # button pad came back at a colour distance of 10 on one sheet and 82 on
    # the next, from an unchanged prompt and an unchanged reference. About
    # half of them pass at the first attempt, so a single pass loses half the
    # prop's small fittings to nothing more than the roll of the dice. Asking
    # again for only the ones that failed costs a sheet per three of them and
    # takes the miss rate down with each round.
    todo = want
    for attempt in range(max(1, args.tries)):
        if not todo:
            break
        if attempt:
            print(f"  {len(todo)} fitting(s) not yet good enough -- "
                  f"attempt {attempt + 1}")
        run(todo, attempt)
        todo = [q for q in todo if q["name"] not in got]

    for stale in det.glob("*.png"):
        if stale.stem not in got:
            stale.unlink()
    (d / "detail.json").write_text(json.dumps(
        {"face": args.face, "redrawn": got}, indent=1))
    print(f"  {len(got)} of {len(want)} fitting(s) redrawn large "
          f"-> {d / 'detail.json'}")


if __name__ == "__main__":
    main()
