#!/usr/bin/env python3
"""Solve the leftover front detail exactly, instead of asking for it again.

    python3 tools/authoring/front_plate.py parts.json reference_front.png \
        --out parts_plated.json

Authoring tool. NOT a build, CI or runtime dependency.

WHY. refine_parts.py climbs from 51% to 63% and then flattens: the model is
good at structure -- a body, a plinth, a bezel, a marquee, each a named part
with a sensible depth -- and bad at the last few voxels of a two-pixel trim
line. Asking it for those again costs a round and returns the same answer.

But the target is fully known. We have the reference front, measured, and we
can project any part list onto the same plane, so the residual -- every cell
where the projection has the wrong colour -- is computable exactly. And the
residual is a set of coloured pixels on a grid, which is a rectangle-covering
problem, not a judgement.

So cover it: for each colour, take the cells that should be that colour and
are not, and repeatedly cut out the largest all-true rectangle (the standard
histogram scan) until the remainder is smaller than --min-area. Each rectangle
becomes a shallow box at the front face.

This is the same division of labour the rest of the pipeline uses -- the model
supplies structure and naming, arithmetic supplies the numbers -- applied to
the one place the model demonstrably plateaus. The parts it adds are decals in
everything but name, which is what a pixel-art front elevation mostly is.

DEPTH. Plates sit in y 0..--depth, so they read as surface detail rather than
changing the silhouette from any other angle. They cannot fix a body that is
the wrong shape; if the silhouette is wrong, fix that first.
"""
import argparse
import json

from project_score import project, reference_grid, rgb, nearest


def largest_rect(mask, W, H):
    """Largest all-true axis-aligned rectangle in a set of (x,z) cells.

    Histogram scan: for each row, the run of consecutive true cells below each
    column, then the largest rectangle in that histogram.
    """
    best = (0, None)
    heights = [0] * W
    for z in range(H):
        for x in range(W):
            heights[x] = heights[x] + 1 if (x, z) in mask else 0
        stack = []
        for x in range(W + 1):
            cur = heights[x] if x < W else 0
            start = x
            while stack and stack[-1][1] >= cur:
                s, h = stack.pop()
                area = h * (x - s)
                if area > best[0]:
                    best = (area, (s, z - h + 1, x, z + 1))
                start = s
            stack.append((start, cur))
    return best


def trim(parts, ref, W, H):
    """Shrink boxes that project OUTSIDE the reference silhouette.

    Plates can only add. Once colour agreement reaches 100% the whole
    remaining loss is silhouette, and most of it is the model overhanging the
    reference -- material no plate can remove. For each box, take the cells of
    its footprint that lie inside the silhouette, cut the largest rectangle out
    of that, and resize the box to it. A box entirely outside is dropped.

    Only x and z change; depth is untouched, so a part keeps its place in the
    front-to-back order and its name.
    """
    out, dropped, shrunk = [], 0, 0
    for b in parts:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        foot = {(x, z) for x in range(max(0, x0), min(W, x1))
                for z in range(max(0, z0), min(H, z1))}
        if not foot:
            dropped += 1
            continue
        inside = {c for c in foot if c in ref}
        if len(inside) == len(foot):
            out.append(b)
            continue
        if not inside:
            dropped += 1
            continue
        area, box = largest_rect(inside, W, H)
        if not box or area < 1:
            dropped += 1
            continue
        nx0, nz0, nx1, nz1 = box
        nb = dict(b)
        nb["min"] = [nx0, y0, nz0]
        nb["max"] = [nx1, y1, nz1]
        out.append(nb)
        shrunk += 1
    return out, shrunk, dropped


def plate(parts_path, ref_path, depth=2, min_area=4, max_plates=120,
          extra_palette=()):
    d = json.load(open(parts_path))
    grid = d["grid"]
    W, D, H = grid
    parts = list(d["boxes"])
    # The parts' own palette loses whatever the model never used. Saturated
    # accents are exactly what an area filter drops and exactly what carries an
    # object's identity, so they are added explicitly.
    pal = sorted({b["colour"] for b in parts} | set(extra_palette))
    ref = reference_grid(ref_path, W, H, pal)

    # MAKE ROOM AT THE FRONT. project() resolves a column by smallest y_min
    # with a strict <, so a plate laid at y=0 ties with any part that already
    # starts at y=0 and loses -- which is why plating saturated at 69.53%
    # whether it added forty plates or seven hundred. Push the model back by
    # the plate depth first, and the plates are genuinely in front.
    if any(b["min"][1] < depth for b in parts):
        room = D - max(b["max"][1] for b in parts)
        shift = min(depth, max(0, room))
        for b in parts:
            b["min"] = [b["min"][0], b["min"][1] + shift, b["min"][2]]
            b["max"] = [b["max"][0], min(D, b["max"][1] + shift), b["max"][2]]

    # trim overhang BEFORE plating, so plates fill against a correct silhouette
    parts, shrunk, dropped = trim(parts, ref, W, H)
    if shrunk or dropped:
        print(f"  trim: {shrunk} boxes shrunk, {dropped} dropped")

    added = 0
    for _ in range(max_plates):
        proj = project(parts, grid)
        # residual, grouped by the colour it should be
        byc = {}
        for k, want in ref.items():
            if proj.get(k) != want:
                byc.setdefault(want, set()).add(k)
        if not byc:
            break
        pick = None
        for colour, cells in byc.items():
            area, box = largest_rect(cells, W, H)
            if area >= min_area and (pick is None or area > pick[0]):
                pick = (area, box, colour)
        if pick is None:
            break
        area, (x0, z0, x1, z1), colour = pick
        parts.append({"name": f"plate {added}", "colour": colour,
                      "min": [x0, 0, z0], "max": [x1, depth, z1],
                      "palette": colour})
        added += 1
    return {"grid": grid, "boxes": parts}, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts")
    ap.add_argument("reference")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--min-area", type=int, default=4)
    ap.add_argument("--max-plates", type=int, default=120)
    ap.add_argument("--accents", action="store_true",
                    help="rescue small saturated colours from the reference")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    extra = ()
    if args.accents:
        from reference_regions import accents
        extra = accents(args.reference)
        print(f"  accents rescued: {extra}")
    out, added = plate(args.parts, args.reference, args.depth,
                       args.min_area, args.max_plates, extra)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"added {added} plates -> {len(out['boxes'])} parts, wrote {args.out}")


if __name__ == "__main__":
    main()
