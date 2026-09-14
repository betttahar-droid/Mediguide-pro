#!/usr/bin/env python3
"""One drawn region belongs to ONE part. Cut it out of every larger one.

    python3 tools/authoring/overlap_cut.py work/ps1 --apply
    python3 tools/authoring/overlap_cut.py --sweep

Authoring tool. NOT a build, CI or runtime dependency.

WHY. A 1.7x jukebox rendered its song list THREE TIMES, stacked up the cabinet
with wood between the copies. Nothing repeated it: `grow_bands` was empty, gOfT
was the identity, and no part carried a count. `raycast.mjs` named the three
copies in one call and the answer was three different meshes --

    top     arch_lights_mesh
    middle  title_strip_mesh
    bottom  speaker_grille_mesh

-- because the three boxes OVERLAP in the drawing. `arch_lights` is rows 4..205
and `title_strip` is 188..273, so the arch's texture carries the list's top
seventeen rows; `speaker_grille` is 225..564, so the grille's texture carries
its bottom forty-eight. layer_build cuts each part straight out of the
elevation at its own box, so every pixel in an overlap is cut into BOTH parts.

AT 1x THIS IS INVISIBLE, which is why it survived so long. The copies land
exactly on top of each other and you see one list. They come apart the moment
anything moves: these three all hold their drawn size, two anchor to the top
and one to the bottom, so a taller prop slides them apart and each takes its
own slice of the shared artwork with it. A door that opens does the same thing
sideways.

Swept across the corpus: 73 of 96 props have at least one pair of partly
overlapping boxes. It is not a jukebox problem.

THIS IS THE RULE layer_build ALREADY APPLIES ONE LEVEL UP. The background is
not allowed to keep a copy of a fitting -- `fill_from_panel` paints every part
out of it, and the note there records exactly this failure at that level ("the
background kept a thin dark tracery of the door... the moment the background
repeats, that tracery repeats with it"). Parts were simply never held to the
same rule with respect to each other.

WHO KEEPS THE PIXELS: THE SMALLEST PART THAT COVERS THEM. That is the same
ordering `hostOf` and segment_audit's swallowed-box test already use -- the
smaller box is the more specific feature, and the larger is its host or its
panel. A song list is a title strip; it is not an arch and it is not a grille.

WHAT IS CUT IS THE MASK, NOT THE BOX. Every part PNG carries its own alpha, so
the region erased from the host is the rider's actual shape.

AND IT IS NOT DILATED, which fill_from_panel's note argues for and which is
wrong here. There, dilating closes a hairline of fitting left in a background
that is about to repeat. Here the hole is not filled with anything -- dilating
it only makes the hole LARGER THAN THE RIDER, so a rim of body shows round every
cut at any camera angle off dead-on. Measured at radius 2 against radius 0, over
four props: 4.23% -> 2.70%, 1.85% -> 1.03%, 1.08% -> 0.56%, 1.29% -> 0.66% of
the 1x render. Half of the change was rim.

WHAT THE REST OF THE CHANGE IS, because "the 1x render must not move" was the
bar and it does move. It moves where the two copies were already fighting, and
it moves for the better: on the jukebox the song list's centre divider had a
dark smear through it from two near-coplanar copies, and it comes out clean; on
v46_vending_machine nine product tiles were being CLIPPED by the larger part
drawn over them and come out whole. The residue is darker patches where a hole
shows the body behind a proud slab. That is a real cost and it is smaller than
nine clipped products.

WHAT IT REFUSES TO CUT. If the overlap is more than half of the LARGER part,
the two boxes are not a fitting on a panel -- they are one region segmented
twice, and cutting would gut a part to fix a decomposition. Those are reported
as leads for segment_audit and left alone. Measured: they are rare, and they
are real segmentation faults when they happen.
"""
import argparse
import json
import sys
from pathlib import Path

# More than this much of the LARGER part covered means the two boxes are the
# same region twice over, not a fitting sitting on a panel. Cutting there would
# remove most of a part to fix a fault that belongs to segmentation.
GUT = 0.50
# Zero, and the docstring says why: a dilated hole is bigger than the thing that
# fills it, so every cut grows a rim of body. Kept as a constant rather than
# deleted because the number is the finding.
DILATE = 0


def _pairs(parts):
    """(host, rider, overlap_box) for every pair that shares drawn pixels.

    Ordered so the LARGER box is the host. Pairs where the overlap would gut
    the host come back with rider None, as a lead rather than a cut.
    """
    out = []
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            a, b = parts[i], parts[j]
            ax0, ay0, ax1, ay1 = a["px"]
            bx0, by0, bx1, by1 = b["px"]
            ox0, oy0 = max(ax0, bx0), max(ay0, by0)
            ox1, oy1 = min(ax1, bx1), min(ay1, by1)
            if ox1 <= ox0 or oy1 <= oy0:
                continue
            aa = (ax1 - ax0) * (ay1 - ay0)
            ab = (bx1 - bx0) * (by1 - by0)
            host, rider = (a, b) if aa >= ab else (b, a)
            big = max(aa, ab)
            ov = (ox1 - ox0) * (oy1 - oy0)
            if ov > GUT * big:
                out.append((host, None, (ox0, oy0, ox1, oy1)))
            else:
                out.append((host, rider, (ox0, oy0, ox1, oy1)))
    return out


def _cut(host_im, host_px, rider_im, rider_px, box):
    """Erase the rider's shape from the host. The erased pixels become HOLES.

    TRIED AND REVERTED: PATCHING THE HOLE WITH THE HOST'S OWN PANEL, the way
    fill_from_panel patches the background -- for each erased pixel, the nearest
    row at the same x that was not erased. That works on an elevation because a
    hole there is small against a tall column of panel. It does not work here,
    because a rider routinely covers the whole top edge of its host: the nearest
    surviving row is then whatever happens to sit BELOW the hole, and the
    jukebox's grille smeared its dark selection-display chrome up through the
    entire song-list region in black bars. 1.19% of the 1x render changed, and
    the 1x render is the one thing this pass must not touch.

    A hole is the honest answer and needs no colour invented for it. The pixels
    belong to the rider; what is behind the rider is the BODY, and layer_build
    has already painted clean panel there -- that is what paint_out exists for.
    At 1x the rider sits exactly over the hole and nothing changes at all, which
    is the property worth having. When they come apart, body shows through,
    which is what is actually behind a song list you have slid away from.
    """
    hx0, hy0 = host_px[0], host_px[1]
    W, H = host_im.size
    rx0, ry0 = rider_px[0], rider_px[1]
    rw, rh = rider_im.size
    rp = rider_im.load()

    covered = [[False] * H for _ in range(W)]
    x0, y0, x1, y1 = box
    for gx in range(x0, x1):
        for gy in range(y0, y1):
            lx, ly = gx - rx0, gy - ry0
            if not (0 <= lx < rw and 0 <= ly < rh):
                continue
            if rp[lx, ly][3] <= 128:
                continue
            for dx in range(-DILATE, DILATE + 1):
                for dy in range(-DILATE, DILATE + 1):
                    hx, hy = gx - hx0 + dx, gy - hy0 + dy
                    if 0 <= hx < W and 0 <= hy < H:
                        covered[hx][hy] = True

    out = host_im.copy()
    op = out.load()
    n = 0
    for x in range(W):
        for y in range(H):
            if covered[x][y] and op[x, y][3] > 0:
                op[x, y] = (0, 0, 0, 0)
                n += 1
    return out, n


def audit(prop_dir, face="front"):
    d = Path(prop_dir)
    try:
        pj = json.loads((d / f"parts_{face}.json").read_text())
    except Exception:
        return {"cuts": [], "leads": [], "why": "no parts file"}
    parts = pj.get("parts") or []
    cuts, leads = [], []
    for host, rider, box in _pairs(parts):
        if rider is None:
            leads.append({"part": host["name"], "box": list(box),
                          "why": "the overlap is more than half of this part: "
                                 "one region segmented twice, not a fitting"})
            continue
        cuts.append({"host": host["name"], "rider": rider["name"],
                     "box": list(box)})
    return {"cuts": cuts, "leads": leads}


def apply(prop_dir, face="front"):
    """Erase every rider's shape from every larger part it overlaps.

    Returns the cuts actually made. Rewrites parts/<host>.png in place and
    appends to overlap_log.json.
    """
    from PIL import Image
    d = Path(prop_dir)
    r = audit(d, face)
    if not r["cuts"]:
        return r
    pj = json.loads((d / f"parts_{face}.json").read_text())
    box = {p["name"]: p["px"] for p in pj["parts"]}
    # ONE PASS PER HOST, NOT PER PAIR. A grille under four decals must be read
    # once and written once, or the second cut reloads the file from disk and
    # discards the first.
    loaded, done = {}, []
    for c in r["cuts"]:
        for n in (c["host"], c["rider"]):
            if n in loaded:
                continue
            p = d / "parts" / f"{n}.png"
            if not p.exists():
                loaded[n] = None
                continue
            loaded[n] = Image.open(p).convert("RGBA")
    for c in r["cuts"]:
        h, ri = loaded.get(c["host"]), loaded.get(c["rider"])
        if h is None or ri is None:
            continue
        new, n = _cut(h, box[c["host"]], ri, box[c["rider"]], tuple(c["box"]))
        if not n:
            continue
        loaded[c["host"]] = new
        done.append({**c, "pixels": n})
    for c in done:
        loaded[c["host"]].save(d / "parts" / f"{c['host']}.png")
    if done:
        log = d / "overlap_log.json"
        try:
            prev = json.loads(log.read_text())
        except Exception:
            prev = []
        prev.append({"face": face, "cuts": done, "leads": r["leads"]})
        log.write_text(json.dumps(prev, indent=1))
    return {"cuts": done, "leads": r["leads"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--face", default="front")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        work = Path(__file__).resolve().parents[1] / "img2threejs-work"
        props = hit = pairs = leads = 0
        worst = []
        for pj in sorted(work.glob(f"*/parts_{args.face}.json")):
            r = audit(pj.parent, args.face)
            if not r["cuts"] and not r["leads"]:
                continue
            props += 1
            pairs += len(r["cuts"])
            leads += len(r["leads"])
            if r["cuts"]:
                hit += 1
                worst.append((len(r["cuts"]), pj.parent.name))
        print(f"{props} props with overlapping boxes")
        print(f"   {hit} have cuttable overlaps, {pairs} pair(s) in all")
        print(f"   {leads} lead(s) for segment_audit (one region twice)")
        for n, name in sorted(worst, reverse=True)[:12]:
            print(f"      {n:3} pair(s)  {name}")
        return

    d = Path(args.prop_dir)
    if args.apply:
        r = apply(d, args.face)
        print(f"overlap: {len(r['cuts'])} cut(s)")
        for c in r["cuts"]:
            print(f"   {c['rider']} taken out of {c['host']} "
                  f"({c['pixels']} px)")
    else:
        r = audit(d, args.face)
        print(f"overlap: {len(r['cuts'])} cuttable pair(s), "
              f"{len(r['leads'])} lead(s)")
        for c in r["cuts"]:
            print(f"   {c['rider']:22} is also inside {c['host']}")
    for l in r["leads"]:
        print(f"   LEAD {l['part']}: {l['why']}")


if __name__ == "__main__":
    main()
