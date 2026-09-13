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


class Feature:
    """One instance. Never a kind, never a group."""

    __slots__ = ("id", "role", "host", "surface", "region", "thickness",
                 "aspect", "appearance", "resize", "evidence", "source")

    def __init__(self, fid, role="unknown", host=None, surface="front",
                 region=(0.0, 0.0, 1.0, 1.0), thickness=0.0, aspect=None,
                 appearance=None, resize="fixed", evidence=None, source=None):
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
                "evidence": self.evidence, "source": self.source}

    @staticmethod
    def from_json(d):
        return Feature(d["id"], d.get("role"), d.get("host"),
                       d.get("surface", "front"),
                       d.get("region", (0, 0, 1, 1)), d.get("thickness", 0.0),
                       d.get("aspect"), d.get("appearance"),
                       d.get("resize", "fixed"), d.get("evidence"),
                       d.get("source"))


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
        else:
            region = (x0 / W, 1 - y1 / H, x1 / W, 1 - y0 / H)

        ev = {"region": MEASURED, "surface": DERIVED, "host": MEASURED if host
              else DEFAULT, "resize": PROPOSED, "role": PROPOSED}
        src = {"region": f"parts_{face}.json px, normalised to "
                         f"{'host ' + host if host else 'the face'}",
               "host": "measured containment" if host else "no containing box"}

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
        ev["thickness"] = PROPOSED if p.get("depth") else ABSENT
        src["thickness"] = (f"depth adjective {p.get('depth')!r} -> "
                            f"{thick:+.3f} in parts_view DEPTH; no elevation "
                            f"measures depth")

        out.append(Feature(
            fid=p["name"], role=role_of(p), host=host, surface=face,
            region=region, aspect=None,
            thickness=abs(thick),
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
    if not f.aspect:
        return UNVERIFIED, "no aspect range given for this role"
    lo, hi = f.aspect
    if f.h <= 0:
        return FAIL, "zero height"
    a = f.w / f.h
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
    ap.add_argument("prop_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

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
