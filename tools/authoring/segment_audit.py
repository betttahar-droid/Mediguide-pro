#!/usr/bin/env python3
"""Catch under-segmentation that a part COUNT cannot see.

    python3 tools/authoring/segment_audit.py tools/img2threejs-work/v48_jukebox
    python3 tools/authoring/segment_audit.py work/ps1 --face front --json

Measurement-only. Reads parts_<face>.json and <face>.png; writes nothing,
calls nothing else in the pipeline, and never modifies a prop. Not a build,
CI or runtime dependency.

WHY THE EXISTING GUARD MISSES THIS. make_prop.py already refuses a
segmentation map that names fewer than half the fittings region_parts can
measure (`seg_n * 2 >= meas_n`). That catches a map that gave up early -- a
COUNT problem. It cannot catch a map whose count looks normal while one box
is doing the work of three, because the count never drops:

  v48_jukebox has 24 parts, not a suspiciously low number. Its speaker_grille
  is box [7,225,255,564] -- 47% of the whole silhouette -- and swallows the
  left bubble tube whole; only bubble_tube_right exists.
  v47_arcade_cabinet has 4 parts. Four is not obviously few for a stripped
  cabinet front, and there is no missing-COUNT signal at all: the marquee was
  never named, so it was never a box that under- or over-counted anything.
  Its rows 0-83 (12% of the silhouette, and 87% of that band is the painted
  "ARCADE" banner) are touched by NO part whatsoever.

Both are real and both are invisible to a count comparison. This file
measures for two DIFFERENT failure shapes because they are not the same
fault and one signal cannot see both:

  MISSING BAND   a horizontal strip of the silhouette that no part's box
                 touches at all, where the strip is not just bare panel but
                 carries real painted content. Rows that no part owns are
                 exactly the rows a growth band treats as safe to repeat --
                 the arcade cabinet's marquee text got copied five times
                 down the widened front because of this.
  SWALLOWED BOX  a single named part whose box is a large fraction of the
                 silhouette and whose interior -- once you remove whatever
                 other parts are legitimately nested inside it -- still
                 contains more than one substantial object-sized region, one
                 of them a clear outlier against the surrounding texture.

Both are measured straight off parts_<face>.json + the elevation, with no
model call and no knowledge of which source (segment_sheet's map or
region_parts' measurement) produced the boxes.

THE PART-COUNT VERSION OF SIGNAL 1 DOES NOT WORK. Comparing the count of
touched vs untouched silhouette pixels globally puts v47_arcade_cabinet in
the MIDDLE of the corpus, not at the top: plenty of props leave more of
their silhouette untouched by any part than v47 does, because a large flat
side panel or a plain kick rail is *correctly* left as background, not a
fault. What matters is not how much is untouched but whether the untouched
part is a physically separate horizontal STRIP no row of which any part
reaches, and whether that strip itself is busy with paint rather than bare
material. Row-banding was tried first as a plain area count and gave the
same non-result; it only separates once "untouched" means "not one row of
this touches a part," which a marquee band satisfies and an ordinary bare
side panel usually does not (something else touches most of its rows).

"BUSY" CANNOT BE COLOUR DISTANCE FROM THE PANEL ALONE. The first version of
the band check flagged any band whose pixels differ from the estimated panel
colour by more than a tolerance (region_parts.not_panel's own test). Swept
over the corpus this fired just as often on a perfectly ordinary two-tone
kick rail -- a flat grey ledge sitting above a flat brown wood-grain
lower cabinet, no fitting at all, just two panel colours meeting -- as it did
on the arcade marquee, because both differ from a single global panel
colour by roughly the same amount (art_frac 0.89 vs 0.87 on this corpus, no
gap between them at all). Colour distance cannot tell "a different flat
material" from "painted content" apart; it is the same trap the rest of this
tool avoids by never reading a proportion off a colour. Requiring the band
ALSO carry meaningful edge energy where it differs from panel -- letters have
strokes, an unlifted marquee has serifs, a two-tone seam does not -- separates
them: the kick-rail case scores 0.14 on that combined measure, every band
this file now flags scores at least 0.16, and the confirmed marquee scores
0.33.

SWALLOWED-BOX HAS A KNOWN FALSE-POSITIVE MODE, WRITTEN DOWN RATHER THAN
CHASED. A screen with a bright glare streak or its own in-screen title text
produces the identical MEASURED signature as a swallowed fitting: one
sub-region distinctly larger than the scattered noise around it, sitting
inside an otherwise busy interior (screen static, a game sprite scene).
v37_arcade_cabinet's screen ("ASTEROID RAIDERS" plus a ship sprite) and
v14_arcade_cabinet's screen (a diagonal reflection over static) both trip
this test and are not swallowed fittings -- they are one screen's own
content. Distinguishing "a bright outlier region is a separate physical
object" from "a bright outlier region is what is drawn on the one object
already named" was not solved here; it would need to know what a reflection
looks like, which is exactly the kind of perceptual question S14.0 and this
whole tool exist to avoid asking a threshold. Read a swallowed-box finding
named "screen" or "screen_bezel" with that in mind -- verified by eye on two
cases below, not fixed. A finding on a box that ISN'T a screen (a cabinet
door, a display window, a grille) did not show this failure mode in the
sample checked.

WHAT WAS NOT ATTEMPTED: masks. segment_sheet.py's masks/*.png give an exact
pixel shape per part where a model segmentation was accepted, and every prop
audited here came from region_parts' measured boxes instead (no masks/
directory in the sample), so this file works from rectangles throughout.
A mask-aware version would tighten "interior minus children" and is worth
doing the day a segmented prop needs auditing, but there was nothing in the
corpus to calibrate it against.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from identify_parts import object_crop, edge_energy  # noqa: E402
from layer_build import silhouette  # noqa: E402
from region_parts import cells, panel_colour, not_panel  # noqa: E402

# Every threshold below was checked against all ~95 props in
# tools/img2threejs-work/ (see the module docstring and the tool's own
# report), not fitted to the two confirmed cases alone.
BAND_FRAC_MIN = 0.08     # a band must be at least 8% of the silhouette
BAND_ART_MIN = 0.50      # and mostly not the panel colour
BAND_BOTH_MIN = 0.16     # and mostly not-panel AND edge-busy at once
BOX_FRAC_MIN = 0.18      # a box worth auditing is at least 18% of the prop
BOX_TOP_MIN = 0.12       # its largest orphan sub-region is a real object
BOX_RATIO_MIN = 7.0      # ... and stands out from the surrounding texture
BOX_TOTAL_MAX = 0.55     # ... inside an interior that is not just "flat"
CHILD_CONTAINMENT = 0.80  # a box counts as nested inside another at 80%+


def _components(mask, W, H, min_px=1):
    """Flood-fill connected components of `mask`; sizes only, cheap and dumb."""
    seen = [[False] * H for _ in range(W)]
    sizes = []
    for sx in range(W):
        for sy in range(H):
            if not mask[sx][sy] or seen[sx][sy]:
                continue
            stack, n = [(sx, sy)], 0
            seen[sx][sy] = True
            while stack:
                x, y = stack.pop()
                n += 1
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < W and 0 <= ny < H and mask[nx][ny] \
                            and not seen[nx][ny]:
                        seen[nx][ny] = True
                        stack.append((nx, ny))
            if n >= min_px:
                sizes.append(n)
    return sizes


def _wall_mask(E, W, H, thresh):
    """Strong-edge pixels, dilated by one -- region_parts.cells' own
    definition of a wall, reused here because it is the one already
    calibrated (quantile 0.75, floor 30) against this exact corpus."""
    wall = [[False] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            if E[x][y] >= thresh:
                for dx in (-1, 0, 1):
                    xx = x + dx
                    if xx < 0 or xx >= W:
                        continue
                    for dy in (-1, 0, 1):
                        yy = y + dy
                        if 0 <= yy < H:
                            wall[xx][yy] = True
    return wall


def load_face(prop_dir, face):
    d = Path(prop_dir)
    pj = json.loads((d / f"parts_{face}.json").read_text())
    parts = pj.get("parts", [])
    ob = object_crop(d / f"{face}.png")
    W, H = ob.size
    if [W, H] != list(pj.get("size", [W, H])):
        print(f"  note: object_crop {W}x{H} != parts_{face}.json size "
              f"{pj.get('size')} -- measuring in the crop's own coordinates")
    return pj, parts, ob, W, H


def find_boxes(parts, W, H):
    boxes = []
    for p in parts:
        b = p.get("px")
        if not (isinstance(b, list) and len(b) == 4):
            continue
        x0, y0, x1, y1 = (int(v) for v in b)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        if x1 > x0 and y1 > y0:
            boxes.append((x0, y0, x1, y1, p.get("name", "?")))
    return boxes


def missing_bands(boxes, sil, W, H, sil_area, npmask, E, ethresh):
    """Rows no part's box touches at all, where the row band is real content.

    A row with SOME coverage is not a candidate at all -- only a strip every
    part ignores can be the marquee-shaped fault this measures. Coverage is
    checked per PART BOX, not per part-and-its-children, because the boxes
    are all this file has to go on; a mask-based version would be tighter.
    """
    covered_rows = [False] * H
    for (x0, y0, x1, y1, _n) in boxes:
        for y in range(y0, y1):
            covered_rows[y] = True
    sil_row = [sum(1 for x in range(W) if sil[x][y]) for y in range(H)]

    findings = []
    y = 0
    while y < H:
        if covered_rows[y] or sil_row[y] == 0:
            y += 1
            continue
        y0 = y
        while y < H and not covered_rows[y] and sil_row[y] > 0:
            y += 1
        y1 = y
        band_area = sum(sil_row[yy] for yy in range(y0, y1))
        frac = band_area / sil_area
        if frac < BAND_FRAC_MIN:
            continue
        art = both = 0
        for x in range(W):
            for yy in range(y0, y1):
                if not sil[x][yy]:
                    continue
                a = npmask[x][yy]
                if a:
                    art += 1
                    if E[x][yy] >= ethresh:
                        both += 1
        art_frac = art / max(1, band_area)
        both_frac = both / max(1, band_area)
        if art_frac >= BAND_ART_MIN and both_frac >= BAND_BOTH_MIN:
            findings.append({
                "rows": [y0, y1], "frac_of_silhouette": round(frac, 3),
                "artwork_frac": round(art_frac, 3),
                "busy_artwork_frac": round(both_frac, 3),
            })
    return findings


def swallowed_boxes(boxes, sil, W, H, sil_area, wall):
    """Large boxes whose interior -- minus anything already nested in them
    -- still contains more than one object-sized region."""
    findings = []
    for (x0, y0, x1, y1, name) in boxes:
        area = sum(1 for x in range(x0, x1) for y in range(y0, y1) if sil[x][y])
        frac = area / sil_area
        if frac < BOX_FRAC_MIN:
            continue

        child = [[False] * H for _ in range(W)]
        for (cx0, cy0, cx1, cy1, cname) in boxes:
            if cname == name:
                continue
            cw = min(x1, cx1) - max(x0, cx0)
            ch = min(y1, cy1) - max(y0, cy0)
            carea = max(0, cx1 - cx0) * max(0, cy1 - cy0)
            if cw > 0 and ch > 0 and carea > 0 and \
                    (cw * ch) / carea >= CHILD_CONTAINMENT:
                for x in range(max(x0, cx0), min(x1, cx1)):
                    for y in range(max(y0, cy0), min(y1, cy1)):
                        child[x][y] = True

        interior = sum(1 for x in range(x0, x1) for y in range(y0, y1)
                        if sil[x][y] and not child[x][y])
        if interior == 0:
            continue
        notwall = [[x0 <= x < x1 and y0 <= y < y1 and sil[x][y]
                    and not child[x][y] and not wall[x][y]
                    for y in range(H)] for x in range(W)]
        sub = sorted(_components(notwall, W, H, min_px=3), reverse=True)
        if not sub:
            continue
        fracs = [s / interior for s in sub]
        top = fracs[0]
        total = sum(fracs)
        rest = fracs[1:11]
        mean_rest = sum(rest) / len(rest) if rest else 0.0
        ratio = top / mean_rest if mean_rest > 0 else float("inf")
        if top >= BOX_TOP_MIN and ratio >= BOX_RATIO_MIN and total <= BOX_TOTAL_MAX:
            findings.append({
                "part": name, "frac_of_silhouette": round(frac, 3),
                "orphan_regions": len(sub),
                "largest_orphan_frac_of_interior": round(top, 3),
                "outlier_ratio": round(ratio, 1),
                "interior_notwall_frac": round(total, 3),
            })
    return findings


def _is_screen(finding):
    n = str(finding.get("part", finding.get("name", ""))).lower()
    return "screen" in n or "bezel" in n or "monitor" in n


def _hard(findings):
    """Box findings that do not name a screen -- the ones that held up."""
    return [f for f in findings if not _is_screen(f)]


def audit(prop_dir, face):
    pj, parts, ob, W, H = load_face(prop_dir, face)
    sil = silhouette(ob, erode=0)
    sil_area = sum(sum(1 for y in range(H) if sil[x][y]) for x in range(W))
    if sil_area == 0:
        return {"error": "empty silhouette"}

    E = edge_energy(ob)
    vals = sorted(E[x][y] for x in range(0, W, 2) for y in range(0, H, 2))
    ethresh = max(vals[int(0.75 * (len(vals) - 1))], 30)
    wall = _wall_mask(E, W, H, ethresh)

    cellmask = cells(ob)
    panel = panel_colour(ob, cellmask)
    npmask = not_panel(ob, panel)

    boxes = find_boxes(parts, W, H)
    covered = sum(1 for x in range(W) for y in range(H) if sil[x][y]
                  and any(x0 <= x < x1 and y0 <= y < y1
                          for (x0, y0, x1, y1, _n) in boxes))
    largest = max(((min(x1, W) - max(x0, 0)) * (min(y1, H) - max(y0, 0))
                    for (x0, y0, x1, y1, _n) in boxes), default=0)

    bands = missing_bands(boxes, sil, W, H, sil_area, npmask, E, ethresh)
    boxfindings = swallowed_boxes(boxes, sil, W, H, sil_area, wall)

    return {
        "prop": str(Path(prop_dir).name), "face": face, "size": [W, H],
        "n_parts": len(parts),
        "coverage": round(covered / sil_area, 3),
        "uncovered_frac": round(1 - covered / sil_area, 3),
        "largest_part_frac": round(largest / sil_area, 3),
        "panel_colour": list(panel),
        "missing_bands": bands,
        "swallowed_boxes": boxfindings,
        # GRADED BY CONFIDENCE, because the two signals are not worth the
        # same and one of them has a known blind spot. Inspected by eye across
        # the corpus: every MISSING BAND held up, and every SWALLOWED BOX
        # naming a door, a display window or a grille held up. A SWALLOWED BOX
        # naming a SCREEN did not -- a glare streak or the screen's own title
        # art produces the same measured signature as a hidden fitting, and
        # nothing tried separates them (v14_arcade_cabinet's "orphan region"
        # at ratio 13.7 is a diagonal reflection; v37's is the words ASTEROID
        # RAIDERS). 6 of 23 box findings name a screen or bezel.
        #
        # So a screen finding is reported as a LEAD, in the same vocabulary
        # feature_intent uses: not a fault, not a pass, but a thing no
        # measurement here can settle. Calling it UNDER_SEGMENTED would put a
        # false positive on a third of the box findings; dropping it would
        # hide the real ones. This is the "some things cannot be measured"
        # precedent applied rather than re-derived.
        "verdict": ("UNDER_SEGMENTED" if (bands or _hard(boxfindings))
                    else "LEAD" if boxfindings else "OK"),
        "leads": [b for b in boxfindings if _is_screen(b)],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = Path(args.prop_dir)
    if not (d / f"parts_{args.face}.json").exists():
        raise SystemExit(f"no parts_{args.face}.json in {d}")
    if not (d / f"{args.face}.png").exists():
        raise SystemExit(f"no {args.face}.png in {d}")

    r = audit(d, args.face)
    if args.json:
        print(json.dumps(r, indent=1))
        return

    if "error" in r:
        print(f"{d.name}: {r['error']}")
        return

    print(f"{r['prop']} ({r['face']}, {r['size'][0]}x{r['size'][1]}, "
          f"{r['n_parts']} parts)")
    print(f"  coverage            {100*r['coverage']:5.1f}% of silhouette "
          f"touched by some part")
    print(f"  largest single part {100*r['largest_part_frac']:5.1f}% of "
          f"silhouette")
    for b in r["missing_bands"]:
        print(f"  MISSING BAND  rows {b['rows'][0]}-{b['rows'][1]}  "
              f"({100*b['frac_of_silhouette']:.1f}% of silhouette, "
              f"{100*b['artwork_frac']:.0f}% not panel colour, "
              f"{100*b['busy_artwork_frac']:.0f}% not-panel-and-edge-busy) "
              f"-- no part touches these rows")
    for x in r["swallowed_boxes"]:
        print(f"  SWALLOWED BOX {x['part']!r}  ({100*x['frac_of_silhouette']:.1f}% "
              f"of silhouette)  {x['orphan_regions']} orphan region(s) inside "
              f"it, largest {100*x['largest_orphan_frac_of_interior']:.0f}% of "
              f"its own interior, {x['outlier_ratio']}x the surrounding "
              f"texture -- looks like it hides something not accounted for")
    print(f"  VERDICT: {r['verdict']}")


if __name__ == "__main__":
    main()
