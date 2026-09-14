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
| `image_bench.py` | which image model to buy, on `wide_art`/`tall_body`'s own bars | **yes** — its table is the ladder in `concept_sheet` |
| `judge_bench.py` | whether a judge can see a repeat `repeat_score` can | diagnostic — the answer is no, for every model tried |
| `depth_scale.py` | how far a part really stands off, against the side view | **yes** — its sweep set the renderer's `DEPTH` |
| `part_bulge.py` | which single part makes a prop the wrong shape, by name | diagnostic — it named the joystick, the legs and the twist |
| `raycast.mjs` | names the object under a render pixel | n/a (diagnostic) |

---

## The corpus, as currently measured

98 props with a part list, 1776 feature instances. Re-measured, not remembered.

```
acceptance     53 DRAFT   42 REJECTED   3 ACCEPTED   90 declaring the depth limit
overlap        90 props, 1555 pairs of parts sharing drawn pixels -- cut
growth place   72 props repeat a measured band; 26 stretch -- 8 because their
               bands need more than the renderer's 10 copies, 8 with nowhere
               bare at all, and 10 whose every place is a MEMBER
member bands   of those 10, 5 gain drawn body and 5 gain nothing, and the line
               between them is every pinball in the corpus: a leg has no body
               behind it to go blank (tall_body.body_behind)
tall body      17 props have their extra carcass DRAWN rather than stretched
wide art       21 parts across 17 props that no rule can widen -- bought
resize audit   229 adaptations across 68 props, median 3 per prop
recomposition  0.00% on 89 of 90 props, away from part boxes and the outline
               (the 26% layer_build used to print was sheet and dilation ring)
vertical rule  121 parts held their height that were stretching it
               (56 sign, 28 button, 17 decal, 11 slot, 8 screen, 1 light)
flank check    75 bands had never been checked against the other elevations -> 0
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
- **One account running out of credit stopped ten tools that know nothing about
  billing** — nine that draw, plus the second judge. All of them go through two
  functions, `concept_sheet.generate_image` and `gemini_judge.vision_json`, so
  the fallback to OpenRouter lives in those two and nowhere else.
- **The drawing model is now chosen by measurement, not by argument.**
  `image_bench` scores candidates on the same arithmetic that decides whether a
  drawing is composited, and reports **dollars per ACCEPTED drawing** — the
  metric that matters when a refusal buys another call:

  ```
  google/gemini-3.1-flash-lite-image   $0.034/img   14/20   $0.0475/accepted   4.8s
  google/gemini-3.1-flash-image        $0.067/img   13/20   $0.1056/accepted  11.1s
  ```

  Indistinguishable on quality over twenty drawings, half the price, half the
  wait. And because the two fail on **different** cases, a refusal now escalates
  to a different model rather than re-rolling the same one.
- **The judges were nearly written off for a budget fault.** Two Gemini models
  returned unparseable JSON at `max_tokens=4096` — not schema failures,
  truncation, which reads identically. `auto_prop.glm` carries the same finding
  in its docstring one file over. At 12000 both answer; `gemini-2.5-flash-lite`
  still runs past 37k characters and is dropped.

---

### The geometry, measured against the drawings it claims to be

`geometry_audit` renders the model from three axes and scores each outline
against its elevation. Across 98 props:

```
                                                          at the session's start
front  IoU median 0.9859   min 0.936   below 0.95:  4/98   0.9852  0.934   4
side   IoU median 0.9792   min 0.926   below 0.95:  8/98   0.9659  0.762  19
top    IoU median 0.9766   min 0.902   below 0.95: 10/98   0.9628  0.876  22

all three faces >= 0.95 on 81 of 98 props; >= 0.97 on 52
```

**Two props had no side profile at all**, so the renderer built them as plain
boxes at a default depth rather than lofting them — and they were the two worst
side outlines in the corpus by a wide margin, 0.763 and 0.794. Building the
profiles took them to 0.977 and 0.941. `geometry_audit` now reports a missing
side profile and a missing plan.

**Every prop in the tree was built with a rectangular footprint.** 100 of 100
had a `top.png` and none had a `top_profile.json`, so the renderer fell back to
square corners while each prop's own plan drawing showed them chamfered — and
nothing said so, because a rectangular plan looks like a body rather than like a
bug. Building the plans is most of the top column above. `geometry_audit` now
reports when a prop has no plan.

**The body is not the weak part — the parts standing off it were.** Rendering
the loft with no parts on it at all settles which half is at fault:
`v8_arcade_cabinet` goes 0.898 → **0.993** on the side with the parts removed,
`v51_pinball` 0.851 → 0.973, `v48_arcade_cabinet` 0.916 → 0.992. Nine of twelve
improve by 0.06–0.12. Halving the stand-offs took the side median from 0.966 to
0.978 and the props below 0.95 from 19 to 12 — 87 better, 5 worse, none by more
than 0.009.

**The sweep could not choose the number and the pictures could.** Side IoU rises
monotonically as relief shrinks, all the way to a prop with no relief at all, so
it is a bound and not an optimum. See `parts_view/index.html`'s `DEPTH`.

---

### The judges cannot see the fault they report most, and now there is a number

`repeat_score` supplies ground truth no model provides. Taking the five props
whose renders it scores **+0.62 and up** against their own 1×, and the five it
scores **−0.08 and down** — a gap of 0.86 — and asking each judge the real
`JUDGE` prompt about the real renders:

```
google/gemini-3.1-flash-lite   found 5/5 real   false alarm on 5/5 clean
google/gemini-2.5-flash        found 5/5 real   false alarm on 4/5 clean
```

flash-lite said "there is a repeat" on **all ten props**. It is not detecting
anything; it is saying yes, and it finds every real case the way a stopped clock
is right twice a day. Both sit at chance.

This is CLAUDE.md's existing finding — *the judges report that class constantly
and cannot actually see it*, from 181 of 306 blocking faults being one sentence
in different words — arrived at independently and with a measurement behind it.
It is why `repeat_score` runs in **front** of the judges. It is also an argument
that a repeat the judges call blocking and the arithmetic does not should not be
blocking, and **that change has not been made**: ten props, one fault class, and
*count the props your change breaks* applies to scoring most of all.

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
