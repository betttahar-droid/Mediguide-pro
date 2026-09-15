#!/usr/bin/env python3
"""Trace the prop's profile out of the side elevation, and say which way it faces.

    python3 tools/authoring/side_profile.py work/ps1

Authoring tool. NOT a build, CI or runtime dependency.

WHY. body_faces.py textures a BOX, and an arcade cabinet is not one: it has a
sloped back, a jutting control deck and a recessed screen. Pasting the side
elevation onto a rectangular face left pale slabs where the sheet showed past
the profile, and clamping the edge pixels outwards only replaced them with
smeared vent stripes. Both are the same mistake -- painting a shape instead of
building it.

The side elevation already IS the profile, drawn dead on at the same height as
the front. Tracing it gives, for every height, where the prop's front surface
and back surface actually are. Extruding that across the width is the model.

WHICH EDGE IS THE FRONT IS MEASURED, NOT ASSUMED. A turnaround's "left side"
can put the nose either way round depending on which way the artist rotated
the object, and getting it backwards mounts the marquee on the back of the
cabinet -- the same class of bug as the rotateY(-90) that faced an earlier
model away from the camera. So it is decided by the silhouette's own RELIEF,
with the vision model as the tiebreak on props whose profile is a plain box.
See relief_bias() for the two tests that failed before this one.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from identify_parts import object_crop  # noqa: E402
from layer_build import silhouette  # noqa: E402


def strip_mean(im, x0, x1):
    px = im.load()
    H = im.size[1]
    n = 0
    acc = [0, 0, 0]
    for x in range(x0, x1):
        for y in range(0, H, 2):
            c = px[x, y]
            acc = [a + v for a, v in zip(acc, c)]
            n += 1
    return [a / max(1, n) for a in acc]


def dist(a, b):
    return sum(abs(p - q) for p, q in zip(a, b)) / 3


def relief_bias(inside, W, H):
    """Which boundary of the profile has RELIEF. >0 means the left one.

    A prop's front is where it changes shape -- a control deck juts, a bezel
    steps back, a hopper slopes. Its back is a flat panel. So the boundary that
    wanders is the front, and the one that runs straight is the back.

    Two earlier tests failed here and both failed instructively. Matching edge
    STRIP COLOURS against the front and back elevations scored 96.95 against
    96.95 on the cabinet: front and back share a corner colour, so the two
    hypotheses were equal by construction and the tie defaulted silently to
    'left'. Then counting EDGE ENERGY per half called the cabinet's front the
    right-hand edge, because the side art is a big detailed decal and the deck
    that actually marks the front is a small plain bump -- it was measuring
    where the picture was busy, not where the object was.

    Shape is the thing that distinguishes a front from a back, so measure
    shape: the total variation of each silhouette boundary.
    """
    lo, hi = [], []
    for y in range(H):
        run = [x for x in range(W) if inside[x][y]]
        if run:
            lo.append(run[0])
            hi.append(run[-1])
    if len(lo) < 8:
        return 0.0

    # SMOOTH BEFORE MEASURING, OR THE JAGGIES ARE THE SIGNAL. The vending
    # machine's side is a plain rectangle -- both boundaries dead straight --
    # and raw total variation still scored it 0.487, which is antialiasing on
    # a drawn edge, not a control deck. A prop that really is a box must come
    # out near zero and let the model decide, because on a box it does not
    # matter which way round the profile goes.
    def smooth(a, k=5):
        return [sum(a[max(0, i - k):i + k + 1]) / len(a[max(0, i - k):i + k + 1])
                for i in range(len(a))]

    def tv(a):
        a = smooth(a)
        return sum(abs(a[i + 1] - a[i]) for i in range(len(a) - 1)) / W

    l, r = tv(lo), tv(hi)
    if l + r < 0.05:            # both walls straight: this prop is a box
        return 0.0
    return (l - r) / max(1e-6, l + r)


def front_is_left(side, inside, asset="game prop"):
    """Which edge of the side elevation is the prop's front.

    Getting this backwards mounts the marquee on the back of the cabinet, so it
    is worth a model call: it is a naming question, one glance answers it, and
    naming is what the vision model is for here. The arithmetic bias above is
    the cross-check, and the fallback when the call fails.
    """
    bias = relief_bias(inside, *side.size)
    said = None
    try:
        from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
            side.save(t.name)
            uri = data_uri(Path(t.name))
        ask = (f"This is a SIDE elevation of a {asset}, drawn dead on.\n\n"
               "Which edge of this image is the prop's FRONT -- the face a "
               "person stands at, where the screen, controls, door or spout "
               "are? The other edge is its plain back.\n\n"
               'JSON only: {"front": "left"} or {"front": "right"}')
        r = as_json(glm([{"role": "user", "content": [
            {"type": "text", "text": ask},
            {"type": "image_url", "image_url": {"url": uri}}]}],
            CRITIC_MODEL, _openrouter_key(), max_tokens=4000, temperature=0.0))
        v = str(r.get("front", "")).strip().lower()
        if v in ("left", "right"):
            said = v
    except Exception as e:
        print(f"  ! front-edge call failed ({type(e).__name__}), "
              f"falling back to detail bias")
    # THE MEASUREMENT OUTRANKS THE CLAIM WHEN IT IS DECISIVE. glm-5.3-flash
    # answered "right" and then "left" for the same vending machine on two
    # runs at temperature 0, so its answer is not stable enough to be the last
    # word on a question that, got wrong, mounts the marquee on the back. Where
    # the silhouette actually has relief, the relief decides; where it has none
    # the prop is a box, nothing depends on the answer, and the model's reading
    # of the picture is the better guess.
    by_bias = "left" if bias > 0 else "right" if bias < 0 else None
    if by_bias and abs(bias) >= 0.15:
        choice = by_bias
    else:
        choice = said or by_bias or "left"
    return choice == "left", said, by_bias, bias


def simplify(pts, tol):
    """Douglas-Peucker. A PS1 prop's profile is a dozen segments, not 600."""
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    n = (dx * dx + dy * dy) ** 0.5 or 1e-9
    worst, wi = 0.0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs(dy * x - dx * y + x1 * y0 - y1 * x0) / n
        if d > worst:
            worst, wi = d, i
    if worst <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:wi + 1], tol)[:-1] + simplify(pts[wi:], tol)


def fit(pts, want_px, span_px, cap=40):
    """Simplify only as far as the shape survives, and no further.

    A FIXED TOLERANCE THROWS AWAY WHATEVER IS SHORTEST, WHICH IS THE DETAIL.
    Douglas-Peucker at 0.012 of the height gave this cabinet a twelve-point
    front wall, and the places it went wrong were not spread out -- they were
    the corners: 29 pixels at the junction where the control deck meets the
    screen slope, 20 at the plinth, 15 under the deck. Those are exactly the
    features a cabinet is RECOGNISED by, and they are short, so they are the
    first things a tolerance eats. The prop then reads as a slab with a lean
    on it, which is what a slope and a bevel look like once they have been
    averaged away.

    The tolerance is not a thing to tune, it is a thing to solve for: halve it
    until the polyline sits within `want_px` of the traced edge everywhere, or
    the point budget is spent. A box still comes back four points because
    there is nothing to lose; a cabinet gets the thirty it needs, which is
    nothing for a prop of this era and is the difference between its silhouette
    reading as the object or not.
    """
    tol = 0.05
    under = None                       # the finest fit still inside the budget
    for _ in range(12):
        got = simplify(pts, tol)
        err = max_dev(pts, got) * span_px
        if len(got) <= cap:
            under = (got, tol, err)
        if err <= want_px:
            # a fit that meets the target but blows the budget is not a fit:
            # a profile is meant to be a few dozen segments, and chasing the
            # last half pixel took this cabinet's front wall to 185 points --
            # 185 rings in the loft, for a shape a player reads in one glance
            return (got, tol, err) if len(got) <= cap else under
        tol /= 2
    return under or (simplify(pts, tol), tol, max_dev(pts, simplify(pts, tol)) * span_px)


def pull_inside(poly, pts, sign, cap=None):
    """Move the polyline until it is nowhere OUTSIDE the edge it was traced from.

    `fit` simplifies to within `want_px` of the traced edge, and a tolerance is
    symmetric: half the error is the polyline bulging past the art. The body is
    lofted from this polyline and clothed in that art, so wherever it bulges
    there is body with no texture on it -- and the renderer alpha-tests those
    texels away, which is DAYLIGHT THROUGH THE PROP. 4.2% of all rows in the
    corpus are in that state, up to 9 pixels on v11_vending_machine, which is
    the prop with the worst remaining hole.

    Growing the art to cover the body was tried first and reverted, with the
    numbers, in `layer_build.sheet_mask`: a silhouette two pixels fat everywhere
    costs twelve props on the front to fix a fringe on three. This is the same
    disagreement settled from the other side, where it belongs -- the art is the
    reference and the polyline is the approximation, so the approximation moves.

    One pass is exact. Pushing BOTH endpoints of a segment inward by that
    segment's worst violation moves the interpolant inward by at least as much
    everywhere along it, because the interpolant is linear in its endpoints.

    sign is +1 for a wall whose material lies to the RIGHT of the value (a left
    wall, a back wall) and -1 for one whose material lies to the left.

    AND CAPPED AT THE TOLERANCE THAT CAUSED IT, which is the whole difference
    between this working and this being a disaster. Uncapped, the push is the
    WORST violation on a segment, and one traced row is enough to carry it: the
    first version moved v45_jukebox's walls far enough to take its side outline
    from 0.983 to 0.736 and its top from 0.985 to 0.839, and 40 of 98 props were
    worse. One sample moving a whole estimate -- MISTAKES.md's seventeenth entry,
    walked into while fixing something else.
    The correction is bounded by construction: the bulge this exists to remove
    is simplification error, so it can never legitimately exceed the tolerance
    `fit` was solved to. Anything past that is a spike in the TRACE, which is
    `_trim_ends`'s business and not this function's.
    """
    seg = [[] for _ in range(max(1, len(poly) - 1))]
    for y, f in pts:
        for i in range(len(poly) - 1):
            y0, x0 = poly[i]
            y1, x1 = poly[i + 1]
            lo, hi = (y0, y1) if y0 <= y1 else (y1, y0)
            if lo - 1e-9 <= y <= hi + 1e-9:
                t = 0.0 if abs(y1 - y0) < 1e-12 else (y - y0) / (y1 - y0)
                seg[i].append(max(0.0, sign * (f - (x0 + t * (x1 - x0)))))
                break
    # THE EIGHTIETH PERCENTILE OF A SEGMENT'S VIOLATIONS, NOT THE WORST. The
    # worst is one row, and one row is how the uncapped version took a jukebox
    # to 0.736. A bulge worth removing is a bulge most of the segment sits in.
    need = [0.0] * len(poly)
    for i, v in enumerate(seg):
        if not v:
            continue
        v = sorted(v)
        d = v[min(len(v) - 1, int(0.8 * len(v)))]
        need[i] = max(need[i], d)
        need[i + 1] = max(need[i + 1], d)
    if cap is not None:
        need = [min(n, cap) for n in need]
    return ([(y, x + sign * n) for (y, x), n in zip(poly, need)],
            max(need) if need else 0.0)


def max_dev(pts, poly):
    """The worst gap between the traced edge and the polyline standing in for it.

    Measured PERPENDICULAR to the polyline, not straight across at the same
    height. A profile's most important features are its vertical steps -- the
    face of a control deck, the drop under a marquee -- and a step is where a
    vertical reading is meaningless: the traced edge crosses the whole step
    within one or two rows, so comparing at equal height reports the full
    height of the step as an error. It reported 29 pixels on this cabinet and
    stayed at 29 however many points were spent, right up to 185, because no
    number of points makes a vertical segment single-valued. The distance from
    the drawn edge to the LINE is what "does this polyline follow that edge"
    actually means, and it is the same distance Douglas-Peucker minimises.
    """
    p = sorted(poly)
    worst = 0.0
    for a, b in pts:
        best = float("inf")
        for i in range(len(p) - 1):
            x0, y0 = p[i]
            x1, y1 = p[i + 1]
            dx, dy = x1 - x0, y1 - y0
            n2 = dx * dx + dy * dy
            t = 0.0 if n2 < 1e-18 else max(0.0, min(1.0, ((a - x0) * dx + (b - y0) * dy) / n2))
            best = min(best, ((a - (x0 + t * dx)) ** 2 + (b - (y0 + t * dy)) ** 2) ** 0.5)
        worst = max(worst, best)
    return worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--asset", default="game prop")
    ap.add_argument("--want", type=float, default=2.0,
                    help="how close the polyline must sit to the traced edge, "
                         "in pixels of the elevation")
    args = ap.parse_args()
    d = Path(args.sheet_dir)

    side = object_crop(d / "side.png")
    front = object_crop(d / "front.png")
    W, H = side.size
    FW, FH = front.size

    inside = silhouette(side, erode=0)
    left, said, by_bias, bias = front_is_left(side, inside, args.asset)

    # for each row, the first and last solid column: the front and back walls
    rows = []
    for y in range(H):
        run = [x for x in range(W) if inside[x][y]]
        if run:
            rows.append((y, run[0], run[-1]))
    if not rows:
        raise SystemExit("side elevation has no silhouette")
    # AND THE SAME CLEAN-UP THE FRONT PROFILE NEEDS, for the same reason on the
    # same axis of the same crop: a terminal row that is a quarter of its
    # neighbour's depth is antialiasing or a drop shadow, and a lone narrow row
    # between two full ones is a band the silhouette lost. Either one puts a
    # spike in the polyline and a spike in the body. front_profile.py carries
    # the measurement; this is the depth wall rather than the width wall.
    from front_profile import _trim_ends
    rows = _trim_ends(rows, "side")

    # in prop units: y measured from the BOTTOM, 0..1 over the front's height;
    # z measured forward from the body's centre
    depth = W / FH

    def to_z(x):
        # f is the distance back from the prop's nose, 0 at the front face;
        # +z faces whoever is looking at the front elevation
        f = x / W if left else 1 - x / W
        return (0.5 - f) * depth

    prof = []
    for (y, a, b) in rows:
        yy = 1 - y / H
        za, zb = to_z(a), to_z(b)
        prof.append((yy, max(za, zb), min(za, zb)))   # (height, front z, back z)

    # simplify the two walls independently -- the front wall carries the deck
    # and the back wall the slope, and they are not the same curve -- and each
    # only as far as its own shape survives, measured in pixels of the drawing
    fw, ftol, ferr = fit([(p[0], p[1]) for p in prof], args.want, H)
    bw, btol, berr = fit([(p[0], p[2]) for p in prof], args.want, H)
    # AND NEVER OUTSIDE THE ART -- see pull_inside(). The front wall's material
    # lies BEHIND it and the back wall's in front, so the signs are the other
    # way round from the front elevation's left and right.
    fw, fp_ = pull_inside(fw, [(p[0], p[1]) for p in prof], -1,
                          max(args.want, ferr) / H)
    bw, bp_ = pull_inside(bw, [(p[0], p[2]) for p in prof], +1,
                          max(args.want, berr) / H)
    if max(fp_, bp_) * H > 0.5:
        print(f"  side trace: pulled the walls in by up to "
              f"{max(fp_, bp_) * H:.1f}px so the body is nowhere deeper than "
              f"the artwork that covers it")

    out = {
        "depth": round(depth, 5),
        "aspect": round(FW / FH, 5),
        "front_edge": "left" if left else "right",
        "front_edge_said": said, "front_edge_by_relief": by_bias,
        "relief_bias": round(bias, 4),
        "front_wall": [[round(a, 5), round(b, 5)] for a, b in fw],
        "back_wall": [[round(a, 5), round(b, 5)] for a, b in bw],
    }
    (d / "profile.json").write_text(json.dumps(out, indent=1))
    flat = max(abs(b - fw[0][1]) for _, b in fw)
    agree = ("agree" if said == by_bias else
             "profile is a box, relief has no opinion" if by_bias is None else
             "no call" if not said else f"DISAGREE (relief says {by_bias})")
    print(f"profile: depth {depth:.3f}, front edge = {out['front_edge']}  "
          f"[model {said or '-'}, relief {by_bias} {bias:+.3f}, {agree}]")
    print(f"  front wall {len(fw)} points, within {ferr:.1f}px of the drawing "
          f"(tol {ftol:.4f}); deepest step {flat:.3f} "
          f"({'shaped' if flat > 0.02 else 'essentially flat'})")
    print(f"  back  wall {len(bw)} points, within {berr:.1f}px -> "
          f"{d / 'profile.json'}")


if __name__ == "__main__":
    main()
