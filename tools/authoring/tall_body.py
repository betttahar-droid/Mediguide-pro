#!/usr/bin/env python3
"""Draw the extra carcass a taller prop needs, where there is nowhere to repeat.

    python3 tools/authoring/tall_body.py work/ps1 --asset "jukebox"
    python3 tools/authoring/tall_body.py --sweep

Authoring tool. NOT a build, CI or runtime dependency.

WHY. `wide_art` buys the missing WIDTH for the parts no rule can widen. The
obvious next move is the same thing on the other axis, and measuring it says
there is nothing there: of 31 parts across the corpus carrying a `spany` rule,
ZERO are tall, non-countable and without a vertical band. The symmetry does not
hold, and the reason is plain once measured -- a part that must lengthen is a
leg, a column, a rail or a tube, and those are uniform along their length by
what they are, so a band is always found. The parts that carry art are WIDE.

THE ENTIRE TALLER-AXIS NEED IS THE BODY. Sixteen props reach the renderer with
no growth band at all, because `strip_slice` could find nowhere on them bare
enough to repeat, and the carcass then stretches uniformly: a jukebox's
semicircular arch comes out as a bullet, an arcade cabinet's screen grows with
the cabinet. That is the fault, and it is one fault on sixteen props rather than
a scattering across hundreds of parts.

AND THE BAR THOSE PROPS FAILED IS ABOUT REPEATING, NOT ABOUT DRAWING. Copies of
rows carrying artwork duplicate that artwork -- that is the whole reason
`strip_slice` demands bareness, and every entry in its four reverted lists is
about that. Nothing in it forbids DRAWING new body into those rows. A place too
covered to repeat is exactly where the body score said the body is, which is the
place a taller one of this machine actually gains height. So the band the veto
throws away is recorded as `stretch_band` and this asks for it to be filled.

WHAT IS SHOWN, and it is the BACKGROUND rather than the elevation. `bg_front`
is the drawing with every fitting lifted out and its hole patched, so asking for
more of it cannot duplicate a coin slot, a sign or a grille -- they are not in
the picture. The parts go back on top afterwards at their own sizes, by their
own rules, which is what they already do.

    the canvas   bg_front with a magenta band inserted at the stretch band,
                 as tall as the height the prop is short of
    the ask      fill the magenta with more of this machine's body
    the keep     everything outside the band is composited back EXACTLY; only
                 the new rows are the model's

That is `paint_out`'s trick and `wide_art`'s, for the third time, and its note
is the reason: holes are shown, not described.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))

# Below this the prop is barely taller and a stretch is not worth a model call.
MIN_TALL = 1.15
# wide_art's bars, and its reasoning: a continuation is not a copy, so the
# similarity score is a FLOOR against the model duplicating what is beside it,
# and the palette is the thing that must match.
MIN_UNLIKE = 0.25
MAX_TINT = 48
# AND THE JOIN MUST NOT BE A LINE THE PROP DOES NOT HAVE.
#
# The first reply passed both bars above -- 0.99 unlike, tint 0 -- and had drawn
# a distinct PANEL let into the body with a hard light rule across the top and
# bottom of it, which is the one thing the prompt forbids in as many words.
# Neither a palette check nor a similarity check can see a seam: the material
# either side is the right colour and the right kind of thing, and what is wrong
# is the two rows where they meet.
#
# It is very measurable. `row_diff` at the joins came back 46.3 and 40.3 against
# a median of 0.98 and a p90 of 1.55 for the whole image -- 47x and 30x. The bar
# does not need choosing, because the prop's own drawing sets it: the busiest
# row anywhere in the drawn background is 8.30, so a join is allowed to be as
# busy as the strongest line this machine really has and no busier. The refused
# reply is 5.6x that.
SEAM_X = 1.0        # times the busiest row in the prop's own drawn background
# AND ACROSS THE BAND AS WELL AS ALONG IT -- "quiet along one axis is not quiet",
# which CLAUDE.md records three separate faults for. The seam check above looks
# at ROW differences at the two horizontal joins, and the second reply passed it
# at 1.0 of 8.3 with a clean continuation of the wood, and had a bright WHITE
# STRIPE down the left and right edges of the new band where its material met
# the image border. A row-wise test structurally cannot see a vertical line.
#
# Measured per column, the new rows against the forty above and below: median
# deviation 0.9, interior max 18.3, and the edge columns 209 and 211. The prop's
# own drawing sets the bar again -- the worst per-column step between adjacent
# forty-row strips of the real background is 53.8, so the stripe is 3.9x
# something the drawing does and the interior is 0.34x it.
COL_X = 1.0         # times the drawn background's own worst column step
JOIN = 8            # rows of real prop the cut must leave on each side of it,
                    # the same floor `extra` is clamped to -- a band joins body
                    # at both ends and cannot join to the sheet
HALF = 0.5          # of the prop's own median row width: narrower than this and
                    # the band is a dome tip or a foot, not a place to grow
MAGENTA = (255, 0, 255)

PROMPT = """The attached image is the front of a {asset} with all of its
fittings taken off -- the bare body, its panels, its trim and its wear.

A FLAT MAGENTA BAND runs across it. This is the same {asset} built TALLER, and
the magenta is the extra body it gains.

FILL THE MAGENTA, and change nothing else.

  - Continue the body through it. Whatever runs into the band from above and
    below should run through and MEET: a panel line, a moulding, a wood grain,
    a seam, a streak of grime, a colour gradient. The result must read as one
    continuous piece of this machine, not as a patch let into it.
  - THE REST OF THE IMAGE MUST COME BACK EXACTLY AS IT IS. Do not redraw it, do
    not move anything, do not recolour it, do not sharpen or clean it up.
  - Do NOT add fittings. No doors, grilles, vents, slots, buttons, signs,
    lettering, badges or panels with a function. This is PLAIN BODY: the
    machine is taller, not better equipped.
  - Do NOT repeat something that appears once above or below the band.
  - No magenta may remain anywhere in the result.

FLAT ORTHOGRAPHIC FRONT VIEW, filling the canvas edge to edge. No perspective,
no drop shadow, no glow, no frame. Hand-painted PlayStation-era look, low
resolution, the palette taken from the body around the band.
"""


def needs(prop_dir, face="front"):
    """(band, ratio) when this prop stretches and could be drawn instead."""
    d = Path(prop_dir)
    try:
        s = json.loads((d / f"strips_{face}.json").read_text())
        sr = json.loads((d / "scale_rules.json").read_text())
    except Exception:
        return None, 1.0
    hx = float(sr.get("max_taller") or 1.0)
    band = s.get("stretch_band")
    if not band:
        return None, hx
    # A PROP WITH BANDS IS LEFT ALONE -- unless every one of them is a MEMBER.
    # Then the members lengthen, correctly, and the body behind them gains
    # nothing: what repeats there is the patched hole the members were lifted
    # out of, which is why v52_jukebox came back with its bubbler tubes running
    # the full height over a blank wood midsection, called by both judges and by
    # resize_audit independently. strip_slice marks that case `with_members`.
    # ... or every one of them is BUSY ON A FLANK. strip_slice marks that
    # `flank_busy`: the front's band is bare and repeating it is fine for the
    # front, but the side and back carry artwork across those same rows and a
    # taller prop stacks it. Drawing the band makes every face agree -- gOfT
    # reads the drawn rows rather than copying, on the flanks exactly as on the
    # front -- which is why the front is drawn here too rather than left to
    # repeat while the flanks are drawn. Two growth models on one prop would put
    # the flank's inserted rows somewhere gOfT does not have them.
    if s.get("grow_bands") and not (band.get("with_members")
                                    or band.get("flank_busy")):
        return None, hx
    # AND A MEMBER WITH NO BODY BEHIND IT GAINS NOTHING EITHER.
    #
    # The clause above was shipped one prop wide and flagged as an over-reach in
    # its own commit message, because "every growth place is a member" is true
    # of 10 props and every pinball in the corpus is among them -- and the
    # pinball's taller render is RIGHT. A leg has nothing behind it to go blank.
    #
    # SCOPED TO MEMBER BANDS, because that is the entire population its two
    # thresholds were set from -- 12 bands, all of them `side: itself`. A
    # flank_busy band is a measured RUN, whose `part` is "(measured)" and whose
    # boxes therefore match nothing, so `behind` collapses to `solid` and the
    # check silently becomes a different one. Whether a run band has body to
    # grow is already answered by place_cut's width test.
    if band.get("with_members") and not body_behind(d, s["grow_bands"], face):
        return None, hx
    return band, hx


# The two thresholds below are the whole of the distinction, and they are set
# from the 12 member bands that exist -- which is the entire population this
# question is asked of, so this is a full sweep and not a fit to one prop.
#
#        behind  solid   prop                  the band
#          0.0%  53.0%   v45_pinball           cabinet_body
#          0.4%  99.6%   v49_pinball           backglass
#          0.5%  50.9%   v47_pinball           cabinet_front
#          0.5%  50.9%   v49_pinball           coin_door_panel
#          4.9%  21.4%   v44_pinball           leg_left+leg_right
#          8.7%  24.8%   v46_pinball           leg_left+leg_right
#       -------------------------------------- draw nothing above this line
#         10.6%  99.6%   v45_arcade_cabinet    coin_door+control_deck+cabinet_door
#         34.2%  68.3%   v52_jukebox           bottom_rail
#         63.4%  96.5%   v52_jukebox           bubbler tubes x10
#         69.3%  96.1%   v45_jukebox           side_pillar x4
#         77.1%  96.4%   v46_jukebox           bubble_tube x4
#         83.2%  99.7%   v45_vending_machine   coin_return_door
#
# Every pinball above the line, every other prop below it, and the renders
# agree: v44's band is the gap between two legs and is magenta from edge to
# edge; v52's is the middle of a solid cabinet with tubes lying on it.
#
# ONE threshold would do it -- behind < 0.10 separates 8.7 from 10.6 -- and it
# is not used, because a 1.9-point gap is a number fitted to this corpus. Two
# rules each sit in the middle of a wide one, and each states a different
# physical fact about why there is no carcass to draw.
AIR = 0.45      # of the band's rows is not prop at all: nothing stands there
OWN = 0.02      # of the band's rows is prop that is not the member: it IS the body


def body_behind(d, bands, face="front"):
    """Is there carcass behind these members for a taller prop to gain?

    Two ways the answer is no, and they are not the same shape:

      NOTHING STANDS THERE. The band's rows are mostly air -- a pinball's legs
      with the floor showing between them, 21% and 25% solid against 68% and up
      for everything else. Growing the body means growing the legs, which the
      member rule already does.

      THE MEMBER IS THE BODY. Every solid pixel at those rows belongs to the
      member itself -- `cabinet_body` on v45_pinball, which is the cabinet. The
      member lengthening IS the body lengthening; there is no second thing.

    Read off bg_front.png and NOT front.png. front.png is the uncropped RGB
    elevation, sheet and all, opaque at every pixel: the first version of this
    measured its alpha, got "100% solid" for every row of every prop, and ranked
    the pinball's legs as having MORE body behind them than a jukebox's bubbler
    tubes. A silhouette measured off an image with no silhouette in it.
    """
    from PIL import Image
    import numpy as np
    try:
        alpha = np.array(Image.open(d / f"bg_{face}.png").convert("RGBA"))[..., 3] > 128
        pf = json.loads((d / f"parts_{face}.json").read_text())
    except Exception:
        return True          # cannot tell: leave the band alone, do not skip it
    H, W = alpha.shape
    if tuple(pf.get("size", ())) != (W, H):
        return True          # different frames; the boxes would not line up
    box = {p["name"]: p["px"] for p in pf.get("parts", []) if p.get("px")}

    for b in bands:
        y0, y1 = max(0, int(b["px"][0])), min(H, int(b["px"][1]))
        if y1 <= y0:
            continue
        own = np.zeros((H, W), bool)
        for nm in str(b.get("part", "")).split("+"):
            bx = box.get(nm)
            if bx:
                x0, by0, x1, by1 = [int(v) for v in bx]
                own[max(0, by0):min(H, by1), max(0, x0):min(W, x1)] = True
        strip = alpha[y0:y1]
        solid = strip.mean()
        behind = (strip & ~own[y0:y1]).mean()
        if solid < AIR or behind < OWN:
            return False
    return True


def place_cut(d, band, H, face="front"):
    """Where to insert, which must not be inside a part.

    strip_slice says this about its own cut in as many words: "Inserting there
    slid the hole out from under the door, which is anchored to the bottom, and
    tore the cabinet open." Taking the band's midpoint put the jukebox's 416 new
    rows through the middle of speaker_grille -- the grille slid to the floor and
    the new body opened between the song list and the selection display, which is
    nowhere a jukebox gains height.

    On these props EVERY row is inside some part, because having nowhere bare is
    why they are here at all. So the cut goes where the FEWEST parts cover, and a
    tie goes to a part BOUNDARY: a row where one part ends or the next begins is
    a seam the drawing already has, and inserting at it slides parts apart rather
    than through them.
    """
    a, b = int(band["px"][0]), int(band["px"][1])
    mid = (a + b) // 2
    cover = [0] * (H + 1)
    edges = set()
    try:
        pj = json.loads((d / f"parts_{face}.json").read_text())
        for q in pj.get("parts", []):
            x0, y0, x1, y1 = q["px"]
            for y in range(max(0, y0), min(H, y1)):
                cover[y] += 1
            edges.add(max(0, y0)); edges.add(min(H, y1))
    except Exception:
        pass
    lo, hi = max(0, min(a, b)), min(H, max(a, b))
    if hi <= lo:
        lo, hi = 0, H

    # AND IT MUST BE INSIDE THE PROP, WHICH THE SCORE ABOVE MAKES CERTAIN IT IS
    # NOT. Row 0 is covered by no part at all and is a part boundary, so it wins
    # on both keys and loses only the tiebreak -- and a band starting at row 0
    # hands it the range to win in. v17_jukebox cut at 0 with a band of 0..216,
    # v18_jukebox at 0 with 0..11, v25_jukebox at 0 with 0..15: three props
    # opening 269, 264 and 391 rows of new body ABOVE THEIR OWN CROWNS rather
    # than through them. It surfaced as a crash in check() -- `above` is a
    # zero-height crop and median_rgb of nothing is None -- which is the only
    # reason it was seen at all, and the crash is the symptom, not the fault.
    #
    # A cut joins new body to old at BOTH its ends, so it needs prop on both
    # sides. The silhouette says where the prop is; JOIN is the same 8 rows the
    # extra height is floored at, so the margin is a number already in this file
    # rather than a new one.
    wide = None
    try:
        import numpy as np
        from PIL import Image
        al = np.array(Image.open(d / f"bg_{face}.png").convert("RGBA"))[..., 3] > 128
        rows = np.flatnonzero(al.any(axis=1))
        if len(rows):
            top, bot = int(rows[0]), int(rows[-1])
            lo, hi = max(lo, top + JOIN), min(hi, bot - JOIN)
            if hi <= lo:                 # the band lies outside the body
                lo, hi = top + JOIN, bot - JOIN
            if hi <= lo:                 # the prop is too short to cut at all
                return None, 0, False

            # AND WHERE THE PROP IS WIDE, NOT MERELY WHERE IT IS PRESENT.
            #
            # The margin above is necessary and not sufficient: clamped to it,
            # v18_jukebox and v25_jukebox cut at row 8, which is inside the tip
            # of a domed crown. The band handed to the model spans the whole
            # canvas width, so at a row where the prop is 20 pixels of 300 the
            # request is 280 pixels of magenta OUTSIDE the object -- which is
            # the exact fault this file already records two paragraphs down, the
            # one that came back with four replies painting the outside white.
            #
            # The bar is the prop's OWN median row width, so it needs no
            # choosing: a cabinet's mid-body is at or above it and a dome tip is
            # nowhere near. Where the band offers nothing that wide -- a prop
            # tapered along its whole height -- the widest row in the band is
            # taken instead, because the band is still where the prop was
            # measured to grow and a narrower join beats no drawing at all.
            w = al.sum(axis=1)
            bar = float(np.median(w[w > 0]))
            wide = [y for y in range(lo, hi + 1) if w[y] >= bar]
            if not wide:
                best = max(range(lo, hi + 1), key=lambda y: w[y])
                # AND WHERE THE BAND OFFERS NOWHERE WIDE ENOUGH, THERE IS NO
                # HONEST PLACE TO OPEN ONE. Three props in the corpus have a
                # band that is wrong at source -- v18_jukebox at rows 0..11 and
                # v25_jukebox at 0..15 are the crown of a domed arch, a sliver
                # of prop; v16_vending_machine at 606..617 is the foot strip
                # under a featureless slab. Their widest rows are 0.37, 0.43
                # and 0.18 of their own median, against 1.00 or better for
                # every one of the other fourteen. Drawing there hands the
                # model a request that is mostly outside the object, which is
                # the failure two paragraphs down; stretching a slab that
                # carries no artwork is the better of the two.
                #
                # HALF sits in the middle of that gap -- 0.43 to 1.00, a factor
                # of 2.3 with nothing in it -- and it is a ratio to the prop's
                # own median rather than a width in pixels.
                if w[best] < HALF * bar:
                    return None, 0, False
                wide = [best]
    except Exception:
        pass

    span = wide if wide else list(range(lo, hi + 1))
    cut = min(span, key=lambda y: (cover[y], 0 if y in edges else 1, abs(y - mid)))
    return cut, cover[cut], (cut in edges)


def check(src, got, cut, extra, W, H):
    """Why this drawing is not usable, as a sentence, or None if it is.

    Every one of these is quoted back to the model on the next attempt, so each
    has to say what is wrong in terms the model can act on -- and each bar comes
    from the prop's OWN drawing rather than from a number chosen here.
    """
    import numpy as np
    from PIL import Image
    from detail_sheet import resemblance, median_rgb
    from strip_slice import row_diff

    new = got.crop((0, cut, W, cut + extra))
    # WHAT THE BAND IS JUDGED AGAINST IS WHAT IT JOINS, AND THERE MAY BE LESS OF
    # IT THAN extra. This was `cut - extra`, unclamped: on a cut near the top of
    # the prop it is a zero-height crop, median_rgb of nothing is None, and the
    # whole check raised TypeError instead of returning a verdict -- three props
    # scored as refusals by a benchmark that was measuring image models. The cut
    # is now kept inside the body (see place_cut), so this cannot go to zero;
    # it is clamped anyway, because a check that crashes reports nothing and a
    # check that reports nothing is indistinguishable from one that passed.
    above = src.convert("RGB").crop((0, max(0, cut - extra), W, cut))
    if above.height < 1:
        return ("the cut sits at the very top of the prop, so the new band has "
                "no body above it to continue from.")
    a0 = np.asarray(src.convert("RGB")).astype(float)
    g = np.asarray(got).astype(float)

    left = int(((np.abs(g[:, :, 0] - 255) < 40) & (g[:, :, 1] < 60)
                & (np.abs(g[:, :, 2] - 255) < 40)).sum())
    if left > 0.02 * extra * W:
        return (f"{left} pixels of the magenta came back unfilled. Every "
                f"magenta pixel must become body.")

    # THE SEAM, which no palette or similarity test can see. The first reply
    # passed both of those at 0.99 and 0 and had drawn a distinct PANEL let into
    # the body with a hard rule across each join -- the one thing the prompt
    # forbids in as many words. row_diff at the joins came back 46.3 and 40.3
    # against a median of 0.98. The bar needs no choosing: the prop's own
    # busiest row is 8.30.
    worst_row = max(row_diff(src.convert("RGB")) or [1.0])
    rd = row_diff(got)
    joins = [max(rd[max(0, y - 3):y + 4] or [0])
             for y in (cut, cut + extra) if 0 < y < len(rd)]
    seam = max(joins) if joins else 0.0
    if seam > SEAM_X * worst_row:
        return (f"the top and bottom of the new band are hard horizontal "
                f"lines -- a row difference of {seam:.0f} where the strongest "
                f"line anywhere on this machine is {worst_row:.0f}. You drew a "
                f"separate panel let into the body. The body must run THROUGH "
                f"the band with nothing to see where it joins.")

    # AND ACROSS IT AS WELL AS ALONG IT -- "quiet along one axis is not quiet".
    # A row-wise test cannot see a vertical line, and a reply that painted its
    # left four columns white scored 209 there against an interior max of 18.
    #
    # AGAINST THE ORIGINAL'S ROWS, NEVER THE REPLY'S. Compared to its own
    # neighbours the white reply agreed with itself at 10 and passed. Comparing
    # a reply against itself measures its consistency, not its correctness.
    band = g[cut:cut + extra].mean(axis=(0, 2))
    ref = np.r_[a0[max(0, cut - 40):cut], a0[cut:cut + 40]].mean(axis=(0, 2))
    col = float(np.abs(band - ref).max()) if len(ref) else 0.0
    steps = [float(np.abs(a0[y - 40:y].mean(axis=(0, 2))
                          - a0[y:y + 40].mean(axis=(0, 2))).max())
             for y in range(40, a0.shape[0] - 40, 20)]
    worst_col = max(steps) if steps else 255.0
    if col > COL_X * worst_col:
        return (f"the new band has a vertical edge down it: one column differs "
                f"from the body above and below by {col:.0f}, where the biggest "
                f"such step on this machine is {worst_col:.0f}. Do not draw a "
                f"border, a frame or a lighter strip at the sides -- the body "
                f"reaches the edge of the canvas exactly as it does elsewhere.")

    unlike = resemblance(new, above)
    tint = sum(abs(x - y) for x, y in zip(median_rgb(new), median_rgb(above))) / 3
    if unlike < MIN_UNLIKE:
        return (f"the new band is a copy of the rows just above it. It should "
                f"be a continuation of the body, not a repeat of a piece of it.")
    if tint > MAX_TINT:
        return (f"the new band's colour is {tint:.0f} away from the body it "
                f"joins. Take the palette from the rows either side of it.")
    return None


def draw(prop_dir, asset, face="front", redraw=False):
    from PIL import Image
    import numpy as np
    from concept_sheet import generate_image, load_key
    import image_ledger
    from detail_sheet import median_rgb

    d = Path(prop_dir)
    band, hx = needs(d, face)
    if band is None:
        print("this prop has somewhere to repeat, or no band recorded: "
              "nothing to draw")
        return None
    if hx < MIN_TALL:
        print(f"max_taller is {hx:.2f}: barely taller, nothing to draw")
        return None
    bg = d / f"bg_{face}.png"
    if not bg.exists():
        print("no background on disk yet")
        return None
    dst = d / f"bg_{face}_tall.png"
    if dst.exists() and not redraw:
        print("  already drawn")
        try:
            return json.loads((d / "tall_body.json").read_text())
        except Exception:
            return None

    src = Image.open(bg).convert("RGBA")
    W, H = src.size
    extra = int(round((hx - 1.0) * H))
    # THE BAND CARRIES THE WHOLE GROWTH, because the renderer gives it the whole
    # growth. This used to be SHARED with the members -- the members keep
    # lengthening, so the body was given only its own fraction of the extra
    # height, on the reasoning that a prop should not both grow its tubes to
    # full height and gain a full band of new carcass.
    #
    # That reasoning is about how much new material to SHOW. The renderer is not
    # having that conversation. `drawnBand` replaces the member bands in gOfT
    # outright and is handed a share of 1.0, so the band absorbs every row the
    # prop grows by; the members lengthen separately, through their own parts'
    # spany_repeat, and contribute nothing to the body's height. So a texture
    # drawn for a fraction of the growth gets stretched to cover all of it.
    #
    # v52_jukebox is the case, and it is severe. Its band was drawn 90 rows tall
    # against a 594-row prop -- enough for 1.151x -- and at the 1.6x its own
    # scale rule asks for it is stretched FOUR TIMES over. Rendered at exactly
    # 1.151x the prop is perfect: arch, dome, song list, selection display,
    # grille and scroll all at their drawn sizes. Rendered at 1.6x the middle is
    # a smeared blank panel with the grille pulled out of shape, which is the
    # fault this file was written to remove, reintroduced by its own arithmetic.
    #
    # A band is now drawn for the full (max_taller - 1) x H. It is a bigger ask
    # of the model -- 356 rows of new body on a 594-row jukebox -- and check()
    # still refuses a bad one, which is the right place for that judgement.
    if extra < 8:
        print(f"  the body's share is {extra} rows: not worth a drawing")
        return None
    cut, ncov, on_edge = place_cut(d, band, H, face)
    if cut is None:
        print("  the prop is too short to open a band inside its own body")
        return None
    print(f"    cut at row {cut} of {H}: {ncov} part(s) cover it"
          + (", and it is a part boundary" if on_edge else ""))

    # THE ONLY MAGENTA IS THE BAND. This composited the RGBA background over a
    # magenta base, and bg_front is transparent wherever the prop is not -- the
    # jukebox's domed top, its tapered plinth -- so every one of those pixels
    # came out magenta too. The model was shown a prop with magenta AROUND it as
    # well as across it, read the whole lot as "fill this", and painted the
    # outside white: four replies running, columns 0..3 at (255,255,255) against
    # a body of (57,46,35). The band is the request; the silhouette is not.
    flat = src.convert("RGB")
    ask = Image.new("RGB", (W, H + extra), MAGENTA)
    ask.paste(flat.crop((0, 0, W, cut)), (0, 0))
    ask.paste(flat.crop((0, cut, W, H)), (0, cut + extra))
    ask_p = d / f"_tall_ask_{face}.png"
    ask.save(ask_p)

    # A REFUSAL IS A VERDICT ON ONE DRAWING, NOT ON THE PROP. CLAUDE.md's rule,
    # and detail_sheet already follows it: "the same pad scored a colour
    # distance of 10 on one sheet and 82 on the next from an identical prompt."
    # Every check above is a sentence the model can act on, so it is quoted back
    # instead of thrown away, and the prop falls through to a stretch only after
    # three drawings have failed.
    key = load_key()
    got = last = None
    for attempt in range(3):
        ask_more = "" if not last else (
            "\n\nYOUR LAST ATTEMPT WAS REJECTED, measured against this "
            f"machine's own drawing: {last}\nDraw it again and fix that.")
        try:
            # AND EACH RE-ASK GOES TO A DIFFERENT MODEL. The refusals are
            # measured to be model-specific rather than case-specific: the two
            # image models on the ladder fail on different props, so a second
            # opinion is a better second drawing than a second roll of the same
            # dice. `tier` is the attempt number; concept_sheet holds the order.
            generate_image(PROMPT.format(asset=asset) + ask_more, dst, key,
                           refs=[ask_p], tier=attempt)
        except Exception as e:
            print(f"  not drawn ({type(e).__name__})")
            return None
        raw = Image.open(dst)
        want = W / float(H + extra)
        ar = raw.width / float(raw.height)
        if abs(ar - want) / want > 0.12:
            last = (f"it came back {ar:.2f} wide for its height against the "
                    f"{want:.2f} of the canvas you were given. Fill the canvas "
                    f"you are given, edge to edge.")
        else:
            cand = raw.convert("RGB").resize((W, H + extra), Image.LANCZOS)
            last = check(src, cand, cut, extra, W, H)
            if last is None:
                got = cand
        # The price of this drawing was recorded when it was bought; this is
        # the other half. See image_ledger -- a model is cheap or dear per
        # drawing that survives THIS line, not per call.
        image_ledger.verdict(dst, last is None, last or "")
        if got is not None:
            break
        print(f"  attempt {attempt + 1} refused: {last[:96]}")
    if got is None:
        print("  three drawings refused; the body stretches instead")
        dst.rename(d / f"_tall_refused_{face}.png")
        ask_p.unlink(missing_ok=True)
        return None

    # AND THE BAND IS TONED TO ITS NEIGHBOURS, by arithmetic rather than by
    # asking again. The reply comes back the right material and the right grain
    # and a different exposure -- a median 11 lighter than the body it joins,
    # inside the palette bar and still reading as a lighter panel let into the
    # wood. A level is the one thing here that does not need a model: the
    # renderer already tints its carcass to rowRGB for exactly this reason.
    a0 = np.asarray(flat).astype(float)
    bm = median_rgb(got.crop((0, cut, W, cut + extra)))
    nb = median_rgb(Image.fromarray(
        np.r_[a0[max(0, cut - 60):cut], a0[cut:cut + 60]].astype("uint8")))
    sh = [int(round(n - b)) for n, b in zip(nb, bm)]
    if any(abs(v) > 1 for v in sh):
        arr = np.asarray(got).astype(int)
        arr[cut:cut + extra] = np.clip(
            arr[cut:cut + extra] + np.array(sh, dtype=int), 0, 255)
        got = Image.fromarray(arr.astype("uint8"))
        print(f"    band toned to its neighbours by {tuple(sh)}")

    # THE DRAWN BODY GOES BACK OVER EVERYTHING OUTSIDE THE BAND, exactly. Only
    # the new rows are the model's, for the reason wide_art gives: a generated
    # body that quietly redraws the panel lines has lost fidelity to the
    # reference at the size the reference was drawn, and that is not tradeable.
    out = got.convert("RGBA")
    out.paste(src.crop((0, 0, W, cut)), (0, 0))
    out.paste(src.crop((0, cut, W, H)), (0, cut + extra))
    # AND THE SILHOUETTE IS CARRIED THROUGH THE BAND. The drawn background is
    # transparent outside the prop; the new rows must be too, or a taller prop
    # gains a rectangle of body where its outline tapers.
    al = src.split()[3]
    full = Image.new("L", (W, H + extra), 255)
    full.paste(al.crop((0, 0, W, cut)), (0, 0))
    full.paste(al.crop((0, max(0, cut - 1), W, max(1, cut)))
               .resize((W, extra)), (0, cut))
    full.paste(al.crop((0, cut, W, H)), (0, cut + extra))
    out.putalpha(full)
    out.save(dst)
    ask_p.unlink(missing_ok=True)
    rec = {"face": face, "ratio": hx, "cut": cut, "extra": extra,
           "size": [W, H + extra], "drawn_size": [W, H],
           "cover_at_cut": ncov, "on_part_boundary": on_edge,
           "attempts": attempt + 1, "evidence": "proposed"}
    rec["flanks"] = draw_flanks(d, asset, cut, extra, H, redraw)
    (d / "tall_body.json").write_text(json.dumps(rec, indent=1))
    print(f"  {extra} rows of new body drawn at row {cut} of {H} "
          f"on attempt {attempt + 1} -- the drawn body kept")
    return rec


FLANK_PROMPT = """IMAGE 1 is the {face} elevation of a {asset}, drawn flat and
straight on.

A FLAT MAGENTA BAND runs across it. This is the same {asset} built TALLER, and
the magenta is the extra height, seen from the {face}.

FILL THE MAGENTA, and change nothing else.

  - Continue the body through it. Whatever runs into the band from above and
    below should run through and MEET: a panel line, a moulding, a seam, a wood
    grain, a streak of grime, a colour gradient.
  - THE REST OF THE IMAGE MUST COME BACK EXACTLY AS IT IS. Do not redraw it, do
    not move anything, do not recolour it.
  - Do NOT add fittings, lettering, badges, logos or graphics. This is PLAIN
    BODY: the machine is taller, not better decorated.
  - Do NOT repeat a graphic that appears once above or below the band. If a
    decal or a title sits above the band, it stays there, once.
  - No magenta may remain anywhere in the result.

FLAT ORTHOGRAPHIC VIEW, filling the canvas edge to edge. No perspective, no
drop shadow, no frame. Hand-painted PlayStation-era look, low resolution, the
palette taken from the body around the band."""


def draw_flanks(d, asset, cut, extra, H, redraw=False):
    """The side and back grown the same way, at the same cut.

    WHY THIS EXISTS. The growth band is measured on the FRONT and applied to
    every face, and the renderer says so in as many words: "Only the front takes
    this: the flanks are still the drawn side elevation." So a prop bare across
    some rows at the front and carrying a rocket across the same rows on its
    FLANK either stacks that rocket (when the rows repeat) or stretches it (when
    the body is drawn taller and the flank is left to be scaled into the new
    height). Measured across the corpus with strip_slice's own busy_elsewhere
    arithmetic: 38 of 98 props repeat or stretch rows that are busy on a flank.

    TRIED AND REVERTED BEFORE, AND THIS IS NOT THAT. `paint_out.py` records an
    attempt to paint the graphics OFF the side, which failed twice over -- with
    no parts_side.json there are no holes to composite through, and a band of
    reply composited into the original seams at each end. This asks the opposite
    question. Nothing is removed: a band of NEW BODY is opened between the
    flank's own rows, exactly as on the front, so the rocket is never repeated,
    never stretched and never touched. And the seam that sank the earlier
    attempt is the thing `check` measures and refuses on, against the prop's own
    busiest row.

    THE CUT IS THE FRONT'S CUT, and that is what keeps the prop a prop. Every
    face is drawn at the same height, so inserting at the same row on each means
    a rail that runs from the front round the corner still meets itself. Letting
    each face grow where it is individually barest would give a better band on
    every face and a discontinuity at every corner.
    """
    from PIL import Image
    import numpy as np
    from concept_sheet import generate_image, load_key
    import image_ledger
    from detail_sheet import median_rgb

    try:
        meta = json.loads((d / "body.json").read_text())
    except Exception:
        return []
    out = []
    for face in ("side", "back"):
        info = meta.get(face) or {}
        src_p = d / str(info.get("image") or f"body_{face}.png")
        if not src_p.exists():
            continue
        src = Image.open(src_p).convert("RGBA")
        W, Hf = src.size
        if Hf != H:
            # The faces are drawn at the prop's height, so this should not
            # happen -- if it does, the front's cut row means nothing here.
            print(f"    {face}: {Hf} rows against the front's {H} -- not drawn")
            continue
        dst = d / f"body_{face}_tall.png"
        if dst.exists() and not redraw:
            out.append({"face": face, "image": dst.name, "cached": True})
            continue

        flat = src.convert("RGB")
        ask = Image.new("RGB", (W, H + extra), MAGENTA)
        ask.paste(flat.crop((0, 0, W, cut)), (0, 0))
        ask.paste(flat.crop((0, cut, W, H)), (0, cut + extra))
        ask_p = d / f"_tall_ask_{face}.png"
        ask.save(ask_p)

        key = load_key()
        got = last = None
        for attempt in range(3):
            more = "" if not last else (
                "\n\nYOUR LAST ATTEMPT WAS REJECTED, measured against this "
                f"machine's own drawing: {last}\nDraw it again and fix that.")
            try:
                generate_image(FLANK_PROMPT.format(asset=asset, face=face) + more,
                               dst, key, refs=[ask_p], tier=attempt)
            except Exception as e:
                print(f"    {face}: not drawn ({type(e).__name__})")
                break
            raw = Image.open(dst)
            want = W / float(H + extra)
            ar = raw.width / float(raw.height)
            if abs(ar - want) / want > 0.12:
                last = (f"it came back {ar:.2f} wide for its height against the "
                        f"{want:.2f} of the canvas you were given. Fill the "
                        f"canvas you are given, edge to edge.")
            else:
                cand = raw.convert("RGB").resize((W, H + extra), Image.LANCZOS)
                last = check(src, cand, cut, extra, W, H)
                if last is None:
                    got = cand
            image_ledger.verdict(dst, last is None, last or "")
            if got is not None:
                break
            print(f"    {face}: attempt {attempt + 1} refused: {last[:78]}")
        if got is None:
            print(f"    {face}: refused -- this flank stretches")
            dst.unlink(missing_ok=True)
            ask_p.unlink(missing_ok=True)
            out.append({"face": face, "status": "refused"})
            continue

        a0 = np.asarray(flat).astype(float)
        bm = median_rgb(got.crop((0, cut, W, cut + extra)))
        nb = median_rgb(Image.fromarray(
            np.r_[a0[max(0, cut - 60):cut], a0[cut:cut + 60]].astype("uint8")))
        sh = [int(round(n - b)) for n, b in zip(nb, bm)]
        if any(abs(v) > 1 for v in sh):
            arr = np.asarray(got).astype(int)
            arr[cut:cut + extra] = np.clip(
                arr[cut:cut + extra] + np.array(sh, dtype=int), 0, 255)
            got = Image.fromarray(arr.astype("uint8"))

        res = got.convert("RGBA")
        res.paste(src.crop((0, 0, W, cut)), (0, 0))
        res.paste(src.crop((0, cut, W, H)), (0, cut + extra))
        al = src.split()[3]
        full = Image.new("L", (W, H + extra), 255)
        full.paste(al.crop((0, 0, W, cut)), (0, 0))
        full.paste(al.crop((0, max(0, cut - 1), W, max(1, cut)))
                   .resize((W, extra)), (0, cut))
        full.paste(al.crop((0, cut, W, H)), (0, cut + extra))
        res.putalpha(full)
        res.save(dst)
        ask_p.unlink(missing_ok=True)
        out.append({"face": face, "image": dst.name, "size": [W, H + extra],
                    "attempts": attempt + 1})
        print(f"    {face}: {extra} rows of new body drawn on attempt "
              f"{attempt + 1}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--asset", default="prop")
    ap.add_argument("--face", default="front")
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        # THE SWEEP RUNS THE SAME GATES draw() DOES, INCLUDING place_cut. It
        # stopped at needs(), so after place_cut learned to refuse a band with
        # nowhere wide enough to open it, the sweep went on reporting 17 props
        # where 14 would be drawn -- a count that disagrees with the tool it
        # counts. A sweep is a claim about what the pipeline will do.
        from PIL import Image
        work = ROOT / "tools" / "img2threejs-work"
        n = skipped = 0
        for f in sorted(work.glob(f"strips_{args.face}.json".join(["*/", ""]))):
            d = f.parent
            band, hx = needs(d, args.face)
            if not band or hx < MIN_TALL:
                continue
            bg = d / f"bg_{args.face}.png"
            cut = None
            if bg.exists():
                cut, _c, _e = place_cut(d, band, Image.open(bg).height, args.face)
            if cut is None:
                skipped += 1
                print(f"   {d.name:26} {hx:.2f}x  rows "
                      f"{band['px'][0]}..{band['px'][1]}  "
                      f"-- nowhere wide enough to open a band; it stretches")
                continue
            n += 1
            print(f"   {d.name:26} {hx:.2f}x  rows "
                  f"{band['px'][0]}..{band['px'][1]}  cut {cut}  "
                  f"{band['why'][:48]}")
        print(f"{n} prop(s) would have their extra body drawn, "
              f"{skipped} fall through to the stretch")
        return
    draw(Path(args.prop_dir), args.asset, args.face, args.redraw)


if __name__ == "__main__":
    main()
