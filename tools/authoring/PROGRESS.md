# What has been built, and what it measured

A running record for whoever picks this up next — including a future me with no
memory of the session that wrote it. Every claim here has a number behind it,
because the claims without numbers are the ones that turned out to be wrong.

Read `ARCHITECTURE.md` first for the shape of the thing, `MISTAKES.md` for the
ways it has gone wrong, and this file for what actually exists.

---

## The state in one line

The pipeline makes props end to end and its best judged scores went from
6/4/5/6 blocking faults to **2/3/2/3** across the four reference props. Every
measurement tool is now wired to a lever. The widening axis is right; the
taller axis was wrong on 33 of 65 props and is now fixed at the cause.

---

## Tools that exist

| tool | what it measures | wired into `make_prop`? |
|---|---|---|
| `repeat_score.py` | a repeat or dead band the drawn prop did not have | **yes** — runs *before* the judges, as evidence |
| `feature_intent.py` | typed intent, face-local, per-field evidence; 3-valued acceptance | **yes** — via `intent_gate.acceptance`, into the judge loop |
| `resize_policy.py` | whether a feature's resize contradicts its role | **yes** — via `intent_gate.apply_resize_policy`, before the layers are cut |
| `segment_audit.py` | boxes that swallowed fittings; bands never lifted | **yes** — one re-draw when `UNDER_SEGMENTED` |
| `depth_probe.py` | a feature's thickness off the side elevation | **yes** — and its answer is almost always `UNMEASURABLE`, which is the finding |
| `overlap_cut.py` | drawn pixels claimed by more than one part | **yes** — cuts them out of the larger part after `detail_sheet` |
| `recompose_score.py` | whether the parts lay back down as the reference | diagnostic — it is 0.00% on 89 of 90 props, so there is nothing to gate on |
| `wide_art.py` | parts no rule can widen; buys the missing width | **yes** — in `rebuild`, and the renderer loads it above the drawn ratio |
| `tall_body.py` | props with nowhere bare; draws the extra carcass | **yes** — in `rebuild` after `strip_slice`, and the renderer paints from it |
| `resize_audit.py` | every resize decision, one at a time, against glm-5.3 | **yes** — in front of the judges, findings quoted and patch merged |
| `raycast.mjs` | names the object under a render pixel | n/a (diagnostic) |

---

## The corpus, as currently measured

95 props, 1673 feature instances.

```
acceptance     53 DRAFT   40 REJECTED   3 ACCEPTED   88 declaring the depth limit
resize policy  65% agree  20% unknown-role  14% disagree  0.4% unverified
segmentation   33 of 95 flagged (23 swallowed boxes, 18 missing bands; 6 are screens -> LEAD)
unverified     407 aspect (was 1673)   291 thickness (UNMEASURABLE, declared)
growth place   44 props moved off the blind band onto a measured bare run
               9 props have nowhere bare at all and now stretch instead
               10 more had bands too small for the renderer's 10-copy bound
overlap        88 props, 1462 pairs of parts sharing drawn pixels -- cut
vertical rule  121 parts held their height that were stretching it
               (56 sign, 28 button, 17 decal, 11 slot, 8 screen, 1 light)
flank check    75 bands had never been checked against the other elevations -> 0
recomposition  0.00% on 89 of 90 props, away from part boxes and the outline
               (the 26% layer_build used to print was sheet and dilation ring)
```

**No prop can reach a meaningful ACCEPTED from four elevations**, and that is
now a stated result rather than a gap. A side silhouette traces the frontmost
point at each height, so a recess never touches it: 291 thicknesses are
`UNMEASURABLE`, and the verdict declares the format limit instead of blocking
on it. The 3 ACCEPTED props pass only because they contain no such feature.
Roadmap 2b — a three-quarter reference view — is the only way past it.

---

## What was fixed, with the evidence

### Texturing and fill

- **The arithmetic tile was painting over the model's plate.** `layer_build`
  composited the model's fill and then tiled a fallback across *every* covered
  pixel, so one refused hole out of 26 discarded all 25 good answers. Measured:
  plate grain 2.2–3.3 in each hole, background on disk a flat 26,29,36.
- **Holes are now shown, not described.** The paint-out prompt listed
  categories ("doors, panels, buttons, screens, shelves…") and the model read
  it and emptied an entire display case. Painting the outstanding holes flat
  magenta took the vending machine from **19/29 fittings to 28/29**.
- **A member is not a fitting.** The pinball's only parts were its legs, and
  there is nothing behind a leg to draw. It ended every run with "nothing
  usable in the plate"; skipping lengthening members took it to **17/17**.
- **Grime is a fixed height off the floor.** An adaptive-material generator
  applied as a *differential* — verified **pixel-exact at 1×**, max channel
  difference 0 over 987,136 pixels — so a panel lifted clear of the skirting
  loses its grime and new material at the skirting gains it. `?wear=0` isolates
  it. Honest: the effect is small, because these bodies are near-uniform down
  their height once fittings are lifted.

### Geometry

- **The sheet colour comes from the sheet.** `silhouette` read it off the
  *crop's* corners; the pinball's sheet is the same blue as its cabinet, the
  estimate landed 45 away against a tolerance of 40, and the machine rendered
  with a blue slab hanging between its legs. Now carried on `.info['sheet_bg']`
  from the uncropped image.
- **Riders travel with a moving host.** `hostOf()` existed, was correct, and
  was never called, so doors swung open out from under their own fittings.
- **A member can lengthen at all** — `shaft_band`, `spany_repeat` instead of
  `spany_center`, and its own share of the height via `gOfT` rather than the
  whole prop's.
- **One drawn region belongs to one part.** `layer_build` cuts each part out of
  the elevation at its own box, so overlapping boxes put the same artwork in
  both textures. Invisible at 1x, where the copies coincide — a 1.7x jukebox
  rendered its song list **three times**, and `raycast` named the copies
  `arch_lights_mesh`, `title_strip_mesh`, `speaker_grille_mesh`. 88 props, 1462
  pairs. `overlap_cut` erases the rider's alpha shape from the larger part and
  leaves a hole, because behind the rider is the body and `paint_out` has
  already painted it clean. Dilating that hole was tried and reverted: unfilled,
  a dilated hole is larger than the thing covering it, and half the 1x change
  measured was rim (4.23→2.70, 1.85→1.03, 1.08→0.56, 1.29→0.66 per cent).
- **Artwork holds its height, not just its width.** `rule_y` fell back to the
  across-rule, and `faceQuads` **stretches** every Y rule that is not
  `spany_repeat` — so `screen: spanx_center` meant stretch, and a taller cabinet
  grew a taller screen. 121 parts across 65 props.
- **A part that lengthens is not standing in the way.** `strip_slice`'s
  occupancy tally counted every part against every row it stands in, including
  full-height rails that lengthen with the prop. `v50_vending_machine`'s two
  frames are 63 px of a 297-wide face over all 517 rows, so **no row on the prop
  was ever bare**: it fell through to the stretch, where its nine per-tier
  product windows held their size while the background carrying their price
  labels stretched past them. Excluding lengthening parts it finds 56 bare rows
  at 6.5 copies. Props stretching: 19 → 16.
- **A shelf repeats down the case it is in.** `hostSpan`'s body fallback returns
  `v: [0, 1]` — the honest answer to "how wide", read as a tier span. v50's
  bottom row of drinks rendered below the push bar, outside the glass;
  `raycast` named it `product_window_8_tier1_mesh`. When no part is the case,
  the tiers' own bounding extent is the interior, and the count is the HOST's
  growth through `gOfT` rather than the prop's — which reduces to `round(FH)`
  exactly when the host is the whole prop, so nothing else moves.
- **A growth band may not be made of fittings.** A 1.6× pinball came out with
  four playfields stacked diagonally up its cabinet. Two faults in series: an
  empty `taller_at` outranked a members-only one in `scale_rules` (an empty list
  is not "all members", so it scored in the better tier — 3 props for 3 lost
  their answer that way), and an empty `taller_at` then hands the question to
  the renderer's per-strip fallback, the one path that never checks what it is
  about to repeat. `free_frac` scores a whole strip; the band it copies is a
  sub-run of it. **33 of the 65 props** reaching that fallback had a band more
  than half covered by fittings — the pinball's was 86%. Now: three ranked
  tiers, the measured bare-run search supplies bands from zero (44 props move
  onto an occupancy-tested band), and where nothing is bare the body stretches
  rather than repeat artwork (9 props).

### The loop

- **Verdicts are written to disk.** They existed only on stdout and died with
  the shell — twice. Writing them down is what made the next three findings
  visible at all.
- **`count` — a lever for the commonest complaint.** The judges asked for "more
  of this, not a stretched one" in every round and no patch field could say it.
- **Field-level patch merge.** Whole-entry merge meant the first judge naming a
  part discarded everything the second said about it; a coin door's hinge was
  thrown away four rounds running.
- **A third grader that is arithmetic.** `repeat_score` separates every case in
  the corpus that was judged by eye (+0.24, +0.26, +0.44) from every clean one
  (−0.23 to +0.03). It runs **in front of** the judges so its findings have a
  lever.

### Cost and resilience

- A 402 names the budget it *can* afford — take it rather than dying.
- At a true zero balance, fall back to `openrouter/free`, which judged the
  five-stacked-marquee cabinet correctly (`blocking=2`, "duplicated sign",
  "tiling repeat") — the call **both paid judges got wrong**. No `z-ai/glm`
  model is free at any size.
- `glm-5.3-flash` costs **$0.0002** per judge call. Cost was never the problem.

---

## The strongest single result

Three independent channels converge on `v49_vending_machine/decal_1`:

1. **Role logic** — a decal carries reference artwork and must hold its size.
2. **The judge's own patch record** — it set `resize=spanx_repeat` *and*
   `count=both`, multiplying drawn artwork twice over.
3. **Autocorrelation of the rendered pixels** — that prop at 1.7× tall
   self-correlates **1.009 against 0.384 drawn**.

Nothing links those three. They agree because the feature is genuinely broken.
That is the standard any new check should be held to.
