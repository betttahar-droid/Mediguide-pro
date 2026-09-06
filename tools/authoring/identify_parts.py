#!/usr/bin/env python3
"""Ask the vision model WHAT the parts are; measure WHERE they are.

    python3 tools/authoring/identify_parts.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS REPLACES THE SCAN IN extract_fittings.py. That one segmented the
elevation with 1D row and column differences, and the result was not parts at
all: four of its nine "fittings" were FULL-WIDTH BANDS, which is the image
sliced into strips rather than decomposed into things. Reassembling strips at
a new size then mapped the coin door onto the control panel, which is what
every one of eight judges independently reported.

A cabinet front is a 2D arrangement of named objects -- marquee, speaker
grille, screen, control deck, coin door -- and naming objects is what a vision
model is for. glm-5.3-flash costs $0.0002 a call and, benchmarked against
seven others on exactly this kind of question, was the only one to diagnose a
cause rather than list symptoms.

BUT IT IS NOT ALLOWED TO MEASURE. Models are unreliable at precise boxes and
S14.0 forbids reading proportions off pixels regardless. So the split is the
same one that has worked all session:

    the model NAMES a part, says roughly where it is, and says how it should
    behave when the prop resizes
    arithmetic SNAPS the box to the real edges near that estimate

A rough box is enough to seed a snap, and the snap is exact.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL  # noqa: E402

ASK = """This is the FRONT ELEVATION of a game prop, drawn dead on.

List every distinct PART fixed to its front face -- the things a modeller
would build separately, such as a marquee, a speaker grille, a screen, a
control panel, a coin door, a trim rail. Ignore the plain painted panel they
sit on; that is the background, not a part.

For each part give:
  "name"   a short lowercase identifier, e.g. "coin_door"
  "box"    [x0, y0, x1, y1] as fractions of the image, 0,0 at the TOP-LEFT.
           Approximate is fine, it will be refined by measurement.
  "resize" how it must behave when the prop is made larger:
             "fixed"         keeps its real size and stays put (a coin door,
                             a button, a badge, a screen)
             "spanx_repeat"  runs the full width and its middle REPEATS when
                             widened -- right for a control deck, where a
                             wider cabinet means more button clusters
             "spanx_center"  runs the full width but its middle must stay ONE
                             size, centred, with the ends extending -- right
                             for a marquee, where you want one title and not
                             three copies of it
             "spany_repeat" / "spany_center"  the same for the vertical axis
                             (a side rail repeats; a badge on a post centres)
  "anchor" which edge it holds to: "top", "bottom", "left", "right", or
           "center" if it belongs to the middle of the face

Reply with JSON only:
{"parts": [{"name": "...", "box": [0,0,0,0], "resize": "...", "anchor": "..."}]}"""


def object_crop(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    xs = [x for x in range(w) if any(not is_bg(px[x, y]) for y in range(0, h, 2))]
    ys = [y for y in range(h) if any(not is_bg(px[x, y]) for x in range(0, w, 2))]
    return im.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1))


def edge_energy(ob):
    """Per-pixel gradient magnitude, cheap. A part's border is where this
    spikes, which is what a rough box gets snapped to."""
    W, H = ob.size
    px = ob.load()
    E = [[0] * H for _ in range(W)]
    for x in range(W - 1):
        for y in range(H - 1):
            a, b, c = px[x, y], px[x + 1, y], px[x, y + 1]
            E[x][y] = (sum(abs(p - q) for p, q in zip(a, b))
                       + sum(abs(p - q) for p, q in zip(a, c)))
    return E


def snap(box, E, W, H, slack=0.06):
    """Pull each side of a rough box to the strongest edge line near it.

    The model is being asked what a part IS, not where its pixels are, so its
    box arrives a few percent out. Each side is searched within `slack` of the
    frame for the row or column carrying the most edge energy, which is the
    part's real border.
    """
    x0, y0, x1, y1 = box
    px0, py0 = int(x0 * W), int(y0 * H)
    px1, py1 = int(x1 * W), int(y1 * H)
    sx, sy = int(slack * W), int(slack * H)

    def best_col(lo, hi, ylo, yhi):
        lo, hi = max(0, lo), min(W - 1, hi)
        if hi <= lo:
            return lo
        return max(range(lo, hi + 1),
                   key=lambda x: sum(E[x][y] for y in range(max(0, ylo),
                                                            min(H - 1, yhi))))

    def best_row(lo, hi, xlo, xhi):
        lo, hi = max(0, lo), min(H - 1, hi)
        if hi <= lo:
            return lo
        return max(range(lo, hi + 1),
                   key=lambda y: sum(E[x][y] for x in range(max(0, xlo),
                                                            min(W - 1, xhi))))

    nx0 = best_col(px0 - sx, px0 + sx, py0, py1)
    nx1 = best_col(px1 - sx, px1 + sx, py0, py1)
    ny0 = best_row(py0 - sy, py0 + sy, px0, px1)
    ny1 = best_row(py1 - sy, py1 + sy, px0, px1)
    if nx1 <= nx0:
        nx0, nx1 = px0, px1
    if ny1 <= ny0:
        ny0, ny1 = py0, py1
    return [nx0, ny0, nx1 + 1, ny1 + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    src = d / f"{args.face}.png"
    ob = object_crop(src)
    tmp = d / f"_{args.face}_obj.png"
    ob.save(tmp)

    content = [{"type": "text", "text": ASK},
               {"type": "image_url", "image_url": {"url": data_uri(tmp)}}]
    reply = glm([{"role": "user", "content": content}], CRITIC_MODEL,
                _openrouter_key(), max_tokens=12000)
    parts = as_json(reply).get("parts", [])
    print(f"{CRITIC_MODEL} named {len(parts)} parts on the {args.face}")

    W, H = ob.size
    E = edge_energy(ob)
    out = []
    for p in parts:
        b = p.get("box")
        if not (isinstance(b, list) and len(b) == 4):
            print(f"  skip {p.get('name')}: no box")
            continue
        b = [max(0.0, min(1.0, float(v))) for v in b]
        if b[2] <= b[0] or b[3] <= b[1]:
            print(f"  skip {p.get('name')}: empty box {b}")
            continue
        sb = snap(b, E, W, H)
        moved = max(abs(sb[0] - b[0] * W), abs(sb[1] - b[1] * H),
                    abs(sb[2] - b[2] * W), abs(sb[3] - b[3] * H))
        out.append({"name": p.get("name", "part"), "px": sb,
                    "resize": p.get("resize", "fixed"),
                    "anchor": p.get("anchor", "center")})
        print(f"  {p.get('name','?'):16} {p.get('resize','?'):6} "
              f"{p.get('anchor','?'):7} px {sb}  (snapped {moved:.0f}px)")

    man = {"face": args.face, "size": [W, H], "parts": out}
    dst = Path(args.out or d / f"parts_{args.face}.json")
    dst.write_text(json.dumps(man, indent=1))
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
