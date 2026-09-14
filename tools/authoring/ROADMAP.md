# What to do next, in order

Ordered by what unblocks the most, not by what is most interesting. Each item
says what "done" means, because the failure recorded as mistake #1 is finishing
something that measures and calling it finished.

`PROGRESS.md` says what exists. `MISTAKES.md` says how it has gone wrong.

---

## 1. Wire the three standalone tools into the loop — **DONE**

`intent_gate` is the correcting channel. `apply_resize_policy` rewrites
contradictory rules for the unambiguous roles and logs every change to
`policy_log.json`; `segmentation_verdict` forces one re-draw before anything is
built on a bad decomposition; `acceptance` reaches the judge loop as faults and
is recorded in `verdicts.json`. Verified live on `v50_vending_machine`:
under-segmented → re-drawn 30→27 parts → two policy corrections → `REJECTED`
carried into round 0.

---

## 2. Measure depth from the reference — **DONE, and the answer is "you cannot"**

Three approaches, all swept, all recorded in `depth_probe.py`: edge shading
(recessed 9.64 / flush 8.08 / proud 8.92 — no separation at all), `profile.json`
(a simplified polyline, 1.0% MEASURED), and the raw side silhouette (6 of 1700,
every one a body section).

**A side silhouette traces the frontmost point at each height, so a recess never
touches it.** That is a fact about the reference format, not a threshold to
loosen. `UNMEASURABLE` and `FORMAT_LIMITS` exist so the verdict *declares* the
limit instead of blocking on it; 88 of 95 props now do.

**The one way out, not yet built:** a three-quarter reference view, which shows a
recess directly. That is a change to what the tool asks the image model for, and
it is the next thing worth spending money on.

---

## 2b. A three-quarter reference view

**The only route past (2), and therefore past a meaningful `ACCEPTED`.** Four
orthographic elevations cannot show a recess; one three-quarter view can. Every
`NEEDS_RECESS` role — window, screen, drawer — is stuck at `UNVERIFIED` until
one exists.

**Done when:** `depth_probe` returns `MEASURED` for a feature whose role
requires a recess, and the acceptance sweep shows a prop reaching `ACCEPTED` on
it.

**The risk to watch:** a generated three-quarter view is a *fifth* source that
can contradict the other four. It must be fitted as evidence with its own
residual, never used to overwrite an elevation — which is requirement 10 of the
spec, and the reason (7) exists.

---

## 2c. Buy the artwork that no rule can make — **BUILT, needs the loop to call it**

Raised by the user as "a big texture that gets unmasked as you scale". There is
no bigger drawing to unmask — the reference is one elevation at one size — but
the same idea works as a **purchase**: ask the image model for the missing width
only, for the parts that provably cannot grow.

**Which parts, measured:** 363 parts across the corpus ask for a span rule; 107
have no uniform band and no plain flank. Filtered to those that could actually
use a wider drawing — at least three quarters of the face, and not a role in
`COUNTABLE` — **21 parts across 17 props**, and the list is `marquee` ×8,
`backglass`, `arch_marquee`, `control_deck`, `title_strip_panel`.

**Done:** `wide_art.py` builds a canvas at the target aspect with the artwork in
the middle and the new width as flat magenta, composites the drawn artwork back
over the middle so only the ends are the model's, and refuses on aspect, on
leftover magenta, on palette, and on the ends being a copy of the middle. The
renderer loads it above the ratio it was drawn for. Verified on `v48_jukebox`.

**Still to do:** `make_prop` does not call it — it is a manual step today, so it
is a lever nothing pulls. It belongs in `rebuild()` after `layer_build`, and it
should re-ask when the judges report the part still gaping, the way
`detail_sheet` re-asks.

**And the taller axis has no equivalent.** Same argument, same 107-part
measurement, nothing built.

---

## 3. Operators

`slot_array`, `panel/window with a fixed rim and recessed backing`, `handle
with a real positive opening`, `analog scale with deterministic ticks`.

**Why third.** A role currently carries a requirement (`NEEDS_OPENING`) that
nothing can satisfy — there is no code that builds an opening. Operators are
what turn a label into buildable geometry, and they need (2b) to know how deep
to cut.

**Done when:** a `slot_array` intent compiles to geometry with N real openings
and per-instance validation counts N, not "there is a slot".

---

## 4. The jukebox grey slab — **DONE, from the other end**

The slab was the renderer's `MAX_REPS` fallback: eleven bare rows needed
twenty-eight copies at 1.7×, the run was marked `carcass`, and flat tile filled
half the cabinet. That choice was made between *repeating* and *flat*, because
stretching was not something `strip_slice` could ask for. It is now, and the
same prop is its own wood all the way down.

The tint path itself turned out to be sound — `tintFor(rowRGB(...))` is applied
per corner and `materials.json` does carry the `median` it needs. What was wrong
was reaching the fallback at all.

---

## 5. Lift side and back decals — **half done**

The growth band is measured on the front and applied to every face, so a prop
bare at the front and carrying artwork on its flank stacks that artwork down a
taller prop.

**Done:** every candidate band is now checked against the other elevations and
clean ones are preferred. `busy_elsewhere` had answered this since it was
written and was only ever called on the places the model names — 75 of the
corpus's 105 bands were measured runs and reached the renderer unasked.
Unchecked: 75 → 0.

**Still open:** 23 bands are known to carry flank artwork and are used anyway.
**Looked at, and the trade is right.** `v49_vending_machine` uses an unclean
band below its dispenser flap; `raycast` confirms the repeated bars are
`materialIndex 0`, the side texture, so this is the fault exactly. Forcing it to
the clean band alone — which is 17 rows against the 54 it needs, so it falls to
a stretch — is **much worse**: the display window detaches and slides up, a
blank panel floats across the DRINKS sign, and the products compress. Four
stacked bin lips and a duplicated flank vent is the better of the two.

So do not veto unclean bands. The gain here is only that they are now *known*,
and the real fix is below.

**The real fix needs** `decal_sheet` to record *where* the decals were, so they
can be painted off the flank. Painting off was tried and reverted (see
`paint_out.py`): with no `parts_side.json` there are no holes to composite
through, and a band composited into the original seams at both ends.

---

## 6. Transactional per-feature repair — **smaller than it looked**

**Measured, and the deterministic half is already transactional.** Two identical
rebuilds produce **38 byte-identical artefacts** — every part texture, the
background, the layer manifest, the strips, the slice. Patching one part's
resize and rebuilding changes nothing about any other part. The premise that "a
patch rebuilds everything and can break features that were passing" is not true
of the arithmetic.

**What is left is `paint_out`**, one model call per rebuild, which can come back
different and repaint holes that were fine. That is the only non-deterministic
step in `rebuild()`, and the transactional version of it is: re-ask only for the
holes belonging to features that failed, and keep the rest of the plate.

**Found while measuring this, and fixed separately:** the judge's resize patch
was being silently discarded for 265 parts across 76 props. See the commit — a
judge that looked at the render has evidence the namer did not, and a patch the
geometry genuinely refuses is now quoted back instead of vanishing.

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
