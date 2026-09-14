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

**Wired:** `rebuild()` calls it after `overlap_cut`, cached per part, so a prop
with no such part costs no call at all.

**Still to do:** it does not re-ask when the judges report the part still gaping,
the way `detail_sheet` re-asks a refused fitting. A refusal is a verdict on one
drawing, not on the part — that rule is in `CLAUDE.md` and this does not follow
it yet.

**And the taller axis needed something different, which is the finding.** Of 31
parts across the corpus carrying a `spany` rule, **zero** are tall,
non-countable and without a vertical band — the symmetry does not hold, because
a part that must lengthen is a leg, a column, a rail or a tube and those are
uniform along their length by what they are. The parts that carry art are wide.

The whole taller-axis need is the **body**: 16 props with nowhere bare to
repeat, whose carcass stretches. `tall_body.py` draws the extra carcass into the
band `strip_slice` vetoed — the bar that band failed is about *copying* rows
that carry artwork, and nothing in it forbids *drawing* new body there. Wired
into `rebuild()` and into the renderer; a drawn band is a growth band that does
not repeat, so `gOfT` places the parts and the taller texture paints the body,
and the two agree by construction.

Verified on `v49_jukebox` at 1.7×: the whole upper assembly at its drawn
proportions, the extra height as plain body beneath. Five faults were found
building it and all are in the file with their numbers.

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

**And so is `paint_out`, which was the other half of the premise and was also
already true.** "One model call per rebuild, which can come back different and
repaint holes that were fine" is not what happens: `rebuild()` never passes
`--redraw`, so the plate is bought once and cached, and two consecutive runs
produce a **byte-identical composite on every prop tried**. The only
non-deterministic step in `rebuild()` is non-deterministic once, not once a
round.

**Done anyway, because that safety was the cache's and not the design's.** Two
changes, both measured:

- **The last round's fills are carried forward** through `_painted_<face>_mask`
  rather than re-scored from scratch. A part leaves the queue only when every
  pixel of its *current* hole is already painted, so a part that moved or grew
  comes back and a hole that no longer exists cannot keep its fill. Verified
  exactly: adding a fitting to a finished prop changes **3465 pixels, every one
  of them inside the new hole and none outside it**.
- **A cached plate is checked against the question it was drawn from**, which is
  `_plate_in_<face>.png`, sitting on disk beside it. The cache was keyed on the
  plate *existing*. Across the corpus **4 of 14 props were scoring holes against
  a plate that had never been shown them** — the plate still has the fitting
  there, and what it paints is whatever happened to be at those coordinates.

  Honest about the size of this: the colour bar already refuses the loud cases
  (a fitting 53 away from its surroundings against a bar of 46), and **no prop
  in the corpus is known to have had a fitting painted back into its
  background**. What the check closes is the quiet case — a flush, low-contrast
  fitting, which is the exact thing `MISTAKES.md` records as unmeasurable by
  every other means.

**The change broke itself first, and the sweep is what caught it.** Writing the
magenta mask on every attempt overwrote the record of what had bought the plate,
so a round that carried all but one hole left a one-hole question behind and the
*next* round re-bought a drawing it already had. Two props. Tested on three, and
all three were the ones where it did not show.

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
