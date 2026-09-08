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

# The three the judge sees, in the order it sees them. Anchored on what
# follows the height, because "w-1-h-1-" is also the prefix of "w-1-h-1-5-":
# matched loosely, the first column showed the TALLER render and the sheet
# quietly compared a prop against itself.
ORDER = [("as drawn", re.compile(r"w-1-h-1-[a-z]")),
         ("2x wider", re.compile(r"w-2[-0]*-h-1-[a-z]")),
         ("taller", re.compile(r"w-1-h-1-[0-9]"))]


def latest_round(d):
    rs = sorted([p for p in d.glob("r[0-9]*") if p.is_dir()],
                key=lambda p: int(p.name[1:] or 0))
    return rs[-1] if rs else None


def shots_for(d):
    """the three judged renders of one prop, newest round that has them"""
    for r in reversed(sorted([p for p in d.glob("r[0-9]*") if p.is_dir()],
                             key=lambda p: int(p.name[1:] or 0))):
        found = []
        for label, pat in ORDER:
            hit = next((p for p in sorted(r.glob("*.png")) if pat.search(p.name)),
                       None)
            found.append((label, hit))
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
    for i, (label, _) in enumerate(ORDER):
        dr.text((190 + i * (C + pad) + 4, 6), label, fill=(210, 210, 210))
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
