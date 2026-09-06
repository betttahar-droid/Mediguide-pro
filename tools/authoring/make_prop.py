#!/usr/bin/env python3
"""One noun in, a resizable textured prop out. No human in the loop.

    npx vite --port 5173 &
    python3 tools/authoring/make_prop.py "arcade cabinet" --rounds 4

Authoring tool. NOT a build, CI or runtime dependency.

THE WHOLE CHAIN, and who does what:

    Nano Banana 2   one turnaround sheet, four true elevations in one pass
    arithmetic      split it, crop the captions off, measure the object boxes
    glm-5.3-flash   name the parts and say how each resizes
    arithmetic      snap the boxes, cut the parts, fill the background,
                    measure the stretch bands
    the renderer    background nine-sliced with its middle REPEATED, parts
                    anchored at real size
    glm-5.3-flash   look at the result and say what is wrong with it
    the loop        apply the judge's corrections and go round again

THE JUDGE RETURNS A PATCH, NOT PROSE. That is the difference between a
critique and a loop. Told "the marquee is stretched", nothing can act; told
{"name":"marquee","resize":"spanx_center"}, the tool rebuilds and re-renders.
The patch schema is deliberately narrow -- a resize rule, an anchor, or a
part dropped -- so a judge cannot invent geometry, only reclassify what
measurement already found.

Every fix in the loop is one the tool applies. Nothing here is hand-tuned per
prop; the same run makes a cabinet, a vending machine or a jukebox.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL  # noqa: E402

RESIZES = {"fixed", "spanx_repeat", "spanx_center", "spany_repeat", "spany_center"}
ANCHORS = {"top", "bottom", "left", "right", "center"}

JUDGE = """IMAGE 1 is the reference front elevation of a {asset}.
IMAGE 2 is the 3D model at its ORIGINAL size -- it should match image 1 closely.
IMAGE 3 is the same model made TWICE AS WIDE, and IMAGE 4 twice as tall. Those
two SHOULD be bigger; judge only whether they still look like a well-made
{asset}, not whether they differ in size.

The model is built as a background panel plus these parts, each with a resize
rule:
{parts}

The BACKGROUND panel behind the parts is also adjustable. If its texture looks
smeared, streaked or banded where the prop was made larger, patch the name
"background" with "mode": "mirror" (every other repeat is flipped, so joins
reflect instead of cutting) or "repeat" (plain tiling).

Rules available:
  "fixed"         keeps its real size and stays put
  "spanx_repeat"  runs the full width; its middle REPEATS when widened
                  (right for a control deck: a wider cabinet gets more
                  button clusters)
  "spanx_center"  runs the full width; its middle stays ONE size in the centre
                  and the ends extend (right for a marquee: you want one
                  title, not three)
  "spany_repeat" / "spany_center"  the same for the vertical axis

Report what looks wrong, then give a PATCH: only parts whose rule or anchor
should change, or that should be dropped because they are not really a part.
Change nothing that already looks right. If all three images look like a
well-made {asset}, set looks_good true and return an empty patch.

JSON only:
{{"looks_good": false,
  "faults": [{{"part": "...", "fault": "..."}}],
  "patch": [{{"name": "...", "resize": "...", "anchor": "...", "drop": false}}]}}"""


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("  ! " + (r.stderr or r.stdout).strip().splitlines()[-1][:160])
    return r


def render(d, out, sizes):
    qs = [f"dir=/{d.relative_to(ROOT)}&w={w}&h={h}" for (w, h) in sizes]
    run(["node", str(ROOT / "tools/authoring/layer_view/shoot.mjs"), str(out), *qs],
        env={**__import__("os").environ,
             "CHROMIUM_PATH": __import__("os").environ.get(
                 "CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")})
    got = []
    for (w, h) in sizes:
        m = sorted(out.glob(f"*w-{str(w).replace('.','-')}-h-{str(h).replace('.','-')}*.png"))
        got.append(m[0] if m else None)
    return got


def rebuild(d, face="front"):
    run([sys.executable, "tools/authoring/layer_build.py", str(d), "--face", face])
    run([sys.executable, "tools/authoring/nine_slice.py", str(d / f"bg_{face}.png"),
         "--out", str(d / "slice_bg.json")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-sheet", action="store_true")
    args = ap.parse_args()

    import re
    d = Path(args.out or ROOT / "tools/img2threejs-work" /
             ("prop_" + re.sub(r"\W+", "_", args.asset.lower())))
    d.mkdir(parents=True, exist_ok=True)
    key = _openrouter_key()
    print(f"=== {args.asset} -> {d} ===")

    if not args.skip_sheet:
        print("[1] turnaround sheet ...", flush=True)
        r = run([sys.executable, "tools/authoring/ps1_sheet.py", args.asset, "--out", str(d)])
        print("   ", (r.stdout or "").strip().splitlines()[-1][:120] if r.stdout else "")
    if not (d / "front.png").exists():
        raise SystemExit("no front.png -- the sheet did not split into views")

    print("[2] naming parts ...", flush=True)
    r = run([sys.executable, "tools/authoring/identify_parts.py", str(d), "--face", "front"])
    if not (d / "parts_front.json").exists():
        raise SystemExit("identify_parts produced nothing")
    print("   ", (r.stdout or "").strip().splitlines()[0][:120])

    rebuild(d)
    best = None
    for rnd in range(args.rounds):
        shots = render(d, d / f"r{rnd}", [(1, 1), (2, 1), (1, 1.8)])
        if not all(shots):
            raise SystemExit("render failed -- is the dev server up on 5173?")
        man = json.loads((d / "layers_front.json").read_text())
        listing = "\n".join(f"  {p['name']}: {p['resize']}, anchored {p['anchor']}"
                            for p in man["parts"])
        content = [{"type": "text",
                    "text": JUDGE.format(asset=args.asset, parts=listing)}]
        for img in [d / "front.png", *shots]:
            content.append({"type": "image_url",
                            "image_url": {"url": data_uri(img)}})
        try:
            v = as_json(glm([{"role": "user", "content": content}], CRITIC_MODEL,
                            key, max_tokens=14000))
        except SystemExit as e:
            print(f"  round {rnd}: judge failed -- {str(e)[:100]}")
            break

        faults = v.get("faults", [])
        print(f"\n  round {rnd}: looks_good={v.get('looks_good')}  "
              f"{len(faults)} faults, {len(v.get('patch', []))} corrections")
        for f in faults[:6]:
            print(f"    - {f.get('part')}: {f.get('fault')}")
        if best is None or len(faults) < best[0]:
            best = (len(faults), rnd)
        if v.get("looks_good"):
            print("  JUDGE PASSED")
            break

        # apply the patch -- narrow schema, so a judge can only reclassify
        patch = {p.get("name"): p for p in v.get("patch", []) if p.get("name")}
        # the background is not a part but it IS adjustable; without this the
        # judge's commonest complaint had no lever and the loop stalled on
        # round 0 reporting "no actionable corrections"
        man_path = d / "layers_front.json"
        for key_name in ("background", "background_panel", "panel", "body"):
            q = patch.pop(key_name, None)
            if q and q.get("mode") in ("mirror", "repeat"):
                mm = json.loads(man_path.read_text())
                if mm.get("background_mode") != q["mode"]:
                    mm["background_mode"] = q["mode"]
                    man_path.write_text(json.dumps(mm, indent=1))
                    print(f"    background: mode -> {q['mode']}")
        pm = json.loads((d / "parts_front.json").read_text())
        keep, changed = [], 0
        bg_changed = json.loads(man_path.read_text()).get("background_mode")
        for p in pm["parts"]:
            q = patch.get(p["name"])
            if q and q.get("drop"):
                print(f"    dropped {p['name']}")
                changed += 1
                continue
            if q and q.get("resize") in RESIZES and q["resize"] != p["resize"]:
                print(f"    {p['name']}: {p['resize']} -> {q['resize']}")
                p["resize"] = q["resize"]
                changed += 1
            if q and q.get("anchor") in ANCHORS and q["anchor"] != p["anchor"]:
                print(f"    {p['name']}: anchor {p['anchor']} -> {q['anchor']}")
                p["anchor"] = q["anchor"]
                changed += 1
            keep.append(p)
        if not changed and not bg_changed:
            print("  no actionable corrections -- stopping")
            break
        pm["parts"] = keep
        (d / "parts_front.json").write_text(json.dumps(pm, indent=1))
        rebuild(d)

    print(f"\ndone: {d}")


if __name__ == "__main__":
    main()
