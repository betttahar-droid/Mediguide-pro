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
  "taller_at"     WHERE on this prop that extra height physically goes, as the
                  outlined parts it goes next to. One entry per place, each
                  {{"n": <part number>, "side": "above"|"below"}}: "above" means
                  the new body is added between that part and whatever is above
                  it, "below" means between it and whatever is below.
                  GIVE EVERY PLACE YOUR OWN taller_means SENTENCE NAMES, and
                  look for more -- two, three or four, not one. The height is
                  SHARED between them, so one place has to stretch several
                  times further than four do, and a single narrow gap cannot
                  absorb the change at all: it comes back as a band of noise
                  where the body should be. Prefer the WIDE, EMPTY stretches
                  of the prop -- a plain lower body, a kick panel, the run
                  between two fittings -- over a thin gap at the very edge of
                  the drawing.
                  Name the places where a real one of these has PLAIN MATERIAL
                  that simply gets longer -- never inside a screen, a grille, a
                  sign or a control deck. If this prop genuinely has nowhere
                  like that, give an empty list; that is a real answer.
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

  "per_tier"      the same question for HEIGHT: the NUMBERS of the parts a
                  TALLER one of these has MORE OF rather than BIGGER ones. A
                  shelf, a product row, a title strip, a drawer, a rack. A
                  taller vending machine has more shelves, not taller shelves;
                  a taller jukebox has more title strips, not taller ones. Most
                  props have none of these -- a cabinet's screen, marquee and
                  coin door are each one of a kind at any height -- and an
                  empty list is the usual answer. Never list something that is
                  one per prop however tall it gets.
                  BUT IT MUST AGREE WITH YOUR OWN taller_means SENTENCE. If
                  that sentence says a taller one has MORE of something, that
                  something goes here. An empty per_tier beside a taller_means
                  promising more shelves is a contradiction, and the shelves
                  will come back stretched.
                  A part may be in BOTH per_bay and per_tier -- a product slot
                  in a grid is one more column when the machine is wider and
                  one more row when it is taller, and that is two answers to
                  two different questions, not a mistake.

  "spans"         the NUMBERS of the parts that are STRUCTURE rather than
                  content -- the housings and frames that physically run the
                  whole width of the prop and must keep doing so at any size: a
                  marquee housing, a screen bezel, a control deck, a kick
                  panel, a plinth. These get WIDER when the prop does. Do not
                  list content that merely sits on them: a title, a screen
                  image, a logo, a coin door, a joystick.

Be strict about per_bay. Anything you list will be DUPLICATED when the prop is
widened, so list only what genuinely comes in multiples on a bigger machine.

Every part is outlined and numbered on the image, including the small unnamed
decals -- a joystick or a button cluster is often one of those, so judge by
what you can SEE in each outline, not by its name.

JSON only:
{{"wider_means": "...", "taller_means": "...",
  "taller_at": [{{"n": 1, "side": "above"}}, {{"n": 9, "side": "below"}}],
  "max_wider": 2.0, "max_taller": 1.6, "per_bay": [4, 7],
  "per_tier": [], "spans": [1, 3]}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--asset", default="game prop")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    man = json.loads((d / f"parts_{args.face}.json").read_text())
    parts = man["parts"]
    H_face = man.get("size", [0, 0])[1] or max(
        [p["px"][3] for p in parts] + [1])
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

    def numbers(key):
        got_list = []
        for n in got.get(key, []):
            try:
                i = int(n)
            except (TypeError, ValueError):
                continue
            if 1 <= i <= len(parts):
                got_list.append(parts[i - 1]["name"])
        return got_list

    spans = numbers("spans")
    # A TALLER MACHINE HAS MORE SHELVES, NOT TALLER ONES. per_bay has always
    # been able to say "a wider one has more of these" and height had no way to
    # say it at all, so a taller vending machine grew its product rows instead
    # of gaining one. Same flag, same instancing, other axis.
    per_tier = numbers("per_tier")
    per_bay = []
    for n in got.get("per_bay", []):
        try:
            i = int(n)
        except (TypeError, ValueError):
            per_bay += [p["name"] for p in parts if p["name"] == str(n)]
            continue
        if 1 <= i <= len(parts):
            per_bay.append(parts[i - 1]["name"])
    # WHAT SITS ON A BAY REPEATS WITH THE BAY, WHETHER OR NOT IT WAS LISTED.
    # The model named this cabinet's six buttons and forgot its two joysticks,
    # and both judges caught the result in the same words: "the widened deck
    # gets a second button field with no second stick". That is not a matter of
    # taste, it is arithmetic. A part in `spans` is bay-level STRUCTURE -- a
    # control deck, a kick panel -- and everything mounted on it comes with it.
    # So if anything standing on a structure repeats per bay, everything
    # standing on that same structure does, because they are one station. Left
    # to the model this needs a perfect list every time; measured from the
    # boxes it needs the model to be right once.
    # at this stage a part is still a pixel box on the face; u and v are added
    # later by layer_build, so the fractions are taken from px directly
    SW, SH = man["size"]

    def box(p):
        x0, y0, x1, y1 = p["px"]
        return x0 / SW, x1 / SW, 1 - y1 / SH, 1 - y0 / SH

    def sits_on(p, s):
        pu0, pu1, pv0, pv1 = box(p)
        su0, su1, sv0, sv1 = box(s)
        m = 0.03
        return (pu0 >= su0 - m and pu1 <= su1 + m
                and pv0 >= sv0 - m and pv1 <= sv1 + m)

    # A STATION'S PARTS ARE PEERS, SO THE CLOSURE ONLY REACHES PEERS. The rule
    # as first written promoted anything standing on a structure once one of
    # its neighbours was per-bay -- and on this cabinet the screen stands on
    # the screen bezel alongside a coin slot that does repeat, so the SCREEN
    # was marked per-bay. A widened cabinet would have come back with two
    # screens side by side, which is the exact failure the per_bay prompt warns
    # about in as many words. A joystick and a button are the same order of
    # thing; a screen is not, and size says so without being told.
    def area(p):
        u0, u1, v0, v1 = box(p)
        return max(0.0, u1 - u0) * max(0.0, v1 - v0)

    added = []
    for s in [p for p in parts if p["name"] in spans]:
        riders = [p for p in parts
                  if p["name"] != s["name"] and p["name"] not in spans
                  and sits_on(p, s)]
        seats = [p for p in riders if p["name"] in per_bay]
        if not seats:
            continue
        biggest = max(area(p) for p in seats)
        for p in riders:
            if p["name"] in per_bay:
                continue
            if area(p) > 0.08:
                continue                     # too big to be one player's fitting
            if area(p) > 3 * biggest:
                continue                     # not a peer of what already repeats
            per_bay.append(p["name"])
            added.append(f"{p['name']} (stands on {s['name']})")

    # WHERE THE PROP GETS TALLER, AS ROWS. taller_means has always said it in
    # words -- "more carcass above the marquee and below the coin door" -- and
    # nothing downstream could read a sentence, so strip_slice searched the
    # whole prop for somewhere quiet and bare and landed wherever its score
    # came out. On a densely fitted cabinet that is a compromise every time,
    # and five different scorings of it have been tried and reverted.
    #
    # The model already knows the answer and is good at this question; it is
    # the same division the rest of the tool runs on. It names a fitting and a
    # side, arithmetic turns that into the gap between that fitting and its
    # neighbour, and the band is then chosen inside a place a real one of these
    # actually gets longer rather than anywhere that measures calm.
    taller_at = []
    for e in (got.get("taller_at") or []):
        try:
            i = int(e.get("n"))
            side = str(e.get("side", "")).lower()
        except (TypeError, ValueError, AttributeError):
            continue
        if not (1 <= i <= len(parts)) or side not in ("above", "below"):
            continue
        q = parts[i - 1]
        y0, y1 = q["px"][1], q["px"][3]
        # the gap runs to the nearest edge of any part on the far side of it,
        # or to the prop's own end -- measured, not asserted
        if side == "above":
            lo = max([p["px"][3] for p in parts
                      if p["px"][3] <= y0 and p is not q] + [0])
            gap = [lo, y0]
        else:
            hi = min([p["px"][1] for p in parts
                      if p["px"][1] >= y1 and p is not q] + [H_face])
            gap = [y1, hi]
        if gap[1] - gap[0] >= 6:
            taller_at.append({"part": q["name"], "side": side,
                              "px": [int(gap[0]), int(gap[1])]})

    rules = {
        "wider_means": str(got.get("wider_means", "a wider one of the same thing"))[:300],
        "taller_means": str(got.get("taller_means", "more body, same fittings"))[:300],
        "taller_at": taller_at,
        "max_wider": clamp(got.get("max_wider"), 1.0, 3.0, 2.0),
        "max_taller": clamp(got.get("max_taller"), 1.0, 3.0, 1.6),
        "per_bay": per_bay,
        # BOTH AXES IS ALLOWED, and the vending machine is why. Its product
        # slots are a grid: a wider machine has more columns of them and a
        # taller one more rows, which is two answers to two different questions.
        # Excluding the overlap silently dropped every one of them from the
        # height axis, since they were all named per_bay first.
        "per_tier": per_tier,
        # a part cannot be both the frame and the thing bolted into it
        "spans": [n for n in spans if n not in per_bay],
    }
    (d / "scale_rules.json").write_text(json.dumps(rules, indent=1))

    # the manifest carries the flag, so the renderer needs nothing else
    for p in parts:
        p["per_bay"] = p["name"] in per_bay
        p["per_tier"] = p["name"] in rules["per_tier"]
        p["spans"] = p["name"] in rules["spans"]
    (d / f"parts_{args.face}.json").write_text(json.dumps(man, indent=1))

    print(f"wider  x{rules['max_wider']}: {rules['wider_means']}")
    print(f"taller x{rules['max_taller']}: {rules['taller_means']}")
    print(f"per bay: {', '.join(per_bay) if per_bay else '(nothing repeats)'}")
    if rules["per_tier"]:
        print(f"per tier: {', '.join(rules['per_tier'])}")
    for a in added:
        print(f"  + {a}")
    print(f"spans:   {', '.join(rules['spans']) if rules['spans'] else '(nothing spans)'}")


if __name__ == "__main__":
    main()
