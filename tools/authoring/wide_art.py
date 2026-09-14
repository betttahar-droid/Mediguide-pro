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
        a = p.get("resize") or "fixed"
        if not a.startswith("spanx") and not q.get("spans"):
            continue
        if b.get("h") or q.get("hf"):
            continue                      # a rule can answer: leave it alone
        if (p["px"][2] - p["px"][0]) / float(W) < 0.75:
            continue                      # a fitting, and it may not span anyway
        if role_of(p) in COUNTABLE:
            continue                      # comes in numbers, not in widths
        out.append(q["name"])
    return out, wide


def draw(prop_dir, asset, face="front", redraw=False):
    """Ask for each candidate composed wider; refuse the ones that came back wrong."""
    from PIL import Image
    from concept_sheet import generate_image, load_key
    from detail_sheet import resemblance, median_rgb

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
            print(f"  {n}: already drawn")
            log.append({"part": n, "status": "cached"})
            continue
        crop = Image.open(src).convert("RGBA")
        # the canvas IS the request: the target shape, the artwork in the
        # middle, the missing width shown rather than described
        W2 = max(crop.width + 8, int(round(crop.width * wide)))
        pad = (W2 - crop.width) // 2
        ask = Image.new("RGBA", (W2, crop.height), MAGENTA + (255,))
        ask.alpha_composite(crop, (pad, 0))
        ask_p = outdir / f"{n}.ask.png"
        ask.convert("RGB").save(ask_p)
        try:
            generate_image(
                PROMPT.format(asset=asset, part=n.replace("_", " ")),
                dst, key, refs=[ask_p])
        except Exception as e:
            print(f"  {n}: not drawn ({type(e).__name__})")
            log.append({"part": n, "status": "failed", "why": type(e).__name__})
            continue
        got = Image.open(dst).convert("RGB").resize((W2, crop.height),
                                                    Image.LANCZOS)
        # THE ASPECT IS NOW A HARD REFUSAL. It is the thing the first version
        # could not see and the thing the model got wrong, so it is checked
        # before anything else: a reply whose shape is the drawn part's shape is
        # a copy, whatever it looks like.
        raw = Image.open(dst)
        want = W2 / float(crop.height)
        ar = raw.width / float(raw.height)
        if abs(ar - want) / want > 0.12:
            print(f"  {n}: refused -- came back at aspect {ar:.2f} against "
                  f"{want:.2f} asked; it copied the reference's shape")
            dst.unlink(missing_ok=True)
            ask_p.unlink(missing_ok=True)
            log.append({"part": n, "status": "refused", "why": "aspect",
                        "got": round(ar, 3), "wanted": round(want, 3)})
            continue
        # EACH END AGAINST ITS OWN SIDE. Both were compared against the drawn
        # part's LEFT strip, which asks the new right-hand trim to look like the
        # left-hand trim -- true of a symmetrical marquee and false of anything
        # with a corner detail on one side only. A continuation is judged
        # against what it continues.
        rgb = crop.convert("RGB")
        w = max(4, min(pad, crop.width // 3))
        pairs = [(got.crop((0, 0, pad, crop.height)),
                  rgb.crop((0, 0, w, crop.height))),
                 (got.crop((W2 - pad, 0, W2, crop.height)),
                  rgb.crop((crop.width - w, 0, crop.width, crop.height)))]
        # detail_sheet's own bars, on the NEW MATERIAL only -- the middle is
        # about to be overwritten with the drawn artwork, so judging it would be
        # judging a picture that is not going to be used.
        unlike = max(resemblance(e, r) for e, r in pairs)
        tint = max(sum(abs(x - y) for x, y in zip(median_rgb(e), median_rgb(r)))
                   / 3 for e, r in pairs)
        left = max(sum(1 for p in e.convert("RGB").getdata()
                       if abs(p[0] - 255) < 40 and p[1] < 60
                       and abs(p[2] - 255) < 40) for e, _ in pairs)
        if left > 0.02 * pad * crop.height:
            print(f"  {n}: refused -- {left} px of the magenta came back "
                  f"unfilled; the drawn part stands")
            dst.unlink(missing_ok=True); ask_p.unlink(missing_ok=True)
            log.append({"part": n, "status": "refused", "why": "magenta left"})
            continue
        if unlike < MIN_UNLIKE or tint > MAX_TINT:
            why = ("the new ends are a copy of the middle"
                   if unlike < MIN_UNLIKE else "the palette does not match")
            print(f"  {n}: refused -- {why} ({unlike:.2f} unlike, floor "
                  f"{MIN_UNLIKE}; tint {tint:.0f}, bar {MAX_TINT}); "
                  f"the drawn part stands")
            # THE REFUSED REPLY IS KEPT, not deleted. A refusal with the
            # picture thrown away cannot be checked, and two of this repo's
            # thresholds were wrong the first time they were set.
            dst.rename(outdir / f"{n}.refused.png")
            ask_p.unlink(missing_ok=True)
            log.append({"part": n, "status": "refused",
                        "unlike": round(unlike, 3), "tint": round(tint, 1)})
            continue
        # AND THE DRAWN ARTWORK GOES BACK OVER THE MIDDLE, exactly. Only the
        # ends are the model's. The alpha comes from the original stretched to
        # the new width at the ends and copied at the middle, so a shaped part
        # keeps its silhouette.
        out = got.convert("RGBA")
        out.paste(crop, (pad, 0))
        a = crop.split()[3]
        wa = Image.new("L", (W2, crop.height), 255)
        wa.paste(a.crop((0, 0, 1, crop.height)).resize((pad, crop.height)), (0, 0))
        wa.paste(a, (pad, 0))
        wa.paste(a.crop((crop.width - 1, 0, crop.width, crop.height))
                 .resize((W2 - pad - crop.width, crop.height)),
                 (pad + crop.width, 0))
        out.putalpha(wa)
        out.save(dst)
        ask_p.unlink(missing_ok=True)
        print(f"  {n}: {2*pad}px of new material at the ends, "
              f"{unlike:.2f} unlike, tint {tint:.0f} -- the drawn middle kept")
        log.append({"part": n, "status": "kept", "ratio": wide,
                    "new_px": 2 * pad,
                    "unlike": round(unlike, 3), "tint": round(tint, 1),
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
