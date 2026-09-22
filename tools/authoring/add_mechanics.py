#!/usr/bin/env python3
"""Give already-measured parts their DEPTH and MOTION, without re-identifying.

    python3 tools/authoring/add_mechanics.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS IS SEPARATE FROM identify_parts.py. Identity and mechanics are
different questions and they converge at different times. identify_parts asks
what a part IS and how it RESIZES, and the judge loop then spends rounds
correcting those resize rules -- an arcade cabinet took three rounds to settle.
Re-running identify_parts to pick up the depth and motion fields would throw
every one of those corrections away and start the loop from scratch.

So this reads the parts that are already there, shows the model where they
were MEASURED to be rather than asking it to find them again, and fills in
only the two fields that describe how each part behaves as an object:

    depth   how far it stands off the face, or into it
    motion  which edge or axis it moves about, which is what fixes its pivot

Everything else -- name, box, resize, anchor -- is passed through untouched.
A part the model does not mention keeps whatever it already had, so this is
safe to re-run and cannot lose work.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL  # noqa: E402
from identify_parts import object_crop  # noqa: E402

DEPTHS = {"flush", "proud", "deep", "recessed"}
MOTIONS = {"none", "hinge_left", "hinge_right", "hinge_top", "hinge_bottom",
           "press", "stick", "slide_x", "slide_y"}

ASK = """This is the front elevation of a {asset}, with its parts already
found and outlined. Each outline is numbered.

{listing}

Do NOT re-find the parts and do not move them -- they are measured. Say only
how each one BEHAVES AS AN OBJECT, so it can be built as separate geometry
with a working pivot instead of being painted on flat.

For each numbered part give:

  "depth"   how it sits relative to the face
              "flush"     painted on, no relief -- side art, a printed label,
                          a decal, a stripe
              "proud"     stands off a little -- a bezel, a trim rail, a
                          marquee housing, a control deck, a hinged door
              "deep"      stands well off -- a joystick, a handle, a lever,
                          a spout
              "recessed"  set INTO the body -- a screen, a coin slot, a vent,
                          a delivery tray, a glass window

  "motion"  how it moves, which decides where its pivot goes. A door that
            turns about its middle is not a door, so name the EDGE.
              "none"        static
              "hinge_left" / "hinge_right" / "hinge_top" / "hinge_bottom"
                            swings open about that edge -- a coin door, a
                            service hatch, a glass front, a lid
              "press"       pushes in along its own normal -- a button, a key,
                            a coin slot
              "stick"       tilts about its base -- a joystick, a lever
              "slide_x" / "slide_y"
                            travels along the face -- a drawer, a tray, a
                            dispensing flap

Be conservative: a part you are not sure moves is "none". A flat panel of art
is "flush". Only call something "deep" if it genuinely sticks out.

JSON only, one entry per numbered part, in order:
{{"parts": [{{"n": 1, "name": "...", "depth": "...", "motion": "..."}}]}}"""


def annotate(ob, parts):
    """Draw the measured boxes so the model answers about THESE parts.

    Asked in words alone it drifts -- it answers about the part it would
    expect a cabinet to have rather than the one that was found. Numbered
    outlines make the question unambiguous and make a wrong answer visible.
    """
    im = ob.convert("RGB").copy()
    if max(im.size) < 700:                      # small elevations read badly
        s = 700 / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.NEAREST)
    else:
        s = 1.0
    dr = ImageDraw.Draw(im)
    for i, p in enumerate(parts, 1):
        x0, y0, x1, y1 = [v * s for v in p["px"]]
        dr.rectangle([x0, y0, x1, y1], outline=(255, 0, 255), width=3)
        tag = str(i)
        tx, ty = x0 + 3, y0 + 2
        dr.rectangle([tx - 2, ty - 1, tx + 8 * len(tag) + 2, ty + 14],
                     fill=(255, 0, 255))
        dr.text((tx, ty), tag, fill=(255, 255, 255))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="game prop")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    pf = d / f"parts_{args.face}.json"
    man = json.loads(pf.read_text())
    parts = man["parts"]
    if not parts:
        raise SystemExit("no parts to annotate")

    ob = object_crop(d / f"{args.face}.png")
    shot = annotate(ob, parts)
    tmp = d / f"_mechanics_{args.face}.png"
    shot.save(tmp)

    listing = "\n".join(
        f"  {i}. {p['name']}" for i, p in enumerate(parts, 1))
    content = [{"type": "text",
                "text": ASK.format(asset=args.asset, listing=listing)},
               {"type": "image_url", "image_url": {"url": data_uri(tmp)}}]

    key = _openrouter_key()
    got = None
    for attempt in range(3):
        try:
            got = as_json(glm([{"role": "user", "content": content}],
                              CRITIC_MODEL, key, max_tokens=9000,
                              temperature=0.1 + 0.2 * attempt))
            break
        except Exception as e:
            print(f"  reply unusable ({type(e).__name__}), retry {attempt+1}/3")
    if got is None:
        raise SystemExit("no usable answer in three attempts")

    # MATCH BY NAME FIRST, INDEX SECOND. The model occasionally renumbers; the
    # name is the thing it was given, so trust that and fall back to position.
    by_name = {}
    for q in got.get("parts", []):
        if q.get("name"):
            by_name[str(q["name"]).strip()] = q
    seq = got.get("parts", [])

    n = 0
    for i, p in enumerate(parts):
        q = by_name.get(p["name"])
        if q is None and i < len(seq):
            q = seq[i]
        if not q:
            continue
        dep, mot = str(q.get("depth", "")).strip(), str(q.get("motion", "")).strip()
        if dep in DEPTHS and p.get("depth") != dep:
            p["depth"] = dep
            n += 1
        if mot in MOTIONS and p.get("motion") != mot:
            p["motion"] = mot
            n += 1
        p.setdefault("depth", "proud")
        p.setdefault("motion", "none")

    pf.write_text(json.dumps(man, indent=1))
    movers = [p for p in parts if p.get("motion", "none") != "none"]
    print(f"{CRITIC_MODEL} gave mechanics for {len(parts)} parts "
          f"({n} fields set, {len(movers)} movable)")
    for p in parts:
        print(f"  {p['name']:22} {p.get('depth','?'):9} {p.get('motion','?')}")


if __name__ == "__main__":
    main()
