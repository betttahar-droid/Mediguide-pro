#!/usr/bin/env python3
"""Ask for the prop's MATERIALS, instead of carving them out of a painting.

    python3 tools/authoring/material_atlas.py work/ps1 --asset "arcade cabinet"

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS EXISTS, AND WHY THE OLD WAY COULD NOT WIN.

Every surface in this tool has been reverse-engineered out of one painted
picture of the finished prop: find the flattest patch, divide out its gradient,
cross-blend it into something that tiles, patch the hole it left. That is
un-baking a cake. It works, and the ceiling is exactly where you would expect
-- the last judged run ended on the same fault in three different wordings,
"repeats as visible horizontal bands", "the decal is smeared and cut at the
panel edge", "disjointed stacked panel seams". There is no crop of a
hand-painted, weathered, unevenly lit panel that tiles invisibly. Choosing the
least-bad crop is the whole of what that approach can do.

So ask for the ingredients rather than the dish. A material authored AS a
material has no artwork to separate out, no gradient to divide away and no
hole to patch: it is already the thing the fill wants to be. The elevation
stays exactly where it is useful -- as the reference that keeps the palette
honest, and as the drawing the geometry audit still measures against.

THE MODEL AUTHORS AND NAMES; ARITHMETIC MEASURES AND VERIFIES. That division
is the one thing this repo has learned the hard way (see R3 and section 14.0:
never read proportions off pixels), and it is not relaxed here just because the
model is being asked for something it is good at. "Seamlessly tileable" is a
claim, so it is checked: tile_seam_ratio butts two copies together and scores
the join against the tile's own interior gradient. A swatch that fails goes
through the same overlap blend the carved tiles used, and the score after is
recorded. Nothing is trusted because it was requested.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402
from seamless_tile import (make_seamless_overlap, tile_seam_ratio,  # noqa: E402
                           cross_seam_ratio, damp_outliers)

# Six is a compromise found by looking: three leaves a cabinet without its
# grille or its glass, and nine makes each cell small enough that the model
# starts drawing objects in them instead of material.
COLS, ROWS = 3, 2

PROMPT = """A MATERIAL SWATCH SHEET for a {asset}, in the style of the attached
reference elevations.

Draw a {cols} by {rows} grid of square swatches on a pure white background,
with a wide white gutter between every swatch and a wide white margin around
the whole grid.

Each square is ONE MATERIAL of this {asset}, filling its square edge to edge:

  - the main body panel, as bare material
  - a second body material if the prop has one (a different panel, wood, metal)
  - the metal of its trim, mouldings and fixings
  - a mesh, grille or vent material if it has one
  - a dark material: rubber, plastic, the inside of a recess
  - a worn/dirty version of the main body panel

EVERY SWATCH MUST BE:

  - FLAT MATERIAL ONLY. No object, no fitting, no edge, no corner, no border,
    no outline, no lettering, no logo, no number, no icon, no label.
  - EVENLY LIT. No highlight, no shadow, no vignette, no gradient from one
    side to the other. Same brightness in the middle as at the edges.
  - SEAMLESSLY TILEABLE. The left edge must continue into the right edge and
    the top edge into the bottom, so that copies laid side by side show no
    join at all.
  - FINE GRAINED. Small scale grain, weathering and speckle, of the kind that
    reads as a surface. No large blobs, no big stains, no single feature that
    the eye would find again when the swatch is repeated.

Hand-painted PlayStation-era texture look, low resolution, muted palette taken
from the reference. Do not label the swatches. Do not draw the {asset} itself.
"""

NAME_ASK = """These are material swatches cut from a sheet for a {asset}.

Name each one for what MATERIAL it is, in one or two lowercase words with
underscores -- for example body_panel, worn_panel, metal_trim, vent_mesh,
dark_rubber, wood. Use the same name only once.

Also say, for each, whether it is the prop's MAIN body material.

JSON only, one entry per swatch in the order given:
{{"materials": [{{"n": 1, "name": "...", "main": true}}, ...]}}"""


def cells(path, cols=COLS, rows=ROWS, pad=3):
    """Cut the sheet on its white gutters. Deterministic; no model involved.

    The grid is asked for and then MEASURED, not assumed: a model that draws
    five swatches instead of six, or drifts the spacing, still splits
    correctly, and if the gutters cannot be found at all the even division is
    the fallback rather than the failure.
    """
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[W - 1, 0], px[0, H - 1],
                  px[W - 1, H - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    def runs(flags, lo):
        out, s = [], None
        for i, f in enumerate(flags):
            if f and s is None:
                s = i
            elif not f and s is not None:
                if i - s >= lo:
                    out.append((s, i))
                s = None
        if s is not None and len(flags) - s >= lo:
            out.append((s, len(flags)))
        return out

    xr = runs([any(not is_bg(px[x, y]) for y in range(0, H, 2))
               for x in range(W)], W // (cols * 4))
    yr = runs([any(not is_bg(px[x, y]) for x in range(0, W, 2))
               for y in range(H)], H // (rows * 4))
    # THE GRID IS WHATEVER WAS DRAWN, NOT WHATEVER WAS ASKED FOR. The prompt
    # asks for 3 by 2 and the model drew 2 by 4 -- which is a perfectly good
    # sheet of six materials, and the first version of this splitter measured
    # that correctly and then threw the measurement away in favour of the
    # request. Overriding a measurement with an assumption is the one mistake
    # this whole tool is organised against. The layout is data; only when the
    # gutters yield nothing usable is an even split a better guess than none.
    if not (1 <= len(xr) <= 6 and 1 <= len(yr) <= 6 and 2 <= len(xr) * len(yr) <= 16):
        print(f"  gutters gave {len(xr)}x{len(yr)} -- splitting evenly instead")
        xr = [(int(W * i / cols), int(W * (i + 1) / cols)) for i in range(cols)]
        yr = [(int(H * j / rows), int(H * (j + 1) / rows)) for j in range(rows)]
    else:
        print(f"  grid measured {len(xr)}x{len(yr)}")

    out = []
    for (y0, y1) in yr:
        for (x0, x1) in xr:
            # inset, because the swatch's own outermost pixels are where a
            # drawn square blends into the gutter and are not material
            k = pad + max(2, (x1 - x0) // 24)
            box = (x0 + k, y0 + k, max(x0 + k + 8, x1 - k),
                   max(y0 + k + 8, y1 - k))
            out.append(im.crop(box))
    return out


def prove(sw, size=64):
    """Make it tile, and say by how much it did not.

    A swatch is asked for as tileable and then treated as though it might not
    be, because that is the difference between a pipeline that works and one
    that works when the model is having a good day. The overlap blend is the
    same one the carved tiles used; the only change is that it now starts from
    material rather than from a crop of a painting, which is why it has so
    little left to do.
    """
    src = sw.convert("RGB").resize((size, size), Image.LANCZOS)
    before = max(tile_seam_ratio(src) + cross_seam_ratio(src))
    best = None
    for k in (8, 12, 16):
        big = sw.convert("RGB").resize((size + k, size + k), Image.LANCZOS)
        t = make_seamless_overlap(big, size, size, k)
        got = max(tile_seam_ratio(t) + cross_seam_ratio(t))
        if best is None or got < best[0]:
            best = (got, t)
    after, tile = best
    # KEEP WHICHEVER ACTUALLY TILES BETTER, FULL STOP. The blend exists to
    # rescue a crop that does not wrap; on a swatch drawn as material it has
    # little to fix and can only soften. The vent mesh proved it -- a hard
    # regular grid, 1.36 raw, 1.64 after blending, because cross-fading a
    # lattice against a half-period copy of itself smears the lattice. Gating
    # the raw square behind an absolute threshold threw away the better of the
    # two whenever both were imperfect, which is precisely when it matters.
    if before <= after:
        return damp_outliers(src), before, before
    return damp_outliers(tile), before, after


def flat_cell(face, n=9):
    """The calmest cell on the elevation: this prop's bare panel.

    ASKED HERE RATHER THAN READ FROM A FILE. layer_build works this out and
    writes it down, but layer_build runs later in the pipeline than the atlas
    does -- so on a prop built from scratch the file did not exist yet, the
    grain target fell back to a slab taken by fraction, and that slab lands on
    the coin door and measures EDGES. It reported a panel grain of 5.74 against
    a swatch that cannot exceed about 2 at any scale, so the match pinned
    itself to the end of its range. Same question, asked where it is needed.
    """
    W, H = face.size
    best = None
    for i in range(n):
        for j in range(n):
            box = (int(W * i / n), int(H * j / n),
                   int(W * (i + 1) / n), int(H * (j + 1) / n))
            if box[2] - box[0] < 8 or box[3] - box[1] < 8:
                continue
            c = face.crop(box)
            g = grain_px(c)
            if best is None or g < best[0]:
                best = (g, c)
    return best[1] if best else face


def panel_tile(face, want, n=9, size=64):
    """A tile carved from the prop's own panel, for when the swatch is flat.

    THE ORDINARY RUN OF THE FACE, not the calmest inch of it. flat_cell picks
    the single smoothest cell, which is the right question for a colour and the
    wrong one for a texture -- carving from it would hand back another flat
    square. The cell whose grain is nearest the panel's own is the one that
    looks like the panel, and it has the panel's grime, seams and wear in it
    because it IS the panel.
    """
    W, H = face.size
    best = None
    for i in range(n):
        for j in range(n):
            box = (int(W * i / n), int(H * j / n),
                   int(W * (i + 1) / n), int(H * (j + 1) / n))
            if box[2] - box[0] < 8 or box[3] - box[1] < 8:
                continue
            c = face.crop(box)
            d = abs(grain_px(c) - want)
            if best is None or d < best[0]:
                best = (d, c)
    if not best:
        return None
    k = 12
    big = best[1].convert("RGB").resize((size + k, size + k), Image.LANCZOS)
    return damp_outliers(make_seamless_overlap(big, size, size, k))


def recolour(tile, target):
    """Put the swatch's median onto the panel's, channel by channel."""
    px = tile.load()
    W, H = tile.size
    for c in range(3):
        vals = sorted(px[x, y][c] for x in range(W) for y in range(H))
        have = vals[len(vals) // 2]
        k = 0.0 if have <= 0 else max(0.25, min(4.0, target[c] / have))
        for x in range(W):
            for y in range(H):
                q = list(px[x, y])
                q[c] = max(0, min(255, int(round(q[c] * k))))
                px[x, y] = tuple(q)
    return tile


def grain_px(im, step=1):
    """How fine this surface is: mean absolute neighbour difference."""
    g = im.convert("RGB")
    W, H = g.size
    px = g.load()
    n = tot = 0
    for x in range(0, W - step, 2):
        for y in range(0, H - step, 2):
            a, b = px[x, y], px[x + step, y + step]
            tot += sum(abs(p - q) for p, q in zip(a, b)) / 3
            n += 1
    return tot / max(1, n)


def lo_hi_clear(n, lo=16, hi=192):
    """Did the search settle inside its range, or give up at an edge?"""
    return lo * 1.05 < n < hi * 0.95


def panel_grain(face, n=9):
    """How coarse this prop's PANEL is, as opposed to its flattest inch.

    THE FLATTEST CELL IS THE WRONG TARGET FOR GRAIN, and it is the right one
    for colour, which is how the mistake got in. The flat cell is chosen
    precisely because it is the smoothest patch on the face -- ideal for taking
    a median colour off, since no edge pollutes it -- so matching a material's
    grain to it asks the material to be as smooth as the smoothest thing on the
    prop. The search obligingly went to the bottom of its range on two props
    running, which is the same "pinned to an endpoint" answer that the coin
    door gave at the other end, and means the match never converged at all.
    The panel is not the smoothest cell and it is not the busiest either: it is
    the ordinary run of the face. Taking the median grain of the calmer half of
    the cells says that, and drops the fittings without landing on a mirror.
    """
    W, H = face.size
    vals = []
    for i in range(n):
        for j in range(n):
            box = (int(W * i / n), int(H * j / n),
                   int(W * (i + 1) / n), int(H * (j + 1) / n))
            if box[2] - box[0] >= 8 and box[3] - box[1] >= 8:
                vals.append(grain_px(face.crop(box)))
    if not vals:
        return 1.0
    vals.sort()
    calm = vals[:max(1, len(vals) // 2)]
    return calm[len(calm) // 2]


def match_grain(tile, want, lo=16, hi=192, tall=None):
    """How many elevation pixels one tile should cover.

    A SWATCH HAS NO SCALE OF ITS OWN. It is a square of material and nothing in
    it says whether that square is a hand's width or a wall. Guessing a number
    puts the prop's grain at a size unrelated to its painted panels, and the
    two then disagree wherever they meet -- which is exactly the join the fill
    has to cross. The elevation already shows this material at the right size,
    so match to it: resample the tile to each candidate size and take the one
    whose grain statistic lands closest to the painted panel's. Measured, per
    prop, from the drawing that is already the reference for everything else.
    """
    # A REPEAT IS VISIBLE BECAUSE IT REPEATS OFTEN, so the size a material is
    # shown at is bounded before it is optimised. Two things pushed the search
    # to the bottom of its range and both were artefacts rather than answers:
    # damping the tile's outliers -- necessary, it is what stops a blob reading
    # as wallpaper -- leaves it smoother, so the matcher chased the panel's
    # coarser grain by shrinking; and shrinking is measured by downsampling,
    # which ALIASES, so a small tile scores a high grain it does not really
    # have. The result was a 16px tile repeating nearly forty times up the
    # prop, which is precisely the "visible repeating hatch/dot pattern" both
    # judges then reported. No material on a prop this size repeats ten times,
    # whatever the statistic says, so that is the floor and the match chooses
    # within it.
    if tall:
        lo = max(lo, tall // 10)
        hi = max(lo + 1, hi)
    best = None
    n = lo
    while n <= hi:
        got = grain_px(tile.resize((n, n), Image.LANCZOS))
        d = abs(got - want)
        if best is None or d < best[0]:
            best = (d, n, got)
        n = int(n * 1.4)
    return best[1], round(want, 2), round(best[2], 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--redraw", action="store_true")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    d.mkdir(parents=True, exist_ok=True)
    sheet = d / "materials.png"
    key = load_key()

    if args.redraw or not sheet.exists():
        refs = [p for p in (d / "front.png", d / "side.png") if p.exists()]
        generate_image(
            PROMPT.format(asset=args.asset, cols=COLS, rows=ROWS),
            sheet, key, refs=refs)
        print(f"  drew {sheet}")

    sw = cells(sheet)
    print(f"  {len(sw)} swatches")

    out = d / "materials"
    out.mkdir(exist_ok=True)
    got = []
    for i, s in enumerate(sw, 1):
        tile, before, after = prove(s, args.size)
        p = out / f"m{i}.png"
        tile.save(p)
        tq = tile.convert("RGB").load()
        med = [sorted(tq[x, y][c] for x in range(tile.size[0])
                      for y in range(tile.size[1]))[
                   tile.size[0] * tile.size[1] // 2] for c in range(3)]
        got.append({"n": i, "image": f"materials/m{i}.png",
                    "seam_before": round(before, 3),
                    "seam_after": round(after, 3),
                    "median": med,
                    "tiles": bool(after <= 1.25)})
        print(f"    m{i}: seam {before:.2f} -> {after:.2f}"
              f"{'' if after <= 1.25 else '   STILL SEAMS'}")

    # NAMING IS THE MODEL'S JOB AND MEASURING IS NOT, so it is asked only what
    # each material IS -- never how big, how it repeats or where it goes.
    named = {}
    try:
        from gemini_judge import vision_json
        r, model = vision_json(NAME_ASK.format(asset=args.asset),
                               [out / f"m{i}.png" for i in range(1, len(sw) + 1)],
                               key)
        for e in r.get("materials", []):
            try:
                named[int(e["n"])] = (str(e.get("name", "")).strip().lower()
                                      .replace(" ", "_")[:32],
                                      bool(e.get("main")))
            except (KeyError, TypeError, ValueError):
                continue
        print(f"    {model} named {len(named)} of {len(sw)}")
    except Exception as e:
        print(f"  ! naming failed ({type(e).__name__}) -- numbers will do")

    seen = set()
    for g in got:
        nm, main = named.get(g["n"], (f"material_{g['n']}", False))
        if not nm or nm in seen:
            nm = f"material_{g['n']}"
        seen.add(nm)
        g["name"], g["main"] = nm, main
    if not any(g["main"] for g in got):
        got[0]["main"] = True         # something has to be the carcass

    # THE SWATCH CARRIES THE GRAIN; THE PROP DECIDES THE COLOUR. This rule was
    # already proved once, on the carved tile, and then not applied to the
    # authored one -- an inconsistency both judges found within a round. The
    # atlas for this cabinet came back with a body panel at (44,43,44), a
    # neutral near-black, against a prop whose own panel is (53,74,69), a green
    # grey. On the previous prop the two happened to agree and it looked
    # perfect; here the fill read as exactly what the graders called it,
    # "massive flat untextured grey voids". Which is the whole point of asking
    # a drawing model for material rather than for a colour: it is very good at
    # the grain and it has no way to know what this particular cabinet is
    # painted. So the main material -- the one the carcass is filled with -- is
    # put onto the prop's own panel median. The others keep their colours,
    # because a wood or a rubber is supposed to differ from the panel.
    px_per_tile = 48
    try:
        from identify_parts import object_crop
        face = object_crop(d / "front.png").convert("RGB")
        W2, H2 = face.size
        # FROM THE CLEANEST FLAT CELL, NOT FROM THE MIDDLE OF THE FACE. A slab
        # taken by fraction lands on the coin door and its trim, and the grain
        # statistic then measures EDGES rather than material -- 11.1 against a
        # swatch that cannot exceed about 2 however it is scaled, so the match
        # pins itself to whichever end of the range it started from.
        # layer_build already finds the flattest cell on the face and writes it
        # down for the panel patch; that is the same question asked once.
        panel = flat_cell(face)
        main = next(g for g in got if g["main"])
        pp = panel.convert("RGB").load()
        pw2, ph2 = panel.size
        target = [sorted(pp[x, y][c] for x in range(pw2) for y in range(ph2))[
            pw2 * ph2 // 2] for c in range(3)]
        mt = recolour(Image.open(out / f"m{main['n']}.png").convert("RGB"), target)
        mt.save(out / f"m{main['n']}.png")
        main["median"] = target
        print(f"  {main['name']} recoloured to the prop's panel {target}")
        pg = panel_grain(face)
        px_per_tile, want, gotg = match_grain(mt, pg, tall=H2)
        # A MATERIAL WITH NO GRAIN IS NOT A MATERIAL. Everything here checks
        # that the swatch TILES, and a flat square of colour tiles perfectly --
        # it scores about 1.0 on both seam ratios and sails through, which is
        # how this cabinet's cabinet_body came back as a featureless grey-green
        # square and got used. Every judge for two rounds then reported the
        # same thing in the same words: at 1.5x height "the lower cabinet
        # extends as an enormous flat, untextured, featureless grey monolith",
        # at 2x width "massive blank flat grey areas". They were describing the
        # material exactly. Its grain was 0.49 against a painted panel of 8.07,
        # sixteen times too smooth at any scale the matcher could reach, and
        # the match duly pinned itself to the end of its range -- which was
        # already being PRINTED as a warning every run and treated as noise.
        #
        # The painting always has the answer: the prop's own panel, carved and
        # made to wrap, is the material by definition. It is the fallback the
        # renderer has always had for a missing atlas; it just needed to also
        # be the fallback for an empty one.
        if gotg < want / 3:
            carved = panel_tile(face, pg)
            if carved is not None:
                carved = recolour(carved, target)
                carved.save(out / f"m{main['n']}.png")
                mt = carved
                n2, want, g2 = match_grain(mt, pg, tall=H2)
                print(f"  {main['name']} came back FLAT ({gotg} against a "
                      f"panel of {want}) -- carved from the prop's own panel "
                      f"instead, now {g2}")
                px_per_tile, gotg = n2, g2
        edge = ("" if lo_hi_clear(px_per_tile, max(16, H2 // 10))
                else "   (at the end of the range)")
        print(f"  grain: panel {want}, tile {gotg} at {px_per_tile}px "
              f"of a {H2}px elevation{edge}")
    except Exception as e:
        print(f"  ! grain match failed ({type(e).__name__}), using {px_per_tile}px")

    (d / "materials.json").write_text(json.dumps(
        {"asset": args.asset, "px_per_tile": px_per_tile,
         "materials": got}, indent=1))
    ok = sum(1 for g in got if g["tiles"])
    print(f"  {ok}/{len(got)} tile cleanly -> {d / 'materials.json'}")
    print("   ", ", ".join(f"{g['name']}{'*' if g['main'] else ''}" for g in got))


if __name__ == "__main__":
    main()
