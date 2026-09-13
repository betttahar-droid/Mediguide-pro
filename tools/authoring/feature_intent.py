#!/usr/bin/env python3
"""Typed intent for every feature, in FACE-LOCAL coordinates, with evidence.

    python3 tools/authoring/feature_intent.py work/ps1 --face front
    python3 tools/authoring/feature_intent.py work/ps1 --report

Authoring tool. NOT a build, CI or runtime dependency.

WHY. A part in parts_front.json is a pixel box plus five enums:

    {"name": "display_window", "px": [10,60,201,315],
     "resize": "spanx_center", "anchor": "top", "depth": "recessed", ...}

Everything that record does not say has been a fault this year. It does not
say what the feature IS for (a window, a slot array, a scale, a handle), so
the loop can only reclassify how it stretches. It does not say what it is
mounted ON, so a rider and its host are related only by whoever notices their
boxes overlap. It does not say which SURFACE it lives on, so every part is
implicitly on the front. It has no thickness at all -- "depth" is one of four
words -- so a recess cannot be checked for being a recess. And it records no
EVIDENCE, so a number measured off the drawing and a number the model asserted
are indistinguishable once written.

THE COORDINATES ARE THE HEART OF IT. A feature's width and height are local to
the face it is mounted on, and its thickness is perpendicular to that face.
Those three are not world X, Y and Z, and treating them as though they were is
how a slot 40mm wide across the front becomes 40mm DEEP when the same intent is
compiled onto the side. So a Feature carries:

    surface     which face it is mounted on
    region      (u0, v0, u1, v1), normalised WITHIN that surface
    w, h        the local extent, in the surface's own axes
    thickness   perpendicular to the surface, and never derived from the region

Compiling to world coordinates is the one place the mapping happens, and it is
a single function that every surface goes through, so the same intent behaves
the same way on the front, the side and the top.

UNVERIFIED IS A RESULT, NOT A GAP. The measurements here come from different
places and are worth different amounts. A region measured off the elevation's
own pixels is evidence. A thickness the model proposed because a coin slot is
usually about that deep is a guess -- defensible, useful, and not a
measurement. Recording which is which lets the acceptance reducer say the only
honest thing about a prop built partly from guesses: it is a DRAFT that
complies with the prompt, not a reconstruction that fits the reference. The
previous system had no way to say that, so it said "success" instead, and a
synthesised part counted the same as a measured one.

PER INSTANCE, NEVER PER KIND. Four legs are four features. A grid of nine
product slots is nine. This is the rule the old validation broke by counting
object types: one visible knob satisfied "has knobs", one drawn grid cell
satisfied the grid, and the count was never checked. Every check here runs on
an instance and reports on that instance alone.
"""
import argparse
import json
import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Evidence. Every scalar on a Feature is one of these, and the reducer treats
# them very differently.

MEASURED = "measured"       # read off the reference pixels by arithmetic
DERIVED = "derived"         # computed from measured values by a known rule
PROPOSED = "proposed"       # the model's answer; plausible, not evidence
DEFAULT = "default"         # the tool's fallback; weaker than proposed
ABSENT = "absent"           # nothing said at all

EVIDENCE_RANK = {MEASURED: 3, DERIVED: 2, PROPOSED: 1, DEFAULT: 0, ABSENT: -1}

PASS, FAIL, UNVERIFIED = "PASS", "FAIL", "UNVERIFIED"
REJECTED, DRAFT, ACCEPTED = "REJECTED", "DRAFT", "ACCEPTED"

# The surfaces a feature can be mounted on. Face-local axes are named per
# surface so the compiler can never silently read a width as a depth.
#
#   u runs left-to-right across the face as drawn, v runs bottom-to-top,
#   and n is the outward normal. Thickness is always along n.
SURFACES = {
    "front": {"u": "+x", "v": "+y", "n": "+z"},
    "back":  {"u": "-x", "v": "+y", "n": "-z"},
    "side":  {"u": "-z", "v": "+y", "n": "+x"},   # the right flank
    "side_left": {"u": "+z", "v": "+y", "n": "-x"},
    "top":   {"u": "+x", "v": "-z", "n": "+y"},
    "bottom": {"u": "+x", "v": "+z", "n": "-y"},
}

# Semantic roles. The point of a role is that it carries REQUIREMENTS -- an
# operator knows what a slot array must look like in a way that "decal_7" never
# can. Roles the tool cannot infer stay "unknown", which is honest and which
# the reducer counts as unverified rather than as a pass.
ROLES = {
    "panel", "window", "screen", "slot", "slot_array", "button", "button_grid",
    "knob", "dial", "scale", "handle", "door", "flap", "drawer", "grille",
    "vent", "sign", "label", "decal", "light", "member", "plinth", "trim",
    "unknown",
}

# A role that must have a real opening or recess cannot be satisfied by paint.
# This is the check that "openings and recesses are geometry, not texture".
NEEDS_OPENING = {"slot", "slot_array", "vent", "grille", "handle"}
NEEDS_RECESS = {"window", "screen", "drawer"}

# What the renderer actually builds from each depth adjective, quoted from
# parts_view/index.html so the two cannot drift apart silently. These are the
# real stand-offs; they are simply not measurements of the reference.
DEPTH_ADJECTIVE = {"flush": 0.004, "proud": 0.018, "deep": 0.055,
                   "recessed": -0.014}

# Permitted width/height ratio, PER ROLE, measured across every parts_front.json
# in the work tree (see measure_role_aspects, which produced this literal --
# rerun it when the corpus grows rather than hand-editing these numbers).
#
# 2nd/98th percentile. This started at the 10th/90th, which is wrong for a
# reason worth keeping: a band drawn at p10/p90 excludes a fifth of the data it
# was derived from BY DEFINITION, so it is a tautology rather than a defect
# detector. Measured, it rejected 19-25% of every single role -- decal 20%,
# button 19%, screen 22%, member 25% -- which is the percentile's own arithmetic
# and says nothing about any prop. At p2/p98 the same corpus rejects 3-8%, and
# what falls outside is a gross outlier rather than an ordinary instance.
#
# Not min/max either: the corpus has known-bad segmentations
# (a jukebox grille boxed at 52.75:1, a decal at 39.4:1, a member at 0.04:1)
# and min/max would let check_aspect pass anything short of those extremes.
# The threshold for even having a range is 20 instances -- fewer than that and
# the two percentiles are just two of the observations, not a distribution.
#
# "unknown" is deliberately absent even though it clears 20 instances (343).
# It is not a role, it is the record of role_of() failing to find one, so its
# members share no shape contract -- a leg role_of() missed and a decal it
# missed sit in the same bucket. Giving it a range would fail or pass a part
# for its aspect based on what OTHER unrelated parts looked like, which is the
# exact failure role_of()'s docstring warns against: a wrong classification is
# worse than an honest unknown.
ROLE_ASPECT = {
    "button": (0.45, 3.9),
    "decal": (0.04, 13.31),
    "door": (0.24, 5.37),
    "grille": (0.26, 8.58),
    "member": (0.05, 2.56),
    "panel": (0.27, 6.29),
    "screen": (0.99, 1.79),
    "sign": (0.91, 7.48),
    "slot": (0.29, 4.18),
    "window": (0.44, 4.5),
}

# How many observed instances each ROLE_ASPECT range came from -- kept
# separately so lift() can name it in Feature.source without re-deriving it,
# and so a stale mismatch between this and ROLE_ASPECT (after a hand edit that
# forgot the other one) is visible on sight rather than silently wrong.
ROLE_ASPECT_N = {
    "button": 238,
    "decal": 555,
    "door": 81,
    "grille": 101,
    "member": 24,
    "panel": 39,
    "screen": 54,
    "sign": 67,
    "slot": 81,
    "window": 26,
}


class Feature:
    """One instance. Never a kind, never a group."""

    __slots__ = ("id", "role", "host", "surface", "region", "thickness",
                 "aspect", "appearance", "resize", "evidence", "source",
                 "extent")

    def __init__(self, fid, role="unknown", host=None, surface="front",
                 region=(0.0, 0.0, 1.0, 1.0), thickness=0.0, aspect=None,
                 appearance=None, resize="fixed", evidence=None, source=None,
                 extent=(1.0, 1.0)):
        self.id = fid
        self.role = role if role in ROLES else "unknown"
        self.host = host                  # id of the feature it is mounted on
        self.surface = surface
        self.region = tuple(float(v) for v in region)
        self.thickness = float(thickness)
        self.aspect = aspect              # (lo, hi) permitted w/h, or None
        self.appearance = appearance or {}
        self.resize = resize
        # field -> one of the evidence constants. A field missing from this
        # dict is ABSENT, which is the strongest statement the reducer makes.
        self.evidence = dict(evidence or {})
        self.source = source or {}        # field -> what actually measured it
        # THE REAL EXTENT OF THE SPACE `region` IS NORMALISED AGAINST, in the
        # pixels it was measured in. Without it a region is a ratio with no
        # units and NOTHING can be recovered from it -- which is not a detail,
        # it is this file's own subject. See check_aspect.
        self.extent = (float(extent[0]), float(extent[1]))

    # -- face-local geometry -------------------------------------------------

    @property
    def w(self):
        """Local width, in the surface's own u axis. Never a world axis."""
        return self.region[2] - self.region[0]

    @property
    def h(self):
        """Local height, in the surface's own v axis."""
        return self.region[3] - self.region[1]

    def local_size(self, surface_extent):
        """(w, h, thickness) in real units, given the surface's own extent.

        surface_extent is (u_len, v_len) for the face this sits on. Thickness
        is NOT scaled by it -- that is the whole point. A 12mm-deep coin slot
        is 12mm deep on a small machine and on a large one, and on the front
        and on the flank.
        """
        ue, ve = surface_extent
        return (self.w * ue, self.h * ve, self.thickness)

    def ev(self, field):
        return self.evidence.get(field, ABSENT)

    def to_json(self):
        return {"id": self.id, "role": self.role, "host": self.host,
                "surface": self.surface, "region": list(self.region),
                "thickness": self.thickness, "aspect": self.aspect,
                "appearance": self.appearance, "resize": self.resize,
                "extent": list(self.extent),
                "evidence": self.evidence, "source": self.source}

    @staticmethod
    def from_json(d):
        return Feature(d["id"], d.get("role"), d.get("host"),
                       d.get("surface", "front"),
                       d.get("region", (0, 0, 1, 1)), d.get("thickness", 0.0),
                       d.get("aspect"), d.get("appearance"),
                       d.get("resize", "fixed"), d.get("evidence"),
                       d.get("source"), d.get("extent", (1.0, 1.0)))


# ---------------------------------------------------------------------------
# Deriving intent from what the tool already measures.
#
# This is deliberately a LIFT rather than a rewrite: fifty finished props sit
# in the work tree with parts_front.json files, and an intent schema nothing
# can produce is a design document, not a stage. Every field it can fill from
# a real measurement is marked MEASURED; every field it cannot is marked
# honestly and stays unverified all the way to the reducer.

def lift(parts_json, face="front"):
    """Turn a measured parts_<face>.json into typed, face-local intents."""
    W, H = parts_json.get("size", [1, 1])
    W, H = max(1, W), max(1, H)
    parts = parts_json.get("parts", [])

    # host: the smallest OTHER part that strictly contains this one. The
    # relation is measured, not asserted -- which is what makes it evidence.
    def host_of(p):
        x0, y0, x1, y1 = p["px"]
        a = (x1 - x0) * (y1 - y0)
        best, best_a = None, None
        for q in parts:
            if q is p:
                continue
            qx0, qy0, qx1, qy1 = q["px"]
            if not (qx0 <= x0 and qy0 <= y0 and qx1 >= x1 and qy1 >= y1):
                continue
            qa = (qx1 - qx0) * (qy1 - qy0)
            if qa <= a * 1.05:            # same box, not a host
                continue
            if best_a is None or qa < best_a:
                best, best_a = q["name"], qa
        return best

    out = []
    for p in parts:
        x0, y0, x1, y1 = p["px"]
        host = host_of(p)
        # the region is normalised WITHIN THE HOST when there is one, so a
        # button on a door keeps its place when the door moves or resizes --
        # which is the face-local promise applied one level down
        if host:
            h = next(q for q in parts if q["name"] == host)
            hx0, hy0, hx1, hy1 = h["px"]
            hw, hh = max(1, hx1 - hx0), max(1, hy1 - hy0)
            region = ((x0 - hx0) / hw, 1 - (y1 - hy0) / hh,
                      (x1 - hx0) / hw, 1 - (y0 - hy0) / hh)
            extent = (hw, hh)
        else:
            region = (x0 / W, 1 - y1 / H, x1 / W, 1 - y0 / H)
            extent = (W, H)

        # carried so a normalised region can be turned back into real units;
        # DERIVED because it is computed from measured boxes by a known rule
        ev_extent = DERIVED
        ev = {"region": MEASURED, "surface": DERIVED, "host": MEASURED if host
              else DEFAULT, "resize": PROPOSED, "role": PROPOSED}
        src = {"region": f"parts_{face}.json px, normalised to "
                         f"{'host ' + host if host else 'the face'}",
               "host": "measured containment" if host else "no containing box"}

        role = role_of(p)
        aspect = ROLE_ASPECT.get(role)
        ev["aspect"] = MEASURED if aspect else ABSENT
        if aspect:
            n = ROLE_ASPECT_N.get(role, "?")
            src["aspect"] = (f"{aspect[0]}-{aspect[1]} is the 10th-90th "
                             f"percentile of {n} measured {role!r} instances "
                             f"across the work tree")
        else:
            src["aspect"] = (f"role {role!r} has no measured range -- either "
                             f"fewer than 20 instances or it is 'unknown'")

        # THICKNESS IS NOT MEASURED ANYWHERE, and saying so is the point. The
        # elevations are flat: nothing in them says how far a coin slot is
        # recessed. "depth" is one of four adjectives chosen by a model, so it
        # is PROPOSED at best -- and a prop whose recesses are all proposed
        # cannot be called a reconstruction of its reference, however good it
        # looks. This single honest ABSENT is what stops the reducer saying
        # "accepted" about a prop nobody measured the depth of.
        # AND IT IS READ AS WHAT THE RENDERER ACTUALLY BUILDS, not as zero.
        # Writing 0 here and then failing the feature for "being paint" would
        # be this file committing the overclaim it exists to prevent, with the
        # sign reversed: the pipeline does give every part a stand-off from its
        # depth adjective, so the geometry is there. What it is NOT is
        # measured -- four adjectives chosen by a model, mapped to four
        # constants in the renderer, and no elevation anywhere says how far a
        # coin slot is recessed. That is exactly a DRAFT, and saying REJECTED
        # instead would be as wrong as saying ACCEPTED.
        thick = DEPTH_ADJECTIVE.get(p.get("depth") or "", 0.0)
        ev["extent"] = ev_extent
        ev["thickness"] = PROPOSED if p.get("depth") else ABSENT
        src["thickness"] = (f"depth adjective {p.get('depth')!r} -> "
                            f"{thick:+.3f} in parts_view DEPTH; no elevation "
                            f"measures depth")

        out.append(Feature(
            fid=p["name"], role=role, host=host, surface=face,
            region=region, aspect=aspect,
            thickness=abs(thick), extent=extent,
            appearance={"depth": p.get("depth"), "motion": p.get("motion")},
            resize=p.get("resize", "fixed"), evidence=ev, source=src))
    return out


def role_of(p):
    """A role from the name the model gave it, where the name is unambiguous.

    Names are the model's own words and this only reads the ones that map to a
    role with REQUIREMENTS attached. Everything else stays "unknown" -- a wrong
    role is worse than none, because it would impose a requirement the feature
    was never meant to meet.
    """
    n = (p.get("name") or "").lower()
    for key, role in (("window", "window"), ("screen", "screen"),
                      ("grille", "grille"), ("vent", "vent"),
                      ("slot", "slot"), ("button", "button"),
                      ("knob", "knob"), ("dial", "dial"),
                      ("handle", "handle"), ("door", "door"),
                      ("flap", "flap"), ("drawer", "drawer"),
                      ("tray", "drawer"), ("sign", "sign"),
                      ("marquee", "sign"), ("label", "label"),
                      ("decal", "decal"), ("leg", "member"),
                      ("foot", "member"), ("pillar", "member"),
                      ("column", "member"), ("upright", "member"),
                      ("plinth", "plinth"), ("panel", "panel"),
                      ("trim", "trim"), ("light", "light"),
                      ("tube", "member")):
        if key in n:
            return role
    return "unknown"


def _percentile(values, pct):
    """Linear-interpolation percentile, matching numpy.percentile's default.

    Not worth a numpy dependency for two calls; verified against
    numpy.percentile on the full corpus before trusting it (see the
    --measure-aspects output, which does not use numpy either).
    """
    s = sorted(values)
    n = len(s)
    if n == 1:
        return s[0]
    k = (n - 1) * pct
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def measure_role_aspects(work_dir, min_instances=20):
    """Re-derive ROLE_ASPECT from every parts_front.json under work_dir.

    Gathers the observed w/h of every part instance, grouped by role_of(),
    and reports the 10th/90th percentile for every role with at least
    min_instances observations -- min/max is not used because the corpus
    contains known-bad segmentations (a grille boxed at 52.75:1 on one prop,
    a decal at 39.4:1 on another) that would set a range wide enough to pass
    almost anything. "unknown" is excluded on principle, not by instance
    count: it is not a role, it is the record of role_of() finding none, so
    its members share no shape contract to measure.

    Returns {role: (lo, hi, n)}, rounded to 2 decimals, sorted by n
    descending -- this is the function that produced the ROLE_ASPECT and
    ROLE_ASPECT_N literals above. Rerun it (via --measure-aspects) when the
    work tree grows rather than hand-editing those dicts.
    """
    observed = {}
    for pf in sorted(Path(work_dir).glob("*/parts_front.json")):
        try:
            pj = json.loads(pf.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for p in pj.get("parts", []):
            x0, y0, x1, y1 = p["px"]
            w, h = x1 - x0, y1 - y0
            if w <= 0 or h <= 0:
                continue
            role = role_of(p)
            if role == "unknown":
                continue
            observed.setdefault(role, []).append(w / h)

    result = {}
    for role, vals in observed.items():
        if len(vals) < min_instances:
            continue
        # ROUNDED OUTWARD, not to nearest. Rounding a bound to 2dp can move
        # it PAST the very instance that defined the percentile: a speaker
        # grille measuring 8.574 set the p98 and then failed "8.57 outside
        # 0.27..8.57" on its own number.
        lo = math.floor(_percentile(vals, 0.02) * 100) / 100
        hi = math.ceil(_percentile(vals, 0.98) * 100) / 100
        result[role] = (lo, hi, len(vals))
    return dict(sorted(result.items(), key=lambda kv: -kv[1][2]))


# ---------------------------------------------------------------------------
# Per-instance checks. Each returns (status, note) for ONE feature.

def check_region(f):
    u0, v0, u1, v1 = f.region
    if u1 <= u0 or v1 <= v0:
        return FAIL, "region is empty or inverted"
    if f.ev("region") != MEASURED:
        return UNVERIFIED, f"region is {f.ev('region')}, not measured"
    if min(u0, v0) < -0.02 or max(u1, v1) > 1.02:
        return FAIL, f"region {tuple(round(v,3) for v in f.region)} leaves its host"
    return PASS, ""


def check_aspect(f):
    """Real aspect, never the normalised one. This file wrote the bug it warns about.

    `region` is normalised inside its host, so f.w and f.h are fractions of a
    box that is itself not square, and their ratio is the real aspect times the
    host's own inverse aspect. Measured on this cabinet: a screen whose pixel
    box is 244x171, real aspect 1.427, returns f.w/f.h = 3.429, because the
    face is 263x632 and 1.427 x (632/263) = 3.429 exactly.

    Compared against ranges derived from real pixel aspects, that scored 83 of
    95 props REJECTED -- and 335 of the 506 failures, 66%, were this artefact
    rather than a bad part. The docstring at the top of this file says a
    feature's w and h are local to its face and are not world axes; the same
    discipline says a NORMALISED local length is not a real one either, and
    only local_size() converts between them. check_aspect did not call it.

    That is the Astra finding reproduced inside the module written to prevent
    it, which is worth leaving on the record rather than quietly correcting.
    """
    if not f.aspect:
        return UNVERIFIED, "no aspect range given for this role"
    lo, hi = f.aspect
    w, h, _ = f.local_size(f.extent)
    if h <= 0:
        return FAIL, "zero height"
    a = w / h
    if a < lo or a > hi:
        return FAIL, f"aspect {a:.2f} outside {lo}..{hi}"
    return PASS, f"aspect {a:.2f}"


def check_thickness(f):
    """A role that must open or recess needs a thickness, and a measured one.

    This is the check the old system could not make, and the reason a painted
    slot counted as a slot. It does not invent a number -- it reports that the
    prop does not contain one.
    """
    if f.role not in NEEDS_OPENING and f.role not in NEEDS_RECESS:
        return PASS, "role needs no opening"
    e = f.ev("thickness")
    if e == ABSENT:
        return UNVERIFIED, (f"{f.role} must be a real "
                            f"{'opening' if f.role in NEEDS_OPENING else 'recess'}"
                            f" and no thickness is recorded")
    if f.thickness <= 0:
        return FAIL, f"{f.role} has thickness {f.thickness}, so it is paint"
    if e != MEASURED:
        return UNVERIFIED, f"thickness is {e}; no elevation measures depth"
    return PASS, ""


def check_host(f, by_id):
    if f.host is None:
        return PASS, "mounted on the body"
    if f.host not in by_id:
        return FAIL, f"host {f.host!r} is not a feature"
    if by_id[f.host].surface != f.surface:
        return FAIL, (f"mounted on {f.host} which is on "
                      f"{by_id[f.host].surface}, not {f.surface}")
    return PASS, ""


CHECKS = (("region", check_region), ("aspect", check_aspect),
          ("thickness", check_thickness))


def validate(features):
    """Every instance, every check, separately. No check speaks for two."""
    by_id = {f.id: f for f in features}
    rows = []
    for f in features:
        res = {}
        for name, fn in CHECKS:
            res[name] = fn(f)
        res["host"] = check_host(f, by_id)
        rows.append({"id": f.id, "role": f.role, "surface": f.surface,
                     "checks": {k: {"status": s, "note": n}
                                for k, (s, n) in res.items()}})
    return rows


# ---------------------------------------------------------------------------
# The central acceptance reducer.

def reduce_acceptance(rows):
    """One verdict for the prop, and it is three-valued on purpose.

    REJECTED      some instance failed a check outright
    DRAFT         nothing failed, but something is unverified. The prop may
                  comply with the prompt and look correct; it is not a fitted
                  reconstruction of the reference and must not be called one.
    ACCEPTED      every instance passed every check on MEASURED evidence.

    The middle state is the whole reason this exists. The system this replaces
    had two states and therefore called a prop built from synthesised parts a
    success, because the parts were there and were of the right type. Counting
    is not fitting.
    """
    fails, unver = [], []
    for r in rows:
        for cname, c in r["checks"].items():
            if c["status"] == FAIL:
                fails.append((r["id"], cname, c["note"]))
            elif c["status"] == UNVERIFIED:
                unver.append((r["id"], cname, c["note"]))
    verdict = REJECTED if fails else (DRAFT if unver else ACCEPTED)
    return {"verdict": verdict, "instances": len(rows),
            "failed": fails, "unverified": unver}





def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", help="a single prop dir, or -- with "
                    "--measure-aspects -- the work tree that holds them")
    ap.add_argument("--face", default="front")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--measure-aspects", action="store_true",
                    help="re-derive ROLE_ASPECT from prop_dir/*/parts_front.json "
                    "and print it; does not validate anything or write it back")
    args = ap.parse_args()

    if args.measure_aspects:
        table = measure_role_aspects(args.prop_dir)
        print(f"{'role':10} {'lo':>6} {'hi':>6} {'n':>6}   (10th/90th pct, n>=20)")
        for role, (lo, hi, n) in table.items():
            stale = " *** ROLE_ASPECT differs" if ROLE_ASPECT.get(role) != (lo, hi) else ""
            print(f"{role:10} {lo:6.2f} {hi:6.2f} {n:6}{stale}")
        dropped = sorted(set(ROLE_ASPECT) - set(table))
        if dropped:
            print(f"in ROLE_ASPECT but no longer >=20 instances: {dropped}")
        return

    d = Path(args.prop_dir)
    pj = json.loads((d / f"parts_{args.face}.json").read_text())
    feats = lift(pj, args.face)
    rows = validate(feats)
    verdict = reduce_acceptance(rows)
    (d / f"intent_{args.face}.json").write_text(json.dumps(
        {"features": [f.to_json() for f in feats],
         "validation": rows, "acceptance": verdict}, indent=1))

    if args.json:
        print(json.dumps(verdict, indent=1))
        return
    print(f"{d.name}: {verdict['verdict']}  "
          f"({verdict['instances']} instances, {len(verdict['failed'])} failed, "
          f"{len(verdict['unverified'])} unverified)")
    for i, (fid, c, note) in enumerate(verdict["failed"][:8]):
        print(f"   FAIL       {fid:24} {c:10} {note}")
    seen = set()
    for fid, c, note in verdict["unverified"]:
        if (c, note) in seen:
            continue
        seen.add((c, note))
        n = sum(1 for a, b, x in verdict["unverified"] if (b, x) == (c, note))
        print(f"   UNVERIFIED {c:10} x{n:<4} {note}")


if __name__ == "__main__":
    main()
