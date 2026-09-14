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
