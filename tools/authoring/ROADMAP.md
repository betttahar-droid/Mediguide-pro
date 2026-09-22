# What to do next, in order

Ordered by what unblocks the most, not by what is most interesting. Each item
says what "done" means, because the failure recorded as mistake #1 is finishing
something that measures and calling it finished.

`PROGRESS.md` says what exists. `MISTAKES.md` says how it has gone wrong.

---

## 0. START HERE — the live state, as of the last session

Everything below this section is history, ordered by what unblocks what. This
section is the handover: what is in flight, what is measured, what to do first.

### First, re-baseline. The measurements are not in the repo.

`geometry_sweep` diffs against a saved baseline, and that baseline is scratch —
it does not survive a fresh clone. Take one before changing anything, or the
first sweep will look like a catastrophe:

```bash
npx vite --port 5173 &                                  # anything that renders needs this
python3 tools/authoring/geometry_sweep.py --save        # ~8 min, writes the baseline
python3 tools/authoring/scale_check.py                  # 94/98 expected
```

The 98-prop corpus is gitignored. If `tools/img2threejs-work/` is empty:

```bash
git fetch origin corpus-data
git checkout corpus-data -- tools/img2threejs-work
git checkout claude/prop-maker-tool-repo-xun9e0
```

### The one open fault, and it costs money to close

`paint_out` was accepting fills that **redrew** the fitting instead of removing
it — 20% of 469 accepted holes, measured by comparing each fill against the
original drawing inside the same hole (bimodal: a cluster near zero, the bulk
past 20). The background plate is what a resize repeats, so a fitting left in
the plate is stamped down the prop. That is the judges' commonest complaint:
149 of 457 logged faults mention a repeat, 58 say "mirrored".

**The gate is in** (`--same-bar 6.0`) so no new plate can carry this. **The
built props keep their bad plates** until `paint_out` is re-run — one image per
prop, about $0.034 each. Worst first, by how little the plate differs from the
drawing inside its fitting boxes (corpus median 36.67):

| prop | plate | mirror/duplicate faults logged |
|---|---|---|
| `v45_jukebox` | 7.59 | **41** — more than every other prop combined |
| `v44_jukebox` | 11.43 | |
| `v45_pinball` | 14.78 | 2 |
| `v51_pinball` | 17.02 | 4 |
| `v45_vending_machine` | 17.67 | 5 |

Do five, verify the gate rejects a repeat offence, then widen. After each,
re-compare plate against drawing per hole — that check is the evidence, not the
model's word.

### The other open axis, which is free to work on

24 props still band when made 1.5× taller (down from 57). Copies is no longer
the cause for most of them — they sit at 4 or fewer. Worst first:

```
v36_arcade_cabinet +0.63   v13_arcade_cabinet +0.60   v8_vending_machine  +0.57
v48_arcade_cabinet +0.53   v7_arcade_cabinet  +0.49   v49_jukebox         +0.46
v42_arcade_cabinet +0.46   v5_jukebox         +0.45   v27_arcade_cabinet  +0.44
v32_arcade_cabinet +0.38   v7_jukebox         +0.38   v12_vending_machine +0.37
```

`v49_jukebox` has no growth band at all and stretches; `v27_arcade_cabinet`
regressed identically with and without its authored place, so its cause is
something else.

### Five hypotheses already disconfirmed — do not re-derive them

Each cost an hour and each is the obvious next idea:

- **A tilted plan is a perspective view.** No: measured taper correlates with
  the top outline at −0.180, and the most tapered plan in the corpus scores
  above median. The plans are honest outlines that disagree about *scale*.
- **A ledge inside the growth band causes banding.** No: corr +0.025, banding
  and clean props indistinguishable (17.19 vs 16.93).
- **A bezel should be roled as trim.** No: 10 of 11 such parts pass already.
- **Skip the aspect check on side-word names.** No: 393 of 405 pass.
- **Horizontal duplication is detectable in the render.** Four ways tried — row
  autocorrelation, its transpose, mirror symmetry, scene-graph instance counts.
  All failed. The cause was upstream in `paint_out`, not in the resize.

### A sixth hypothesis, measured this session and reverted

- **The growth band is chosen on rows that are not the prop, and stopping that
  fixes the tall axis.** HALF RIGHT, AND THE HALF THAT IS WRONG IS THE FIX.
  `object_crop` returns a bounding box and a prop is not a rectangle, so above a
  marquee, around a jukebox's dome and below its feet the crop holds sheet.
  Sheet passes both tests `bare()` applies -- no segmenter boxes the sky, and
  the sky is the quietest thing on any drawing -- so the chooser PREFERS it:

  ```
  rows under 80% inside the silhouette
    of every row in the corpus          5.9%
    of rows already in a growth band   16.1%      a 2.7x enrichment
  ```

  Three props' bands are ENTIRELY sheet (prop_jukebox 42 rows of sky above its
  dome, v7_jukebox 60, v44_pinball 44) and 24 have one that is mostly sheet.
  v13_arcade_cabinet stacks four white bars over its marquee at 1.5x tall.

  Removing them does not fix the axis. Two forms, both measured against a
  before-set of 76 props, both reverted:

  ```
  row-level (a sheet row is never a candidate)    50 props measured twice
      median rise +0.097 -> +0.091   banding 14 -> 16
      better 12  worse 13            crossed the bar: fixed 5, broken 7
  run-level (skip a run that is majority sheet)   18 props measured twice
      median rise +0.200 -> +0.195   banding  8 ->  9
      better  4  worse  4            crossed the bar: fixed 1, broken 2
  ```

  Flat both times, the identity of the broken props changing and not their
  number, which is the shape CLAUDE.md says to revert on. THE REASON IS
  STRUCTURAL AND ALREADY IN THIS FILE: removing a bad band does not create a
  good one, it concentrates the growth into whatever is left. prop_jukebox has
  other bare rows and went +0.301 -> **-0.185**; v24_arcade_cabinet has none,
  so the height moved into the vent stack above its screen and it went +0.045
  -> +0.276 -- and there the render agrees with the number, six stacked grilles
  instead of four plus three bars of sky.

  So a prop whose only spare rows are sheet is a prop with **nowhere to grow**,
  and the answer for it is `tall_body` (section 2c), not a choice of band.

  Worth keeping even though the fix was not: `silhouette()` exists because
  layer_build once picked a jukebox's dome as "clean panel", and the band
  chooser never got the same fix. Anyone reaching for a coverage test should
  know it has been tried twice and what it costs.

- **`repeat_score` inverted again, on exactly this class of change.** CLAUDE.md
  records one counterexample (v48, the artwork test); this is a second.
  ps1_arcade scored its worst of the session, +0.180 -> +0.552, on a render
  that LOST two stacked lower panels and their hard white seams and became one
  continuous panel. Eight of the eighteen props above moved by exactly 0.000
  while their stacked sky disappeared. Judge this axis on the pictures.

### What the corpus branch does not carry, and what that breaks

`corpus-data` has the manifests and the part crops but NOT the derived rasters.
100 of 104 props reference a `body_side/back/top.png` that is absent; the
renderer's `load()` is unguarded there, so every render fails and
`geometry_sweep` prints `all three >= 0.95: 0/98`, which reads as catastrophe
and means "nothing rendered". `body_faces.py` rebuilds them for free and its
`body.json` comes back byte-identical to the committed one. `seamless_tile.py`
does NOT reproduce its committed manifest (size 24 -> 56), so leave
`tile_front.png` missing: the renderer falls back and the silhouette is
unaffected.

18 props cannot be rendered at 1.5x tall at all from a clean checkout -- they
name purchased `tall_body` / `side_other` art the branch does not carry, and
the tall-flank load is the one not wrapped in a try.

On Windows, `geometry_audit.shoot` defaults CHROMIUM_PATH to a Linux path, with
the same silent-empty-render result.

### ONE PROMPT IN, A BUILT PROP OUT -- and what it still gets wrong

With `_gemini_text` wired in (the brief is the one ask nothing can check, so it
is the one that must be bought -- $0.004 per prop), `auto_prop "arcade cabinet"`
followed by `make_prop --skip-sheet --rounds 1` runs the whole way with nobody
in the loop. On `final_arcade_cabinet`:

```
sheet        front/side/back 312x738, 309x738, 306x738; flat elevations
materials    5/6 tile cleanly: wood, scratched_metal, speaker_cloth,
             teal_paint, vent_mesh, worn_wood
segmentation 17 parts; 16 overlaps cut (joystick out of control_deck, ...)
geometry     front 99.7%  side 93.4%  top 94.4% outline vs its own drawings
glTF         37 nodes, 19 meshes, 17 named parts, mechanism per part:
             joystick=stick, button_1..6=press, coin_door=hinge_left,
             coin_slot_left/right=press
2x wide      37 -> 61 nodes. joystick 1->2, button_1..6 each 1->2,
             instruction_card 1->2, while the marquee text and coin door
             HOLD their drawn size. A two-player cabinet, not a stretch.
resize audit 5 adaptations judged, 5 FAIL
```

**The instancing works and the ARTWORK does not**, which is the same fault
class as the growth-band entry above, reproduced on a fresh prop by the loop's
own judge: the screen bezel repeats into three CRT bulges at 2x, the marquee
band tiles behind "ARCADE HEROES", the kickplate counters duplicate. Run with
`--rounds 1`, so it stopped after round 0 rather than attempting the
corrections it had just diagnosed. **Next: more rounds, and see whether the
judge's patches actually close any of the five.**

Two gaps this run exposes that are not in any list yet:
  - the exported glTF has **0 animation clips**. The rig is posable and the
    motion is recorded per part in `extras`, but an importer must drive it
    rather than press play. Bake a clip per `motion` on export.
  - `image_ledger` records 42 calls at $0.0000 -- the DIRECT Gemini image path
    does not report a price, only the OpenRouter one does, so the ledger cannot
    answer "what did this cost" for the path the tool actually uses.

### The one-prompt run, traced end to end, and the ONE stage that fails

Run from the words "arcade cabinet" with nobody in the loop: brief on local
Ollama (qwen2.5:3b), images on Nano Banana, segmentation and judging on local
qwen2.5vl. Every stage behaved correctly. The trace:

```
[1/4] brief        3 perspective faults caught, re-asked, struck
                   subject: "a rectangular box, 10 x 10 x 10 units,
                             front face red, back face blue"        <- THE FAULT
[2/4] four views   gate 4/4 PASS
[3/4] cross-view   front=side=back=top=654x675   PASS
      front.png is a proper flat elevation (the ELEVATION clause works)
[1b]  materials    6/6 tile cleanly: body_panel, wood, metal_trim,
                   vent_mesh, dark_rubber, worn_panel
      decals       0 survived keying -- "drawn as a panel, not a decal"
                   (non-blocking by design)
[2]   segmentation 3 draws, all rejected: silhouette 99.9% (needs 88) but
                   borders on real edges 21.0% (needs 55)
                   -> fell back to measuring the regions
      measurement  "no regions found -- the elevation reads as all panel"
      BUILD STOPS  "neither segmentation nor measurement produced parts"
```

**AND THAT IS THE CORRECT ANSWER TO A CUBE.** The elevation really is all
panel, because the subject really is a cube; there are no fittings to find and
the build refuses rather than shipping a one-mesh box. Segmentation's fallback
fired, the border check caught a bad decomposition, the material atlas proved
six tiles, the projection clause held. Every verified stage did its job.

So the one-prompt path has exactly ONE broken stage left, and it is the one
stage NOTHING CAN CHECK: the subject. `brief_faults` can prove a view
instruction does not ask for perspective; no arithmetic separates "a tall
cabinet on a plinth with a marquee hood, a bezel-framed screen, an angled
control panel holding a joystick and six buttons" from "a rectangular box, 10 x
10 x 10, front face red". The corpus brief that produced usable props is the
first; a 3B model writes the second, and everything downstream then behaves
perfectly on a cube.

**DONE for this item means:** `author_brief` on a capable model, and the same
command carried through to a glTF with named parts. The machinery below it is
proven -- the 42-node rig, the 2x-width instancing and the held sizes in
section 0's sibling entry were all measured on a prop this same path built.

### Superseded: "the image model draws isometric and disobeys"

An earlier entry here concluded that PS1_STYLE already says "STRICT
ORTHOGRAPHIC PROJECTION" and the drawing model ignores it. THAT WAS WRONG and
one image disproved it -- the style prefix is preamble, the VIEW INSTRUCTION is
the request, and appending an explicit per-view elevation clause fixes the
projection deterministically. See the trace above and ELEVATION in auto_prop.

What does survive from it: `gate()` measures fill and bounding box, and a
perspective drawing passes both (22%, box 0.399..0.836), so the gate cannot see
projection. The obvious silhouette test -- a true elevation has vertical left
and right edges -- was measured and does NOT separate them (0.0057 against a
corpus median of 0.0031, two corpus sheets worse), because a box drawn at an
angle still has a near-vertical front face in outline.

### Free local models work, with one condition

`tools/authoring/LOCAL.md` and `bash tools/setup/local-setup.sh --pull`. The
condition is the corollary in CLAUDE.md: an ask arithmetic **checks** can take a
weak model. Measured — a free 8B vision model named a growth place where the
paid model returned `null`, and that prop went +0.480 → +0.102. The judges,
which nothing checks, are the exception.

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

## 6b. The geometry, and what is left of it — **mostly DONE**

The outline against the prop's own three elevations, and the resize promises
against the prop's own rules. Both are arithmetic and both now have tools.

```
                     start        now      gate
front   median       0.9852     0.9896     geometry_sweep.py --save, then diff
        below .95         4          0
side    median       0.9659     0.9817
        min           0.762      0.945
        below .95        19          2
top     median       0.9628     0.9832
        below .95        22          1
all three >= 0.95    ~76/98     95/98
resize promises kept     --      94/98     scale_check.py
props you can see through --       3/98     geometry_audit `daylight`
```

**What is left, in the order it is worth doing:**

1. **4 span rules that cannot act** (`scale_check`), down from 25. What closed
   the other 21 was not artwork but three levers that had written and whose
   writing did not survive: the renderer squashed bought art back to the drawn
   width, `wide_art` relabelled its own cache so the renderer stopped using it,
   and `wide_art` and `spansOf` used different tests for "can this part span".
   The four left are `count` decisions rather than purchases — a jukebox's dome
   window and a cabinet's vent grille are COUNTABLE by role, so a bigger one has
   MORE of them, and nothing has said whether that is true of THIS prop.
   **Done when:** the judges have answered each with a `count` or a `fixed`,
   through the `scale_check` evidence that now reaches them.
2. **Three props you can see through**, worst 0.99%: a fringe where the traced
   polyline and the art it was traced from disagree by a pixel or two. Growing
   the alpha cut was measured and reverted — twelve props worse for one prop's
   fringe — so this belongs where the polyline is built, in `front_profile` /
   `top_profile`. **Done when:** `daylight` is under 0.004 on every prop.
3. **The pinballs**, which are six of the ten worst props on both the side and
   the top. Their plans include a plunger rod the model does not build, and the
   tight crop makes that stub rescale the whole plan. **Done when:** a pinball's
   top outline is above 0.97 without special-casing the metric.

**What is NOT worth doing**, with the numbers, so it is not re-derived: chasing
`part_bulge` findings below about 0.03. On a flat-fronted prop the wall carries
no relief, so every part's stand-off is depth the elevation does not show, and
the objective is monotone in it. See `depth_scale.py` and `part_bulge.py`.

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
