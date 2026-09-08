#!/usr/bin/env python3
"""Draw the prop's OTHER flank, because one drawing cannot serve both.

    python3 tools/authoring/other_side.py work/ps1 --asset "arcade cabinet"

Authoring tool. NOT a build, CI or runtime dependency.

WHY. A side elevation depicts one flank. Two things have to be true of a flank
in the model -- its art must READ correctly from outside, and its drawn control
deck must sit at the same end as the modelled one -- and on the flank the
drawing does NOT depict, those two are in direct conflict. Reading correctly
puts the drawn nose at the model's tail; aligning the nose mirrors the
lettering. A side elevation ties its letter direction to which end its nose is
on, so one image cannot be its own reflection, and every UV expression is only
a choice of which fault to have. Both judges called it three rounds running:
"the side art decal is mirrored backwards", "'GALAXY' reads mirrored (YXAJLAG)".

The missing thing is information, and there is a model here that makes exactly
this kind of information. A real cabinet has two side decals that are mirror
images as printed, so that each reads correctly from its own side. So ask for
the second one.

VERIFIED, NOT TRUSTED. The reply is only usable if it is the same object: its
silhouette is compared against the mirror of the original's, and it has to
agree. A model asked to mirror a drawing will sometimes redraw the object, and
a differently-shaped flank would cut against the wrong outline and show sheet
through the prop. Where the check fails the tool says so and the renderer falls
back to the mirrored texture, which is the old behaviour and no worse.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402
from identify_parts import object_crop  # noqa: E402
from layer_build import silhouette  # noqa: E402

# MIRROR IT HERE, AND ASK THE MODEL ONLY FOR THE PART IT IS GOOD AT.
# Asked to draw the opposite flank from scratch, the model redrew the SAME
# flank -- correct lettering, nose on the original side -- and the silhouette
# check rejected it at 62%. That is the right outcome from the check and the
# wrong division of labour: mirroring an image is arithmetic, exact and free,
# and the only thing that survives a mirror badly is text. So the flip is done
# here, the mirrored image is handed over as the target composition, and the
# single instruction is to turn the lettering back the right way round. The
# silhouette check then has almost nothing left to fail on, which is how you
# can tell the work was split correctly.
PROMPT = """The attached image is a {asset}'s side panel that has been FLIPPED
horizontally, so its artwork is correct but every piece of LETTERING is now
mirrored and reads backwards.

Redraw this exact image with the lettering corrected, so every word, logo and
number reads normally from left to right.

  - Change NOTHING else. Same silhouette, same outline, same size and position
    in frame, same illustration, same colours, same grime and wear in the same
    places. The control deck stays exactly where it is.
  - Only the text is redrawn, in place, at the same size and in the same
    style, reading forwards instead of backwards.

Plain flat background, no shadow, no ground plane, nothing else in frame.
"""


def text_boxes(a, b, min_frac=0.0008):
    """Where the model changed the picture -- which is where the text is.

    THE MODEL CANNOT TURN THE WORD AROUND, BUT IT CAN SHOW ME WHERE IT IS.
    Three tries at un-mirroring the lettering gave YXALAG, GXAAXY and YXALAG:
    it flips each glyph where it stands and loses their order, every time. That
    is a real limit, not a prompt to be tuned.

    But it edited only the lettering -- the silhouettes agreed to 99.8% -- so
    the difference between its attempt and the plain mirror IS the text, boxed
    for free. And flipping a box of pixels is arithmetic that cannot scramble
    anything: mirroring the whole panel and then flipping each text box back in
    place puts the word at its mirrored position, reading forwards, glyph order
    intact. The model finds it; the arithmetic turns it.
    """
    a = a.convert("RGB"); b = b.convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size)
    W, H = a.size
    pa, pb = a.load(), b.load()
    hot = [[sum(abs(p - q) for p, q in zip(pa[x, y], pb[x, y])) > 110
            for y in range(H)] for x in range(W)]
    # close small gaps so the glyphs of one word become one box
    k = max(2, W // 40)
    grown = [[False] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            if not hot[x][y]:
                continue
            for dx in range(-k, k + 1):
                for dy in range(-k, k + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H:
                        grown[nx][ny] = True
    seen = [[False] * H for _ in range(W)]
    out = []
    for sx in range(W):
        for sy in range(H):
            if not grown[sx][sy] or seen[sx][sy]:
                continue
            stack, cells = [(sx, sy)], []
            seen[sx][sy] = True
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                    if 0 <= nx < W and 0 <= ny < H and grown[nx][ny] \
                            and not seen[nx][ny]:
                        seen[nx][ny] = True
                        stack.append((nx, ny))
            if len(cells) < min_frac * W * H:
                continue
            xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1))

    # GROUP THEM INTO LINES, or flipping each one reproduces the fault. Ten
    # separate boxes came back and flipping each in place is precisely what the
    # model did wrong: every glyph faces forwards and the word still reads
    # backwards. A WORD is the unit that has to turn, and a word is a row of
    # marks that overlap each other vertically. Merging on that gives one box
    # per line of text, and one flip per line puts the letters back in order.
    merged = True
    while merged:
        merged = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a0, b0, a1, b1 = out[i]
                c0, d0, c1, d1 = out[j]
                lo, hi = max(b0, d0), min(b1, d1)
                overlap = hi - lo
                if overlap > 0.4 * min(b1 - b0, d1 - d0):
                    out[i] = (min(a0, c0), min(b0, d0), max(a1, c1), max(b1, d1))
                    out.pop(j)
                    merged = True
                    break
            if merged:
                break

    # AND SHRINK EACH LINE BACK ONTO ITS OWN INK. The boxes are grown to close
    # the gaps between glyphs and merged to make a line, and both steps sweep
    # in background -- which then gets flipped along with the letters, so the
    # planet behind the word no longer lines up with the planet either side of
    # it and the paste shows as a rectangle. Recomputing each line's bounds
    # from the undilated difference keeps the word and drops the scenery.
    tight = []
    for (x0, y0, x1, y1) in out:
        xs = [x for x in range(x0, x1)
              if any(hot[x][y] for y in range(y0, y1))]
        ys = [y for y in range(y0, y1)
              if any(hot[x][y] for x in range(x0, x1))]
        if xs and ys:
            tight.append((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1))
    return tight


def flip_boxes(im, boxes, feather=10):
    """Turn each box's contents back the right way round, in place.

    FEATHERED, because a flipped rectangle cannot align with what surrounds it.
    However tightly the box is drawn it still carries some scenery, and that
    scenery is now mirrored against its own continuation -- on this cabinet the
    planet behind the word steps sideways at the box edge and reads as a pasted
    rectangle. Ramping the paste over a few pixels trades a hard line for a
    soft one, which on a hand-painted panel at this resolution is the
    difference between a fault and a brush stroke.
    """
    im = im.copy()
    for (x0, y0, x1, y1) in boxes:
        w, h = x1 - x0, y1 - y0
        if w < 4 or h < 4:
            continue
        patch = im.crop((x0, y0, x1, y1)).transpose(Image.FLIP_LEFT_RIGHT)
        k = max(1, min(feather, w // 3, h // 3))
        mask = Image.new("L", (w, h), 255)
        mp = mask.load()
        for x in range(w):
            for y in range(h):
                e = min(x, y, w - 1 - x, h - 1 - y)
                if e < k:
                    mp[x, y] = int(255 * (e + 1) / (k + 1))
        im.paste(patch, (x0, y0), mask)
    return im


def read_word(path, asset):
    """The largest piece of lettering on the panel, as a word.

    A SHAPE CHECK CANNOT SEE A SCRAMBLED WORD. Handing the model a mirrored
    panel and asking it to turn the text around produced a silhouette that
    agreed with the original to 99.6% -- and a cabinet whose side read GXAJAY
    where the original reads GALAXY. It un-mirrored each glyph on the spot and
    lost their order, which is exactly the kind of fault a silhouette test is
    blind to, and exactly the kind a reading test catches. Reading a word off a
    picture is naming, which is what these models are for.
    """
    try:
        from gemini_judge import vision_json
        r, _m = vision_json(
            f"This is the side panel of a {asset}. Read the LARGEST piece of "
            "lettering on it -- the main word or title.\n\n"
            'Reply with what it literally says, exactly as the glyphs appear '
            'left to right, even if that is not a real word. JSON only: '
            '{"text": "..."}',
            [path])
        t = "".join(ch for ch in str(r.get("text", "")).upper()
                    if ch.isalnum())
        return t or None
    except Exception:
        return None


def sil_image(path):
    ob = object_crop(path)
    m = silhouette(ob, erode=0)
    W, H = ob.size
    im = Image.new("L", (W, H))
    px = im.load()
    for x in range(W):
        for y in range(H):
            px[x, y] = 255 if m[x][y] else 0
    return im


def agree(a, b, n=128):
    """IoU of two silhouettes, each scaled into the same box."""
    pa = a.resize((n, n), Image.NEAREST).load()
    pb = b.resize((n, n), Image.NEAREST).load()
    inter = union = 0
    for x in range(n):
        for y in range(n):
            p, q = pa[x, y] > 127, pb[x, y] > 127
            if p or q:
                union += 1
            if p and q:
                inter += 1
    return inter / max(1, union)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--want", type=float, default=0.86,
                    help="silhouette agreement with the mirrored original")
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--redraw", action="store_true")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    src = d / "side.png"
    if not src.exists():
        raise SystemExit("no side.png -- nothing to mirror")
    try:
        front = json.loads((d / "profile.json").read_text())["front_edge"]
    except Exception:
        front = "left"
    other = "right" if front == "left" else "left"

    out = d / "side_other.png"
    flipped = d / "_side_flipped.png"
    Image.open(src).transpose(Image.FLIP_LEFT_RIGHT).save(flipped)

    want_word = read_word(src, args.asset)
    print(f"  the original's side art reads {want_word or '(no lettering found)'}")

    a = sil_image(src).transpose(Image.FLIP_LEFT_RIGHT)
    # THE MODEL'S RAW ATTEMPT KEEPS ITS OWN FILE. Writing the finished panel
    # back over it made the next run diff the mirror against my own composite,
    # find the regions I had already flipped, and flip them back -- so a second
    # run silently undid the first. A step that is not idempotent is a step
    # that breaks the moment anything re-runs it, which in this pipeline is
    # every round.
    edit = d / "_side_edit.png"
    if args.redraw or not edit.exists():
        generate_image(PROMPT.format(asset=args.asset), edit, load_key(),
                       refs=[flipped])

    # the model's edit localises the lettering; the flip is done here
    M = Image.open(flipped).convert("RGB")
    boxes = text_boxes(M, Image.open(edit).convert("RGB"))
    print(f"  the model's edit localises {len(boxes)} lettering region(s)")
    fixed = flip_boxes(M, boxes)
    fixed.save(out)

    got = agree(a, sil_image(out))
    word = read_word(out, args.asset)
    same = bool(want_word and word and word == want_word)
    print(f"  silhouette {100*got:.1f}%, reads {word or '(nothing)'}"
          f"{'  MATCHES' if same else '  WRONG WORD' if want_word else ''}")
    ok = got >= args.want and (same or not want_word)
    print(f"  {'USABLE' if ok else 'REJECTED'}")

    # cut to the prop's outline, the same treatment body_side.png gets, so the
    # renderer can drop it straight in as the other flank's map
    if ok:
        ob = object_crop(out).convert("RGBA")
        m = silhouette(ob, erode=0)
        W2, H2 = ob.size
        pp = ob.load()
        for x in range(W2):
            for y in range(H2):
                if not m[x][y]:
                    r, g, b, _ = pp[x, y]
                    pp[x, y] = (r, g, b, 0)
        ob.save(d / "body_side_other.png")
        print(f"  wrote {d / 'body_side_other.png'} ({W2}x{H2})")

    meta = {"image": "side_other.png", "cut": "body_side_other.png",
            "front_edge": other,
            "agreement": round(got, 4), "text": word, "text_ok": bool(same),
            "usable": bool(ok)}
    (d / "side_other.json").write_text(json.dumps(meta, indent=1))
    if not ok:
        print("  the renderer will mirror the original instead, as before")


if __name__ == "__main__":
    main()
