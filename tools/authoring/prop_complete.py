#!/usr/bin/env python3
"""Is this prop actually finished, or does it just render?

    python3 tools/authoring/prop_complete.py                 # the whole tree
    python3 tools/authoring/prop_complete.py --only work/ps1
    python3 tools/authoring/prop_complete.py --verbose

Authoring tool. NOT a build, CI or runtime dependency. Needs no renders.

WHY. Three separate faults in one session were the same fault: an artefact the
renderer wants was missing, and the fallback looked like a body rather than like
a bug.

  - 100 of 100 props had no `top_profile.json`, so every one was built with a
    rectangular footprint while its own plan drawing showed chamfered corners.
    Building them moved the top outline from a median of 0.963 to 0.976.
  - 2 props had no `profile.json` at all, so they were not lofted -- they were
    BoxGeometry at a default depth. They were the two worst side outlines in the
    corpus by a wide margin, 0.763 and 0.794, and nothing said why.
  - Several `tall_body.json` bands were drawn for a fraction of the growth they
    are rendered at, so the drawn body stretched up to four times over.

None of these is a wrong number. Each is a file that is absent or short, and in
every case the renderer did something reasonable instead of complaining. That is
the right behaviour for a renderer and the wrong behaviour for a pipeline, so
the complaining belongs here.

WHAT IT DOES NOT DO is judge quality. A prop can pass every check here and still
look wrong; `geometry_audit` and the judges are for that. This only answers "has
every step that was supposed to run, run, and does what it wrote still match
what everything else wrote" -- which is the question that had no owner.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tools" / "img2threejs-work"


def check(d, face="front"):
    """[(severity, message)] for one prop. severity: 'gap' | 'odd'."""
    out = []

    def j(name):
        try:
            return json.loads((d / name).read_text())
        except Exception:
            return None

    layers = j(f"layers_{face}.json")
    if layers is None:
        return [("gap", "no layers_front.json -- nothing is built")]

    # --- the three profiles the body is lofted from -------------------------
    if not (d / "profile.json").exists():
        out.append(("gap", "no profile.json: the body is a BOX at a default "
                           "depth, not a loft (side_profile.py)"))
    if not (d / f"front_profile_{face}.json").exists():
        out.append(("gap", "no front_profile: the body is the same width at "
                           "every height (front_profile.py)"))
    if not (d / "top_profile.json").exists():
        out.append(("gap", "no top_profile: the footprint is a plain rectangle "
                           "(top_profile.py)"))

    # --- every part's texture is on disk ------------------------------------
    missing = [p["name"] for p in layers.get("parts", [])
               if p.get("image") and not (d / p["image"]).exists()]
    if missing:
        out.append(("gap", f"{len(missing)} part texture(s) missing: "
                           f"{', '.join(missing[:4])}"))
    bg = layers.get("background")
    if bg and not (d / bg).exists():
        out.append(("gap", f"the background {bg} is missing"))

    # --- the frames all agree ------------------------------------------------
    # A size mismatch here is the quiet kind: every box in parts_front is in the
    # elevation's pixels, and a background written at another size silently puts
    # every part in the wrong place.
    parts = j(f"parts_{face}.json")
    if parts and layers.get("size") and parts.get("size") \
            and list(parts["size"]) != list(layers["size"]):
        out.append(("gap", f"parts_{face} is {parts['size']} and layers_{face} "
                           f"is {layers['size']} -- different frames"))

    # --- a drawn tall body has to cover the ratio it is used at --------------
    tb = j("tall_body.json")
    if tb:
        try:
            covers = tb["size"][1] / tb["drawn_size"][1]
            if covers * 1.02 < tb["ratio"]:
                out.append(("gap", f"tall_body covers {covers:.3f}x but the "
                                   f"prop is scaled to {tb['ratio']}x -- the "
                                   f"renderer will refuse it (tall_body.py)"))
            for f in tb.get("flanks", []):
                if f.get("image") and not (d / f["image"]).exists():
                    out.append(("gap", f"tall {f['face']} {f['image']} missing"))
        except Exception:
            out.append(("odd", "tall_body.json is malformed"))

    # --- a bought wider part has to be on disk ------------------------------
    wa = j("wide_art.json")
    for p in (wa or {}).get("parts", []):
        if p.get("status") == "kept" and not (d / "parts_wide" /
                                              f"{p['part']}.png").exists():
            out.append(("gap", f"wide_art kept {p['part']} but its drawing is "
                               f"not on disk"))

    # --- the other faces ----------------------------------------------------
    body = j("body.json")
    for f in ("side", "back", "top"):
        info = (body or {}).get(f)
        if info and info.get("image") and not (d / info["image"]).exists():
            out.append(("gap", f"body.json names {info['image']} and it is "
                               f"not there"))
    if body is None:
        out.append(("odd", "no body.json: the flanks have no texture"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--face", default="front")
    ap.add_argument("--verbose", action="store_true",
                    help="list every prop, not only the ones with gaps")
    args = ap.parse_args()

    props = ([Path(args.only).resolve()] if args.only
             else sorted(p.parent for p in WORK.glob(f"*/layers_{args.face}.json")))
    bad = 0
    counts = {}
    for d in props:
        rows = check(d, args.face)
        for _, m in rows:
            counts[m.split(":")[0].split("--")[0].strip()] = \
                counts.get(m.split(":")[0].split("--")[0].strip(), 0) + 1
        if rows:
            bad += 1
            print(f"  {d.name}")
            for sev, m in rows:
                print(f"      [{sev}] {m}")
        elif args.verbose:
            print(f"  {d.name}  complete")
    print(f"\n{len(props) - bad} of {len(props)} props complete, {bad} with gaps")
    if counts:
        print("\n  by kind:")
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"    {v:3}  {k}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
