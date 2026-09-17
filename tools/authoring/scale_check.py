#!/usr/bin/env python3
"""Does the prop actually obey its own resize rules when it is resized?

    python3 tools/authoring/scale_check.py                 # the whole tree
    python3 tools/authoring/scale_check.py --only tools/img2threejs-work/v8_arcade_cabinet
    python3 tools/authoring/scale_check.py --verbose

Authoring tool. NOT a build, CI or runtime dependency. Needs the dev server up.

WHY. This is the tool's entire purpose and nothing was checking it. `geometry_
audit` scores the prop against its drawings at ONE size; the judges are shown
three sizes and asked what looks wrong, and CLAUDE.md records what that is worth
-- 181 of 306 blocking faults in one sentence, two judges passing a pinball on
stilts. But "a part marked `fixed` is the same size on a cabinet twice as wide"
is not an opinion. It is arithmetic, it is the promise the whole resize system
makes, and it is exactly the thing a language model cannot see and a bounding
box can.

WHAT IT CHECKS, all off the scene graph rather than off a picture:

  HELD      a part whose rule is `fixed` on an axis must have the SAME world
            extent on that axis at 2x wide and 1.5x tall as at 1x. This is the
            nine-slice promise: a marquee reading ARCADE does not become a
            marquee reading ARCADE stretched.
  GREW      a part whose rule spans an axis must actually get bigger on it. A
            span rule that changes nothing is a rule that did not reach the
            renderer, which is the shape MISTAKES.md calls a signal that
            reaches nothing.
  COUNTED   a `per_bay` part on a prop twice as wide must be placed twice, and
            a `per_tier` part on a prop half again as tall must gain a tier.
            "A bigger one of these should have MORE of this, not a stretched
            one" is the judges' commonest complaint in the whole verdict log,
            and it has an exact answer.
  INSIDE    every part must still be within the body's own box, on every axis,
            at every size. A part that leaves the prop when the prop grows is
            the loudest possible fault and the cheapest to detect.

THE TOLERANCE IS 2%, and it is not fitted: the renderer's own arithmetic rounds
bay counts and repeat counts to integers, so a held part can move by a texel
without anything being wrong. Anything above that is a real change of size.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tools" / "img2threejs-work"
TOL = 0.02
SIZES = {"wide": "w=2", "tall": "h=1.5"}


def probe(d, extra=""):
    q = f"dir=/{d.relative_to(ROOT)}" + (f"&{extra}" if extra else "")
    env = {**os.environ, "CHROMIUM_PATH": os.environ.get(
        "CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")}
    r = subprocess.run(
        ["node", str(ROOT / "tools/authoring/parts_view/probe.mjs"), q],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=300)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stderr or r.stdout or "")[-200:]}


def span(box, axis):
    i = {"x": 0, "y": 1, "z": 2}[axis]
    return box[i + 3] - box[i]


def union(boxes):
    return [min(b[i] for b in boxes) for i in range(3)] + \
           [max(b[i + 3] for b in boxes) for i in range(3)]


def check(d):
    """[(kind, part, message)] for one prop."""
    base = probe(d)
    if "parts" not in base:
        return [("gap", "-", f"1x render failed: {base.get('error')}")]
    out = []
    for name, q in SIZES.items():
        big = probe(d, q)
        if "parts" not in big:
            out.append(("gap", "-", f"{name} render failed: "
                                    f"{big.get('error')}"))
            continue
        axis = "x" if name == "wide" else "y"
        want = 2.0 if name == "wide" else 1.5
        # the body really did grow: if it did not, nothing below means anything
        gb, gs = span(base["body"], axis), span(big["body"], axis)
        if gs < gb * want * (1 - TOL):
            out.append(("gap", "body", f"{name}: the body grew {gs/gb:.3f}x, "
                                       f"not {want}x -- nothing else here is "
                                       f"meaningful"))
            continue
        for part, b in base["parts"].items():
            a = big["parts"].get(part)
            if not a:
                out.append(("gap", part, f"{name}: the part is not placed at "
                                         f"all"))
                continue
            # THE TWO AXES HAVE TWO RULES. `resize` is the x rule and
            # `resize_y` falls back to it; reading `resize` for both called a
            # jukebox's bubbler tubes `fixed` on y while their own rule
            # lengthens them, and reported seven parts growing 2.3x as faults.
            rule = (b.get("resize") if axis == "x"
                    else b.get("resize_y")) or "fixed"
            held = not (rule.startswith("spanx") if axis == "x"
                        else rule.startswith("spany"))
            if axis == "y" and b.get("lengthens"):
                held = False
            # MEASURED AS THE FOOTPRINT ON THE FACE, which is the only one of
            # the three available numbers that answers the question. The world
            # box is axis-aligned, so a part lying in a chamfer reports its
            # DEPTH swung into its width -- 1.19x on a decal that had not
            # changed at all. The built mesh carries the 1/cos cover allowance,
            # which is a property of the surface: v15_arcade_cabinet's control
            # deck reads 1.41x on a prop half again as tall because the profile
            # it lies in got steeper, and a steeper slope IS longer. `drawn` is
            # the footprint before either, straight off the placement.
            i = "xy".index(axis)
            s0 = (b.get("drawn") or [0, 0])[i] or span(b["boxes"][0], axis)
            s1 = (a.get("drawn") or [0, 0])[i] or span(a["boxes"][0], axis)
            k = s1 / max(1e-6, s0)
            if held and k > 1 + TOL:
                out.append(("odd", part, f"{name}: `{rule}` holds on {axis}, "
                                         f"and it grew {k:.2f}x"))
            # A RULE THAT DID NOTHING IS ONLY A FAULT IF IT COULD HAVE DONE
            # SOMETHING. The growth is inserted at particular rows, and a part
            # outside them rides up with the prop rather than growing -- which
            # is the right answer, not a broken rule. v52_jukebox's bubbler tube
            # segments hold their drawn length while the column they belong to
            # doubles, and the render of that prop at 1.5x is correct. `reach`
            # is the part's own drawn extent mapped through gOfT, so 1.0 means
            # the prop's added height never arrived at these rows at all.
            reach = (a.get("reach") if axis == "y" else None)
            if not held and k < 1 + TOL and a["n"] <= b["n"] \
                    and not (reach is not None and reach < 1 + TOL):
                out.append(("odd", part, f"{name}: `{rule}` spans {axis}, and "
                                         f"nothing happened ({k:.2f}x, "
                                         f"{a['n']} placed)"))
            # every instance still ON the prop, with a texel of slack.
            # x AND y ONLY: standing out in z is what relief is, and the first
            # run of this flagged v8_arcade_cabinet's joystick for rising 0.016
            # off the front of the cabinet, which is a joystick.
            bb = big["body"]
            u = union(a["boxes"])
            for i, ax in enumerate("xy"):
                slack = 0.02 * max(1e-6, span(bb, ax))
                if u[i] < bb[i] - slack or u[i + 3] > bb[i + 3] + slack:
                    out.append(("gap", part, f"{name}: hangs off the body on "
                                             f"{ax} ({u[i]:.3f}..{u[i+3]:.3f} "
                                             f"against {bb[i]:.3f}.."
                                             f"{bb[i+3]:.3f})"))
                    break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after this many props")
    args = ap.parse_args()

    props = ([Path(args.only).resolve()] if args.only
             else sorted(p.parent for p in WORK.glob("*/layers_front.json")))
    if args.limit:
        props = props[:args.limit]
    bad = 0
    kinds = {}
    for d in props:
        rows = check(d)
        for _, _, m in rows:
            key = m.split(":")[-1].split("(")[0].strip()[:56]
            kinds[key] = kinds.get(key, 0) + 1
        if rows:
            bad += 1
            print(f"  {d.name}")
            for sev, part, m in rows[:8]:
                print(f"      [{sev}] {part}: {m}")
            if len(rows) > 8:
                print(f"      ... and {len(rows) - 8} more")
        elif args.verbose:
            print(f"  {d.name}  every rule holds")
        sys.stdout.flush()
    print(f"\n{len(props) - bad} of {len(props)} props keep every resize "
          f"promise, {bad} do not")
    if kinds:
        print("\n  by kind:")
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:14]:
            print(f"    {v:4}  {k}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
