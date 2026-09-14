#!/usr/bin/env python3
"""The lever for the three tools that only measured. One entry point per act.

    python3 tools/authoring/intent_gate.py work/ps1 --apply
    python3 tools/authoring/intent_gate.py work/ps1 --report

Authoring tool. NOT a build, CI or runtime dependency.

WHY. feature_intent, resize_policy and segment_audit between them find role
contradictions, swallowed boxes and unverified thicknesses across the whole
corpus, and until this file existed NOTHING IN THE PIPELINE READ ANY OF IT.
That is the failure the redesign was meant to remove, in a new costume: a
system that knows a great deal more than it did and behaves identically. It is
also the rule in CLAUDE.md -- anything that can block must be able to correct
-- broken by the very work written to honour it.

So this is the correcting channel, and it does three separate things because
the three findings act at three different points in the run:

    SEGMENTATION   segment_audit says a box swallowed its contents, before
                   anything is built on that decomposition
    RESIZE         resize_policy says a feature's stored rule contradicts what
                   it IS, before the layers are cut
    ACCEPTANCE     feature_intent says whether the prop may be called fitted,
                   at the point the judges are asked

WHAT IT WILL AND WILL NOT CORRECT, which is the whole design.

It rewrites a resize rule ONLY for roles whose policy is unambiguous -- the
ones that carry the reference's own artwork and the ones that come in numbers.
A sign that repeats is a category error, measured at 56 instances in the
corpus, and correcting it cannot be wrong. It does NOT touch FRAME or ABSORB
roles: measuring that assumption showed it was wrong for 93% of frame-role
features, and a policy I have already caught being over-confident does not get
write access on the strength of having been fixed once.

AND EVERY CORRECTION IS RECORDED, in policy_log.json beside the prop. The
disagreement is data: it says either the role is wrong or the resize is, and
silently overwriting one destroys the ability to tell which. A future pass that
finds the policy corrected a part the judges then complained about needs to be
able to see that it did.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_intent import (lift, validate, reduce_acceptance,  # noqa: E402
                            REJECTED, DRAFT)
from resize_policy import (audit as policy_audit, POLICY_RESIZE,  # noqa: E402
                           policy_for, HOLD, COUNT)

# Roles whose policy is unambiguous enough to write. HOLD roles carry the
# reference's own artwork; COUNT roles come in numbers. Both are category
# facts, not judgements about a particular prop.
#
# Deliberately excludes every FRAME and ABSORB role. See the docstring: that
# assumption measured wrong for 93% of the features it covered, and a rule
# that has already been caught over-reaching does not get write access.
SAFE_TO_CORRECT = {"sign", "screen", "label", "decal", "light",
                   "slot", "slot_array", "button", "button_grid"}


def apply_resize_policy(prop_dir, face="front"):
    """Rewrite resize rules that contradict an unambiguous role.

    Returns the list of corrections made. Writes parts_<face>.json in place and
    appends to policy_log.json.
    """
    d = Path(prop_dir)
    pj_path = d / f"parts_{face}.json"
    try:
        pj = json.loads(pj_path.read_text())
    except Exception:
        return []
    if not pj.get("parts"):
        return []

    rows = {r["id"]: r for r in policy_audit(pj, face, d)}
    feats = {f.id: f for f in lift(pj, face)}
    fixed = []
    for p in pj["parts"]:
        r = rows.get(p["name"])
        if not r or r["status"] != "disagree":
            continue
        f = feats.get(p["name"])
        if not f or f.role not in SAFE_TO_CORRECT:
            continue
        across, up = policy_for(f.role)
        want = POLICY_RESIZE[across] | POLICY_RESIZE[up]
        # "fixed" is in every safe policy's permitted set, and it is the
        # conservative choice: a part held at its drawn size is the one
        # outcome that cannot invent anything that was not in the reference.
        new = "fixed" if "fixed" in want else sorted(want)[0]
        if p.get("resize") == new:
            continue
        fixed.append({"part": p["name"], "role": f.role,
                      "was": p.get("resize"), "now": new, "why": r["note"]})
        p["resize"] = new
        # AND THE PATCH MARK GOES WITH IT. layer_build lets a judge's rule
        # survive the structure guard -- a judge looked at the render, the
        # namer did not -- which would otherwise let a judge make a SIGN repeat
        # and put it past the one check that catches that. A rule this file has
        # just overruled is no longer the judge's, so it must not carry the
        # judge's exemption.
        p.pop("patched_resize", None)
        # A COUNT ROLE THAT WAS STRETCHED IS USUALLY ALSO COUNTED, and the two
        # together multiply it twice. v49_vending_machine/decal_1 was patched
        # resize=spanx_repeat AND count=both in one round, which is how a decal
        # ends up laid down in a grid. Holding it is only half the fix.
        if across == COUNT and f.role in ("slot", "button", "slot_array",
                                          "button_grid"):
            pass                      # counting these IS correct; leave flags
        elif p.get("per_bay") or p.get("per_tier"):
            fixed[-1]["also"] = "cleared per_bay/per_tier"
            p["per_bay"] = p["per_tier"] = False

    if fixed:
        pj_path.write_text(json.dumps(pj, indent=1))
        log = d / "policy_log.json"
        try:
            prev = json.loads(log.read_text())
        except Exception:
            prev = []
        prev.append({"face": face, "corrections": fixed})
        log.write_text(json.dumps(prev, indent=1))
    return fixed


_SIDE = re.compile(r"(^|_)(left|right)(?=_|$|\d)", re.I)


def apply_side_names(prop_dir, face="front"):
    """A part named `left` that sits on the right is misnamed, and the drawing
    says which it is.

    "The model authors and names; arithmetic measures and verifies" -- this is
    the NAME being verified, which nothing had done. A part's IDENTITY is
    authorship and stays untouched: whether a thing is a joystick, a coin
    button, a bubbler tube is not something pixels can settle. Which SIDE of the
    machine it stands on is not an opinion.

    Measured across the corpus: 361 parts carry a left or a right in their name
    and 49 of them, on 19 of 58 props, sit on the other side. The pattern says
    what happened -- they come in SWAPPED PAIRS (joystick_left with
    joystick_right, coin_button_left with coin_button_right, grille_post_left
    with grille_post_right), which is the model naming from the machine's own
    left, as you would describe a person's left hand. That is a defensible
    convention and it is not the one anything downstream uses: the renderer, the
    exported rig and the judges all work in the viewer's frame, so a mesh called
    bubbler_tube_left standing at the right-hand end of the cabinet misleads
    every one of them and anyone who opens the asset afterwards.

    A SWAP IS ONLY APPLIED WHOLE. Renaming one half of a pair would collide with
    the other half, so the new names are computed first and applied only if they
    are still all distinct; a rename that would collide is reported and skipped
    rather than silently dropping a part.
    """
    d = Path(prop_dir)
    pj_path = d / f"parts_{face}.json"
    try:
        pj = json.loads(pj_path.read_text())
    except Exception:
        return []
    W = (pj.get("size") or [1, 1])[0]
    parts = pj.get("parts", [])
    rename, seen = {}, {p.get("name") for p in parts}
    for p in parts:
        n = p.get("name") or ""
        m = _SIDE.search(n)
        if not m or not p.get("px"):
            continue
        xc = (p["px"][0] + p["px"][2]) / 2 / max(1, W) - 0.5
        # ON THE CENTRELINE THERE IS NO SIDE TO BE WRONG ABOUT. A start button
        # dead centre named `_right` is naming a pair position, not a place.
        if abs(xc) < 0.02:
            continue
        want = "right" if xc > 0 else "left"
        has = m.group(2).lower()
        if has == want:
            continue
        rename[n] = n[:m.start(2)] + want + n[m.end(2):]
    if not rename:
        return []
    # DROP ONLY THE RENAMES THAT COLLIDE, NOT THE PROP. Refusing the whole prop
    # on one collision cost 38 good corrections out of 49: v38_arcade_cabinet
    # has coin_door and coin_slot cleanly swapped and ONE cashbox_door_left with
    # no partner to trade with, and all five were abandoned for the sake of the
    # one. A rename is impossible only when some other part will still be
    # holding the name it wants -- so drop those and look again, because
    # dropping one can leave a name occupied that had been about to be vacated.
    names = [p.get("name") for p in parts]
    while True:
        clash = [s for s, t in rename.items()
                 if any(n != s and rename.get(n, n) == t for n in names)]
        if not clash:
            break
        for s in clash:
            print(f"    side: {s} sits on the other side but "
                  f"{rename[s]} is taken -- left alone")
            del rename[s]
    if not rename:
        return []
    for p in parts:
        if p["name"] in rename:
            p["name"] = rename[p["name"]]
    pj_path.write_text(json.dumps(pj, indent=1))
    log = d / "policy_log.json"
    try:
        prev = json.loads(log.read_text())
    except Exception:
        prev = []
    prev.append({"face": face, "side_names":
                 [{"was": a, "now": b} for a, b in rename.items()]})
    log.write_text(json.dumps(prev, indent=1))
    for a, b in rename.items():
        print(f"    side: {a} sits on the other side -- {b}")
    return [{"was": a, "now": b} for a, b in rename.items()]


# A STICK IS TALLER THAN IT IS WIDE. That is the whole of what makes it one.
#
# 3.5 is measured, not chosen. Setting the motion to `none` on each stick part
# in the corpus and re-scoring its outlines against the three elevations:
#
#   w/h    prop / part                         side+top change
#   10.81  v8_arcade_cabinet/joystick_left          +0.141
#    4.38  v20_arcade_cabinet/joystick              +0.055
#    3.71  v13_arcade_cabinet/joystick_left         +0.058
#   ------------------------------------------------ 3.5
#    3.20  v41_arcade_cabinet/joystick_ball_2       +0.000
#    2.61  v28_arcade_cabinet/joystick_ball         -0.001
#    2.13  v41_arcade_cabinet/joystick_ball         +0.001
#    1.77  v42_arcade_cabinet/joystick_left         -0.048
#
# Everything above the line gains a lot; everything below it is neutral or is
# made worse. The three neutral ones are joystick BALLS -- the knob on top of a
# shaft really is wider than it is tall, and it is small enough that how it is
# built changes nothing. The one at 1.77 is a real joystick, and treating it as
# a flat panel costs 0.048 and pulls the FRONT down too, 0.984 to 0.953.
STICK_MAX_WH = 3.5


def apply_stick_shape(prop_dir, face="front"):
    """A part that pivots like a stick has to be shaped like one.

    The renderer builds a `stick` part as an upright standing off the surface it
    is mounted on, pivoting about its bottom edge -- which is what a joystick
    is. Handed a box that is ten times wider than it is tall, it builds a SLAB
    standing off a sloped control deck, and that is not a joystick, it is a
    wing.

    v8_arcade_cabinet is the case. Its `joystick_left` is 0.556 of the prop's
    WIDTH -- the segmenter boxed most of the control deck and called it a
    joystick -- and built as a stick it adds 18% to the prop's whole side
    silhouette, ten times more than any other part on the machine. Its side
    outline scores 0.889 against the elevation where the body alone scores
    0.993. One field, and it goes to 0.975 with the top following from 0.909 to
    0.963.

    THE IDENTITY IS NOT TOUCHED, only the mechanism. Whether the thing is a
    joystick is the model's call and it is probably right -- there IS a joystick
    in that box, along with half a control panel. What the geometry can settle
    is that a box this shape cannot move the way a stick moves, and building it
    as one costs more than leaving it still.
    """
    d = Path(prop_dir)
    pj_path = d / f"parts_{face}.json"
    try:
        pj = json.loads(pj_path.read_text())
    except Exception:
        return []
    size = pj.get("size") or [1, 1]
    fixed = []
    for p in pj.get("parts", []):
        if p.get("motion") != "stick" or not p.get("px"):
            continue
        w = (p["px"][2] - p["px"][0]) / max(1, size[0])
        h = (p["px"][3] - p["px"][1]) / max(1, size[1])
        if h <= 0 or w / h <= STICK_MAX_WH:
            continue
        fixed.append({"part": p["name"], "was": "stick", "now": "none",
                      "w_over_h": round(w / h, 2),
                      "why": f"a stick is taller than it is wide; this box is "
                             f"{w / h:.1f}x wider, so built as one it is a slab"})
        p["motion"] = "none"
    if not fixed:
        return []
    pj_path.write_text(json.dumps(pj, indent=1))
    log = d / "policy_log.json"
    try:
        prev = json.loads(log.read_text())
    except Exception:
        prev = []
    prev.append({"face": face, "stick_shape": fixed})
    log.write_text(json.dumps(prev, indent=1))
    for c in fixed:
        print(f"    stick: {c['part']} is {c['w_over_h']}x wider than tall -- "
              f"it cannot pivot like a stick")
    return fixed


def segmentation_verdict(prop_dir, face="front"):
    """UNDER_SEGMENTED / LEAD / OK, with the parts named."""
    try:
        import segment_audit
        r = segment_audit.audit(str(prop_dir), face)
    except Exception as e:
        return {"verdict": "unavailable", "why": type(e).__name__}
    return {"verdict": r.get("verdict", "OK"),
            "swallowed": [b["part"] for b in r.get("swallowed_boxes", [])
                          if b not in r.get("leads", [])],
            "bands": len(r.get("missing_bands", [])),
            "leads": [b.get("part") for b in r.get("leads", [])]}


def acceptance(prop_dir, face="front"):
    """The three-valued verdict, as faults the judge loop can carry."""
    d = Path(prop_dir)
    try:
        pj = json.loads((d / f"parts_{face}.json").read_text())
    except Exception:
        return None
    if not pj.get("parts"):
        return None
    v = reduce_acceptance(validate(lift(pj, face)))
    faults = []
    for fid, check, note in v["failed"]:
        faults.append({"part": f"{fid} (intent)", "severity": "blocking",
                       "fault": f"{check}: {note}"})
    return {"verdict": v["verdict"], "faults": faults,
            "unverified": len(v["unverified"]), "instances": v["instances"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir")
    ap.add_argument("--face", default="front")
    ap.add_argument("--apply", action="store_true",
                    help="rewrite resize rules that contradict a safe role")
    args = ap.parse_args()

    d = Path(args.prop_dir)
    seg = segmentation_verdict(d, args.face)
    print(f"segmentation: {seg['verdict']}"
          + (f"  swallowed={seg.get('swallowed')}" if seg.get("swallowed") else "")
          + (f"  leads={seg.get('leads')}" if seg.get("leads") else ""))

    if args.apply:
        fixed = apply_resize_policy(d, args.face)
        print(f"resize policy: {len(fixed)} correction(s)")
        for c in fixed:
            print(f"   {c['part']:24} {c['role']:7} {c['was']} -> {c['now']}"
                  + (f"  ({c['also']})" if c.get("also") else ""))
    else:
        pj = json.loads((d / f"parts_{args.face}.json").read_text())
        bad = [r for r in policy_audit(pj, args.face, d)
               if r["status"] == "disagree"]
        print(f"resize policy: {len(bad)} contradiction(s), "
              f"--apply would correct the safe ones")

    a = acceptance(d, args.face)
    if a:
        print(f"acceptance: {a['verdict']}  ({a['instances']} instances, "
              f"{len(a['faults'])} blocking, {a['unverified']} unverified)")


if __name__ == "__main__":
    main()
