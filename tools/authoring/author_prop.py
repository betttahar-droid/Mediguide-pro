#!/usr/bin/env python3
"""Author a prop as a PART LIST and refine it by looking at the render.

    npx vite --port 5173 &
    python3 tools/authoring/author_prop.py "arcade cabinet" --rounds 2

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS EXISTS, AND WHY IT IS NOT auto_prop.py.

auto_prop.py reconstructs: Nano Banana draws elevations, voxel_carve intersects
their silhouettes, something fits parts to the result. Measured, that path
costs more than it returns:

  - shape-from-silhouette cannot represent a recess in a face (11.7% phantom on
    a modest one) and collapses an open shelf into a near-solid block (55.8%
    IoU, 79.2% phantom). No better view lifts either; they are properties of
    the visual hull.
  - a generated "front elevation" came back three-quarter, and the carver took
    its width from that frame -- a grid 2.81x too wide. b8a7f61 gates it now,
    but the gate exists to survive the reconstruction, not because anyone
    wanted it.
  - the output is not a module. The arcade carve is 3620 boxes and 40296
    triangles using 0 of 41 material families, with no sockets, no 9-slice
    margins and no repeat axes -- none of which is recoverable from occupancy,
    because none of it is in the silhouettes.

The deliverable is about thirty boxes. vaccineFridge.js is 34 hand-written
ones. So write the thirty boxes: GLM 5.3 authors the part list against the
palette and the grid, glm-5.3-flash looks at the render and names what is
wrong with it, and GLM 5.3 rewrites. The same arcade cabinet comes out in 23
named parts and 276 triangles -- 146x less geometry than the carve, in the
project's own palette, with flat faces and no unpainted black.

The reference image is not gone; its job changes. It stops being the thing we
reconstruct from and becomes the thing we are judged against, which is what
Nano Banana is actually good for.

THE VIEWER ALREADY EATS THIS SCHEMA. main.js ?carved= takes {grid, boxes[]},
so a part list renders with no bridge. src/modules/fromSculptSpec.js is the
route on from here -- it turns a part spec into buildParts output with the
material strips, accent slots and 9-slice attributes a real module needs.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import (glm, as_json, data_uri, _openrouter_key,  # noqa: E402
                       AUTHOR_MODEL, CRITIC_MODEL)

# src/art/palette.js is the single source of truth (S4.4 forbids hex literals
# outside it). Mirrored here because this tool writes JSON, not JS.
PALETTE = {
    "paper": "#f9efdc", "bone": "#ecdcc0", "putty": "#d3c3a4",
    "oak": "#dda265", "oakDark": "#b0763e", "walnut": "#6b4426",
    "mint": "#9ad9b8", "teal": "#57a98d", "tealDeep": "#24544a",
    "signal": "#f5804f", "steel": "#b0bcbd", "steelDark": "#68777c",
    "glass": "#d2e8e4", "charcoal": "#39424a", "espresso": "#4a3626",
}

GRID_RULES = """\
COORDINATES. Integer voxel grid [width X, depth Y, height Z]. Z is UP and z=0
is the floor. Each box is {"min": [x,y,z], "max": [x,y,z]}, half-open, so max
is exclusive and every max must exceed its min. Stay inside the grid. X is
left-right seen from the front; Y is front-to-back with y=0 the FRONT face.

RULES.
- 22 to 40 boxes. This is a part list, not a voxel dump: one box per part.
- Every part carries a short "name" saying what it is.
- Parts touch or overlap their neighbours. Nothing floats, nothing hangs in
  mid-air with nothing under it.
- Build the SILHOUETTE first (body, plinth, top), then what sits on or in it.
  A feature that reads at a distance is worth more than one that does not.
- Recesses and openings are encouraged: leave a gap rather than filling solid."""


def validate(spec):
    """Reject a box before it reaches the renderer, and say why."""
    W, D, H = spec["grid"]
    good, bad = [], []
    for b in spec.get("boxes", []):
        mn, mx, name = b.get("min"), b.get("max"), b.get("name", "?")
        if not (isinstance(mn, list) and isinstance(mx, list)
                and len(mn) == 3 and len(mx) == 3):
            bad.append(f"{name}: min/max not [x,y,z]")
            continue
        if any(mx[i] <= mn[i] for i in range(3)):
            bad.append(f"{name}: max <= min {mn}->{mx}")
            continue
        if any(mn[i] < 0 for i in range(3)) or mx[0] > W or mx[1] > D or mx[2] > H:
            bad.append(f"{name}: outside grid {mn}->{mx}")
            continue
        hexv = b.get("hex")
        if isinstance(hexv, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", hexv or ""):
            colour, tag = hexv.lower(), hexv.lower()
        elif b.get("palette") in PALETTE:
            colour, tag = PALETTE[b["palette"]], b["palette"]
        else:
            bad.append(f"{name}: no usable colour "
                       f"(palette={b.get('palette')!r} hex={hexv!r})")
            continue
        good.append({"min": mn, "max": mx, "colour": colour,
                     "name": name, "palette": tag})
    return good, bad


def author_from_reference(asset, grid, ref, key):
    """Extrude a MEASURED reference into 3D. No pixels reach the model.

    The front elevation supplies x and z for every part and its colour; the
    side supplies y as a depth-per-height profile. That is the whole geometry
    problem stated in numbers, which is the form S14.0 permits -- the objection
    was ever to reading proportions OFF an image, not to measuring one.
    """
    rects, prof, palette = ref["regions"], ref["profile"], ref["palette"]
    ask = f"""Build a 3D part list for a low-poly "{asset}" on a {grid} voxel grid.

You are given the object's own FRONT ELEVATION, already measured into coloured
rectangles, and its DEPTH PROFILE measured from the side. Do not invent
proportions -- these ARE the proportions. Your job is to give each rectangle a
depth and assemble them.

FRONT RECTANGLES. x and z are fractions of the object's own bounding box,
x left-to-right, z up from the floor. Colour is the reference's own.
{json.dumps(rects, indent=1)}

DEPTH PROFILE from the side, floor first. y is a fraction of the object's
depth, y=0 the front face. Where the profile narrows, the object is stepped --
a control panel shelf, a recessed base, a leaning screen.
{json.dumps(prof, indent=1)}

PALETTE. Use ONLY these hex values, which are the reference's own colours:
{json.dumps(palette, indent=1)}

HOW TO BUILD IT.
- Convert each fraction to a voxel index: x_voxels = round(x * W), and so on
  for z with H and y with D. Round, do not guess.
- Every front rectangle becomes at least one box, keeping its x, z and colour.
- Choose each box's y extent from the depth profile at that height. A part
  that reads as surface detail (a trim strip, a screen, a button) is shallow
  and sits at the FRONT, y starting at 0. The body is deep.
- Add the parts the front cannot show -- a back panel, a top cap -- using the
  profile for their depth.
- Merge rectangles that are obviously one part; drop ones that are outline
  fragments. Aim for 22 to 40 boxes.

{GRID_RULES}

Reply with JSON only: {{"grid": [W,D,H], "boxes": [{{"name","min","max","hex"}}]}}
where "hex" is one of the palette values above."""
    return as_json(glm([{"role": "user", "content": ask}], AUTHOR_MODEL, key,
                       max_tokens=30000))


def author(asset, grid, key, faults=None, previous=None):
    if faults is None:
        ask = (f'Author a low-poly prop as a PART LIST of axis-aligned boxes: "{asset}".\n\n'
               f'The grid is {grid}.\n\n{GRID_RULES}\n\n'
               f'PALETTE. Use ONLY these names; no hex, no other colours:\n'
               f'{json.dumps(PALETTE, indent=1)}\n\n'
               'Reply with JSON only: {"grid": [W,D,H], "boxes": '
               '[{"name": "...", "min": [x,y,z], "max": [x,y,z], "palette": "..."}]}')
    else:
        ask = (f'Here is a part list for a low-poly "{asset}" on a {grid} grid '
               f'(z up, z=0 floor, y=0 front, max exclusive):\n\n'
               f'{json.dumps(previous, indent=1)}\n\n'
               f'A reviewer looking at the render reported these faults:\n'
               f'{json.dumps(faults, indent=1)}\n\n'
               'Rewrite the part list to fix them. Keep what already works. You may '
               f'add, remove, move or resize parts.\n\n{GRID_RULES}\n\n'
               f'PALETTE names only, from: {list(PALETTE)}\n\n'
               'Reply with JSON only: {"grid": [W,D,H], "boxes": '
               '[{"name","min","max","palette"}]}')
    return as_json(glm([{"role": "user", "content": ask}], AUTHOR_MODEL, key,
                       max_tokens=30000))


def critique(asset, boxes, shot, key):
    names = ", ".join(b["name"] for b in boxes)
    content = [{"type": "text", "text": f"""This is a render of a low-poly "{asset}" built from a
part list of {len(boxes)} axis-aligned boxes: {names}.

Name what is WRONG with it as an "{asset}" -- a part missing, a part the wrong
size or in the wrong place, a proportion that reads badly, a colour that fights
the object. Say WHICH named part and WHAT to change. Do not give measurements.

Reply with JSON only:
{{"faults": [{{"part": "...", "fault": "...", "fix": "..."}}], "verdict": "..."}}"""},
               {"type": "image_url", "image_url": {"url": data_uri(shot)}}]
    return as_json(glm([{"role": "user", "content": content}], CRITIC_MODEL, key,
                       max_tokens=16000))


def render(spec_path, out_dir, port):
    """shoot.mjs against the running dev server. Returns the iso shot."""
    rel = "/" + str(spec_path.relative_to(ROOT))
    q = f"carved={rel}&view=iso"
    subprocess.run(
        ["node", str(ROOT / "tools" / "voxel-fridge" / "shoot.mjs"), str(out_dir), q],
        cwd=ROOT, check=False,
        env={**__import__("os").environ,
             "CHROMIUM_PATH": __import__("os").environ.get(
                 "CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")})
    shots = sorted(out_dir.glob("*iso*.png"))
    return shots[0] if shots else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset")
    ap.add_argument("--grid", default="40 x 46 x 96")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--port", type=int, default=5173)
    ap.add_argument("--reference", default=None,
                    help="directory holding front.png and side.png to measure "
                         "and extrude, instead of authoring from the noun alone")
    args = ap.parse_args()

    out = Path(args.out or (ROOT / "tools" / "img2threejs-work" /
                            ("authored_" + re.sub(r"\W+", "_", args.asset.lower()))))
    out.mkdir(parents=True, exist_ok=True)
    key = _openrouter_key()

    ref = None
    if args.reference:
        from reference_regions import regions, depth_profile
        rd = Path(args.reference)
        rects, _, _ = regions(rd / "front.png")
        rects = [r for r in rects if r["fill"] >= 0.80]
        prof = depth_profile(rd / "side.png")
        pal = sorted({r["colour"] for r in rects})
        ref = {"regions": rects, "profile": prof, "palette": pal}
        print(f"reference: {len(rects)} rectangles, {len(prof)} depth bands, "
              f"{len(pal)} colours {pal}")

    spec, faults, prev = None, None, None
    for rnd in range(args.rounds):
        print(f"\n=== round {rnd}: {AUTHOR_MODEL} authoring ===", flush=True)
        if ref is not None and faults is None:
            spec = author_from_reference(args.asset, args.grid, ref, key)
        else:
            spec = author(args.asset, args.grid, key, faults, prev)
        boxes, bad = validate(spec)
        print(f"  {len(spec.get('boxes', []))} boxes -> {len(boxes)} valid")
        for m in bad:
            print("  REJECT", m)
        if not boxes:
            raise SystemExit("nothing valid to render")
        print("  parts:", ", ".join(b["name"] for b in boxes))

        spec_path = ROOT / "tools" / "voxel-fridge" / f"_authored_r{rnd}.json"
        spec_path.write_text(json.dumps(
            {"grid": spec["grid"],
             "boxes": [{"min": b["min"], "max": b["max"], "colour": b["colour"]}
                       for b in boxes]}, indent=1))
        (out / f"parts_r{rnd}.json").write_text(json.dumps(
            {"grid": spec["grid"], "boxes": boxes}, indent=1))

        shot = render(spec_path, out / f"r{rnd}", args.port)
        if not shot:
            print("  no render -- is the dev server up? npx vite --port 5173 &")
            break
        print(f"  rendered {shot}")

        if rnd == args.rounds - 1:
            break
        print(f"  {CRITIC_MODEL} reviewing ...", flush=True)
        crit = critique(args.asset, boxes, shot, key)
        faults = crit.get("faults", [])
        prev = [{k: b[k] for k in ("name", "min", "max", "palette")} for b in boxes]
        for f in faults:
            print(f"    {f.get('part')}: {f.get('fault')}")
        print(f"    verdict: {crit.get('verdict')}")

    print(f"\nwrote {out}/")


if __name__ == "__main__":
    main()
