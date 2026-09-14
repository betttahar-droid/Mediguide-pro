# What to do next, in order

Ordered by what unblocks the most, not by what is most interesting. Each item
says what "done" means, because the failure recorded as mistake #1 is finishing
something that measures and calling it finished.

`PROGRESS.md` says what exists. `MISTAKES.md` says how it has gone wrong.

---

## 1. Wire the three standalone tools into the loop

**Why first.** `feature_intent`, `resize_policy` and `segment_audit` find 230
role contradictions, 33 under-segmented props and 291 unverified thicknesses,
and nothing reads any of it. A system that knows more and behaves identically
is the failure this whole redesign was meant to remove.

**Each needs a lever, not just a verdict.** The levers already exist:

| finding | lever |
|---|---|
| `resize_policy` disagree | rewrite the stored `resize`; 56 signs are the safest batch |
| `segment_audit` UNDER_SEGMENTED | re-run `segment_sheet` on that prop before building |
| `feature_intent` REJECTED | block the round, the way `repeat_score` does |
| `feature_intent` DRAFT | never call it accepted; it is the honest ceiling today |

**Done when:** a run that starts with a role contradiction ends without one, and
the verdict log shows the correction that removed it.

**Do not** let the policy silently overwrite a model's answer without recording
that it did. The disagreement is data — losing it loses the ability to tell a
bad role from a bad resize.

---

## 2. Measure depth from the reference

**Why second.** It is the only route to a meaningful `ACCEPTED`. Every opening
and every recess in this corpus rests on one of four adjectives mapped to four
constants. A grade nothing can score is not a grade.

**Where the evidence might be.** The side elevation sees depth edge-on; the top
view sees plan depth. `geometry_audit` already cross-checks the two ("side says
depth 0.60, plan says 0.83"), so the machinery for comparing them exists.

**Done when:** at least one role's thickness carries `MEASURED` evidence and
the acceptance sweep shows a prop reaching `ACCEPTED` on a feature that must
open or recess.

**Expect this to be partly impossible.** A flat elevation may simply not
contain the depth of a coin slot. If so, say which roles can be measured and
which cannot, and leave the rest `UNVERIFIED` — that is a result, and the
corpus has three precedents for it.

---

## 3. Operators

`slot_array`, `panel/window with a fixed rim and recessed backing`, `handle
with a real positive opening`, `analog scale with deterministic ticks`.

**Why third.** A role currently carries a requirement (`NEEDS_OPENING`) that
nothing can satisfy — there is no code that builds an opening. Operators are
what turn a label into buildable geometry, and they need (2) to know how deep
to cut.

**Done when:** a `slot_array` intent compiles to geometry with N real openings
and per-instance validation counts N, not "there is a slot".

---

## 4. The jukebox grey slab

Still open, and half traced. The extra height fills with dead grey; `raycast`
named it the carcass fill (world-space UVs, material 5), and the correct brown
tint *computes* — `rowRGB [53,43,33]` against a tile median of `[59,74,92]` —
and does not reach the screen. Not the atlas: `sheet=0` renders identically.

**Done when:** a taller jukebox's new body is its own wood colour.

---

## 5. Lift side and back decals

The growth band is measured on the front and applied to every face, so a prop
bare at the front and carrying artwork on its flank stacks that artwork down a
taller prop. Painting it off was tried and reverted (see `paint_out.py`): with
no `parts_side.json` there are no holes to composite through, and a band
composited into the original seams at both ends.

**Needs:** `decal_sheet` to record *where* the decals were. It already extracts
them.

---

## 6. Transactional per-feature repair

Today a patch rebuilds everything and can break features that were passing.
Unlock only the failed feature and its necessary ancestors.

**Done when:** a repair round can be shown to leave every previously-passing
instance byte-identical.

---

## 7. Staged reference fitting

Camera and root proportions → structural regions → feature placement → texture
placement → held-out validation, each stage reporting residuals rather than a
verdict.

---

## 8. The deterministic geometry compiler

**Still last, deliberately.** It wants operators (3) and measured depth (2) to
exist first, or it gets built twice.

---

## Standing rules for all of the above

- **Sweep before believing a threshold.** One command, and it has caught a
  fitted threshold three times.
- **Look at the renders.** A measure that improves while the pictures get worse
  is a measure, not the goal.
- **Revert loudly.** A reverted attempt with its numbers written down is worth
  more than a change that trades one fault for another.
- **Ask the scene before theorising.** `raycast.mjs` exists now.
- **Keep the model split.** Architecture and thresholds are expensive and rare;
  implementation against a written contract is cheap; counting, measuring and
  acceptance use no model at all.
