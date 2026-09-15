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

VIEWS = {                                        # name: (query, elevation)
    "front": ("yaw=0&pitch=0", "front"),
    "side": ("yaw=90&pitch=0", "side"),
    "top": ("yaw=0&pitch=89.9", "top"),
}


def stem_of(q):
    """The filename `shoot.mjs` gives a query. One definition, four callers."""
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "-", q.replace("/", "-"), flags=_re.I)


def shoot(out, qs):
    """Render every query into `out`; return {query: Path} for what arrived.

    IT RETURNS WHAT ARRIVED BECAUSE NOTHING ARRIVING IS THE COMMON FAILURE.
    `shoot.mjs` needs CHROMIUM_PATH and Playwright's own default is not on this
    box, so a caller that forgets it gets a browser-launch traceback on stderr,
    which is captured, and zero PNGs. Three tools had the default inline and two
    did not; in `part_bulge` the empty result came back as an empty list of
    faults and printed "every part earns its place" for every prop. That is
    CLAUDE.md's shape exactly -- a missing artefact degrading into something
    that looks like an answer -- so the launch lives here once and the callers
    are handed the gap instead of a silence.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CHROMIUM_PATH": os.environ.get(
        "CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")}
    subprocess.run(["node", str(ROOT / "tools/authoring/parts_view/shoot.mjs"),
                    str(out), *qs], cwd=ROOT, capture_output=True, env=env)
    got = {}
    for q in qs:
        f = out / f"{stem_of(q)}.png"
        if f.exists():
            got[q] = f
    return got


def flips(d):
    """Which elevations have to be mirrored before they can be compared.

    A DRAWING FACES WHICHEVER WAY THE ARTIST DREW IT, AND THE CAMERA DOES NOT.
    The side render puts the prop's front at screen-left and the top render
    puts it at screen-bottom, always; the sheet's side elevation may well have
    the nose pointing the other way, and this jukebox's does. Comparing the two
    as-drawn puts the chamfer on opposite corners and cost six points of a
    score that is supposed to measure shape -- a metric that fails on a mirror
    is measuring the drawing's handedness, not the model's geometry.
    Which edge is the front is not guessed here: side_profile and top_profile
    each settle it once, and both record the answer.
    """
    out = {"front": (False, False), "side": (False, False), "top": (False, False)}
    try:
        p = json.loads((d / "profile.json").read_text())
        out["side"] = (p.get("front_edge") == "right", False)
    except Exception:
        pass
    try:
        t = json.loads((d / "top_profile.json").read_text())
        out["top"] = (False, t.get("front_edge") == "top")
    except Exception:
        pass
    return out


def reconcile(d):
    """How deep the prop really is, when its own drawings disagree.

    THE THREE ELEVATIONS AGREE WITH EACH OTHER AND THE TOP VIEW DOES NOT. Both
    props measured here have front, side and back drawn to within one pixel of
    the same height -- a genuine turnaround -- while the plan implies a depth
    45% larger than the side elevation on the jukebox and 22% larger on the
    cabinet. Splitting that difference was the previous rule and it is wrong in
    a way that is provable rather than aesthetic.

    A "top view" that is tilted forward by a few degrees shows the prop's front
    FACE as well as its crown, and the apparent depth becomes D*cos + H*sin,
    which is LARGER than D for any tilt in either direction. Tilt can only ever
    add. So of two estimates of the same depth, the smaller is the one closer
    to the truth, and where the other three views vouch for each other by
    sharing a height, the side elevation IS the truth: the top drawing is used
    for the plan's SHAPE, which tilt barely changes, and never for its scale.

    The jukebox's plan is inflated by 45%, which is an 8.6 degree tilt -- an
    error no judge would ever call, and the reason to measure.
    """
    sizes = {}
    for e in ("front", "side", "back", "top"):
        f = d / f"{e}.png"
        if f.exists():
            sizes[e] = object_crop(f).size
    if "front" not in sizes or "side" not in sizes:
        return None
    (W, H), (Ws, Hs) = sizes["front"], sizes["side"]
    hs = [s[1] for k, s in sizes.items() if k != "top"]
    vouched = len(hs) >= 2 and (max(hs) - min(hs)) / max(hs) < 0.02
    d_side = Ws / Hs
    d_top = None
    if "top" in sizes:
        Wt, Ht = sizes["top"]
        d_top = (W / H) / (Wt / Ht)
    depth = d_side if (vouched or not d_top) else min(d_side, d_top)
    return {"depth": round(depth, 5), "from_side": round(d_side, 5),
            "from_top": round(d_top, 5) if d_top else None,
            "elevations_vouch_for_each_other": vouched,
            "plan_inflation": round(d_top / depth, 4) if d_top else 1.0}


def shot_silhouette(path):
    """Non-magenta pixels: what the model actually covers.

    Eroded by one pixel first. The renderer blends the prop's edge against the
    magenta ground, and a blended pixel is not magenta, so every outline came
    back a pixel fat on all four sides -- which showed up as a uniform red rim
    around an otherwise perfect match and cost several points of a score meant
    to detect shape errors. A metric with a bias that size cannot see the fault
    it exists to find.
    """
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    raw = [[False] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            r, g, b = px[x, y]
            raw[x][y] = not (r > 200 and b > 200 and g < 90)
    m = [[False] * H for _ in range(W)]
    for x in range(1, W - 1):
        for y in range(1, H - 1):
            m[x][y] = (raw[x][y] and raw[x - 1][y] and raw[x + 1][y]
                       and raw[x][y - 1] and raw[x][y + 1])
    return m, W, H


def tight(mask, W, H):
    xs = [x for x in range(W) if any(mask[x][y] for y in range(H))]
    ys = [y for y in range(H) if any(mask[x][y] for x in range(W))]
    if not xs or not ys:
        return None
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


def compare(model_png, elevation_png, n=160, flip_x=False, flip_y=False):
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
    if flip_x:
        e = e.transpose(Image.FLIP_LEFT_RIGHT)
    if flip_y:
        e = e.transpose(Image.FLIP_TOP_BOTTOM)
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
    return (inter / max(1, union), ar_model / max(1e-6, ar_elev),
            daylight(a, e, n))


def daylight(a, e, n):
    """Fraction of the drawing the model shows the background THROUGH.

    An IoU is a comparison of two outlines and a hole in the middle of a prop
    barely moves it -- v17_vending_machine had two slits running its full height
    and scored 0.930, which reads as a shape that is slightly wrong rather than
    as a machine you can see through. From the front it is invisible; from the
    side it is the most obvious defect the prop has.

    A hole is not an outline mismatch, so the two are separated here: this
    counts only pixels the DRAWING says are solid, the model renders as
    background, and the model surrounds on both axes. The gap between a
    pinball's legs is drawn as background and is not counted; a slit through a
    vending machine's flank is.

    The cause, in every case found: body_faces cut the flank texture on "is this
    pixel prop-coloured", and a dark trim strip down a machine's side is not.
    Cutting on what is REACHABLE FROM THE EDGE instead took the corpus from six
    props to three. What is left is small and is listed in ROADMAP.
    """
    A = [[a[x, y] > 127 for y in range(n)] for x in range(n)]
    E = [[e[x, y] > 127 for y in range(n)] for x in range(n)]
    rows, cols = [], []
    for y in range(n):
        xs = [x for x in range(n) if A[x][y]]
        rows.append((xs[0], xs[-1]) if xs else None)
    for x in range(n):
        ys = [y for y in range(n) if A[x][y]]
        cols.append((ys[0], ys[-1]) if ys else None)
    hole = tot = 0
    for x in range(n):
        for y in range(n):
            if E[x][y]:
                tot += 1
                if (not A[x][y] and rows[y] and cols[x]
                        and rows[y][0] <= x <= rows[y][1]
                        and cols[x][0] <= y <= cols[x][1]):
                    hole += 1
    return hole / max(1, tot)


def measure(d, out, verbose=True):
    """Render the model from three axes and score each against its elevation."""
    qs = [f"dir=/{d.relative_to(ROOT)}&audit=1&{q}" for q, _ in VIEWS.values()]
    shoot(out, qs)
    fl = flips(d)
    rec = reconcile(d)
    # the plan drawing over-reports depth by a known factor, so its proportion
    # score is compared against what the drawing WOULD say if it were flat
    inflate = {"top": (rec or {}).get("plan_inflation", 1.0)}
    report = {}
    for (name, (q, elev)), qq in zip(VIEWS.items(), qs):
        f = out / f"{stem_of(qq)}.png"
        src = d / f"{elev}.png"
        if not f.exists() or not src.exists():
            if verbose:
                print(f"  {name:6} -- no render or no {elev}.png")
            continue
        iou, raw, day = compare(f, src, flip_x=fl[name][0], flip_y=fl[name][1])
        ar = raw / inflate.get(name, 1.0)
        report[name] = {"iou": round(iou, 4), "aspect_ratio": round(ar, 4),
                        "aspect_ratio_raw": round(raw, 4),
                        "daylight": round(day, 4)}
        if verbose:
            ok = iou >= 0.90 and 0.9 <= ar <= 1.1 and day < 0.004
            tilt = ("" if abs(inflate.get(name, 1.0) - 1) < 0.02 else
                    f"  [drawing tilted, x{inflate[name]:.2f}]")
            hole = "" if day < 0.004 else \
                f"   HOLES: {100*day:.1f}% of the prop is see-through"
            print(f"  {'OK ' if ok else 'OFF'} {name:6} outline {100*iou:5.1f}%"
                  f"   proportions {ar:.3f}x the elevation's{tilt}{hole}")
    # AND SAY WHETHER THE BODY HAS A PLAN AT ALL, because not having one is a
    # silent downgrade that this audit is otherwise the only thing positioned
    # to notice.
    #
    # The renderer shapes the footprint from top_profile.json and falls back to
    # a plain RECTANGLE when there is none -- quietly, because a rectangular
    # plan is a perfectly valid body and nothing about it looks broken from the
    # front. Every prop in the work tree was in that state: 100 of 100 had a
    # top.png and 0 had a top_profile.json, so every one was built with square
    # corners while its own plan drawing showed them chamfered. Building the
    # plans took the top outline from a median of 0.963 to 0.976, its worst from
    # 0.876 to 0.902, and the props below 0.95 from 22 to 15 -- 66 better, 10
    # worse. Nothing in the pipeline had said a word.
    plan = d / "top_profile.json"
    report["_plan"] = plan.exists()
    if verbose and not plan.exists():
        print(f"  !  no top_profile.json -- the body's footprint is a plain "
              f"RECTANGLE. Run top_profile.py; it is worth about +0.013 median "
              f"on the top outline and much more on a chamfered prop.")
    # AND THE SIDE WALLS, which is the same silence one step worse: with no
    # profile.json the renderer does not loft at all, it builds a BoxGeometry at
    # a default depth. The two props in the tree that were missing one had the
    # two worst side outlines in the corpus by a wide margin, 0.763 and 0.794
    # against a median of 0.979, and nothing anywhere said why.
    side = d / "profile.json"
    report["_side_profile"] = side.exists()
    if verbose and not side.exists():
        print(f"  !  no profile.json -- the body is a plain BOX at a default "
              f"depth, not a loft. Run side_profile.py.")
    report["_reconciled"] = rec
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
                    help="set the body depth to what the true elevations say")
    ap.add_argument("--split", action="store_true",
                    help="the old rule: average the side and the plan")
    ap.add_argument("--passes", type=int, default=3)
    args = ap.parse_args()
    d = Path(args.sheet_dir).resolve()
    out = Path(args.out or d / "_audit")
    out.mkdir(parents=True, exist_ok=True)

    print(f"geometry audit: {d.name}")
    report = measure(d, out)

    # THE DEPTH IS A MEASURABLE ERROR, SO CORRECT IT RATHER THAN GUESS.  # noqa
    # WHICH DRAWING TO BELIEVE IS ITSELF MEASURABLE, so it is no longer split.
    # See reconcile(): front, side and back are drawn to the same height and
    # vouch for each other; a tilted plan can only ever over-report depth. The
    # old rule averaged a true measurement with an inflated one and landed the
    # jukebox 19% too deep, which the side view then reported as a fault the
    # loop could not fix, because it was the loop that caused it.
    if args.fix:
        rec = reconcile(d)
        cur = None
        for name in ("profile.json", "body.json"):
            f = d / name
            if f.exists():
                cur = json.loads(f.read_text()).get("depth", cur)
        if rec and cur:
            k = rec["depth"] / cur
            print(f"  side says depth {rec['from_side']}, plan says "
                  f"{rec['from_top']} -- the elevations vouch for each other"
                  f" ({rec['elevations_vouch_for_each_other']}), so x{k:.3f}")
            if abs(k - 1) > 0.01:
                apply_depth(d, k)
                report = measure(d, out)

    # THE OLD SPLIT, KEPT BEHIND --split FOR A SHEET WITH NO USABLE PLAN.
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
    if args.split:
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

    # SAY IT LOUDLY WHEN NOTHING WAS MEASURED. This printed three quiet "no
    # render" lines and carried on, and that is how a build-order bug hid for
    # weeks: the renderer needs layers_front.json and the pipeline had not cut
    # the layers yet, so on every prop built from scratch the one measurement
    # that can say whether the geometry is right was silently skipped.
    if not [k for k in report if not k.startswith("_")]:
        print("  ! measured NOTHING -- the model did not render. The geometry "
              "is unchecked, not correct.")
    (d / "geometry_audit.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
