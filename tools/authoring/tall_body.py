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
    if s.get("grow_bands") and not band.get("with_members"):
        return None, hx
    # AND A MEMBER WITH NO BODY BEHIND IT GAINS NOTHING EITHER.
    #
    # The clause above was shipped one prop wide and flagged as an over-reach in
    # its own commit message, because "every growth place is a member" is true
    # of 10 props and every pinball in the corpus is among them -- and the
    # pinball's taller render is RIGHT. A leg has nothing behind it to go blank.
    if s.get("grow_bands") and not body_behind(d, s["grow_bands"], face):
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
    cut = min(range(lo, hi + 1),
              key=lambda y: (cover[y], 0 if y in edges else 1, abs(y - mid)))
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
    above = src.convert("RGB").crop((0, max(0, cut - extra), W, cut))
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
    # SHARED BY HEIGHT WITH THE MEMBERS, which is strip_slice's own convention
    # for dividing growth between places. The members keep lengthening; the body
    # takes the rest, so a prop does not both grow its tubes to full height AND
    # gain a full band of new carcass.
    if band.get("with_members"):
        try:
            gb = json.loads((d / f"strips_{face}.json").read_text())["grow_bands"]
            mem = sum(g["px"][1] - g["px"][0] for g in gb)
            own = abs(int(band["px"][1]) - int(band["px"][0]))
            extra = int(round(extra * own / float(max(1, own + mem))))
            print(f"    sharing with {len(gb)} member band(s) by height: "
                  f"{extra} rows to the body")
        except Exception:
            pass
    if extra < 8:
        print(f"  the body's share is {extra} rows: not worth a drawing")
        return None
    cut, ncov, on_edge = place_cut(d, band, H, face)
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
            generate_image(PROMPT.format(asset=asset) + ask_more, dst, key,
                           refs=[ask_p])
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
    (d / "tall_body.json").write_text(json.dumps(rec, indent=1))
    print(f"  {extra} rows of new body drawn at row {cut} of {H} "
          f"on attempt {attempt + 1} -- the drawn body kept")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--asset", default="prop")
    ap.add_argument("--face", default="front")
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        work = ROOT / "tools" / "img2threejs-work"
        n = 0
        for f in sorted(work.glob(f"strips_{args.face}.json".join(["*/", ""]))):
            band, hx = needs(f.parent, args.face)
            if band and hx >= MIN_TALL:
                n += 1
                print(f"   {f.parent.name:26} {hx:.2f}x  rows "
                      f"{band['px'][0]}..{band['px'][1]}  "
                      f"{band['why'][:60]}")
        print(f"{n} prop(s) would have their extra body drawn")
        return
    draw(Path(args.prop_dir), args.asset, args.face, args.redraw)


if __name__ == "__main__":
    main()
