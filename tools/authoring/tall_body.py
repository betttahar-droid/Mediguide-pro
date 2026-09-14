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
    if s.get("grow_bands"):
        return None, hx            # it has somewhere to repeat: leave it alone
    band = s.get("stretch_band")
    if not band:
        return None, hx
    return band, hx


def draw(prop_dir, asset, face="front", redraw=False):
    from PIL import Image
    from concept_sheet import generate_image, load_key
    from detail_sheet import resemblance, median_rgb

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
        return json.loads((d / "tall_body.json").read_text())

    src = Image.open(bg).convert("RGBA")
    W, H = src.size
    extra = int(round((hx - 1.0) * H))
    a, b = int(band["px"][0]), int(band["px"][1])
    cut = max(0, min(H, (a + b) // 2))
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

    try:
        generate_image(PROMPT.format(asset=asset), dst, load_key(), refs=[ask_p])
    except Exception as e:
        print(f"  not drawn ({type(e).__name__})")
        return None

    raw = Image.open(dst)
    want = W / float(H + extra)
    ar = raw.width / float(raw.height)
    if abs(ar - want) / want > 0.12:
        print(f"  refused -- came back at aspect {ar:.2f} against {want:.2f} "
              f"asked; it copied the reference's shape")
        dst.unlink(missing_ok=True)
        return None
    got = raw.convert("RGB").resize((W, H + extra), Image.LANCZOS)
    new = got.crop((0, cut, W, cut + extra))
    above = src.convert("RGB").crop((0, max(0, cut - extra), W, cut))
    left = sum(1 for p in new.getdata()
               if abs(p[0] - 255) < 40 and p[1] < 60 and abs(p[2] - 255) < 40)
    if left > 0.02 * extra * W:
        print(f"  refused -- {left} px of magenta came back unfilled")
        dst.unlink(missing_ok=True); ask_p.unlink(missing_ok=True)
        return None
    # the seam check, before the others: it is the one that caught the first
    # reply and the one a palette test structurally cannot see
    from strip_slice import row_diff
    drawn_rd = row_diff(src.convert("RGB"))
    got_rd = row_diff(got)
    worst_drawn = max(drawn_rd) if drawn_rd else 1.0
    joins = [max(got_rd[max(0, y - 3):y + 4] or [0])
             for y in (cut, cut + extra) if 0 < y < len(got_rd)]
    seam = max(joins) if joins else 0.0
    if seam > SEAM_X * worst_drawn:
        print(f"  refused -- the joins are a hard line: row difference {seam:.1f} "
              f"against {worst_drawn:.1f}, the busiest row this prop actually "
              f"has ({seam / max(0.01, worst_drawn):.1f}x). It drew a panel let "
              f"into the body rather than continuing it")
        dst.rename(d / f"_tall_refused_{face}.png")
        ask_p.unlink(missing_ok=True)
        return None
    # and across it: a bright edge where the new material meets the border
    import numpy as _np
    _g = _np.asarray(got).astype(float)
    # AGAINST THE ORIGINAL'S ROWS, NEVER THE REPLY'S. This first compared the
    # new band to the reply's OWN rows above and below it -- and the reply had
    # painted its left four columns pure white through the whole image, band and
    # neighbours alike, so the two agreed at 10 and the check passed a stripe
    # that is 255 against a body of (57,46,36). Comparing a reply against itself
    # measures its consistency, not its correctness; the drawn background is the
    # only thing here that is known good.
    _a0 = _np.asarray(src.convert("RGB")).astype(float)
    _band = _g[cut:cut + extra].mean(axis=(0, 2))
    _ref = _np.r_[_a0[max(0, cut - 40):cut],
                  _a0[cut:cut + 40]].mean(axis=(0, 2))
    col = float(_np.abs(_band - _ref).max()) if len(_ref) else 0.0
    steps = [float(_np.abs(_a0[y - 40:y].mean(axis=(0, 2))
                           - _a0[y:y + 40].mean(axis=(0, 2))).max())
             for y in range(40, _a0.shape[0] - 40, 20)]
    worst_col = max(steps) if steps else 255.0
    if col > COL_X * worst_col:
        print(f"  refused -- the new band has an edge across it: a column "
              f"differs from its neighbours by {col:.0f} against {worst_col:.0f}, "
              f"the biggest column step this prop's own drawing has "
              f"({col / max(0.01, worst_col):.1f}x)")
        dst.rename(d / f"_tall_refused_{face}.png")
        ask_p.unlink(missing_ok=True)
        return None
    unlike = resemblance(new, above)
    tint = sum(abs(x - y) for x, y in
               zip(median_rgb(new), median_rgb(above))) / 3
    if unlike < MIN_UNLIKE or tint > MAX_TINT:
        why = ("the new band is a copy of the rows above it"
               if unlike < MIN_UNLIKE else "the palette does not match")
        print(f"  refused -- {why} ({unlike:.2f} unlike, floor {MIN_UNLIKE}; "
              f"tint {tint:.0f}, bar {MAX_TINT}); the prop stretches instead")
        dst.rename(d / f"_tall_refused_{face}.png")
        ask_p.unlink(missing_ok=True)
        return None

    # THE DRAWN BODY GOES BACK OVER EVERYTHING OUTSIDE THE BAND, exactly. Only
    # the new rows are the model's, for the reason wide_art gives: a generated
    # body that quietly redraws the panel lines has lost fidelity to the
    # reference at the size the reference was drawn, and that is not tradeable.
    # AND THE BAND IS TONED TO ITS NEIGHBOURS, by arithmetic rather than by
    # asking again. The reply comes back the right material and the right grain
    # and a different exposure -- a median 11 lighter than the body it joins,
    # which is inside the palette bar and still reads as a lighter panel let
    # into the wood. That is a level, and a level is the one thing here that
    # does not need a model: the renderer already tints its carcass to rowRGB
    # for exactly this reason. Shift the band so its median matches the rows it
    # sits between, and the drawn structure survives untouched.
    _bm = median_rgb(got.crop((0, cut, W, cut + extra)))
    _nb = median_rgb(Image.fromarray(
        _np.r_[_a0[max(0, cut - 60):cut],
               _a0[cut:cut + 60]].astype("uint8")))
    _sh = [int(round(n - b)) for n, b in zip(_nb, _bm)]
    if any(abs(v) > 1 for v in _sh):
        _bn = _np.asarray(got).astype(int)
        _bn[cut:cut + extra] = _np.clip(
            _bn[cut:cut + extra] + _np.array(_sh, dtype=int), 0, 255)
        got = Image.fromarray(_bn.astype("uint8"))
        print(f"    band toned to its neighbours by {tuple(_sh)}")
    out = got.convert("RGBA")
    out.paste(src.crop((0, 0, W, cut)), (0, 0))
    out.paste(src.crop((0, cut, W, H)), (0, cut + extra))
    # AND THE SILHOUETTE IS CARRIED THROUGH THE BAND. The drawn background is
    # transparent outside the prop; the new rows must be too, or a taller prop
    # gains a rectangle of body where its outline tapers. The alpha at the cut
    # row is what the prop's outline is doing there, so it is what the inserted
    # rows get.
    al = src.split()[3]
    band_a = al.crop((0, max(0, cut - 1), W, max(1, cut))).resize((W, extra))
    full = Image.new("L", (W, H + extra), 255)
    full.paste(al.crop((0, 0, W, cut)), (0, 0))
    full.paste(band_a, (0, cut))
    full.paste(al.crop((0, cut, W, H)), (0, cut + extra))
    out.putalpha(full)
    out.save(dst)
    ask_p.unlink(missing_ok=True)
    rec = {"face": face, "ratio": hx, "cut": cut, "extra": extra,
           "seam": round(seam, 2), "worst_drawn_row": round(worst_drawn, 2),
           "col": round(col, 1), "worst_drawn_col": round(worst_col, 1),
           "size": [W, H + extra], "drawn_size": [W, H],
           # where the height went, in the DRAWN texture's own 0..1 from the
           # bottom, which is the convention grow_bands already uses
           "band": [round(1 - cut / H, 5), round(1 - cut / H, 5)],
           "unlike": round(unlike, 3), "tint": round(tint, 1),
           "evidence": "proposed"}
    (d / "tall_body.json").write_text(json.dumps(rec, indent=1))
    print(f"  {extra} rows of new body drawn at row {cut} of {H} "
          f"(joins {seam:.1f} of {worst_drawn:.1f}, edges {col:.0f} of "
          f"{worst_col:.0f}, {unlike:.2f} unlike, tint {tint:.0f}) "
          f"-- the drawn body kept")
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
