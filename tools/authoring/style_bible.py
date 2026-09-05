#!/usr/bin/env python3
"""Generate AND MEASURE a style bible, then write it out as numbers.

    python3 tools/authoring/style_bible.py            # generate all sheets
    python3 tools/authoring/style_bible.py scale-ladder face-tints
    python3 tools/authoring/style_bible.py --measure-only

Authoring tool. NOT a build, CI or runtime dependency. The game never calls
this and never reads the key.

WHY THIS EXISTS, AND WHY IT IS NOT "GENERATE A PRETTY STYLE SHEET".

Every earlier pass at matching the reference generated an image, LOOKED at it,
and typed numbers into a build function. Every one of those passes got
something wrong — the door border came out at 15.5% against a measured 8.75%,
the body 12% too shallow, the speckle invented outright — because "how wide is
that border as a fraction of the panel" is not a judgement anybody makes
reliably twelve times in a row. The image was never the problem. Reading it by
eye was.

So each sheet here is designed backwards from a NUMBER it has to yield:

  scale-ladder   the same panel drawn small, medium and large. Measure the
                 border on each. If the border is the same number of PIXELS at
                 all three sizes, the style's borders are FIXED and belong in
                 world units; if it is the same FRACTION, they are relative and
                 belong in UV. This is the single measurement that decides how
                 the whole material system must be built, and it is invisible
                 to the eye on any one panel.
  face-tints     one colour on the top, front and side of a cube. Measure the
                 ratios; they are the entire lighting model of this style.
  palette        the flat colours, so the render can snap to a locked set.
  surface-marks  a big empty panel. Measure what fraction of it is NOT the base
                 colour, which settles arguments about speckle and wear with a
                 number instead of taste.
  edge-vocab     how corners, seams and joints are drawn where forms meet.

THE BACKGROUND IS MAGENTA ON PURPOSE. Measuring an earlier render against a
cream ground silently classified the cream door frame AS ground — the two were
within a few values — and reported a frame three times thinner than it is. A
ground that cannot be confused with any palette colour makes the silhouette
unambiguous. A measurement tool that can mistake the subject for the background
is worse than no tool.

Output carries an invisible SynthID watermark and C2PA credentials.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from concept_sheet import generate_image, load_key  # noqa: E402

OUT = ROOT / "docs" / "style-bible"
REFS = ROOT / "docs" / "reference"
SPEC = ROOT / "docs" / "style-spec.json"

BG = (255, 0, 255)      # magenta: in no palette, so never mistaken for subject

COMMON = (
    "Flat 2D orthographic diagram. NO perspective, NO drop shadow, NO ground "
    "plane, NO reflection, NO gradients, NO anti-aliasing, NO soft edges. "
    "Every region is ONE flat colour with hard pixel edges. "
    "The background is PURE MAGENTA #ff00ff, completely flat, everywhere that "
    "is not part of the diagram. "
    "No text, no numbers, no labels, no captions, no arrows, no watermark."
)

SHEETS = {
    # THE decisive one. Everything else is colour; this is architecture.
    "scale-ladder": (
        "Draw THREE separate rectangular metal panels in a horizontal row on "
        "the magenta background, well separated, all in the same material and "
        "colour: the first small, the second about twice as wide and tall, the "
        "third about four times as wide and tall as the first. "
        "Give all three panels EXACTLY the same edge treatment as each other — "
        "the same dark outline, the same lighter catch along the top and left, "
        "and the same recessed inner border set in from the edge. "
        "Draw that edge treatment the way this art style actually does it when "
        "a panel changes size. Keep the flat middle of each panel plain."),
    "face-tints": (
        "Draw ONE cube in isometric projection on the magenta background, "
        "painted a single flat mid-green colour. Show exactly three faces: the "
        "top, the left side and the right side. Each face is ONE flat colour — "
        "the same hue at three different brightnesses, the top lightest. "
        "No outline between the cube and the background, no texture, no marks "
        "on any face. Nothing else in the image."),
    "palette": (
        "Draw a grid of flat colour swatches on the magenta background: five "
        "columns by four rows of plain square patches, evenly spaced, each a "
        "single flat colour with no border and no shading. Use the full colour "
        "range of the reference images: the creams, the pale blue-greys, the "
        "greens and teals, the muted purples, the warm tans, and the near-black "
        "darks. Nothing else in the image."),
    "surface-marks": (
        "Draw ONE large plain rectangular panel of pale blue-grey painted metal "
        "filling most of the magenta background. Put on it ONLY the surface "
        "marks this art style would actually put on a large empty painted "
        "panel, drawn at the size and spacing the style uses. If the style "
        "leaves such a panel plain, leave it plain."),
    # The reference props carry DENSE per-texel texture — the radio's speaker is
    # a hard checkerboard, its cream panel is dithered, its body is mottled wood.
    # None of that survives a lossy screenshot well enough to measure, so ask for
    # it clean, big, and on a stated texel grid.
    "texture-swatches": (
        "Draw FOUR large square texture swatches in a horizontal row on the "
        "magenta background, well separated, each swatch filling its square "
        "edge to edge with NO border and NO frame: "
        "(1) cream painted metal, (2) dark brown wood, "
        "(3) a dark speaker grille, (4) pale blue-grey painted steel. "
        "Draw each swatch as CHUNKY PIXEL ART on a coarse grid of about 24 by "
        "24 large square pixels, so the individual pixels are obvious. "
        "Show the per-pixel surface texture this art style actually paints: "
        "scattered lighter and darker pixels, dithering, checkerboard "
        "patterns, and grain runs where the style uses them. "
        "Use only two or three closely-related tones within each swatch."),
    "texel-ladder": (
        "Draw TWO squares of the SAME dark brown wood texture side by side on "
        "the magenta background, the second about three times wider and taller "
        "than the first. Draw both as chunky pixel art with the SAME physical "
        "pixel size as each other, so the larger square simply contains MORE "
        "pixels of the same texture rather than the same number of bigger "
        "pixels. No borders, no frames, no outlines."),
    # WHAT ACTUALLY GIVES A PROP CHARACTER. Procedural texture cannot answer
    # this: character is detail that MEANS something and sits where it belongs —
    # a vent where air moves, a label where you would read one, wear on the
    # corner that gets knocked. A uniform hash over every face is the exact
    # opposite, and produces noise that reads as dirt. Ask for the same object
    # twice so the difference IS the answer.
    "character-ab": (
        "Draw the SAME tall narrow cabinet TWICE, side by side on the magenta "
        "background, both exactly the same size and shape and colour, both in "
        "flat orthographic front view. "
        "The LEFT one is completely plain: flat panels, nothing on them. "
        "The RIGHT one is the same cabinet finished by a professional prop "
        "artist in this art style — add the fittings and markings that give a "
        "prop its character, each placed where it would really belong. "
        "Do not add random speckle or dirt to either one."),
    # The fittings themselves, isolated so they can be cut out and measured.
    "fittings": (
        "Draw a set of TWELVE small separate pixel-art fittings for a retro "
        "pharmacy refrigerator, arranged in a loose grid on the magenta "
        "background with clear magenta space between every one of them, each "
        "drawn straight on with no perspective: "
        "a hinge, a latch, a small vent of horizontal slots, a rating plate, a "
        "warning label, a paper label in a holder, a rocker switch, a dial, a "
        "small digital readout, a screw head, a rubber foot, and a short strip "
        "of diagonal hazard stripes. "
        "Each fitting is small and chunky, a few dozen pixels across, drawn "
        "flat with hard pixel edges. Nothing may touch anything else."),
    # SURFACE TILES for the nine-slice detail atlas. Authored in NEUTRAL GREY on
    # purpose: the renderer reads them as a three-level tone mask (shade / base /
    # lit) and substitutes each material's own family, so one "panel" tile
    # renders correctly on cream, teal and blue-grey alike. Asking for colour
    # here would tie every tile to one material and put the atlas back in charge
    # of the palette, which is what broke the previous atlas attempt.
    #
    # Each panel's recessed border must sit exactly AT its own edge, because the
    # nine-slice ring samples the outer texels: put the border there and it
    # becomes the part's border at any size, with the flat middle tiling
    # between. A panel floating inside a margin makes the ring sample margin.
    "surfaces": (
        "Draw FIVE separate square panels in a horizontal row on the magenta "
        "background, well separated from each other. "
        "Every panel is NEUTRAL MID-GREY painted metal — no colour at all — "
        "drawn with exactly three flat greys: a mid-grey field, a darker grey "
        "and a lighter grey. "
        "CRITICAL: draw each panel as VERY LOW RESOLUTION pixel art, only about "
        "TWENTY chunky square pixels across the whole panel. The pixels must be "
        "huge and obvious, like a PlayStation 1 texture. Every mark is one or "
        "two of those huge pixels thick — no thin lines, no fine detail, no "
        "small dots. Blocky, heavy and rugged, not neat. "
        "Each panel's border sits exactly at that panel's outer edge, with "
        "nothing outside it, and is TWO chunky pixels thick. The five are: "
        "(1) a plain pressed panel with a chunky border and one big bolt just "
        "inside each of its four corners; "
        "(2) the same panel but with a thick horizontal seam across its middle; "
        "(3) a panel whose middle is filled with a few thick horizontal vent "
        "slots running edge to edge; "
        "(4) a plain panel with only a chunky border and nothing else; "
        "(5) a panel with one big shallow rectangular recess in its middle. "
        "No text, no colour, no gradients, no anti-aliasing."),
    "edge-vocab": (
        "Draw FOUR separate small studies in a row on the magenta background, "
        "well separated, all in cream and pale blue-grey painted metal: "
        "(1) an outside corner where two panels meet at ninety degrees, "
        "(2) a horizontal seam where an upper panel sits on a lower panel, "
        "(3) a recessed inset panel inside a larger frame, "
        "(4) a raised trim strip running across a panel. "
        "Draw each the way this art style draws it. Nothing else."),
}

REF_INSTRUCTION = (
    "The images above are the STYLE REFERENCE. They are a voxel prop kit: "
    "hard-edged blocky forms, flat faces, a limited muted palette, crisp pixel "
    "edges, panel lines and small sparse accents. Match their rendering style "
    "exactly — the same flat shading, the same edge treatment, the same colour "
    "relationships. Do NOT copy their subject matter, and do NOT draw any of "
    "their objects. Draw only what the instruction below asks for."
    "\n\n"
    # The target sits further toward the chunky end of that reference set than
    # the first pass assumed. A published prop in this style states its own
    # budget: 138 triangles and a 64x32 pixel texture for an entire door. That
    # is the constraint to draw to — an object is a handful of big boxes and its
    # whole surface is a few hundred pixels, so any mark thinner than one of
    # those huge pixels simply cannot exist.
    "ADDITIONALLY, push everything toward the CHUNKY, RUGGED, LOW-BUDGET end of "
    "that style: PlayStation 1 era game art. Very few, very large forms. "
    "Extremely low texture resolution with big obvious square pixels. Heavy, "
    "solid, slightly crude shapes rather than neat precise ones. Thick marks "
    "only. Nothing delicate, nothing thin, nothing finely detailed."
)


def refs():
    """The user's own reference set — the style being matched."""
    return sorted(REFS.glob("crop-*.png")) or sorted(REFS.glob("*.png"))


# ---------------------------------------------------------------------------
# MEASUREMENT. Each function returns plain numbers, or None when the sheet did
# not come back measurable — which is a result too, and better than a guess.

def _load(name, colours=10, snap=16):
    """The sheet, QUANTISED before anything measures it.

    The generator returns anti-aliased art however hard the prompt asks for
    hard pixel edges, so a "flat" panel is really a few hundred near-identical
    values. Run-length measurement on the raw image found 71 colour bands
    across one plain panel and concluded its border was 47% of its width.
    Quantising first is what makes "the flat middle" a thing that exists.
    """
    p = OUT / f"{name}.png"
    if not p.exists():
        return None
    im = Image.open(p).convert("RGB")
    # FLATTEN THE BACKGROUND FIRST. Median-cut allocates its slots by AREA, and
    # the magenta ground is most of the image — asked for 8 colours it spent
    # SEVEN on shades of magenta a hair apart and gave the entire cube one, so
    # all three faces measured identical. Collapsing the ground to a single
    # exact value first leaves every remaining slot for the subject. (This is
    # the same trap that once turned the atlas grille grey.)
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if _is_bg(px[x, y], 180):
                px[x, y] = BG
    im = im.quantize(colors=colours, method=Image.MEDIANCUT).convert("RGB")
    if not snap:
        return im
    # ...then MERGE NEAR-DUPLICATES BY DISTANCE. Quantising alone is not enough:
    # median-cut happily spends two slots on #506060 and #506070, the same
    # colour to any eye, and a flat middle split across both never forms the one
    # wide run the border measurement looks for.
    #
    # Snapping each channel to a grid was the obvious fix and it is wrong — two
    # values 16 apart straddle a 16-grid boundary and survive it, which is
    # exactly the pair above. Greedy merge on distance has no boundaries to
    # straddle. Structure only: measurements that report a COLOUR pass snap=0,
    # because this would also fuse the cube's two side faces.
    px = im.load()
    counts = Counter(px[x, y] for x in range(im.width) for y in range(im.height))
    keep, remap = [], {}
    for c, _ in counts.most_common():
        hit = next((k for k in keep if sum(abs(a - b) for a, b in zip(c, k)) <= snap), None)
        remap[c] = hit or c
        if hit is None:
            keep.append(c)
    for y in range(im.height):
        for x in range(im.width):
            px[x, y] = remap[px[x, y]]
    return im


def _is_bg(c, tol=90):
    return abs(c[0] - 255) + abs(c[1] - 0) + abs(c[2] - 255) < tol


def _blobs(im, min_area=400):
    """Connected non-background regions, as bounding boxes. Coarse on purpose:
    the sheets are a handful of well-separated shapes, not a photo."""
    px = im.load()
    w, h = im.size
    seen = [[False] * h for _ in range(w)]
    out = []
    for sx in range(0, w, 4):
        for sy in range(0, h, 4):
            if seen[sx][sy] or _is_bg(px[sx, sy]):
                continue
            stack, x0, y0, x1, y1, n = [(sx, sy)], sx, sy, sx, sy, 0
            while stack:
                x, y = stack.pop()
                if not (0 <= x < w and 0 <= y < h) or seen[x][y] or _is_bg(px[x, y]):
                    continue
                seen[x][y] = True
                n += 1
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
                stack += [(x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2)]
            if n * 4 >= min_area:
                out.append((x0, y0, x1, y1))
    return sorted(out, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)


def _runs(px, y, x0, x1):
    """Constant-colour runs along a row, as (start, length, colour)."""
    out, st, cur = [], x0, px[x0, y]
    for x in range(x0 + 1, x1 + 2):
        c = px[x, y] if x <= x1 else None
        if c != cur:
            out.append((st, x - st, cur))
            st, cur = x, c
    return out


def measure_scale_ladder():
    """THE measurement: is the border a fixed width, or a fixed fraction?

    Read as the distance from the panel's outer edge to the start of its flat
    middle — found as the LONGEST constant-colour run across the panel's centre
    row. An earlier version walked in until the colour matched the middle, which
    silently reported nonsense because each panel's middle is a slightly
    different value; the longest run needs no such assumption.
    """
    im = _load("scale-ladder", 12, snap=40)
    if not im:
        return None
    px = im.load()
    w, h = im.size
    cols = [any(not _is_bg(px[x, y], 150) for y in range(0, h, 3)) for x in range(w)]
    panels, st = [], None
    for x, v in enumerate(cols + [False]):
        if v and st is None:
            st = x
        elif not v and st is not None:
            if x - st > 40:
                panels.append((st, x - 1))
            st = None
    if len(panels) < 3:
        return {"error": f"found {len(panels)} panels, need 3"}

    rows = []
    for (a, b) in panels:
        ys = [y for y in range(h) if not _is_bg(px[(a + b) // 2, y], 150)]
        cy = (min(ys) + max(ys)) // 2
        pw = b - a + 1
        # The border is the stack of narrow bands between the panel's edge and
        # its wide flat middle. Take runs from the edge inward until one is wide
        # enough to be the middle; drop the 1px magenta fringe on the way in.
        bands = []
        for st_, ln, c in _runs(px, cy, a, b):
            if _is_bg(c, 220) or (ln <= 2 and not bands):
                continue
            if ln > pw * 0.25:
                break
            bands.append((ln, "#%02x%02x%02x" % c))
        rows.append({"panel_px": pw, "border_px": sum(l for l, _ in bands),
                     "bands": bands})
    rows.sort(key=lambda r: r["panel_px"])
    bpx = [r["border_px"] for r in rows]
    bfr = [r["border_px"] / r["panel_px"] for r in rows]

    def spread(v):
        return (max(v) - min(v)) / max(1e-9, sum(v) / len(v))
    fixed = spread(bpx) < spread(bfr)
    return {
        "panels": rows,
        "widths_px": bpx,
        "widths_frac": [round(f, 4) for f in bfr],
        "px_spread": round(spread(bpx), 3),
        "frac_spread": round(spread(bfr), 3),
        "verdict": "fixed" if fixed else "relative",
        "reading": (
            "the border keeps its WIDTH as the panel grows, so borders are a "
            "world-space constant and belong in world units, not UV"
            if fixed else
            "the border keeps its FRACTION, so borders scale with the part"),
    }


def measure_face_tints():
    """The lighting model: how much each face darkens, as a ratio.

    Sampled at geometric points on the cube rather than by counting colours —
    the two side faces are close enough in value that a frequency count picked
    the same face twice and reported a ratio of 1.000.
    """
    im = _load("face-tints", 8, snap=0)
    if not im:
        return None
    px = im.load()
    b = _blobs(im, 20000)
    if not b:
        return {"error": "no cube found"}
    x0, y0, x1, y1 = b[0]
    w, h = x1 - x0, y1 - y0
    pts = {"top": (x0 + w // 2, y0 + int(h * 0.22)),
           "left": (x0 + int(w * 0.22), y0 + int(h * 0.68)),
           "right": (x0 + int(w * 0.78), y0 + int(h * 0.68))}
    face = {k: px[p] for k, p in pts.items()}
    if any(_is_bg(c) for c in face.values()):
        return {"error": "sample points missed the cube"}
    if len({face["left"], face["right"], face["top"]}) < 3:
        return {"error": f"faces not distinct: {face} — check the quantise step"}
    base = max(1e-9, sum(face["left"]) / 3)
    return {"faces_hex": {k: "#%02x%02x%02x" % c for k, c in face.items()},
            "ratio_to_left_face": {k: round(sum(c) / 3 / base, 3)
                                   for k, c in face.items()}}


def measure_palette():
    im = _load("palette", 32, snap=0)
    if not im:
        return None
    px = im.load()
    cnt = Counter(px[x, y] for x in range(0, im.width, 2)
                  for y in range(0, im.height, 2) if not _is_bg(px[x, y], 200))
    kept = []
    for c, n in cnt.most_common(400):
        if n < 40:
            break
        # Drop anything sitting on the magenta ramp: those are the generator's
        # anti-aliasing against the background, not swatches.
        if c[0] > 200 and c[2] > 200 and c[1] < c[0] - 20:
            continue
        if all(sum(abs(a - b) for a, b in zip(c, k)) > 40 for k in kept):
            kept.append(c)
    return {"colours": ["#%02x%02x%02x" % c for c in kept[:24]]}


def measure_surface_marks():
    """What a big empty panel actually carries.

    The interesting answer was not "how speckled is it" but that the style
    SUBDIVIDES a large panel into sub-panels with seams. So measure that: how
    many sub-panels, how flat each one is, and how much of the whole is
    saturated accent. A single "marked fraction" over the whole sheet counted
    the seams and every sub-panel's own shade as marks and read 76%, which said
    "heavily patterned" about an image whose fields are flat.
    """
    im = _load("surface-marks", 16, snap=0)
    if not im:
        return None
    px = im.load()
    b = _blobs(im, 20000)
    if not b:
        return {"error": "no panel found"}
    x0, y0, x1, y1 = b[0]
    ins = [(x, y) for x in range(x0 + 8, x1 - 8, 2) for y in range(y0 + 8, y1 - 8, 2)]
    cnt = Counter(px[p] for p in ins)
    # Sub-panel fields: colours owning a real share of the area. Seams, screws
    # and decals are all small, so they fall below the cut by construction.
    fields = [(c, n) for c, n in cnt.most_common(24) if n / len(ins) > 0.04]
    field_share = sum(n for _, n in fields) / len(ins)
    sat = sum(n for c, n in cnt.items()
              if max(c) - min(c) > 55 and not _is_bg(c)) / len(ins)
    # count vertical seams by scanning one row for narrow dark runs
    cy = (y0 + y1) // 2
    seams = sum(1 for st, ln, c in _runs(px, cy, x0, x1)
                if 1 <= ln <= 14 and sum(c) < sum(fields[0][0]) - 60)
    return {"field_colours": ["#%02x%02x%02x" % c for c, _ in fields],
            "field_share": round(field_share, 3),
            "accent_share": round(sat, 4),
            "seams_across_one_row": seams,
            "reading": (
                "large panels are SUBDIVIDED by seams into flat sub-panels; "
                "the marks are seams, corner fasteners and a few tiny accents "
                "— the fields themselves stay flat")}


MEASURERS = {
    "scale-ladder": measure_scale_ladder,
    "face-tints": measure_face_tints,
    "palette": measure_palette,
    "surface-marks": measure_surface_marks,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="sheets to generate; default all")
    ap.add_argument("--measure-only", action="store_true")
    args = ap.parse_args()
    wanted = args.names or list(SHEETS)
    OUT.mkdir(parents=True, exist_ok=True)

    if not args.measure_only:
        key = load_key()
        r = refs()
        print(f"style reference: {len(r)} images from docs/reference/")
        failed = []
        for name in wanted:
            print(f"generating {name} ...", flush=True)
            try:
                generate_image(f"{COMMON}\n\n{SHEETS[name]}", OUT / f"{name}.png",
                               key, refs=r, ref_instruction=REF_INSTRUCTION)
            except Exception as exc:
                # One sheet tripping a filter must not lose the others: they
                # are already paid for and written.
                failed.append(name)
                print(f"  FAILED {name}: {str(exc)[:160]}")
        if failed:
            print(f"  retry with: style_bible.py {' '.join(failed)}")

    spec = {}
    print("\n--- measured ---")
    for name, fn in MEASURERS.items():
        got = fn()
        if got is None:
            print(f"{name}: (not generated)")
            continue
        spec[name] = got
        print(f"{name}: {json.dumps(got)}")
    if spec:
        SPEC.write_text(json.dumps(spec, indent=2) + "\n")
        print(f"\nwrote {SPEC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
