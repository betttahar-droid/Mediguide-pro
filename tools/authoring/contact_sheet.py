#!/usr/bin/env python3
"""One picture of every prop at every size it is judged at.

    python3 tools/authoring/contact_sheet.py tools/img2threejs-work/v44_* \
        --out /tmp/sheet.png

Authoring tool. NOT a build, CI or runtime dependency.

WHY. The loop judges each prop on three renders -- as drawn, twice as wide,
half again as tall -- and writes them into the round's folder. Looking at a
batch means opening twelve files in turn and holding them in your head, which
is how a fault that is obvious across props gets missed: the marquee smearing
on the widened cabinet was also on the widened jukebox, and it took two
separate sessions to notice because the two were never on the screen together.

A row per prop and a column per size makes "which props does this happen to"
a glance rather than a memory exercise. Nothing here judges anything; it only
puts the pictures where they can be compared.
"""
import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw

# THE SCALES ARE READ, NOT MATCHED. Patterns went wrong twice: "w-1-h-1-" is
# also the prefix of "w-1-h-1-5-", so the as-drawn column showed the TALLER
# render and the sheet quietly compared a prop against itself; and a pattern
# for "w-2" misses a jukebox, whose widest sensible size is 1.6, so its wider
# column came up empty and looked like a failed render. Every prop has its own
# limits -- that is the whole point of scale_rules -- so the filename's numbers
# are parsed and the three are told apart by value.
ORDER = ["as drawn", "wider", "taller"]
SCALE = re.compile(r"-w-(\d+(?:-\d+)?)-h-(\d+(?:-\d+)?)-")


def scales(name):
    m = SCALE.search(name)
    if not m:
        return None
    return tuple(float(g.replace("-", ".")) for g in m.groups())


def latest_round(d):
    rs = sorted([p for p in d.glob("r[0-9]*") if p.is_dir()],
                key=lambda p: int(p.name[1:] or 0))
    return rs[-1] if rs else None


def shots_for(d):
    """the three judged renders of one prop, newest round that has them"""
    for r in reversed(sorted([p for p in d.glob("r[0-9]*") if p.is_dir()],
                             key=lambda p: int(p.name[1:] or 0))):
        found = [(lbl, None) for lbl in ORDER]
        for p in sorted(r.glob("*.png")):
            sc = scales(p.name)
            if sc is None:
                continue
            w, h = sc
            i = 0 if (w == 1 and h == 1) else 1 if w > 1 else 2 if h > 1 else None
            if i is not None and found[i][1] is None:
                found[i] = (ORDER[i] + (f"  x{w:g}" if i == 1 else
                                        f"  x{h:g}" if i == 2 else ""), p)
        if any(h for _, h in found):
            return r.name, found
    return None, [(lbl, None) for lbl, _ in ORDER]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", default="contact_sheet.png")
    ap.add_argument("--cell", type=int, default=380)
    args = ap.parse_args()

    rows = []
    for s in args.dirs:
        d = Path(s)
        if not d.is_dir():
            continue
        rnd, shots = shots_for(d)
        rows.append((d.name, rnd, shots))
    if not rows:
        raise SystemExit("no prop folders with rendered rounds")

    C = args.cell
    pad, head = 8, 22
    W = 190 + len(ORDER) * (C + pad)
    H = head + len(rows) * (C + pad)
    out = Image.new("RGB", (W, H), (26, 26, 30))
    dr = ImageDraw.Draw(out)
    for i, lbl in enumerate(ORDER):
        head_lbl = next((f[0] for r in rows for f in r[2]
                         if f[1] is not None and f[0].startswith(lbl)), lbl)
        dr.text((190 + i * (C + pad) + 4, 6), head_lbl, fill=(210, 210, 210))
    for j, (name, rnd, shots) in enumerate(rows):
        y = head + j * (C + pad)
        dr.text((6, y + C // 2), f"{name}\n{rnd or 'no rounds'}",
                fill=(210, 210, 210))
        for i, (_, p) in enumerate(shots):
            x = 190 + i * (C + pad)
            if p is None:
                dr.rectangle([x, y, x + C, y + C], outline=(80, 60, 60))
                dr.text((x + 8, y + 8), "missing", fill=(150, 110, 110))
                continue
            im = Image.open(p).convert("RGB")
            im.thumbnail((C, C))
            out.paste(im, (x + (C - im.width) // 2, y + (C - im.height) // 2))
    out.save(args.out)
    print(f"{len(rows)} props x {len(ORDER)} sizes -> {args.out}")


if __name__ == "__main__":
    main()
