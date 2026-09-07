#!/usr/bin/env python3
"""Ask what resizing this particular prop is SUPPOSED to mean.

    python3 tools/authoring/scale_rules.py work/ps1 --asset "vending machine"

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Every prop so far was resized the same way -- twice as wide, twice as
tall -- and judged on whether it survived. But those are not the same operation
for different objects. A wider vending machine has MORE PRODUCT COLUMNS. A
wider arcade cabinet is a TWO-PLAYER cabinet: a second joystick, a second set
of buttons. A wider jukebox is just a bigger jukebox. Grow all three by
stretching panel and two of them are wrong even when nothing smears, because
the result does not make sense as the object it claims to be.

So the tool decides, per prop, what its own axes MEAN, and three things follow:

  THE RANGE      how far this prop can sensibly go. A cabinet at three times
                 its width is not a cabinet any more, and rendering it proves
                 nothing.
  WHAT REPEATS   which fittings come once per BAY rather than once per prop.
                 The prop's own width is the unit: a cabinet twice as wide is
                 two bays, so anything the model marks as per-bay appears twice
                 -- which is what makes it a two-player cabinet rather than a
                 one-player cabinet with a lot of spare panel.
  THE BAR        a sentence saying what a correct result looks like, handed
                 straight to the judge. "Judge whether it still looks good" is
                 a weaker question than "a wider one of these must have more
                 product columns; does it?"

The model is asked what the object IS and how it works, which is what it is
good at. Nothing here is measured by it.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL  # noqa: E402
from identify_parts import object_crop  # noqa: E402
from region_parts import annotate  # noqa: E402

ASK = """This is the front elevation of a {asset}. The tool has separated it
into these parts:

{listing}

The prop is built to be RESIZED. Say what resizing this particular object
should physically mean -- not whether it can be stretched, but what a bigger
one of these actually is.

  "wider_means"   one sentence: what IS a wider {asset}? For a vending machine
                  it is more product columns. For an arcade cabinet it is a
                  two-player cabinet -- a second joystick and button set. For a
                  wardrobe it is simply a wider carcass with the same doors.
  "taller_means"  the same for height. Usually more body or more shelves; for
                  most props it is NOT a taller screen or a taller sign.
  "max_wider"     how many times its own width this prop can sensibly reach
                  before it stops being a {asset}. 1.0 means it should not be
                  widened at all. Typically 1.5 to 2.5.
  "max_taller"    the same for height.
  "per_bay"       the NUMBERS of the outlined parts that come ONCE PER BAY rather
                  than once per prop -- the ones a two-player cabinet has two
                  of, the ones a wider machine has more of. A joystick, a
                  button cluster, a product column, a coin slot. NOT a title, a
                  brand sign, a screen, a coin door, or a maker's plate: there
                  is only ever one of those however big the prop gets.

Be strict about per_bay. Anything you list will be DUPLICATED when the prop is
widened, so list only what genuinely comes in multiples on a bigger machine.

Every part is outlined and numbered on the image, including the small unnamed
decals -- a joystick or a button cluster is often one of those, so judge by
what you can SEE in each outline, not by its name.

JSON only:
{{"wider_means": "...", "taller_means": "...",
  "max_wider": 2.0, "max_taller": 1.6, "per_bay": [4, 7]}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="game prop")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    man = json.loads((d / f"parts_{args.face}.json").read_text())
    parts = man["parts"]
    listing = "\n".join(f"  {i}. {p['name']}"
                        for i, p in enumerate(parts, 1)) or "  (none)"

    # SHOW IT WHERE THEY ARE. Asked for names, it answered with fittings the
    # part list does not contain -- the joystick and the button cluster are
    # anonymous decals by this stage, so there was no name to give. Numbered
    # outlines turn it back into the question this tool always asks a model:
    # pick the ones you can see, and never say where anything is.
    ob = object_crop(d / f"{args.face}.png")
    tmp = d / f"_scale_{args.face}.png"
    annotate(ob, [p["px"] for p in parts]).save(tmp)
    content = [{"type": "text",
                "text": ASK.format(asset=args.asset, listing=listing)},
               {"type": "image_url", "image_url": {"url": data_uri(tmp)}}]

    key = _openrouter_key()
    got = None
    for retry in range(3):
        try:
            got = as_json(glm([{"role": "user", "content": content}],
                              CRITIC_MODEL, key, max_tokens=12000,
                              temperature=0.1 + 0.2 * retry))
            break
        except Exception as e:
            print(f"  reply unusable ({type(e).__name__}), retry {retry + 1}/3")
    if got is None:
        got = {}

    def clamp(v, lo, hi, dflt):
        try:
            return max(lo, min(hi, float(v)))
        except (TypeError, ValueError):
            return dflt

    per_bay = []
    for n in got.get("per_bay", []):
        try:
            i = int(n)
        except (TypeError, ValueError):
            per_bay += [p["name"] for p in parts if p["name"] == str(n)]
            continue
        if 1 <= i <= len(parts):
            per_bay.append(parts[i - 1]["name"])
    rules = {
        "wider_means": str(got.get("wider_means", "a wider one of the same thing"))[:300],
        "taller_means": str(got.get("taller_means", "more body, same fittings"))[:300],
        "max_wider": clamp(got.get("max_wider"), 1.0, 3.0, 2.0),
        "max_taller": clamp(got.get("max_taller"), 1.0, 3.0, 1.6),
        "per_bay": per_bay,
    }
    (d / "scale_rules.json").write_text(json.dumps(rules, indent=1))

    # the manifest carries the flag, so the renderer needs nothing else
    for p in parts:
        p["per_bay"] = p["name"] in per_bay
    (d / f"parts_{args.face}.json").write_text(json.dumps(man, indent=1))

    print(f"wider  x{rules['max_wider']}: {rules['wider_means']}")
    print(f"taller x{rules['max_taller']}: {rules['taller_means']}")
    print(f"per bay: {', '.join(per_bay) if per_bay else '(nothing repeats)'}")


if __name__ == "__main__":
    main()
