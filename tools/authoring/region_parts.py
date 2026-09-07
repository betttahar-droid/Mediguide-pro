#!/usr/bin/env python3
"""Find the fittings by measurement; ask the model only what they ARE.

    python3 tools/authoring/region_parts.py work/ps1 --asset "arcade cabinet"

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS REPLACES identify_parts' BOX-FINDING. That asks a vision model to
locate every part on an elevation cold, and on the arcade cabinet it answered
confidently and wrongly: both "speaker grilles" boxed onto the SCREEN, both
"joysticks" and the "control panel" onto the kick plate a hundred pixels below
the deck they name. snap() cannot rescue a box that far out -- it searches six
percent of the frame, so a twenty percent error is merely locked onto the wrong
edge, precisely and permanently. Everything downstream inherits it, and the
losslessness check reports 0.00% throughout, because a wrong box cut and pasted
back lands exactly where it came from.

verify_parts.py tried to fix it by showing the model its own boxes and asking
for corrected ones. It oscillated -- screen moved out and back, a joystick came
back nine pixels wide -- for a reason worth writing down: asking for a
corrected box is asking the model to MEASURE, which is the one thing this tool
has never let it do and the one thing it is reliably bad at. The prompt was
wrong, not the model.

SO SWAP THE TWO JOBS ROUND, the way every other stage here already does it.

  ARITHMETIC finds WHERE. A fitting is where the elevation stops being panel:
             a region of pixels that differ from the panel colour, closed up
             and taken as a connected component. That is measurement, it is
             exact, and it cannot put the grille on the screen.
  THE MODEL   says WHAT. Shown those regions outlined and numbered, it answers
             a naming question -- "region 4 is the screen" -- which is what a
             vision model is actually good at and all this tool has ever
             needed from one.

Nothing is asked for in pixels, so nothing can be wrong in pixels. S14.0 is
satisfied by construction rather than by care.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL  # noqa: E402
from identify_parts import object_crop, edge_energy, snap  # noqa: E402
from layer_build import silhouette  # noqa: E402

ASK = """This is the front elevation of a {asset}. Every region the tool
measured as "not plain panel" is outlined in magenta and numbered.

{listing}

Name each numbered region. You are not being asked where anything is -- the
outlines are measured and correct. Only say what each one IS.

For each region give:
  "n"      its number
  "name"   a short lowercase identifier for what is inside that outline, e.g.
           "coin_door", "speaker_grille", "screen", "joystick", "marquee".
           If two regions are the same kind of thing, distinguish them:
           "speaker_grille_left", "speaker_grille_right".
  "skip"   true if the outline holds nothing worth building separately -- a
           scratch, a patch of grime, a bit of trim, a shadow. Better to skip
           a region than to invent a name for it.
  "resize" how it must behave when the prop is made larger:
             "fixed"         keeps its real size and stays put (a coin door,
                             a button, a badge, a screen)
             "spanx_repeat"  runs the full width, middle REPEATS when widened
                             -- a control deck, where wider means more buttons
             "spanx_center"  runs the full width, middle stays ONE size centred
                             and the ends extend -- a marquee, where you want
                             one title and not three
             "spany_repeat" / "spany_center"  the same for the vertical axis
  "anchor" which edge it holds to: "top", "bottom", "left", "right", "center"
  "depth"  "flush" (painted on) | "proud" (a bezel, a rail, a deck, a door) |
           "deep" (a joystick, a handle, a lever) |
           "recessed" (a screen, a coin slot, a vent, a tray)
  "motion" "none" | "hinge_left" | "hinge_right" | "hinge_top" |
           "hinge_bottom" | "press" | "stick" | "slide_x" | "slide_y"
           -- name the EDGE a door turns about. Be conservative: if you are
           not sure it moves, it is "none".

OUTPUT THE JSON AND NOTHING ELSE. No reasoning, no commentary, no going
through the regions one at a time in prose -- an earlier version of this
narrated region 2 until it ran out of budget and never answered. Decide
silently and emit one object:
{{"parts": [{{"n": 1, "name": "...", "skip": false, "resize": "fixed",
              "anchor": "top", "depth": "proud", "motion": "none"}}]}}"""

RESIZES = {"fixed", "spanx_repeat", "spanx_center", "spany_repeat", "spany_center"}
ANCHORS = {"top", "bottom", "left", "right", "center"}
DEPTHS = {"flush", "proud", "deep", "recessed"}
MOTIONS = {"none", "hinge_left", "hinge_right", "hinge_top", "hinge_bottom",
           "press", "stick", "slide_x", "slide_y"}


def cells(ob, quantile=0.80, floor=40.0):
    """The elevation's flat CELLS: what is left when the strong edges are walls.

    Classifying pixels as panel-or-not was the obvious approach and it does not
    work. The modal colour inside an arcade cabinet came out (48,48,48) -- its
    dark trim, not its grey panel -- so "differs from panel" was true almost
    everywhere and the whole face came back as one region covering 97.7% of it,
    leaving only four stray sprites inside the screen.

    A fitting is not a colour, it is an area FENCED IN by its own border. So
    take the strong edges as walls, dilate them just enough to close, and let
    the connected components of what remains be the candidates. A marquee, a
    grille, a screen, a control deck and a coin door each come out as their own
    cell because each is drawn with an outline -- and so does the panel between
    them, which the model is told it may skip.
    """
    W, H = ob.size
    E = edge_energy(ob)
    inside = silhouette(ob, erode=0)
    vals = sorted(E[x][y] for x in range(0, W, 2) for y in range(0, H, 2))
    thresh = max(vals[int(quantile * (len(vals) - 1))], floor)
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
    return [[inside[x][y] and not wall[x][y] for y in range(H)] for x in range(W)]


def components(mask, W, H, min_px):
    """Connected components, as bounding boxes."""
    seen = [[False] * H for _ in range(W)]
    boxes = []
    for sx in range(W):
        for sy in range(H):
            if not mask[sx][sy] or seen[sx][sy]:
                continue
            stack = [(sx, sy)]
            seen[sx][sy] = True
            x0 = x1 = sx
            y0 = y1 = sy
            n = 0
            while stack:
                x, y = stack.pop()
                n += 1
                x0, x1 = min(x0, x), max(x1, x)
                y0, y1 = min(y0, y), max(y1, y)
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < W and 0 <= ny < H and mask[nx][ny] \
                            and not seen[nx][ny]:
                        seen[nx][ny] = True
                        stack.append((nx, ny))
            if n >= min_px:
                boxes.append([x0, y0, x1 + 1, y1 + 1, n])
    return boxes


def annotate(ob, boxes):
    im = ob.convert("RGB").copy()
    s = 1.0
    if max(im.size) < 760:
        s = 760 / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for i, b in enumerate(boxes, 1):
        x0, y0, x1, y1 = [v * s for v in b[:4]]
        dr.rectangle([x0, y0, x1, y1], outline=(255, 0, 255), width=3)
        tag = str(i)
        dr.rectangle([x0 + 1, y0 + 1, x0 + 11 + 7 * len(tag), y0 + 16],
                     fill=(255, 0, 255))
        dr.text((x0 + 5, y0 + 3), tag, fill=(255, 255, 255))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--max-parts", type=int, default=14)
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    ob = object_crop(d / f"{args.face}.png")
    W, H = ob.size

    boxes = components(cells(ob), W, H, min_px=int(0.0025 * W * H))
    # a region covering half the face is the cabinet, not a fitting on it
    boxes = [b for b in boxes
             if (b[2] - b[0]) * (b[3] - b[1]) < 0.45 * W * H
             and (b[2] - b[0]) >= 7 and (b[3] - b[1]) >= 7]
    # PARTS MUST NOT OVERLAP. Components are disjoint but their bounding boxes
    # are not -- a ring-shaped bezel's box contains the screen's, and the
    # marquee's frame box contains its title's. Cut as separate parts they both
    # carry the shared artwork, and once they are anchored to different edges a
    # widened cabinet draws it twice: the marquee came out reading
    # "TRAIL TRAIL". Merging them into one part is the honest resolution --
    # they are one fitting that happened to measure as two cells.
    def overlap(a, b):
        w = min(a[2], b[2]) - max(a[0], b[0])
        h = min(a[3], b[3]) - max(a[1], b[1])
        if w <= 0 or h <= 0:
            return 0.0
        small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
        return w * h / max(1, small)

    # A WORD IS NOT ITS LETTERS. Cells are disjoint by construction, so a
    # title splits into separate blobs and only some of them land inside the
    # part's box -- the rest stays in the background. At original size that is
    # invisible; widen the prop and the two halves drift apart, which is how a
    # marquee came out reading "ULTIMATE STRIK ... ATE KE". Cells that share a
    # row band and sit close together are one fitting, so group them first.
    def same_row(a, b):
        top, bot = max(a[1], b[1]), min(a[3], b[3])
        ov = max(0, bot - top)
        return ov >= 0.6 * min(a[3] - a[1], b[3] - b[1])

    def near_x(a, b):
        gap = max(a[0], b[0]) - min(a[2], b[2])
        return gap < 0.06 * W

    grouped = True
    while grouped:
        grouped = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if same_row(a, b) and near_x(a, b):
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]),
                                max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                    boxes.pop(j)
                    grouped = True
                    break
            if grouped:
                break

    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if overlap(boxes[i], boxes[j]) < 0.80:
                    continue
                a, b = boxes[i], boxes[j]
                ar = (a[2] - a[0]) * (a[3] - a[1])
                br = (b[2] - b[0]) * (b[3] - b[1])
                big, small = (i, j) if ar >= br else (j, i)
                # CONTAINING SOMETHING IS NOT BEING IT. Merging on containment
                # alone swallowed the coin door into the lower cabinet panel,
                # because a panel's box naturally contains every fitting on it.
                # A box several times larger than what it holds is the PANEL
                # AROUND that fitting, and the background already carries it --
                # so it is dropped, not merged. Boxes of comparable size that
                # overlap really are one fitting measured as two cells, a
                # bezel ring and the glass inside it, and those are merged.
                if max(ar, br) > 3.0 * max(1, min(ar, br)):
                    boxes.pop(big)
                else:
                    boxes[min(i, j)] = [min(a[0], b[0]), min(a[1], b[1]),
                                        max(a[2], b[2]), max(a[3], b[3]),
                                        a[4] + b[4]]
                    boxes.pop(max(i, j))
                merged = True
                break
            if merged:
                break

    boxes.sort(key=lambda b: -b[4])
    boxes = boxes[:args.max_parts]
    boxes.sort(key=lambda b: (b[1], b[0]))          # reading order
    if not boxes:
        raise SystemExit("no regions found -- the elevation reads as all panel")

    shot = annotate(ob, boxes)
    tmp = d / f"_regions_{args.face}.png"
    shot.save(tmp)
    listing = "\n".join(
        f"  {i}. a region {b[2]-b[0]}x{b[3]-b[1]} px" for i, b in enumerate(boxes, 1))
    content = [{"type": "text",
                "text": ASK.format(asset=args.asset, listing=listing)},
               {"type": "image_url", "image_url": {"url": data_uri(tmp)}}]

    key = _openrouter_key()
    got = None
    for retry in range(3):
        try:
            got = as_json(glm([{"role": "user", "content": content}],
                              CRITIC_MODEL, key, max_tokens=20000,
                              temperature=0.1 + 0.2 * retry))
            break
        except Exception as e:
            print(f"  reply unusable ({type(e).__name__}), retry {retry + 1}/3")
    if got is None:
        raise SystemExit("no usable naming in three attempts")

    by_n = {}
    for q in got.get("parts", []):
        try:
            by_n[int(q.get("n"))] = q
        except (TypeError, ValueError):
            pass

    E = edge_energy(ob)
    out, used = [], set()
    for i, b in enumerate(boxes, 1):
        q = by_n.get(i)
        if not q or q.get("skip"):
            continue
        name = str(q.get("name", "")).strip().lower().replace(" ", "_")
        if not name:
            continue
        while name in used:                 # two regions given one name
            name += "_2"
        used.add(name)
        # the region is already exact; snapping only tightens it to the border
        px = snap([b[0] / W, b[1] / H, b[2] / W, b[3] / H], E, W, H, slack=0.02)
        out.append({
            "name": name, "px": px,
            "resize": q.get("resize") if q.get("resize") in RESIZES else "fixed",
            "anchor": q.get("anchor") if q.get("anchor") in ANCHORS else "center",
            "depth": q.get("depth") if q.get("depth") in DEPTHS else "proud",
            "motion": q.get("motion") if q.get("motion") in MOTIONS else "none",
        })

    # PARTS ON THE SAME ROW MUST HOLD TO THE SAME EDGE. Widening the prop moves
    # a left-anchored part left and a right-anchored one right, so a marquee
    # that measured as two cells -- title and artwork -- was pulled apart into
    # "GALACTIC RA ... AIDERS" with panel between the halves. Grouping them into
    # one part instead needed a merge gap so wide it swallowed the whole lower
    # cabinet, which starved the background of panel until the tile it grows
    # with came out the colour of the cabinet's blue trim. Sharing the anchor
    # costs nothing and keeps their spacing exactly: each holds the same
    # distance from the same edge, so they travel together.
    for i, o in enumerate(out):
        band = [q for q in out
                if min(q["px"][3], o["px"][3]) - max(q["px"][1], o["px"][1])
                >= 0.6 * min(q["px"][3] - q["px"][1], o["px"][3] - o["px"][1])]
        if len(band) > 1:
            lead = min(band, key=lambda q: q["px"][0])["anchor"]
            if lead in ("left", "right", "center") and o["anchor"] != lead:
                o["anchor"] = lead

    (d / f"parts_{args.face}.json").write_text(
        json.dumps({"face": args.face, "size": [W, H], "parts": out}, indent=1))
    print(f"measured {len(boxes)} regions, {CRITIC_MODEL} named {len(out)}")
    for o in out:
        print(f"  {o['name']:22} {o['resize']:12} {o['anchor']:7} "
              f"{o['depth']:9} {o['motion']:12} px {o['px']}")


if __name__ == "__main__":
    main()
