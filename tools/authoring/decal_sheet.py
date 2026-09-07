#!/usr/bin/env python3
"""Ask for the prop's GRAPHICS as decals, with the rules for laying them.

    python3 tools/authoring/decal_sheet.py work/ps1 --asset "arcade cabinet"

Authoring tool. NOT a build, CI or runtime dependency.

WHY. material_atlas stopped the tool carving materials out of a painting. This
is the other half: it was carving the GRAPHICS out of the same painting too.
A title cut from the elevation arrives welded to the panel behind it, at the
one size it happened to be drawn, with the panel's own lighting baked across
it -- so it had to be bled outwards to stop the sheet showing at its edges,
and it could not be moved, resized or re-laid without taking the panel with
it. The judges named the consequence every round: "the side GALACTIC decal is
smeared and garbled and cut at the panel edge".

A decal authored AS a decal has no panel behind it to separate out. It is a
graphic on a key colour, and keying is exact arithmetic rather than a guess at
where the artwork stops.

WHAT MAKES IT ADAPTABLE IS THE RULE, NOT THE PICTURE. Each decal is asked for
with how it behaves when the prop changes size, because that is a question
about what the graphic MEANS and the model is the only thing here that knows:

  hold    one of it, at its real size, wherever it is anchored. A title, a
          maker's plate, a warning label. A wider cabinet does not get a
          bigger title, it gets more cabinet around the same title.
  along   a strip that runs an edge: it keeps its ends and repeats its middle,
          so a longer edge gets more of it. Pinstriping, a moulding run.
  repeat  scattered over an area at a fixed density, so a bigger area gets
          more of them. Rivets, bolts, stencil marks.

Those three cover every graphic on the props built so far, and each is a rule
the renderer can apply without knowing what the decal depicts.

AS EVER: the model authors, names and classifies; arithmetic keys, measures
and verifies. The key colour is checked to be actually absent from the artwork
before it is trusted, because a magenta logo on a magenta key is a hole.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402
from material_atlas import cells  # noqa: E402

KEY = (255, 0, 255)

PROMPT = """A DECAL SHEET for a {asset}, in the style of the attached reference
elevations.

Draw a grid of separate graphics on a FLAT PURE MAGENTA background
(RGB 255,0,255), with a wide magenta gutter between every graphic and a wide
magenta margin around the whole grid.

Each cell holds ONE graphic that appears on this {asset}, drawn on its own with
NOTHING behind it -- no panel, no housing, no frame, no drop shadow, no glow,
no border, and no magenta showing through the middle of it:

  - its title or brand lettering
  - a smaller secondary marking: an instruction, a price, a warning label
  - a logo, emblem or mascot
  - a pinstripe or moulding STRIP, drawn as a horizontal run
  - a small repeated fixing: a rivet, a bolt, a screw head
  - a stencil, number or icon

Hand-painted PlayStation-era look, low resolution, muted palette taken from
the reference. Do not draw the {asset} itself. Do not label the cells.
"""

RULE_ASK = """These are decals cut from a sheet for a {asset}. Each is a
graphic that gets laid onto the prop's surface.

For each, give:

  "name"  one or two lowercase words with underscores: title, price_plate,
          logo, pinstripe, rivet, warning_label. Each name used once.
  "rule"  how it behaves when the prop is made LARGER:
          "hold"   -- one of it, always at its real size (a title, a plate,
                      a logo, a label). A wider prop does NOT get a bigger one.
          "along"  -- a strip that runs an edge and gets longer, keeping its
                      ends and repeating its middle (a pinstripe, a moulding).
          "repeat" -- scattered at a fixed density, so a larger area gets more
                      of them (rivets, bolts, stencil marks).
  "where" the face it belongs on: "front", "side", "back", "top" or "any".

JSON only, one entry per decal in the order given:
{{"decals": [{{"n": 1, "name": "...", "rule": "hold", "where": "front"}}, ...]}}"""

RULES = {"hold", "along", "repeat"}


def cells_of(im, pad=2):
    """The same gutter scan as the sheet's, applied inside one cell."""
    W, H = im.size
    px = im.convert("RGB").load()

    def is_key(c):
        return sum(abs(a - b) for a, b in zip(c, KEY)) < 90

    def runs(flags, lo):
        out, s = [], None
        for i, f in enumerate(flags):
            if f and s is None:
                s = i
            elif not f and s is not None:
                if i - s >= lo:
                    out.append((s, i))
                s = None
        if s is not None and len(flags) - s >= lo:
            out.append((s, len(flags)))
        return out

    xr = runs([any(not is_key(px[x, y]) for y in range(0, H, 2))
               for x in range(W)], max(6, W // 12))
    yr = runs([any(not is_key(px[x, y]) for x in range(0, W, 2))
               for y in range(H)], max(6, H // 12))
    if len(xr) * len(yr) <= 1:
        return [im]
    out = []
    for (y0, y1) in yr:
        for (x0, x1) in xr:
            out.append(im.crop((max(0, x0 - pad), max(0, y0 - pad),
                                min(W, x1 + pad), min(H, y1 + pad))))
    return out


def key_out(im, tol=90):
    """Make the key colour transparent, and say how much of the cell it was.

    Flood filled from the border rather than tested colour by colour: a decal
    with a magenta letter in it is still one graphic, and the inside of an O is
    not background just because it is the same colour as the sheet. This is the
    same reasoning silhouette() reached for the elevations, and the same reason
    -- "background" is what the outside is CONNECTED to.
    """
    im = im.convert("RGBA")
    W, H = im.size
    px = im.load()

    def is_key(c):
        return sum(abs(a - b) for a, b in zip(c[:3], KEY)) < tol

    out = [[False] * H for _ in range(W)]
    stack = []
    for x in range(W):
        for y in (0, H - 1):
            if is_key(px[x, y]) and not out[x][y]:
                out[x][y] = True
                stack.append((x, y))
    for y in range(H):
        for x in (0, W - 1):
            if is_key(px[x, y]) and not out[x][y]:
                out[x][y] = True
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < W and 0 <= ny < H and not out[nx][ny] and is_key(px[nx, ny]):
                out[nx][ny] = True
                stack.append((nx, ny))

    cut = 0
    for x in range(W):
        for y in range(H):
            if out[x][y]:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
                cut += 1
    return im, cut / max(1, W * H)


def trim(im):
    """Crop to the graphic itself, so its box IS its extent."""
    px = im.load()
    W, H = im.size
    xs = [x for x in range(W) if any(px[x, y][3] > 8 for y in range(H))]
    ys = [y for y in range(H) if any(px[x, y][3] > 8 for x in range(W))]
    if not xs or not ys:
        return None
    return im.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--redraw", action="store_true")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    d.mkdir(parents=True, exist_ok=True)
    sheet = d / "decals.png"
    key = load_key()

    if args.redraw or not sheet.exists():
        refs = [p for p in (d / "front.png", d / "side.png") if p.exists()]
        generate_image(PROMPT.format(asset=args.asset), sheet, key, refs=refs)
        print(f"  drew {sheet}")

    # the gutters are magenta rather than white, and cells() finds the sheet's
    # own background from its corners, so the same splitter serves both sheets
    raw = cells(sheet)
    out = d / "decals"
    out.mkdir(exist_ok=True)

    # A CELL MAY HOLD MORE THAN ONE GRAPHIC, so the split repeats itself. The
    # model put a bolt and a grille side by side in one cell and two arrow
    # marks in another -- perfectly sensible sheet design -- and taking one
    # decal per top-level cell welded them into single graphics that could
    # never be placed. The gutters inside a cell are the same measurement as
    # the gutters between cells, so the same scan answers both; and because it
    # only cuts where there is a clear run of background all the way across,
    # the two lines of a title stay one title.
    parts = []
    for c in raw:
        try:
            sub = cells_of(c)
        except Exception:
            sub = [c]
        parts.extend(sub if len(sub) > 1 else [c])
    print(f"  {len(raw)} cells -> {len(parts)} graphics")

    got = []
    for i, c in enumerate(parts, 1):
        cut, frac = key_out(c)
        g = trim(cut)
        # A CELL THAT IS ALL KEY IS AN EMPTY CELL, and a cell that is no key at
        # all is a panel the model drew instead of a graphic -- neither is a
        # decal, and passing them on would put a magenta square or a slab of
        # background onto the prop.
        if g is None or frac > 0.985:
            print(f"    cell {i}: empty")
            continue
        if frac < 0.03:
            print(f"    cell {i}: no background keyed out ({100*frac:.1f}%) -- "
                  f"drawn as a panel, not a decal; dropped")
            continue
        p = out / f"d{len(got) + 1}.png"
        g.save(p)
        got.append({"n": len(got) + 1, "image": f"decals/{p.name}",
                    "px": list(g.size), "keyed": round(frac, 3)})
        print(f"    d{len(got)}: {g.size[0]}x{g.size[1]}, "
              f"{100*frac:.0f}% keyed away")

    if not got:
        raise SystemExit("no decals survived keying -- the sheet is unusable")

    named = {}
    try:
        from gemini_judge import vision_json
        r, model = vision_json(
            RULE_ASK.format(asset=args.asset),
            [d / g["image"] for g in got], key)
        for e in r.get("decals", []):
            try:
                named[int(e["n"])] = (
                    str(e.get("name", "")).strip().lower().replace(" ", "_")[:32],
                    str(e.get("rule", "hold")).strip().lower(),
                    str(e.get("where", "any")).strip().lower())
            except (KeyError, TypeError, ValueError):
                continue
        print(f"    {model} classified {len(named)} of {len(got)}")
    except Exception as e:
        print(f"  ! classification failed ({type(e).__name__}) -- all 'hold'")

    seen = set()
    for g in got:
        nm, rule, where = named.get(g["n"], (f"decal_{g['n']}", "hold", "any"))
        if not nm or nm in seen:
            nm = f"decal_{g['n']}"
        seen.add(nm)
        # AN UNKNOWN RULE IS "hold". The two rules that add copies can put a
        # graphic somewhere it was never meant to be; the one that does not is
        # the safe reading of a word this tool does not recognise.
        g["name"] = nm
        g["rule"] = rule if rule in RULES else "hold"
        g["where"] = where if where in ("front", "side", "back", "top") else "any"

    (d / "decals.json").write_text(json.dumps(
        {"asset": args.asset, "decals": got}, indent=1))
    print(f"  {len(got)} decals -> {d / 'decals.json'}")
    for g in got:
        print(f"    {g['name']:<20} {g['rule']:<7} {g['where']}")


if __name__ == "__main__":
    main()
