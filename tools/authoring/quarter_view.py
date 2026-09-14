#!/usr/bin/env python3
"""The one view that can show a recess, and whether it can be measured.

    python3 tools/authoring/quarter_view.py work/ps1 --asset "vending machine"
    python3 tools/authoring/quarter_view.py work/ps1 --probe

Authoring tool. NOT a build, CI or runtime dependency.

WHY. `depth_probe` records three attempts at measuring how far a feature is set
in, all swept across the corpus and all failed, and its conclusion is a fact
about the reference format rather than a threshold to loosen:

    A SILHOUETTE CANNOT SHOW A RECESS. The side elevation's front edge at a
    given height is the FRONTMOST point across the whole width at that height,
    so only the thing that sticks out furthest defines it. A screen set into a
    bezel never does -- the bezel around it is always further forward.

So 291 thicknesses are UNMEASURABLE, every NEEDS_RECESS role is stuck at
UNVERIFIED, and no prop can reach a meaningful ACCEPTED on a feature that must
open or recess. The file names the two ways out and this is the first: a
reference that shows the recess.

A SEPARATE GENERATION, NOT A FIFTH PANEL. The turnaround is one image split on
its background gaps, and a fifth view in the same row makes every view narrower:
the front of a cabinet is already about 250 pixels and detail_sheet exists
because that is the fidelity ceiling. This is asked for on its own, with the
finished sheet attached so it is the same object in the same style.

AND IT IS A FIFTH SOURCE THAT CAN CONTRADICT THE OTHER FOUR, which is the
spec's own warning in as many words -- "generated multi-view references can
contain inconsistencies; treat those inconsistencies as uncertainty". So it is
never allowed to overwrite an elevation. Nothing here writes to parts, profiles
or bands. It answers one question, about depth, and its answers carry their own
evidence grade.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))

# The angle is fixed and stated, because the arithmetic downstream needs it: a
# recess of depth d in the front face projects its inner wall at d*sin(yaw)
# across the picture. Choosing it here rather than letting the model choose is
# the difference between a measurement and a guess.
YAW = 35
PITCH = 12
# AND A VIEW IS ONLY USABLE IF IT IS ACTUALLY TURNED. Aspect agreement alone is
# a weak test and it passed two views that are nearly flat: the jukebox's best
# panel implies 7 degrees and registered at 12%, the arcade cabinet's implies 11.
# A recess of depth t shows a wall t*sin(yaw) wide, so at 7 degrees there is
# 0.12t of wall to read and the drawing carries no depth however well its
# proportions agree. The whole point of the view is the turn.
MIN_YAW = 20

PROMPT = """ONE THREE-QUARTER VIEW of the {asset} in the attached turnaround
sheet. The same object, the same proportions, the same colours, the same wear --
this is that object turned, not a new design of it.

DRAW EXACTLY ONE VIEW. One object, once, filling the frame. Not a turnaround,
not a pair, not a sheet of angles -- ONE picture of the object at ONE angle.

TURN IT {yaw} DEGREES to its left and tip the camera {pitch} degrees down, so
the FRONT face and the LEFT SIDE are both visible and the front is the larger of
the two. Keep the projection parallel -- no vanishing point, no lens, no
foreshortening down the height.

WHAT THIS VIEW IS FOR, and it decides everything about how to draw it: the flat
elevations cannot show how deep anything is set. So every opening, recess and
raised fitting must READ AS ITS DEPTH here.

  - Anything RECESSED -- a screen in its bezel, a window, a drawer, a coin
    return, a vent -- must show the INNER WALL of its recess: the strip of side
    wall you see because the object is turned. Draw that wall, in shadow, at the
    depth it really is.
  - Anything PROUD -- a button, a handle, a knob, a moulding, a coin box --
    must show its own side, catching the light, standing clear of the face
    behind it.
  - Anything FLUSH stays flat with no wall and no side at all.

Every fitting the elevations show must be here, in the same place on the face,
at the same size relative to the object. Do not add fittings, do not move them,
do not leave any out.

{style}

Absolutely flat single-colour background, one colour edge to edge. No drop
shadow, no ground plane, no reflection, no gradient. One object, nothing else in
the frame, no annotations and no text.
"""


def draw(prop_dir, asset, redraw=False):
    from PIL import Image
    from concept_sheet import generate_image, load_key
    from identify_parts import object_crop
    from ps1_sheet import PS1_STYLE

    d = Path(prop_dir)
    dst = d / "quarter.png"
    if dst.exists() and not redraw:
        print(f"  already drawn: {dst}")
        return dst
    sheet = d / "sheet.png"
    refs = [sheet] if sheet.exists() else [
        p for p in (d / "front.png", d / "side.png") if p.exists()]
    if not refs:
        print("no reference on disk to turn")
        return None
    key = load_key()
    # A REFUSAL IS A VERDICT ON ONE DRAWING -- the third time today that rule has
    # earned its place. The model draws a turnaround however firmly the prompt
    # says otherwise, and on two props of four no panel in it was turned enough
    # to carry a recess. So the reply is measured, and if nothing in it is
    # usable the ask is repeated with the measurement quoted back.
    last = None
    for attempt in range(3):
        more = "" if not last else (
            f"\n\nYOUR LAST ATTEMPT WAS REJECTED: {last}\nDraw it again, "
            f"turned properly, as ONE picture.")
        generate_image(
            PROMPT.format(asset=asset, yaw=YAW, pitch=PITCH,
                          style=PS1_STYLE) + more,
            dst, key, refs=refs)
        # AND IF IT DREW MORE THAN ONE, KEEP THE ONE THAT IS TURNED.
        #
        # Asked for a single view it came back with a turnaround -- four panels, one
        # of them a flat front elevation -- twice running, however firmly the prompt
        # says "exactly one". ps1_sheet already splits a sheet on its background
        # gaps, so the panels are cheap to separate; the question is which to keep,
        # and "the largest" is wrong. A flat front view is usually the largest, and
        # that is exactly what the first version kept: a dead-on elevation whose
        # implied yaw is 5.6 degrees, which then read as the drawing failing to
        # register against the other four.
        #
        # Which panel is the three-quarter one is MEASURABLE and does not need the
        # model to cooperate. A prop W wide and D deep turned by yaw is
        # W*cos(yaw) + D*sin(yaw) across, so each panel's own aspect implies a yaw,
        # and the panel to keep is the one whose implied yaw is nearest the angle
        # asked for. A front elevation implies nearly zero and loses.
        try:
            from ps1_sheet import split as _split
            import math
            raw = d / "_quarter_raw.png"
            Image.open(dst).save(raw)
            tmp = d / "_quarter_split"
            tmp.mkdir(exist_ok=True)
            got, _runs = _split(dst, tmp, min_width=60)
            if len(got) > 1:
                fr = object_crop(d / "front.png").convert("RGB")
                sd = object_crop(d / "side.png").convert("RGB")
                W, H = fr.size
                D = sd.size[0]
                pitch = math.radians(PITCH)
                scored = []
                for name, path, size in got:
                    y = math.degrees(_solve_yaw(W, H, D, pitch,
                                                size[0] / float(size[1])))
                    scored.append((abs(y - YAW), y, path, size))
                scored.sort()
                _, y, path, size = scored[0]
                Image.open(path).save(dst)
                print(f"  it drew {len(got)} views; kept the one implying "
                      f"{y:.0f} degrees of turn against the {YAW} asked "
                      f"({size[0]}x{size[1]}); the others implied "
                      + ", ".join(f"{s[1]:.0f}" for s in scored[1:]))
            for f in tmp.glob("*.png"):
                f.unlink()
            tmp.rmdir()
        except Exception as e:
            print(f"  not split ({type(e).__name__}: {e})")
        r = probe(d, meta={"yaw": YAW, "pitch": PITCH})
        if r.get("usable"):
            break
        last = (f"it came back at {r.get('implied_yaw', 0):.0f} degrees of turn "
                f"against the {YAW} asked for"
                if not r.get("turned_enough") else
                f"its proportions are {100 * r.get('off_by', 1):.0f}% away from "
                f"the object in the reference sheet")
        print(f"  attempt {attempt + 1} rejected: {last}")
    else:
        print(f"  three drawings rejected; no usable three-quarter view")
    (d / "quarter.json").write_text(json.dumps(
        {"yaw": YAW, "pitch": PITCH, "asset": asset,
         "evidence": "proposed",
         "note": "a generated fifth source; never overwrites an elevation"},
        indent=1))
    print(f"  wrote {dst} {Image.open(dst).size}")
    return dst


def probe(prop_dir, face="front", meta=None):
    """Does the drawing agree with the elevations about where things are?

    THE FIRST QUESTION IS NOT DEPTH, IT IS WHETHER THIS IS THE SAME OBJECT.
    A fifth source is only evidence if it registers against the four that are
    already measured, and the spec's warning is that it may not. So before any
    depth is read off it, check the cheap thing: the object's own proportions.

    Returns what can be said, with nothing inferred past it.
    """
    from PIL import Image
    from identify_parts import object_crop

    d = Path(prop_dir)
    q = d / "quarter.png"
    if not q.exists():
        return {"state": "absent"}
    try:
        qi = object_crop(q).convert("RGB")
        fr = object_crop(d / f"{face}.png").convert("RGB")
        sd = object_crop(d / "side.png").convert("RGB")
    except Exception as e:
        return {"state": "unreadable", "why": type(e).__name__}

    import math
    if meta is None:
        try:
            meta = json.loads((d / "quarter.json").read_text())
        except Exception:
            meta = {}
    yaw = math.radians(meta.get("yaw", YAW))
    # A prop W wide and D deep, turned by yaw and tipped by pitch, occupies
    # W*cos(yaw) + D*sin(yaw) across the picture and H*cos(pitch) + D*sin(pitch)
    # down it. That is a prediction the four elevations make about the fifth
    # view, and it is falsifiable.
    #
    # THE PITCH TERM WAS MISSING and the first reading blamed the drawing for
    # it: predicted 0.728 against a measured 0.574, declared "does not
    # register". With the camera's 12 degrees of tip the same prop projects
    # 0.679, and the gap is a third of what it was. A prediction is only
    # evidence about the drawing once it is a prediction about the same
    # geometry.
    pitch = math.radians(meta.get("pitch", PITCH))
    W, H = fr.size
    D = sd.size[0]
    want = ((W * math.cos(yaw) + D * math.sin(yaw))
            / (H * math.cos(pitch) + D * math.sin(pitch)))
    got = qi.size[0] / float(qi.size[1])
    off = abs(got - want) / max(1e-6, want)
    iy = math.degrees(_solve_yaw(W, H, D, pitch, got))
    rts = _roots(W, H, D, pitch, got)
    return {"state": "drawn",
            "implied_yaw_roots": rts,
            "yaw_ambiguous": len(rts) > 1,
            "predicted_aspect": round(want, 4),
            "measured_aspect": round(got, 4),
            "off_by": round(off, 4),
            "registers": bool(off <= 0.15),
            # A view is turned enough only if EVERY root it could be is: with
            # two candidates and no way to choose, the weaker one is what the
            # drawing may actually be, and claiming the stronger would be the
            # overclaim feature_intent exists to refuse.
            "turned_enough": bool(rts and min(rts) >= MIN_YAW),
            "usable": bool(off <= 0.15 and rts and min(rts) >= MIN_YAW),
            "implied_yaw": round(iy, 1),
            "why": (f"front {W}x{H}, side depth {D}, turned "
                    f"{math.degrees(yaw):.0f} and tipped "
                    f"{math.degrees(pitch):.0f} predicts an aspect of "
                    f"{want:.3f}; the drawing is {got:.3f}")}


def _roots(W, H, D, pitch, got, tol=0.04):
    """Every yaw whose projected width matches, not just the nearest one."""
    import math
    den = H * math.cos(pitch) + D * math.sin(pitch)
    target = got * den
    hits, run = [], []
    for deg in range(1, 90):
        f = (W * math.cos(math.radians(deg)) + D * math.sin(math.radians(deg)))
        if abs(f - target) <= tol * max(1.0, target):
            run.append(deg)
        elif run:
            hits.append(run[len(run) // 2]); run = []
    if run:
        hits.append(run[len(run) // 2])
    return hits


def _solve_yaw(W, H, D, pitch, got):
    """The yaw the drawing's own proportions imply, whatever was asked for.

    AND THIS IS THE USEFUL NUMBER, not the agreement. The model is not a camera
    and will not hit 35 degrees on request; what matters downstream is the angle
    it ACTUALLY used, because a recess of depth t projects its inner wall at
    t*sin(yaw) and reading that wall needs the real yaw. So invert the
    prediction rather than grade it.

    NOT BY BISECTION, WHICH IS WHAT IT DID FIRST AND WHICH IS INVALID HERE.
    The projected width W*cos(yaw) + D*sin(yaw) is not monotonic in yaw: it
    PEAKS at atan(D/W) and falls away after, so a given width generally has two
    solutions and a width above the peak has none. Bisecting it returned 89
    degrees for the vending machine -- whose picture is plainly turned about a
    third of a right angle -- because the measured width is just past its peak
    of 380 and the search ran to its bound. That reading was one step from being
    written down as a result.

    Scanning is exact enough and cannot do that: take the yaw whose predicted
    width is nearest the measured one, and report the peak itself when the
    drawing is wider than any yaw can make it.

    AND IT IS STILL TWO-TO-ONE, WHICH IS THE HONEST LIMIT OF THIS MEASUREMENT.
    Because the width rises to the peak and falls again, a measured width
    generally has TWO yaws that produce it -- one either side -- and the aspect
    cannot choose between them. The pinball registers against its elevations at
    0.5% and the nearest root is 76 degrees, while the picture is plainly turned
    about half that: 76 and roughly 36 give the same width on a prop 252 wide
    and 372 deep, because its peak is at 56.
    `roots` returns both, and nothing here pretends to know which is the
    drawing's. Choosing needs a second measurement -- where the vertical edge
    between the front and the side falls, which is W*cos(yaw) from the left --
    and that is not built.
    """
    import math
    den = H * math.cos(pitch) + D * math.sin(pitch)
    target = got * den
    best = min(range(1, 90),
               key=lambda deg: abs(W * math.cos(math.radians(deg))
                                   + D * math.sin(math.radians(deg)) - target))
    return math.radians(best)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir")
    ap.add_argument("--asset", default="prop")
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    d = Path(args.prop_dir)
    if not args.probe:
        draw(d, args.asset, args.redraw)
    r = probe(d)
    print(f"quarter view: {r['state']}")
    for k in ("predicted_aspect", "measured_aspect", "off_by", "registers"):
        if k in r:
            print(f"   {k:18} {r[k]}")
    if r.get("why"):
        print(f"   {r['why']}")


if __name__ == "__main__":
    main()
