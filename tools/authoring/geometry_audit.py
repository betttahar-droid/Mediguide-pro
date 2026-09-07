#!/usr/bin/env python3
"""Measure the model's silhouette against the elevations it was built from.

    python3 tools/authoring/geometry_audit.py work/ps1

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Every geometry fault so far was found by looking: a judge said the screen
was buried, I saw spikes in the wireframe. That finds what is glaring and
misses what is merely wrong, and it cannot say whether a fix helped or how much
is left. The sheet already contains four true elevations of the prop, and the
model claims to BE that prop -- so its outline seen from the front must match
the front elevation's outline, and the same from the side and from above. That
is a number, per axis, and it does not care what anything is called.

WHAT IT CATCHES that the eye does not: the body is extruded from the SIDE
profile alone, so its width is constant at every height. Any prop that tapers,
domes or steps in plan -- a jukebox's crown, a cabinet's plinth -- is too wide
somewhere, and the front view is where that shows as a number even when the
textured render looks convincing.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from identify_parts import object_crop  # noqa: E402
from layer_build import silhouette  # noqa: E402

VIEWS = {                      # name: (query, elevation, mirror the elevation?)
    "front": ("yaw=0&pitch=0", "front", False),
    "side": ("yaw=90&pitch=0", "side", False),
    "top": ("yaw=0&pitch=89.9", "top", False),
}


def shot_silhouette(path):
    """Non-magenta pixels: what the model actually covers."""
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    m = [[False] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            r, g, b = px[x, y]
            m[x][y] = not (r > 200 and b > 200 and g < 90)
    return m, W, H


def tight(mask, W, H):
    xs = [x for x in range(W) if any(mask[x][y] for y in range(H))]
    ys = [y for y in range(H) if any(mask[x][y] for x in range(W))]
    if not xs or not ys:
        return None
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


def compare(model_png, elevation_png, n=160):
    """IoU of the two outlines, each scaled into the same n x n box."""
    mm, W, H = shot_silhouette(model_png)
    b = tight(mm, W, H)
    if b is None:
        return 0.0, 0.0
    im = Image.new("L", (W, H))
    ip = im.load()
    for x in range(W):
        for y in range(H):
            ip[x, y] = 255 if mm[x][y] else 0
    a = im.crop(b).resize((n, n), Image.NEAREST).load()

    ob = object_crop(elevation_png)
    sil = silhouette(ob, erode=0)
    ew, eh = ob.size
    e = Image.new("L", (ew, eh))
    ep = e.load()
    for x in range(ew):
        for y in range(eh):
            ep[x, y] = 255 if sil[x][y] else 0
    e = e.resize((n, n), Image.NEAREST).load()

    inter = union = 0
    for x in range(n):
        for y in range(n):
            p, q = a[x, y] > 127, e[x, y] > 127
            if p or q:
                union += 1
            if p and q:
                inter += 1
    # aspect is compared separately, since the IoU above normalises it away
    ar_model = (b[2] - b[0]) / max(1, b[3] - b[1])
    ar_elev = ew / eh
    return inter / max(1, union), ar_model / max(1e-6, ar_elev)


def measure(d, out, verbose=True):
    """Render the model from three axes and score each against its elevation."""
    import re as _re
    qs = [f"dir=/{d.relative_to(ROOT)}&audit=1&{q}" for q, _, _ in VIEWS.values()]
    env = {**os.environ, "CHROMIUM_PATH": os.environ.get(
        "CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")}
    subprocess.run(["node", str(ROOT / "tools/authoring/parts_view/shoot.mjs"),
                    str(out), *qs], cwd=ROOT, capture_output=True, env=env)
    report = {}
    for (name, (q, elev, _)), qq in zip(VIEWS.items(), qs):
        stem = _re.sub(r"[^a-z0-9]+", "-", qq.replace("/", "-"), flags=_re.I)
        f = out / f"{stem}.png"
        src = d / f"{elev}.png"
        if not f.exists() or not src.exists():
            if verbose:
                print(f"  {name:6} -- no render or no {elev}.png")
            continue
        iou, ar = compare(f, src)
        report[name] = {"iou": round(iou, 4), "aspect_ratio": round(ar, 4)}
        if verbose:
            ok = iou >= 0.90 and 0.9 <= ar <= 1.1
            print(f"  {'OK ' if ok else 'OFF'} {name:6} outline {100*iou:5.1f}%"
                  f"   proportions {ar:.3f}x the elevation's")
    return report


def apply_depth(d, factor):
    """Scale the body's depth, and the profile whose z values carry it."""
    for name in ("body.json", "profile.json"):
        f = d / name
        if not f.exists():
            continue
        j = json.loads(f.read_text())
        if "depth" in j:
            j["depth"] = round(j["depth"] * factor, 5)
        for wall in ("front_wall", "back_wall"):
            if wall in j:
                j[wall] = [[a, round(b * factor, 5)] for a, b in j[wall]]
        f.write_text(json.dumps(j, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fix", action="store_true",
                    help="correct the body depth from what the top view says")
    ap.add_argument("--passes", type=int, default=3)
    args = ap.parse_args()
    d = Path(args.sheet_dir).resolve()
    out = Path(args.out or d / "_audit")
    out.mkdir(parents=True, exist_ok=True)

    print(f"geometry audit: {d.name}")
    report = measure(d, out)

    # THE DEPTH IS A MEASURABLE ERROR, SO CORRECT IT RATHER THAN GUESS.
    # body_faces takes the depth from the side elevation's width and warns when
    # the top view disagrees -- and it disagrees a lot: the footprint came out
    # 18% too deep on the cabinet and 39% on the jukebox, on props whose
    # textured renders look convincing. Neither elevation is privileged; both
    # are drawings of the same object. But the MODEL is the object, so rendering
    # it from above and comparing that plan against the top elevation measures
    # the error directly, and one scalar divides it out.
    # AND THE TWO ELEVATIONS DISAGREE, SO SPLIT THE DIFFERENCE HONESTLY.
    # Correcting the depth until the plan matched the top view made the SIDE
    # view wrong by as much as the top had been -- of course it did: the two
    # drawings of this jukebox imply depths of 0.332 and 0.482, and no single
    # number satisfies both. body_faces already printed that warning and then
    # picked one. Weighting the depth by sqrt(top / side) puts the error where
    # it belongs, half in each view, which is the least wrong a model can be
    # about a prop whose own references do not agree.
    if args.fix:
        for _ in range(args.passes):
            top = (report.get("top") or {}).get("aspect_ratio")
            side = (report.get("side") or {}).get("aspect_ratio") or 1.0
            ar = (top / side) ** 0.5 if top else None
            if not ar or 0.97 <= ar <= 1.03:
                break
            # ar is the model plan's width:depth over the elevation's, so
            # ar > 1 means the model is too SHALLOW for its width and the depth
            # must grow. Dividing instead sent it the other way and the loop
            # diverged, 1.39 to 1.89 to 3.37 -- a correction that makes its own
            # measurement worse is applying itself backwards, and the loop that
            # exposed it is the reason to have one.
            print(f"  top says {top:.3f}, side says {side:.3f} -- "
                  f"splitting the difference, depth x{ar:.3f}")
            apply_depth(d, ar)
            report = measure(d, out)

    (d / "geometry_audit.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
