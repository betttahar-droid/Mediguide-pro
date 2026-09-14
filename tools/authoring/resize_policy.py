#!/usr/bin/env python3
"""How a feature resizes follows from WHAT IT IS, not from a per-part guess.

    python3 tools/authoring/resize_policy.py tools/img2threejs-work/v49_jukebox
    python3 tools/authoring/resize_policy.py --sweep

Authoring tool. NOT a build, CI or runtime dependency.

WHY. Every resize fault in the log is the same shape: something was stretched
that should have been counted, counted that should have been held, or held
that should have absorbed. Five stacked ARCADE marquees. A jukebox whose whole
height went into one leg. A vending machine that grew blank panel where
product columns belong. 181 of 306 blocking faults across three runs.

The tool's answer to each was to ask a model for a resize rule per part and
then let two judges argue about it. But a resize rule is not a matter of
opinion about that part -- it follows from the part's ROLE, by rules a person
could write down and never has:

    A SIGN DOES NOT REPEAT.      There is one marquee on a cabinet at any
                                 width. Repeating it is not a judgement call
                                 that came out wrong, it is a category error,
                                 and no amount of re-asking the model fixes a
                                 question that should never have been open.
    A MEMBER DOES NOT MULTIPLY.  A taller machine has longer legs, not more.
    A SLOT DOES NOT STRETCH.     A wider keypad has more buttons the same
                                 size, not the same buttons made wider.
    A PANEL IS WHAT ABSORBS.     Carcass is the only thing that may simply
                                 become more of itself.

So the policy is derived from the role, deterministically and for free, and
the model's per-part answer becomes a PROPOSAL that has to agree with it.
Where the two disagree, the disagreement is the finding: either the role is
wrong or the resize is, and both are worth knowing. That is the same division
this repo runs on -- the model names, arithmetic decides -- applied to a
decision that had been left entirely to naming.

WHAT THIS PREDICTS, which is how it is tested. If the policy is right, the
parts whose stored resize contradicts their role should be the parts that
produced the rendered faults. They are: the cabinet whose marquee is stored
spanx_repeat is the cabinet that stacked ARCADE five times.

FIDELITY IS THE POINT OF THE HOLD POLICIES. A sign, a screen, a label and a
decal carry the reference's own artwork, and the only way to stay faithful to
it at another size is not to touch it: hold the real size, insert the
difference in the plain material beside it. Everything that CAN be invented --
more panel, more slots, more buttons -- is invented; everything that was drawn
once stays drawn once.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_intent import lift, role_of  # noqa: E402

# The five things a feature can do when the prop changes size.
HOLD = "hold"          # keep real size, stay where it is; the difference goes
                       # into the material beside it
COUNT = "count"        # more of them, each at its real size
LENGTHEN = "lengthen"  # this one gets longer along its own long axis
ABSORB = "absorb"      # becomes more of itself; the carcass
FRAME = "frame"        # the surround stretches, the content inside does not

# ROLE -> (across, up). Two axes because they genuinely differ: a vending
# machine's window frames more columns across and more shelves up, while a
# cabinet's marquee holds across and holds up.
ROLE_POLICY = {
    # carries reference artwork -- touching it is the fidelity loss
    "sign":    (HOLD, HOLD),
    "screen":  (HOLD, HOLD),
    "label":   (HOLD, HOLD),
    "decal":   (HOLD, HOLD),
    "light":   (HOLD, HOLD),
    # comes in numbers; a bigger prop has more, the same size
    "slot":       (COUNT, COUNT),
    "slot_array": (COUNT, COUNT),
    "button":     (COUNT, COUNT),
    "button_grid": (COUNT, COUNT),
    "knob":    (COUNT, HOLD),
    "dial":    (HOLD, HOLD),
    # structure that simply gets longer
    "member":  (HOLD, LENGTHEN),
    "plinth":  (ABSORB, HOLD),
    "trim":    (ABSORB, HOLD),
    # the carcass: the only thing that may become more of itself
    "panel":   (ABSORB, ABSORB),
    # a surround whose contents are counted, not stretched
    "window":  (FRAME, FRAME),
    "grille":  (FRAME, FRAME),
    "vent":    (FRAME, FRAME),
    "drawer":  (FRAME, HOLD),
    # openable things keep their own proportions; a wider cabinet does not
    # have a wider door, it has a wider cabinet
    "door":    (HOLD, HOLD),
    "flap":    (HOLD, HOLD),
    "handle":  (HOLD, HOLD),
    "scale":   (HOLD, HOLD),
}

# What each policy means in the renderer's own vocabulary, so a disagreement
# is actionable rather than philosophical. These are the strings parts_view
# and part_slice already read.
POLICY_RESIZE = {
    HOLD: {"fixed"},
    ABSORB: {"spanx_repeat", "spany_repeat"},
    FRAME: {"spanx_center", "spany_center"},
    # COUNT and LENGTHEN are not resize rules at all -- they are the count
    # lever and the lengthens flag. A COUNT feature whose resize is anything
    # but "fixed" is being stretched AND counted, which doubles it.
    COUNT: {"fixed"},
    LENGTHEN: {"spany_center", "spany_repeat", "fixed"},
}


# A FRAME ROLE IS ONLY A FRAME IF IT ACTUALLY FRAMES SOMETHING.
#
# The first version gave every window, grille, vent and drawer FRAME on both
# axes, which is an assumption, and measuring it showed the assumption is
# wrong for 93% of them: of 154 frame-role features in the corpus, only 11
# contain two or more countable children. A small round window with nothing
# inside it is not a frame, it is a shape, and stretching it loses the
# reference's own proportions for no gain.
#
# But "no children" is ambiguous, and the ambiguity is the interesting part. A
# vending machine's display_window with 19 product children is a frame. The
# same window with none might be a plain sheet of glass -- or it might be a
# window whose products were never segmented, which is the single commonest
# defect in this corpus and the reason a widened machine grows blank panel.
#
# segment_audit tells those apart, so the two tools compose: a frame-role
# feature with no children that segment_audit flags as a SWALLOWED BOX has
# contents that were never lifted, and no policy can be decided for it until
# they are. That is an UNVERIFIED, not a guess -- the same vocabulary
# feature_intent uses, for the same reason.
COUNTABLE = {"slot", "button", "window", "light", "knob", "label", "decal"}
FRAME_ROLES = {"window", "grille", "vent", "drawer"}


def policy_for(role, kids=None, swallowed=False):
    """The policy for a role, given what it was measured to contain."""
    base = ROLE_POLICY.get(role, (None, None))
    if role not in FRAME_ROLES or kids is None:
        return base
    if kids >= 2:
        return base                       # it really does frame things
    if swallowed:
        return (None, None)               # contents not segmented; undecidable
    # nothing inside it and nothing hidden inside it: hold the drawn shape
    return (HOLD, HOLD)


def agrees(f, kids=None, swallowed=False):
    """Does this feature's stored resize agree with what its role requires?

    Returns (status, note). "unknown" roles cannot disagree with anything --
    that is what makes an honest unknown safe to carry.
    """
    across, up = policy_for(f.role, kids, swallowed)
    if across is None:
        if f.role in FRAME_ROLES:
            return "unverified", (f"{f.role} holds no segmented children and "
                                  f"segment_audit says something is hidden "
                                  f"inside it -- its contents decide the "
                                  f"policy and they were never lifted")
        return "unknown-role", f"{f.role} has no policy"
    r = f.resize or "fixed"
    want = POLICY_RESIZE[across] | POLICY_RESIZE[up]
    # a COUNT feature is allowed to be flagged per_bay/per_tier instead, which
    # the manifest records separately from resize
    counted = bool(f.appearance.get("per_bay") or f.appearance.get("per_tier"))
    if across == COUNT and counted and r == "fixed":
        return "agree", "counted"
    if r in want:
        return "agree", r
    return "disagree", (f"role {f.role} wants {across}/{up} "
                        f"({'|'.join(sorted(want))}), stored {r}")


def audit(parts_json, face="front", prop_dir=None):
    feats = lift(parts_json, face)
    # how many countable children each feature was MEASURED to contain
    kids = Counter()
    for f in feats:
        if f.host and f.role in COUNTABLE:
            kids[f.host] += 1
    # and which boxes segment_audit believes are hiding something
    swallowed = set()
    if prop_dir:
        try:
            import segment_audit
            r = segment_audit.audit(str(prop_dir), face)
            swallowed = {b["part"] for b in r.get("swallowed_boxes", [])}
        except Exception:
            pass
    rows = []
    for f in feats:
        st, note = agrees(f, kids.get(f.id, 0), f.id in swallowed)
        rows.append({"id": f.id, "role": f.role, "resize": f.resize,
                     "status": st, "note": note})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--face", default="front")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    if args.sweep:
        work = Path(__file__).resolve().parents[1] / "img2threejs-work"
        tally, byrole, worst = Counter(), Counter(), []
        props = 0
        for pj in sorted(work.glob("*/parts_front.json")):
            try:
                data = json.loads(pj.read_text())
            except Exception:
                continue
            if not data.get("parts"):
                continue
            props += 1
            rows = audit(data, "front", pj.parent)
            n = 0
            for r in rows:
                tally[r["status"]] += 1
                if r["status"] == "disagree":
                    byrole[r["role"]] += 1
                    n += 1
            if n:
                worst.append((n, pj.parent.name, rows))
        total = sum(tally.values())
        print(f"{props} props, {total} features")
        for k, v in tally.most_common():
            print(f"   {k:14} {v:5}  ({100*v/max(1,total):4.1f}%)")
        print("\ndisagreements by role:")
        for k, v in byrole.most_common(10):
            print(f"   {k:12} {v}")
        worst.sort(reverse=True)
        print("\nworst props:")
        for n, name, rows in worst[:6]:
            bad = [r for r in rows if r["status"] == "disagree"][:2]
            print(f"   {name:26} {n:3} disagreeing   "
                  + "; ".join(f"{b['id']}({b['role']}->{b['resize']})"
                             for b in bad))
        return

    d = Path(args.prop_dir)
    rows = audit(json.loads((d / f"parts_{args.face}.json").read_text()),
                 args.face, d)
    bad = [r for r in rows if r["status"] == "disagree"]
    unv = [r for r in rows if r["status"] == "unverified"]
    print(f"{d.name}: {len(bad)} of {len(rows)} features contradict their role"
          + (f", {len(unv)} undecidable" if unv else ""))
    for r in bad:
        print(f"   DISAGREE   {r['id']:22} {r['note']}")
    for r in unv:
        print(f"   UNVERIFIED {r['id']:22} {r['note']}")


if __name__ == "__main__":
    main()
