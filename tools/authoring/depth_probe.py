#!/usr/bin/env python3
"""Measure how far a feature is recessed or proud, from the SIDE elevation.

    python3 tools/authoring/depth_probe.py work/ps1
    python3 tools/authoring/depth_probe.py --sweep

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Every opening and every recess in this repo rests on one of four
adjectives -- flush, proud, deep, recessed -- chosen by a model and mapped to
four constants in the renderer. Nothing measures depth anywhere, so a window
that must be a recess and a window painted on a flat panel are
indistinguishable to every check, and NO PROP CAN REACH ACCEPTED on a feature
whose role requires an opening. 291 thicknesses across the corpus are in that
state.

The side elevation is where the evidence is. `profile.json`'s front_wall gives
the body's front surface as a function of height, measured off the drawing by
side_profile.py, and where a band of rows steps BACK the body is recessed
there; where it steps forward it stands proud. That is not an inference about
shading, it is the reference's own geometry.

WHAT IT CAN AND CANNOT SEE, which decides everything below.

A step in the front wall measures the BODY'S SURFACE at those rows. If a
feature occupies substantially the whole band over which the step happens,
that step is the feature's own recess and can be read as its thickness. If a
small feature merely sits inside a larger step -- a decal on a cabinet's
sloped bezel -- the step is the body's shape and says nothing about the decal.
Conflating the two would put a measured-looking number on a guess, which is
the exact failure this file exists to end.

So the rule is containment, and it is strict: the feature must cover most of
the stepped band, and the band must not extend far beyond the feature. Roughly
a third of features qualify; the rest stay ABSENT and therefore UNVERIFIED,
which is the honest answer and not a gap to be filled.

TRIED AND REVERTED: READING DEPTH FROM EDGE SHADING. A recess drawn by hand
has a dark inner edge on the side the light comes from and a light one
opposite, so the asymmetry between the top and bottom borders should separate
recessed from proud. Measured across the corpus against the existing depth
labels, it does not separate them at all:

    label      n   median   mean    p25    p75
    recessed 384     9.64   8.64 -16.31  36.63
    flush    468     8.08  12.93 -12.77  33.38
    proud    422     8.92   9.26 -15.37  39.65
    deep      50    20.51  22.50   0.59  45.54

Three of the four medians sit within a point and a half of each other with the
interquartile ranges completely overlapping. Either PS1-era flat shading does
not draw a consistent recess shadow, or the labels are themselves a model's
guess and cannot serve as ground truth -- and both readings forbid using it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_intent import MEASURED, ABSENT  # noqa: E402

# How much of the stepped band the feature must own before the step is read as
# ITS depth rather than the body's shape. Both directions matter: a feature
# covering a tenth of a long step is sitting on the body, and a feature ten
# times the length of the step has a step somewhere inside it that is not its
# own boundary.
COVER = 0.60          # of the feature's rows that must lie in the step
SPILL = 1.8           # the step may be at most this many times the feature


def raw_front_wall(prop_dir):
    """The front surface per row, measured off side.png at full resolution.

    NOT profile.json. That file is a SIMPLIFIED polyline -- median 11 points
    across a whole prop, one example reduced to six -- because it exists to
    loft a body, and simplification is the right thing for that. It is the
    wrong thing here: the corner-finding has already thrown away exactly the
    small steps a recess consists of. Probing it scored 1.0% MEASURED with
    1497 of 1665 features reporting "too few samples", which is a statement
    about the polyline and not about the prop.

    The side elevation itself still has them: on this vending machine the
    front edge moves through 75 pixels of a 232-pixel-wide view, a third of
    the body's depth. Read the silhouette's frontmost pixel per row and the
    resolution is the drawing's own.

    Returns (wall, depth_px) with wall[i] the depth at height i/(n-1) from the
    bottom, measured inward from the frontmost point of the whole prop.
    """
    d = Path(prop_dir)
    try:
        import json as _json
        pro = _json.loads((d / "profile.json").read_text())
        front_right = str(pro.get("front_edge", "right")) == "right"
    except Exception:
        front_right = True
    try:
        from identify_parts import object_crop
        from layer_build import silhouette
        ob = object_crop(d / "side.png").convert("RGB")
    except Exception:
        return None, 0
    W, H = ob.size
    sil = silhouette(ob, erode=0)
    wall = []
    for y in range(H - 1, -1, -1):            # bottom-up, to match v
        xs = [x for x in range(W) if sil[x][y]]
        if not xs:
            wall.append(None)
            continue
        wall.append((W - 1 - max(xs)) if front_right else min(xs))
    seen = [v for v in wall if v is not None]
    if len(seen) < 8:
        return None, 0
    # carry the last known value across gaps so a domed top does not read as
    # a step of the full depth
    last = seen[0]
    for i, v in enumerate(wall):
        if v is None:
            wall[i] = last
        else:
            last = v
    return wall, max(seen) - min(seen)


def probe(prop_dir, face="front"):
    d = Path(prop_dir)
    try:
        pj = json.loads((d / f"parts_{face}.json").read_text())
    except Exception:
        return []
    if not pj.get("parts"):
        return []
    wall, span = raw_front_wall(d)
    if wall is None:
        return []
    H = pj["size"][1]
    n = len(wall)
    fw = [(i / max(1, n - 1), float(v)) for i, v in enumerate(wall)]
    zs = [z for _, z in fw]
    if span <= 1e-6:
        return [{"part": p["name"], "evidence": ABSENT,
                 "why": "the side elevation shows a flat front: no depth in it"}
                for p in pj["parts"]]

    # the body's "outside" depth: the mode of the wall, i.e. the plain surface
    ordered = sorted(zs)
    base = ordered[len(ordered) // 2]
    out = []
    for p in pj["parts"]:
        x0, y0, x1, y1 = p["px"]
        t0, t1 = 1 - y1 / H, 1 - y0 / H
        rows = [(y, z) for y, z in fw if t0 - 1e-9 <= y <= t1 + 1e-9]
        if len(rows) < 3:
            out.append({"part": p["name"], "evidence": ABSENT,
                        "why": "the side profile has too few samples here"})
            continue
        devs = [z - base for _, z in rows]
        # a step, not a spike: most of the feature's own rows must deviate the
        # same way by a similar amount
        signed = [v for v in devs if abs(v) > 0.06 * span]
        if len(signed) < COVER * len(devs) or not signed:
            out.append({"part": p["name"], "evidence": ABSENT,
                        "why": "the body's front does not step across its rows"})
            continue
        # A SLOPE IS NOT A STEP, and this is where the first version went
        # wrong in exactly the way the docstring predicted. An arcade
        # cabinet's bezel leans back continuously, so the rows under a screen
        # deviate from the median all the same way -- and the screen came back
        # "proud 69.8" and "proud 77.4", a third of the body depth, on two
        # different props. A screen is recessed and never 70 pixels of
        # anything: that number is the cabinet's shape wearing the feature's
        # name.
        #
        # A recess has a FLAT floor: the depth is the same across the
        # feature's rows. A slope's is not. Requiring the deviation to be
        # roughly constant separates them, and it is the feature's own
        # geometry rather than a threshold about how big a step may be.
        mean_dev = sum(signed) / len(signed)
        spread = max(signed) - min(signed)
        if abs(mean_dev) > 1e-9 and spread > 0.8 * abs(mean_dev):
            out.append({"part": p["name"], "evidence": ABSENT,
                        "why": f"the front changes by {spread:.1f} across its "
                               f"rows against a mean of {abs(mean_dev):.1f}: "
                               f"a slope, not a recess with a floor"})
            continue
        if min(signed) < 0 < max(signed):
            out.append({"part": p["name"], "evidence": ABSENT,
                        "why": "the front steps both ways here: this is body "
                               "shape, not one feature's depth"})
            continue
        # and the step must not run far beyond the feature, or it is the body
        same = [y for y, z in fw
                if (z - base) * signed[0] > 0 and abs(z - base) > 0.06 * span]
        if same and (max(same) - min(same)) > SPILL * (t1 - t0):
            out.append({"part": p["name"], "evidence": ABSENT,
                        "why": f"the step runs {(max(same)-min(same))/(t1-t0):.1f}x "
                               f"the feature's own height: it is the body's shape"})
            continue
        # A SILHOUETTE CANNOT SHOW A RECESS. This is the physical limit of the
        # source and it took three passes to see: the side elevation's front
        # edge at a given height is the FRONTMOST point across the whole width
        # at that height, so only the thing that sticks out furthest defines
        # it. A screen set into a bezel never does -- the bezel around it is
        # always further forward -- and asking anyway is how the first version
        # returned "screen, proud, 69.8", a third of the body's depth, for a
        # feature that is recessed by definition. That number was the
        # cabinet's bezel wearing the screen's name.
        #
        # So a reading that comes back RECESSED is not a recess measurement.
        # It is the body being shallower at those rows than at others, which
        # says something about the body and nothing about the feature. Only a
        # PROUD reading is a measurement of the feature, and then only because
        # the feature is what the silhouette is tracing.
        #
        # This closes the route to ACCEPTED for every NEEDS_RECESS role from
        # orthographic elevations alone. It is a fact about the reference
        # format, not a threshold to loosen: a window, a screen and a drawer
        # cannot be verified as recesses from front/side/back/top, and a
        # reference that shows the recess (a three-quarter view) or a different
        # definition of ACCEPTED are the only two ways out.
        depth = sum(signed) / len(signed)
        if depth < 0:
            out.append({"part": p["name"], "evidence": ABSENT,
                        "why": "the body is shallower across its rows, which "
                               "is the body's shape -- a silhouette cannot "
                               "show a recess, only what juts out furthest"})
            continue
        out.append({"part": p["name"], "evidence": MEASURED,
                    "thickness": round(abs(depth), 5),
                    "sense": "recessed" if depth < 0 else "proud",
                    "why": f"the side elevation's front wall steps "
                           f"{'back' if depth < 0 else 'forward'} by "
                           f"{abs(depth):.4f} across {len(signed)} of "
                           f"{len(devs)} of its rows"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--face", default="front")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        work = Path(__file__).resolve().parents[1] / "img2threejs-work"
        n = m = 0
        why = {}
        props = 0
        for pj in sorted(work.glob("*/parts_front.json")):
            rows = probe(pj.parent)
            if not rows:
                continue
            props += 1
            for r in rows:
                n += 1
                if r["evidence"] == MEASURED:
                    m += 1
                else:
                    key = r["why"].split(":")[0][:52]
                    why[key] = why.get(key, 0) + 1
        print(f"{props} props, {n} features")
        print(f"   MEASURED depth  {m:5}  ({100*m/max(1,n):.1f}%)")
        print(f"   ABSENT          {n-m:5}")
        for k, v in sorted(why.items(), key=lambda kv: -kv[1]):
            print(f"      {v:5}  {k}")
        return

    for r in probe(Path(args.prop_dir), args.face):
        if r["evidence"] == MEASURED:
            print(f"   MEASURED {r['part']:24} {r['sense']:8} "
                  f"{r['thickness']:.4f}   {r['why']}")
        else:
            print(f"   absent   {r['part']:24} {r['why']}")


if __name__ == "__main__":
    main()
