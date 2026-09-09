#!/usr/bin/env python3
"""Score a part list against the reference elevation WITHOUT rendering it.

    python3 tools/authoring/project_score.py parts.json reference_front.png

Authoring tool. NOT a build, CI or runtime dependency.

WHY NOT match_score.py. That one compares a RENDER against the reference, and
the renderer applies a toon ramp while the reference is a flat drawing. On the
first reference-guided cabinet the render's most common colour was #768daa at
57.5% where the reference has 5.5% -- the lit face of a black body. Most of
the "disagreement" it reported was the shader doing its job, and style.js has
no unlit mode to turn off (useRawColours only disables colour management).

So do not render. Project the part list onto the front plane directly: for
each column of the grid, walk y from the front and take the first solid box.
That is exactly what the front elevation shows, in the part list's own flat
colours, with no lighting and no camera. The comparison is then like for like
and it is exact.

It is also about a thousand times faster than a browser screenshot, which is
what lets it sit inside a search loop rather than at the end of one.

PER-REGION REPORT. The overall number says how well; the region rows say
WHERE. Each measured reference rectangle is scored on its own, so a marquee
that never got built, or got built in the wrong colour, is named -- and that
list is what goes back to the model, instead of a paragraph of prose.
"""
import argparse
import json
from collections import Counter

from PIL import Image

from reference_regions import object_box, regions


def project(parts, grid):
    """Front elevation of a part list: nearest box along y wins. -> {(x,z): hex}"""
    W, D, H = grid
    best = {}
    for b in parts:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        for x in range(max(0, x0), min(W, x1)):
            for z in range(max(0, z0), min(H, z1)):
                cur = best.get((x, z))
                if cur is None or y0 < cur[0]:
                    best[(x, z)] = (y0, b["colour"])
    return {k: v[1] for k, v in best.items()}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def nearest(c, pal):
    return min(pal, key=lambda p: sum((a - b) ** 2 for a, b in zip(c, rgb(p))))


def reference_grid(ref_path, W, H, pal):
    """The reference front, cropped to its object and resampled to the grid,
    with every pixel snapped to the part list's own palette."""
    im = Image.open(ref_path).convert("RGB")
    box, bg = object_box(im)
    ob = im.crop(box).resize((W, H), Image.NEAREST)
    px = ob.load()
    out = {}
    for x in range(W):
        for y in range(H):
            c = px[x, y]
            if sum(abs(a - b) for a, b in zip(c, bg)) < 40:
                continue
            out[(x, H - 1 - y)] = nearest(c, pal)      # image y down -> z up
    return out


def score(parts_path, ref_path):
    d = json.load(open(parts_path))
    grid = d["grid"]
    W, D, H = grid
    parts = d["boxes"]
    pal = sorted({b["colour"] for b in parts})
    proj = project(parts, grid)
    ref = reference_grid(ref_path, W, H, pal)

    inter = len(set(proj) & set(ref))
    union = len(set(proj) | set(ref))
    agree = sum(1 for k in set(proj) & set(ref) if proj[k] == ref[k])
    return {"grid": grid, "pal": pal, "proj": proj, "ref": ref,
            "iou": inter / max(1, union), "agree": agree / max(1, inter),
            "overall": agree / max(1, union), "inter": inter, "union": union}


def region_report(ref_path, s, min_fill=0.80):
    """Per measured reference rectangle: how much of it did the projection get
    right, and if not, what did it put there instead."""
    W, D, H = s["grid"]
    rs, _, _ = regions(ref_path)
    rs = [r for r in rs if r["fill"] >= min_fill]
    rows = []
    for r in rs:
        x0, x1 = int(r["x"][0] * W), max(int(r["x"][0] * W) + 1, int(r["x"][1] * W))
        z0, z1 = int(r["z"][0] * H), max(int(r["z"][0] * H) + 1, int(r["z"][1] * H))
        want = nearest(rgb(r["colour"]), s["pal"])
        hit = tot = 0
        got = Counter()
        for x in range(x0, min(W, x1)):
            for z in range(z0, min(H, z1)):
                if (x, z) not in s["ref"]:
                    continue
                tot += 1
                c = s["proj"].get((x, z))
                got[c or "empty"] += 1
                if c == want:
                    hit += 1
        rows.append({"colour": r["colour"], "want": want, "area": r["area"],
                     "x": [x0, x1], "z": [z0, z1],
                     "score": hit / max(1, tot),
                     "instead": got.most_common(1)[0][0] if got else "empty"})
    rows.sort(key=lambda q: (q["score"], -q["area"]))
    return rows


def cell_report(s, cols=8, rows=16):
    """A DENSE error map over the whole front plane.

    region_report only scores the rectangles the reference decomposed into,
    and those cover about half the object -- so it reported "everything above
    95%" while colour agreement sat at 61%. Everything it cannot see (outline
    bands, the gaps between rectangles, anything not rectangular) was invisible
    to the loop and therefore never got fixed.

    This tiles the whole plane instead. Each cell reports what the reference
    mostly is there, what the projection mostly is, and how much of the cell
    agrees -- so no part of the object can hide from the feedback.
    """
    W, D, H = s["grid"]
    out = []
    for cx in range(cols):
        for cz in range(rows):
            x0, x1 = cx * W // cols, (cx + 1) * W // cols
            z0, z1 = cz * H // rows, (cz + 1) * H // rows
            want = Counter()
            got = Counter()
            hit = tot = 0
            for x in range(x0, x1):
                for z in range(z0, z1):
                    r = s["ref"].get((x, z))
                    p = s["proj"].get((x, z))
                    if r is None and p is None:
                        continue
                    tot += 1
                    want[r or "empty"] += 1
                    got[p or "empty"] += 1
                    if r == p:
                        hit += 1
            if not tot:
                continue
            out.append({"x": [x0, x1], "z": [z0, z1], "px": tot,
                        "score": hit / tot,
                        "want": want.most_common(1)[0][0],
                        "got": got.most_common(1)[0][0]})
    out.sort(key=lambda c: (c["score"], -c["px"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts")
    ap.add_argument("reference")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    s = score(args.parts, args.reference)
    print(f"grid {s['grid']}   palette {len(s['pal'])}")
    print(f"  silhouette IoU  {100*s['iou']:6.2f}%")
    print(f"  colour agree    {100*s['agree']:6.2f}%  (within the overlap)")
    print(f"  OVERALL MATCH   {100*s['overall']:6.2f}%  (agree / union)")
    rows = region_report(args.reference, s)
    print(f"\n  worst regions ({len(rows)} measured):")
    print(f"    {'score':>6}  {'area':>6}  {'want':9} {'got':9}  x        z")
    for r in rows[:14]:
        print(f"    {100*r['score']:5.1f}%  {r['area']:6.3f}  {r['want']:9} "
              f"{str(r['instead']):9}  {r['x'][0]:2}..{r['x'][1]:<3} {r['z'][0]:2}..{r['z'][1]:<3}")
    if args.json:
        json.dump({"overall": s["overall"], "iou": s["iou"], "agree": s["agree"],
                   "regions": rows}, open(args.json, "w"), indent=1)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
