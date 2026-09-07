#!/usr/bin/env python3
"""Have the image model DRAW the decomposition, then check it against the art.

    python3 tools/authoring/segment_sheet.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Every part-finding rule in this tool is a threshold, and every one of them
holds on the decomposition it was tuned against and breaks on the next sheet.
Cells fenced by edges miss a painted marquee because busy artwork is all wall.
Distance from the panel colour catches the marquee and joins everything through
the trim lines. Merge and drop rules fix one prop and swallow the coin door on
another. The same code produced a clean two-player cabinet on one arcade sheet
and duplicated screens on the next, and the difference was not the code.

The reason is that the question is being asked backwards. "Which pixels group
into a fitting" is a perceptual question, answered by rules about gradients.
But there is already a model here whose entire job is producing images, and
segmentation IS an image: the same picture with every fitting filled a flat
colour. Asking for it is one image-to-image call, and what comes back is not an
estimate to threshold -- it is a MASK, exact to the pixel, with no merge rules,
no size caps and nothing to tune.

Which would be worth nothing on its own, because image models drift: a
segmentation that has quietly moved the coin door is worse than no segmentation
at all. So none of it is believed until it is checked, and both checks are
arithmetic:

  ALIGNMENT   the map's silhouette against the elevation's own. If the model
              redrew the prop instead of tracing it, the outlines disagree and
              the whole map is rejected.
  BOUNDARIES  a region's border should land where the artwork actually has an
              edge. A boundary drawn across flat panel is invented, and a map
              whose borders mostly sit on nothing is rejected too.

That is the same division of labour as everywhere else here -- the model says
what it sees, arithmetic decides whether to believe it -- but it replaces the
one stage that was still guessing.

Regions come out as PIXEL MASKS rather than boxes, which also retires the
overlap problem: two fittings whose bounding boxes overlap no longer fight over
the shared rectangle, because neither is a rectangle.
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
from identify_parts import object_crop, edge_energy  # noqa: E402
from layer_build import silhouette  # noqa: E402

ASK = """Redraw this {asset} front elevation as a FLAT COLOUR SEGMENTATION MAP.

Keep every shape in EXACTLY the same place, at exactly the same size, with
exactly the same outline. Do not redraw, restyle, move, add or remove anything.
You are tracing, not designing.

Fill each distinct fitting with its own single FLAT SOLID COLOUR:
  - everything OUTSIDE the prop's outline: pure white (255,255,255)
  - the plain body panel of the prop itself: pure black (0,0,0)
  - each separate fitting a different saturated colour -- the screen one
    colour, the marquee another, the control deck another, each button cluster,
    each door, each vent, each label, each badge
  - two fittings of the same kind but in different places get DIFFERENT colours

Rules:
  - flat colour only. No shading, no gradients, no outlines, no highlights, no
    texture, no text, no lettering of any kind
  - every pixel is white outside, black body, or one solid fitting colour
  - absolutely no lettering. If the prop has text on it, fill the panel that
    text sits on with that panel's colour and draw no letters at all
  - a fitting that reads as one object gets ONE colour across all of it,
    including its frame and everything printed on it
  - the outline of the whole prop must match the original exactly

Output the segmentation map image only."""


def dominant_colours(im, min_frac=0.0009):
    """Quantise and count: the flat fills the model was asked for."""
    W, H = im.size
    px = im.load()
    q = Counter()
    for x in range(W):
        for y in range(H):
            r, g, b = px[x, y][:3]
            q[(r // 24, g // 24, b // 24)] += 1
    keep = [(c, n) for c, n in q.items() if n >= min_frac * W * H]
    keep.sort(key=lambda t: -t[1])
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--tries", type=int, default=2)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    ob = object_crop(d / f"{args.face}.png")
    W, H = ob.size
    src = d / f"_seg_src_{args.face}.png"
    ob.save(src)

    # DRAW IT MORE THAN ONCE AND KEEP THE BEST. An image model is not
    # deterministic: consecutive runs on the same cabinet returned 12, 17 and 35
    # regions, one of them dithered. That variance was the whole complaint about
    # the threshold rules this replaces, so it would be a poor trade to import
    # it. There are already two arithmetic scores for a map, and picking the
    # better of two draws costs one call and uses them for what they are.
    key = load_key()
    a = silhouette(ob, erode=0)
    E = edge_energy(ob)
    vals = sorted(E[x][y] for x in range(0, W, 2) for y in range(0, H, 2))
    ethresh = max(vals[int(0.75 * (len(vals) - 1))], 30)

    def score(seg):
        sp = seg.load()
        inter = union = 0
        for x in range(W):
            for y in range(H):
                m = a[x][y]
                r, g, b = sp[x, y][:3]
                n = not (r > 210 and g > 210 and b > 210)
                if m or n:
                    union += 1
                if m and n:
                    inter += 1
        iou = inter / max(1, union)
        on = off = 0
        for x in range(1, W - 1):
            for y in range(1, H - 1):
                if sp[x, y] == sp[x + 1, y] and sp[x, y] == sp[x, y + 1]:
                    continue
                near = max(E[i][j]
                           for i in range(max(0, x - 2), min(W - 1, x + 3))
                           for j in range(max(0, y - 2), min(H - 1, y + 3)))
                if near >= ethresh:
                    on += 1
                else:
                    off += 1
        return iou, on / max(1, on + off)

    best = None
    for t in range(max(1, args.tries)):
        cand = d / f"_seg_{args.face}_{t}.png"
        try:
            generate_image(ASK.format(asset=args.asset), cand, key, refs=[src])
        except Exception as e:
            print(f"  draw {t} failed ({type(e).__name__})")
            continue
        if not cand.exists():
            continue
        im2 = Image.open(cand).convert("RGB")
        if im2.size != (W, H):
            im2 = im2.resize((W, H), Image.NEAREST)
        i2, e2 = score(im2)
        print(f"  draw {t}: silhouette {100*i2:.1f}%, borders {100*e2:.1f}%")
        if best is None or (i2 + e2) > (best[0] + best[1]):
            best = (i2, e2, im2)
    if best is None:
        raise SystemExit("no segmentation image came back")
    iou, agree, seg = best
    out = d / f"_seg_{args.face}.png"
    seg.save(out)

    sp = seg.load()

    cols = dominant_colours(seg)
    print(f"segmentation: {len(cols)} flat regions")
    print(f"  silhouette agreement  {100*iou:5.1f}%   (needs 88)")
    print(f"  borders on real edges {100*agree:5.1f}%   (needs 55)")
    ok = iou >= 0.88 and agree >= 0.55
    print(f"  {'USABLE' if ok else 'REJECTED -- falling back to the measured regions'}")

    (d / f"seg_{args.face}.json").write_text(json.dumps({
        "usable": ok, "iou": round(iou, 4), "edge_agreement": round(agree, 4),
        "regions": len(cols), "image": f"_seg_{args.face}.png",
    }, indent=1))
    if not ok:
        return

    # --- the payoff: every fitting as an exact MASK --------------------------
    # A box was always an approximation of a shape, and every overlap rule in
    # this tool existed to manage the consequences: a bezel's box contains the
    # screen's, a marquee's box contains its title's, and the two then fight
    # over the rectangle they share. None of that arises here. A region is the
    # pixels the model filled with one colour, so parts can abut and interlock
    # without overlapping at all, and the background is exactly what is left.
    # CLEAN THE MAP BEFORE BELIEVING IT. The model does not always return flat
    # fills -- one generation came back dithered, and quantising dither into
    # buckets turns a solid screen into confetti, so the masks were full of
    # holes and the background kept the artwork it was supposed to lose. A
    # majority filter is the right tool: a label surrounded by one other label
    # IS that label, and nothing about a real fitting boundary is a single
    # pixel wide at this resolution.
    lab = [[None] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            r, g, b = sp[x, y][:3]
            if r > 210 and g > 210 and b > 210:
                lab[x][y] = "out"
            elif r < 46 and g < 46 and b < 46:
                lab[x][y] = "body"
            else:
                lab[x][y] = (r // 24, g // 24, b // 24)

    for _ in range(3):
        prev = [col[:] for col in lab]
        for x in range(1, W - 1):
            for y in range(1, H - 1):
                c = Counter(prev[i][j]
                            for i in range(x - 1, x + 2)
                            for j in range(y - 1, y + 2))
                lab[x][y] = c.most_common(1)[0][0]

    keyof = {(x, y): lab[x][y] for x in range(W) for y in range(H)
             if lab[x][y] not in ("out", "body")}

    regions, seen = [], set()
    for start in list(keyof):
        if start in seen:
            continue
        col = keyof[start]
        stack, cells_ = [start], []
        seen.add(start)
        while stack:
            x, y = stack.pop()
            cells_.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                q = (nx, ny)
                if q in keyof and q not in seen and keyof[q] == col:
                    seen.add(q)
                    stack.append(q)
        if len(cells_) < 0.0006 * W * H:
            continue
        xs = [c[0] for c in cells_]
        ys = [c[1] for c in cells_]
        regions.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1, cells_))
    regions.sort(key=lambda r: (r[1], r[0]))
    print(f"  {len(regions)} fittings, as masks")

    mdir = d / "masks"
    mdir.mkdir(exist_ok=True)
    boxes = []
    for i, (x0, y0, x1, y1, cells_) in enumerate(regions, 1):
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        mp = m.load()
        for (x, y) in cells_:
            mp[x - x0, y - y0] = 255
        m.save(mdir / f"{i}.png")
        boxes.append([x0, y0, x1, y1])

    # --- name them, the same way every other stage does --------------------
    from region_parts import (ASK as NAME_ASK, annotate, RESIZES, ANCHORS,
                              DEPTHS, MOTIONS)
    from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL
    shot = annotate(ob, boxes)
    tmp = d / f"_seg_named_{args.face}.png"
    shot.save(tmp)
    listing = "\n".join(f"  {i}. a region {b[2]-b[0]}x{b[3]-b[1]} px"
                         for i, b in enumerate(boxes, 1))
    content = [{"type": "text",
                "text": NAME_ASK.format(asset=args.asset, listing=listing)},
               {"type": "image_url", "image_url": {"url": data_uri(tmp)}}]
    got = None
    for retry in range(3):
        try:
            got = as_json(glm([{"role": "user", "content": content}],
                              CRITIC_MODEL, _openrouter_key(), max_tokens=20000,
                              temperature=0.1 + 0.2 * retry))
            break
        except Exception as e:
            print(f"  naming unusable ({type(e).__name__}), retry {retry+1}/3")
    by_n = {}
    for q in (got or {}).get("parts", []):
        try:
            by_n[int(q.get("n"))] = q
        except (TypeError, ValueError):
            pass

    parts, used = [], set()
    for i, b in enumerate(boxes, 1):
        q = by_n.get(i) or {}
        # A REGION THE NAMER SKIPS STILL HAS TO COME OFF THE FACE. Skipping left
        # it painted into the background, and anything left in the background
        # duplicates or smears the moment the prop grows -- the fault this whole
        # approach exists to remove. "Not worth naming" is not "not there": it
        # becomes an anonymous decal, held at its real size against its nearest
        # edge, exactly like every other detail.
        skipped = bool(q.get("skip"))
        if skipped:
            q = {"resize": "fixed", "depth": "flush", "motion": "none",
                 "anchor": "bottom" if (b[1] + b[3]) / 2 > H / 2 else "top"}
        base = ("decal" if skipped else
                str(q.get("name", "")).strip().lower().replace(" ", "_")) or f"part_{i}"
        name, k = base, 1
        while name in used:                    # button, button_2, button_3 ...
            k += 1
            name = f"{base}_{k}"
        used.add(name)
        parts.append({
            "name": name, "px": b, "mask": f"masks/{i}.png",
            "resize": q.get("resize") if q.get("resize") in RESIZES else "fixed",
            "anchor": q.get("anchor") if q.get("anchor") in ANCHORS else "center",
            "depth": q.get("depth") if q.get("depth") in DEPTHS else "proud",
            "motion": q.get("motion") if q.get("motion") in MOTIONS else "none",
        })

    (d / f"parts_{args.face}.json").write_text(json.dumps(
        {"face": args.face, "size": [W, H], "parts": parts}, indent=1))
    print(f"  {CRITIC_MODEL} named {len(parts)} of {len(boxes)} fittings")
    for q in parts:
        print(f"    {q['name']:22} {q['resize']:12} {q['anchor']:7} "
              f"{q['depth']:9} {q['motion']}")


if __name__ == "__main__":
    main()
