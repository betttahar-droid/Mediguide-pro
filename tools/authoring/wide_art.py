#!/usr/bin/env python3
"""Buy the artwork a wider prop needs, for the parts that provably cannot grow.

    python3 tools/authoring/wide_art.py work/ps1 --asset "pinball machine"
    python3 tools/authoring/wide_art.py --sweep

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Everything this tool does about resizing is a RULE BETWEEN CHUNKS: a part
is held, counted, framed, or nine-sliced from its own measured uniform band so
its ends keep their real size and only the middle repeats. That answers for
structure -- rails, panels, cabinets, decks, shelves -- and it is what the last
dozen fixes in this repo are about.

IT CANNOT ANSWER FOR ART DRAWN EDGE TO EDGE, and the tool already knows which
parts those are. `_bands` scans each part for a strip uniform enough to insert
more of, at a deliberately strict bar, and returns NOTHING for a pinball
backglass or a jukebox nameplate -- correctly, because there is no such strip on
them. Swept: of 363 parts across the corpus that ask for a span rule, **107
(29%) have no measured band and no plain flank.** The list is exactly what the
eye would pick -- title_card, nameplate, marquee, ornament_grille,
backglass_art.

That is a refusal, not a gap. A wider backglass needs MORE ARTWORK, and no rule
between chunks can conjure it: stretching smears it, repeating doubles it, and
holding it leaves the panel gaping at the ends. v51_pinball's judges said so in
every round of three, in both models' words --

    "backglass_art: Fixed while the backbox widens, so the artwork gaps/doubles
     rather than widening as a single backglass with the cabinet."
    "Art does not scale across the wider backbox, leaving empty side borders."

-- against a part 86.9% of the face wide whose band scan returns None.

SO THE MISSING ARTWORK IS BOUGHT, ONCE, PER PART THAT NEEDS IT. Not one huge
texture masked down as the prop grows: there is no bigger drawing to mask, the
reference is one elevation at one size. The thing to ask for is the same
fitting COMPOSED WIDER -- a backglass whose art fills a wider panel, which is
what a wider machine's backglass actually is.

This is the move material_atlas made for materials, decal_sheet for graphics
and detail_sheet for small fittings: stop carving the thing out of a picture of
the whole prop and ask for the thing. Here it is asked for at a second aspect.

AND IT IS REFUSED THE SAME WAY. detail_sheet's checks apply unchanged -- a
redraw that comes back as a different object, a different palette or a
featureless panel is rejected and the original stands, so a bad generation
costs a call and changes nothing. The one check that CANNOT carry over is
aspect: this drawing is meant to have a different one. That is the whole point
of it, so `resemblance` compares the two at a common size, which is comparing
composition rather than shape.

WHAT IT DOES NOT CLAIM. The wider artwork is DRAWN, not measured -- it is a
second source, and the spec's own warning applies: generated references can
contradict each other. So it is recorded as `PROPOSED` evidence, it never
overwrites the drawn texture, and the 1x render keeps using the original. A
prop's fidelity to its reference at the size it was drawn is not up for trade.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))

# Below this the part is not really being asked to span and the artwork it has
# will do; a wider drawing is a model call and should be bought for parts that
# visibly gape.
MIN_WIDE = 1.15
# THE SIMILARITY BAR IS INVERTED HERE, and importing it the other way up cost a
# generation that was right. detail_sheet asks "is this the same fitting?" and
# refuses a redraw that scores UNLIKE its crop. This asks "is this a
# CONTINUATION of that edge?", and a continuation is not a copy: the jukebox's
# new ends came back as plain wood with rivets and extended trim -- exactly what
# was asked for -- against original end strips full of the arch's coloured tubes
# and corner brackets. It scored 1.06 unlike and was refused by a bar of 0.85.
#
# The failure this direction actually has is the opposite one: the model
# duplicating a motif from the middle into the ends, which is the category error
# every other part of this repo guards against. That scores LOW. So the bar is a
# floor, not a ceiling, and it is set loose enough to catch only a blatant copy,
# because one sample cannot fit a threshold and this file says so elsewhere.
MIN_UNLIKE = 0.25          # below this the "new" end is a copy of the middle
MAX_TINT = 48              # channel distance between the two median colours


# TRIED AND REVERTED: ASKING FOR THE PART "COMPOSED {ratio}x AS WIDE" IN WORDS,
# with the drawn part as the reference. The model matched the REFERENCE'S shape
# and ignored the number: asked for 2.571 against a marquee drawn at 1.607, it
# returned 1.608 -- a sharper copy of the same picture at four times the
# resolution. And the refusal checks could not see it, because `resemblance`
# puts both images at a common size before correlating, which is exactly what
# makes it a test of composition rather than of proportion.
#
# The reference decides the shape. So the reference IS the new shape: a canvas
# at the target aspect with the drawn artwork pasted into the middle of it and
# the two new strips filled flat magenta. That is paint_out's own trick, and
# its note says why it beats describing the gap -- "Holes are now shown, not
# described... painting the outstanding holes flat magenta took the vending
# machine from 19/29 fittings to 28/29."
#
# AND THE DRAWN ARTWORK IS COMPOSITED BACK OVER THE MIDDLE. Only the ends are
# taken from the reply. A generated wider marquee that quietly redraws the
# lettering has lost fidelity to the reference at the size the reference was
# drawn, and that is not tradeable: the centre is the measurement, the ends are
# the purchase.
MAGENTA = (255, 0, 255)

PROMPT = """The attached image is the {part} of a {asset}, on a canvas WIDER
than the artwork.

The artwork sits in the middle. The two FLAT MAGENTA STRIPS at the left and
right edges are missing: this is the same part on a wider {asset}, and the
magenta is where more of it belongs.

FILL THE MAGENTA, and change nothing else.

  - Continue what is already at that edge outwards: more of the border, more
    of the trim, more of the field the motifs sit on, the same rivets and the
    same wear carrying on. Whatever runs into the magenta should run through it
    to the edge of the canvas.
  - THE MIDDLE MUST COME BACK EXACTLY AS IT IS. Do not redraw the lettering, do
    not move a motif, do not recolour anything, do not sharpen or clean it up.
  - Do NOT repeat a motif that appears once. Do NOT add new lettering, new
    objects, or a second copy of anything. If the strip should just be plain
    panel or plain border, plain is the right answer.
  - No magenta may remain anywhere in the result.

FLAT ORTHOGRAPHIC FRONT VIEW, filling the canvas edge to edge. No perspective,
no drop shadow, no glow, no frame drawn round it. Hand-painted PlayStation-era
look, low resolution, the palette taken from the artwork in the middle.
"""


def candidates(prop_dir, face="front"):
    """Parts asking to span with no band to grow and no plain flank.

    The measurement is already on disk: layer_build writes each part's own
    uniform bands, at a strict bar chosen so a marquee correctly reports none.

    AND A FITTING IS NOT ART THAT MUST WIDEN. The band test alone returned 103
    parts, and the list gave itself away: joystick_right, coin_slot_left,
    bottle_row1_a, button_bank_left. A wider cabinet gets MORE JOYSTICKS, not a
    wider joystick, and buying a wider drawing of one would be the category
    error this repo has caught in four other places -- the sign that repeats,
    the decal laid out in a grid, the screen shown three times side by side.

    Two filters, both quoting bars that already exist rather than choosing new
    ones. Width: layer_build will not let a part span unless it runs at least
    three quarters of the face, so anything narrower is a fitting whatever it
    asked for, and a wider drawing of it could never be used. Role:
    resize_policy's COUNTABLE set is the list of things that come in numbers.
    Between them the 103 come down to the parts that are actually the face.
    """
    d = Path(prop_dir)
    try:
        L = json.loads((d / f"layers_{face}.json").read_text())
        pj = json.loads((d / f"parts_{face}.json").read_text())
        sr = json.loads((d / "scale_rules.json").read_text())
    except Exception:
        return [], 1.0
    try:
        from feature_intent import role_of
        from resize_policy import COUNTABLE
    except Exception:
        role_of, COUNTABLE = (lambda p: "unknown"), set()
    wide = float(sr.get("max_wider") or 1.0)
    W = pj.get("size", [1, 1])[0] or 1
    P = {p["name"]: p for p in pj.get("parts", [])}
    out = []
    for q in L.get("parts", []):
        b = q.get("bands") or {}
        p = P.get(q["name"])
        if not p:
            continue
        # THE RULE THE RENDERER WILL ACTUALLY READ, which is the manifest's and
        # not parts_front's -- layer_build rewrites it, and buying against the
        # pre-rewrite value buys for a part that will be built by another rule.
        a = q.get("resize") or p.get("resize") or "fixed"
        if not a.startswith("spanx") and not q.get("spans"):
            continue
        # THE SAME TEST THE RENDERER USES, NOT A SIMILAR ONE. `spansOf` in
        # part_slice.mjs is the authority and it is not symmetric: `_repeat`
        # needs a measured band OR a plain flank, because it instances a uniform
        # unit; `_center` needs the FLANK specifically, because its job is to
        # hold one piece of artwork at its real size and insert at the plain
        # ends. This asked for "a band or a flank" for both, so a `_center` part
        # with a band and no flank was skipped here as answerable and then
        # refused there as unanswerable, and nothing widened it at all.
        # v47_jukebox's `dome_window` and v48_jukebox's `arch_marquee` are both
        # that case. part_slice.mjs says it in as many words: two places
        # deciding whether a part can span, by different tests, is one decision
        # with a bug in it.
        can_span = bool(q.get("hf")) if a.endswith("_center") \
            else bool(b.get("h") or q.get("hf"))
        if can_span:
            continue                      # a rule can answer: leave it alone
        if (p["px"][2] - p["px"][0]) / float(W) < 0.75:
            continue                      # a fitting, and it may not span anyway
        if role_of(p) in COUNTABLE:
            continue                      # comes in numbers, not in widths
        out.append(q["name"])
    return out, wide


def check(crop, got, pad, W2):
    """Why this drawing is not usable, as a sentence, or None if it is.

    Each is quoted back to the model on the next attempt, so each has to say
    what is wrong in terms it can act on.
    """
    from detail_sheet import resemblance, median_rgb
    rgb = crop.convert("RGB")
    H = crop.height
    # EACH END AGAINST ITS OWN SIDE. Both were compared against the drawn part's
    # LEFT strip, which asks the new right-hand trim to look like the left-hand
    # trim -- true of a symmetrical marquee, false of anything with a corner
    # detail on one side only. A continuation is judged against what it
    # continues.
    w = max(4, min(pad, crop.width // 3))
    pairs = [(got.crop((0, 0, pad, H)), rgb.crop((0, 0, w, H))),
             (got.crop((W2 - pad, 0, W2, H)),
              rgb.crop((crop.width - w, 0, crop.width, H)))]
    left = max(sum(1 for q in e.convert("RGB").getdata()
                   if abs(q[0] - 255) < 40 and q[1] < 60
                   and abs(q[2] - 255) < 40) for e, _ in pairs)
    if left > 0.02 * pad * H:
        return (f"{left} pixels of the magenta came back unfilled. Every "
                f"magenta pixel must become part of this object.")
    # detail_sheet's own bars, on the NEW MATERIAL only -- the middle is about
    # to be overwritten with the drawn artwork, so judging it would be judging a
    # picture that is not going to be used.
    unlike = max(resemblance(e, r) for e, r in pairs)
    tint = max(sum(abs(x - y) for x, y in zip(median_rgb(e), median_rgb(r))) / 3
               for e, r in pairs)
    if unlike < MIN_UNLIKE:
        return ("the new material at the ends is a copy of what is already "
                "there. It should CONTINUE the border and the field outwards, "
                "not repeat a motif that appears once.")
    if tint > MAX_TINT:
        return (f"the new ends are {tint:.0f} away in colour from the artwork "
                f"they join. Take the palette from the edges of the middle.")
    return None


def draw(prop_dir, asset, face="front", redraw=False):
    """Ask for each candidate composed wider; refuse the ones that came back wrong."""
    from PIL import Image
    from concept_sheet import generate_image, load_key

    d = Path(prop_dir)
    names, wide = candidates(d, face)
    if wide < MIN_WIDE:
        print(f"max_wider is {wide:.2f}: nothing gapes, nothing to buy")
        return []
    if not names:
        print("every part that spans has a band to grow: nothing to buy")
        return []
    key = load_key()
    kit = d / "parts"
    outdir = d / "parts_wide"
    outdir.mkdir(exist_ok=True)
    log = []
    for n in names:
        src = kit / f"{n}.png"
        if not src.exists():
            continue
        dst = outdir / f"{n}.png"
        if dst.exists() and not redraw:
            # A CACHED DRAWING IS A KEPT DRAWING, AND IT HAS TO SAY SO. This
            # wrote `{"status": "cached"}` and the renderer only uses a part
            # whose status is `kept` -- and it needs the `ratio` besides, to
            # know how far the part may open. So a second run over a prop that
            # already had its artwork QUIETLY TOOK IT BACK OUT of the build:
            # v20_jukebox's title strip was bought, verified, on disk, and
            # dropped by the run that came after it and found nothing to do.
            # Same shape as the plate mask in paint_out, one file along.
            #
            # The ratio is measured off the file rather than remembered, so this
            # is right even for a drawing whose log entry was lost.
            w0 = Image.open(src).width
            log.append({"part": n, "status": "kept", "attempts": 0,
                        "ratio": round(Image.open(dst).width / max(1, w0), 4),
                        "new_px": Image.open(dst).width - w0,
                        "evidence": "cached"})
            print(f"  {n}: already drawn "
                  f"({log[-1]['ratio']:.2f}x, kept)")
            continue
        crop = Image.open(src).convert("RGBA")
        H = crop.height
        # the canvas IS the request: the target shape, the artwork in the
        # middle, the missing width shown rather than described
        W2 = max(crop.width + 8, int(round(crop.width * wide)))
        pad = (W2 - crop.width) // 2
        # AND THE ONLY MAGENTA IS THE ENDS. This composited the part's RGBA over
        # a magenta base, so every transparent pixel of a SHAPED part -- and
        # more than half of all masks carry real shape -- came out magenta too.
        # The model was shown magenta tracing the part's outline as well as
        # standing at its ends, which is the fault tall_body was caught by: it
        # reads the lot as "fill this" and paints outside the object. The ends
        # are the request; the silhouette is not.
        ask = Image.new("RGB", (W2, H), MAGENTA)
        ask.paste(crop.convert("RGB"), (pad, 0))
        ask_p = outdir / f"{n}.ask.png"
        ask.save(ask_p)

        # A REFUSAL IS A VERDICT ON ONE DRAWING, NOT ON THE PART. CLAUDE.md's
        # rule, which detail_sheet follows and this did not: it gave up after
        # one reply. tall_body, built the same way an hour later, was refused
        # twice for drawing hard joins and passed on the third attempt with the
        # measurement quoted back at it.
        got = last = None
        for attempt in range(3):
            more = "" if not last else (
                "\n\nYOUR LAST ATTEMPT WAS REJECTED, measured against the "
                f"artwork you were given: {last}\nDraw it again and fix that.")
            try:
                # Each re-ask goes to a different model -- the ladder in
                # concept_sheet, in price order. Measured: the models fail on
                # different parts, so a second opinion beats a second roll.
                generate_image(
                    PROMPT.format(asset=asset, part=n.replace("_", " ")) + more,
                    dst, key, refs=[ask_p], tier=attempt)
            except Exception as e:
                print(f"  {n}: not drawn ({type(e).__name__})")
                log.append({"part": n, "status": "failed",
                            "why": type(e).__name__})
                last = None
                break
            raw = Image.open(dst)
            want = W2 / float(H)
            ar = raw.width / float(raw.height)
            # THE ASPECT IS A HARD REFUSAL. It is the thing the first version
            # could not see and the thing the model got wrong -- asked for 2.571
            # against a marquee drawn at 1.607 it returned 1.608, a sharper copy
            # -- because `resemblance` puts both at a common size before
            # correlating, which is what makes it a test of composition.
            if abs(ar - want) / want > 0.12:
                last = (f"it came back {ar:.2f} wide for its height against the "
                        f"{want:.2f} of the canvas you were given. Fill the "
                        f"canvas you are given, edge to edge.")
            else:
                cand = raw.convert("RGB").resize((W2, H), Image.LANCZOS)
                last = check(crop, cand, pad, W2)
                if last is None:
                    got = cand
                    break
            print(f"  {n}: attempt {attempt + 1} refused: {last[:90]}")
        if got is None:
            if last is not None:
                print(f"  {n}: three drawings refused; the drawn part stands")
                # THE REFUSED REPLY IS KEPT, not deleted. A refusal with the
                # picture thrown away cannot be checked, and two of this repo's
                # thresholds were wrong the first time they were set.
                if dst.exists():
                    dst.rename(outdir / f"{n}.refused.png")
                log.append({"part": n, "status": "refused", "why": last[:120]})
            ask_p.unlink(missing_ok=True)
            continue

        # AND THE DRAWN ARTWORK GOES BACK OVER THE MIDDLE, exactly. Only the
        # ends are the model's. The alpha comes from the original stretched to
        # the new width at the ends and copied at the middle, so a shaped part
        # keeps its silhouette.
        out = got.convert("RGBA")
        out.paste(crop, (pad, 0))
        a = crop.split()[3]
        wa = Image.new("L", (W2, H), 255)
        wa.paste(a.crop((0, 0, 1, H)).resize((pad, H)), (0, 0))
        wa.paste(a, (pad, 0))
        wa.paste(a.crop((crop.width - 1, 0, crop.width, H))
                 .resize((W2 - pad - crop.width, H)), (pad + crop.width, 0))
        out.putalpha(wa)
        out.save(dst)
        ask_p.unlink(missing_ok=True)
        print(f"  {n}: {2*pad}px of new material at the ends on attempt "
              f"{attempt + 1} -- the drawn middle kept")
        log.append({"part": n, "status": "kept", "ratio": wide,
                    "new_px": 2 * pad, "attempts": attempt + 1,
                    "evidence": "proposed"})
    (d / "wide_art.json").write_text(json.dumps(
        {"face": face, "ratio": wide, "parts": log}, indent=1))
    return log


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
        props = tot = 0
        rows = []
        for f in sorted(work.glob(f"*/layers_{args.face}.json")):
            names, wide = candidates(f.parent, args.face)
            if not names:
                continue
            props += 1
            tot += len(names)
            rows.append((len(names), wide, f.parent.name, names[:4]))
        rows.sort(reverse=True)
        print(f"{props} props, {tot} part(s) that ask to span with nothing to grow")
        for n, w, name, ex in rows[:14]:
            print(f"   {n:3} at {w:.2f}x  {name:26} {', '.join(ex)}")
        return

    for r in draw(Path(args.prop_dir), args.asset, args.face, args.redraw):
        pass


if __name__ == "__main__":
    main()
