#!/usr/bin/env python3
"""How closely does a render match the reference elevation? A number, not a view.

    python3 tools/authoring/match_score.py reference_front.png render_front.png

Authoring tool. NOT a build, CI or runtime dependency.

WHY. The authoring loop had a vision model saying "this looks wrong", which is
useful for naming a fault and useless for knowing whether a change helped.
compare.py already scores silhouettes, but a prop can have the right outline
and the wrong colours everywhere inside it -- the first authored cabinet was
brown and teal against a black and magenta reference and would have scored
well on silhouette alone.

Two numbers, both against the object's own bounding box so framing and image
size drop out:

  SILHOUETTE IoU   do the outlines agree
  COLOUR AGREE     of the pixels both agree are solid, the share where the
                   render's colour maps to the SAME reference colour as the
                   reference's does. Both sides are snapped to the reference's
                   own palette first, so "near enough black" counts as black
                   and a lighting ramp does not read as a miss.

Per-colour rows show WHERE the loss is: a marquee that never got built shows
up as a colour present in the reference and absent from the render.
"""
import argparse
from collections import Counter

from PIL import Image


def crop_to_object(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    xs = [x for x in range(w) if any(not is_bg(px[x, y]) for y in range(0, h, 2))]
    ys = [y for y in range(h) if any(not is_bg(px[x, y]) for x in range(0, w, 2))]
    if not xs:
        raise SystemExit(f"{path}: no object")
    return im.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1)), bg


def palette_of(im, n):
    q = im.quantize(colors=n, method=Image.MEDIANCUT).convert("RGB")
    counts = Counter(q.load()[x, y] for x in range(q.width) for y in range(q.height))
    return [c for c, _ in counts.most_common(n)]


def nearest(c, pal):
    return min(range(len(pal)), key=lambda i: sum((a - b) ** 2 for a, b in zip(c, pal[i])))


def score(ref_path, render_path, colours=6):
    ref, ref_bg = crop_to_object(ref_path)
    ren, ren_bg = crop_to_object(render_path)
    ren = ren.resize(ref.size, Image.NEAREST)
    pal = palette_of(ref, colours)
    rp, np_ = ref.load(), ren.load()
    w, h = ref.size

    def ref_bgq(c):
        return sum(abs(a - b) for a, b in zip(c, ref_bg)) < 40

    def ren_bgq(c):
        return sum(abs(a - b) for a, b in zip(c, ren_bg)) < 40

    inter = union = agree = 0
    have = Counter()
    want = Counter()
    for x in range(w):
        for y in range(h):
            a, b = rp[x, y], np_[x, y]
            sa, sb = not ref_bgq(a), not ren_bgq(b)
            if sa or sb:
                union += 1
            if sa:
                want[nearest(a, pal)] += 1
            if sa and sb:
                inter += 1
                ia, ib = nearest(a, pal), nearest(b, pal)
                have[ib] += 1
                if ia == ib:
                    agree += 1
    return {"iou": inter / max(1, union), "agree": agree / max(1, inter),
            "pal": pal, "want": want, "have": have, "px": inter}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("render")
    ap.add_argument("--colours", type=int, default=6)
    args = ap.parse_args()
    s = score(args.reference, args.render, args.colours)
    print(f"silhouette IoU  {100*s['iou']:6.2f}%")
    print(f"colour agree    {100*s['agree']:6.2f}%   (of {s['px']} shared pixels)")
    print(f"\n  {'colour':9} {'reference':>10} {'render':>10}")
    tot = max(1, sum(s["want"].values()))
    for i, c in enumerate(s["pal"]):
        print(f"  #{c[0]:02x}{c[1]:02x}{c[2]:02x}  "
              f"{100*s['want'].get(i,0)/tot:9.1f}% {100*s['have'].get(i,0)/tot:9.1f}%")


if __name__ == "__main__":
    main()
