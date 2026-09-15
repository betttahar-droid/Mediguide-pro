# Working on the prop maker

These are the tools that turn one prompt into a resizable, animatable PS1-era
prop with no human in the loop. Each tool's own docstring is the authority on
what it does and on the specific things that have been tried in it and failed.
This file is for the practices that cut across all of them — the ones that have
cost the most time when ignored.

## Read the failures before you change the scoring

Several of these files carry a list of approaches that were implemented,
measured, and reverted, with the numbers. `strip_slice.py`'s docstring has four.
Those lists are the most valuable thing in the repo and they are easy to skim
past on the way to the code.

They are not history. They are live constraints: an idea that reads as obviously
correct is in that list *because* it reads as obviously correct. Scoring the
growth band on its own height and its own free fraction is the right question
and it is the first entry, because bands chosen that way are too short to repeat
and the copy bound sends them back to the flat tile the change was meant to
avoid. That was re-derived from scratch, at length, by not reading it.

Before touching a score, a weight or a threshold in a file: read its docstring
to the end.

## Identify the object before theorising about the cause

A render showing something wrong is a question about *which object*, and that is
cheap to answer and expensive to guess. `parts_view/index.html` exposes
`globalThis.__scene` and `__cam`; a raycast from a canvas pixel names the mesh,
its material and its UV in about a minute:

```js
rc.setFromCamera(new T.Vector2(u * 2 - 1, 1 - v * 2), cam);
const hit = rc.intersectObjects(sc.children, true)[0];
// hit.object.name, hit.uv, hit.object.material.map
```

`?pan=x,y` aims a close `frame=` at any part of the prop; `?wire=1` takes the
artwork away; `?sheet=0` takes the atlas out of the picture.

A session went: is it the vertex tint, the cap chamfer, the shelf material, the
carcass swatch, a missing texture, the atlas, a decal — six theories, each
tested by rendering. The raycast said `control_deck` at uv 0.24,0.50, which was
a light band in one accepted redraw. Ask the scene first.

## Sweep every prop before believing a threshold

`tools/img2threejs-work/` holds dozens of finished props. Any threshold can be
run against all of them in seconds, and until it has been it is a number fitted
to one prop.

`settle_parts.py`'s size floor was set to 0.15 from the arcade cabinet, where it
was right. Swept across the work tree it deleted a jukebox's two coin slots, a
start-button panel and a coin door's lower panel. At 0.30 every case verified by
eye still resolves and none of those is touched. The sweep took one command; the
fault it caught would have shipped.

```
for f in tools/img2threejs-work/*/parts_front.json; do ... done
```

## The proxy is not the objective

Written in `strip_slice.py` about growth bands and true everywhere here. A
measure that improves while the renders get worse is a measure, not the goal.
The renders are the goal. When a change improves the number you are optimising
and you have not looked at the output, you do not yet know anything.

The corollary is that a threshold sweep is necessary and not sufficient: look at
the pictures too.

## Count the props your change breaks, not the one it fixes

Three successive changes to the growth band each fixed the prop the previous one
had broken. The signal that was being ignored: the count of broken props was
flat, only the identity changed. When two consecutive changes move a fault from
one prop to another, the fix is structural and the next threshold will move it
again. Revert and say so.

Reverting is normal here and the docstrings show it. A reverted attempt with its
numbers written down is worth more than a change that trades one fault for
another.

## The model authors and names; arithmetic measures and verifies

The oldest rule in the repo and the one that keeps paying. Never read
proportions off pixels; never let a model's word stand without a measurement.

Two corollaries found this session:

**Show the model the thing, do not describe it.** A 10×13 button marked on a
250-pixel elevation is a description, and the model draws what a fitting of that
name usually looks like — seven flat dark recessed pads came back as bright red
arcade buttons. With the same pads cut out and magnified beside the elevation
they come back the colour they are.

**A refusal is a verdict on one drawing, not on the fitting.** The same pad
scored a colour distance of 10 on one sheet and 82 on the next from an identical
prompt. Anything that asks a model for artwork and checks it should ask again
for what failed.

## When arithmetic keeps failing, check you are not asking it the wrong question

The strongest instance of the rule above, and the one that took longest to see.

`strip_slice.py` picks where the body grows by searching for somewhere quiet,
bare and body-coloured. Five reweightings of that search were implemented,
measured and reverted; the file concludes it is not a weighting problem. It is
not — but neither is it a structural one. "Somewhere calm" is simply not what a
taller cabinet is, and no amount of measuring the artwork will make it so.

`scale_rules.py` had been asking the model what taller *means* since the
beginning and getting a straight answer: *more carcass above the marquee, more
panel between the control deck and the coin door, a taller kick panel below it.*
That sentence was used to judge the result and never to produce it, because
nothing downstream could read a sentence. Asked for the same thing as a fitting
and a side, it becomes rows, and the blind search's single 12-row band (26
copies, over the renderer's bound, so a flat slab) becomes four places totalling
64 rows at 5.7 copies each.

So: when a measurement has failed several times in several forms, ask whether
some part of the pipeline already *knows* the answer in a form nothing reads.
Authorship supplies the constraint; arithmetic verifies it. That is the same
division as everywhere else here — it is easy to forget that it applies to
decisions as well as to geometry.

## Anything that can block the loop must also be able to correct it

Two judges grade every round and a fault either of them calls blocking is
blocking. Only the first judge's *patch* was being read; the second's went on
the floor. The result is a loop that can see a defect every round and is
structurally incapable of acting on it — this cabinet's coin door was reported
as hinging the wrong way in round after round, counted among the blocking
faults each time, never corrected, while every hinge direction it needed had
been supported end to end all along.

When adding a source of faults, check it has a lever, and that the lever is
read. A blocking channel without a correcting channel does not slow the loop
down; it stops it converging at all.

**Three more of these were found by writing the verdicts down**, and none was
visible from the terminal. `make_prop.py` now appends every round's faults and
corrections to `verdicts.json`, and a single sweep of four props × four rounds
showed:

- The judges' commonest complaint is not a seam. It is *"a bigger one of these
  should have MORE of this, not a stretched one"* — and the patch schema had no
  field that could say so. The vending machine's judges patched all twenty-four
  products in every round against "products are fixed, so the widened window
  gains no columns"; the cabinet patched `control_deck` every round against "no
  second joystick". Twelve rounds spent re-reporting three faults the loop
  could see perfectly and could not touch. Hence `count`.
- The two judges' patches were merged **whole entry at a time**, so the first
  judge naming a part discarded everything the second said about it, including
  fields the first never mentioned. Gemini patched the coin door's motion in
  all four rounds; glm patched the same part's resize; the motion went on the
  floor every time. Merge field by field.
- `hostOf()` sat in the renderer, correct and never called, so every door swung
  open out from under its own fittings.

The pattern in all three: a mechanism that *exists*, is *right*, and is not
wired to anything. They are invisible while the only record of a round is
scrollback, and obvious the moment four rounds can be read side by side. If a
loop reports the same fault twice, read the patch it sent — not the fault.

## A grader that cannot separate your worst prop from your best is not grading

The two language judges scored a cabinet carrying **five stacked ARCADE
marquees** at two blocking faults — exactly what they gave the corrected
cabinet beside it. They passed a pinball standing on stilts at zero. Both
graders, both runs.

This matters more than any single fault, because 181 of 306 blocking faults
across three runs were one sentence in different words: *a repeat, seam, smear
or band a player could point at*. The judges report that class constantly and
cannot actually see it. Counting copies of a sign is not what a language model
is for.

`repeat_score.py` measures it instead — autocorrelation of the row-luminance
profile, straight off the renders the loop already made. Two decisions make it
work, and both were wrong first:

- **Control against the prop's own 1× render.** Props are periodic by nature;
  a bare score punishes a vending machine for having shelves. Only the *rise*
  counts.
- **Window it.** A repeat is local. Correlating the whole profile mixes the
  stacked region with the four fifths that is an ordinary cabinet, and read
  that way the stacked cabinet scored *below* its own drawn self — the measure
  ran backwards. Windowed at about three periods, the same pair is 0.55
  against 0.31.

Swept over 75 rendered rounds it separates every case already judged by eye
(+0.24, +0.26, +0.44) from every clean one (−0.23 to +0.03).

**The arithmetic graders can fail the same way, and one did.** `feature_intent`'s
acceptance gate called 42 of 98 props REJECTED, and every failed check in the
whole corpus was `aspect` — against a 2nd/98th percentile band that rejects 4%
of parts *by construction*, which its own docstring says. 31 of those 42 props
had exactly one failing part. A verdict built on a check with a known base rate
has to compare against that rate, not against zero; a binomial tail took it to
9, and those 9 name real segmentation errors (a 211×4 "grille", a decal one
pixel wide). Before trusting a grader, ask what it scores on a prop with nothing
wrong.

**And it goes in FRONT of the judges, not behind them.** Appended after they
reply, its findings were a blocking channel with no correcting one — the loop
could prove a duplicate and had no way to ask for it to be fixed. That is the
rule above, walked into one commit after writing the measure. Neither half
works alone: arithmetic cannot say *which* part is being laid down twice, and
the readers cannot see that it is happening. The measure points; the reader
names; the patch acts.

## A fallback must not overwrite what it is falling back from

`layer_build` composites the model's plate into the background and then tiles an
arithmetic patch over whatever the model refused. The tiling loop painted every
covered pixel, so one refused hole out of twenty-six discarded all twenty-five
answers with it. The plate had grain 2.2–3.3 behind each product; the background
on disk was a flat 26,29,36 rectangle at every one of them. The two facts sat
one function apart and neither looked wrong on its own.

Whenever a good source and a fallback source write to the same buffer, the
fallback needs the predicate, not just the good source.

## Some things cannot be measured, and saying so is the answer

Whether a fitting the segmenter declared is actually *there* was measured four
ways — the step across each of its four box sides, its interior mean and spread
against a ring around it, and edge energy inside against outside. None separates
a cabinet's phantom vent and coin slot from its real speaker grilles, because a
real fitting can be flush, low-contrast and bounded by its neighbours.

Whether a redraw is of the same object was measured five ways — 2-D NCC, NCC of
the row and column luminance profiles, the top and bottom luminance deciles, the
median colour, the saturation percentile. None separates them, because an honest
redraw differs from its crop about as much as a wrong one does.

Whether a part is a *fitting set into a surface* or a *member standing in air*
was measured two ways — the fraction of the ring around it that is prop rather
than sheet, and the absolute count of material pixels in that ring. Neither
separates them, and both get it backwards: a pinball's legs score 20% and 1017
pixels, its shooter lane cover 13% and 279, its start button 11% and 120,
because a small fitting in a crowd of other fittings has a ring made mostly of
their holes. A 50% bar took 187 parts out of 1544 across the work tree,
including a cabinet's coin slots and a jukebox's speaker grille.

Whether a band is *already periodic*, and so safe to repeat, was measured by
autocorrelating the elevation's row profile — the idea being that a grille, a
vent or a rank of louvres can be laid down again invisibly. It fails and it
fails inverted: at a minimum period of 3 scanlines everything scores high
(that is the texel grid), and at 8 and 12 the jukebox's grille — the one band
it was written to admit — scores *lowest* of every case tried, below the
marquee that must never repeat. A diamond mesh has no vertical period in its
row *means*; averaging across a grille's width gives near-constant, which
reads as flat rather than periodic. The row profile finds repeats that span
the prop's width and cannot find texture repeating within it.

In each case a threshold picked anyway would delete real work. The answer is to
stop asking for the thing that cannot be made (`detail_sheet.py` no longer asks
for strips longer than 5:1); to leave the fault standing and write down that it
is standing; or — the third case above — to notice that the pipeline already
holds the answer in authored form. `scale_rules` had asked the model which
parts simply get *longer*, and `strip_slice` had already checked the reply
against the artwork. Do not ship a threshold you cannot defend with numbers.

## Quiet along one axis is not quiet

Three separate faults this session were the same mistake: measuring uniformity
along the axis of growth and not across it.

- The flank window on a marquee is chosen by how much each column differs from
  the one beside it. The gap between two letters differs hardly at all, so the
  window landed inside ASTEROID and a widened cabinet read `AS2 2S2S2STEROI`.
  A column in a letter gap is busy *down* — it carries the tops and bottoms of
  the glyphs either side. Striking out columns by vertical spread fixed it.
- The same window search ran out to 47% of the part, which on a 240-pixel deck
  is its middle. A flank is near an edge.
- The growth band is chosen for quietness and then repeated, and a bare ledge is
  quiet and still reads as a shelf when repeated.

Whenever something is chosen for being uniform, ask uniform *along what*, and
whether that is the direction it will be repeated in.

## The reference format is a constraint, not a nuisance

The single most productive sentence of the geometry work is a fact about what an
elevation *is*:

> A side elevation traces the FRONTMOST point at each height.

Two large consequences, both already paid for:

- **A recess never touches the silhouette**, so its depth is unmeasurable from
  four elevations. `depth_probe` says `UNMEASURABLE` on 291 features and the
  verdict declares the limit rather than blocking on it.
- **The body is lofted from that trace, so it ALREADY CONTAINS whatever the
  drawing shows standing out of it.** A control deck mounted on its own bulge
  and given the full `deep` stand-off is the same depth counted twice — 4.7% too
  deep on a cabinet, and the largest single per-part cost in the corpus.

Whenever a measurement disagrees with a drawing, ask what the drawing can and
cannot depict before changing the measurement.

## The tight crop makes a sliver cost more than its area

`geometry_audit.compare` crops both silhouettes tight and normalises them into
the same n×n box, which is what makes scores comparable across props. It also
means one protruding sliver widens the bounding box and shifts the WHOLE
silhouette against the drawing. v51_pinball's leg protruded 2.9% of the prop's
depth and cost 0.057; v7_vending_machine's recess bezel adds eight pixels to a
338-pixel plan and costs 0.030.

That is right when the protrusion is an error and wrong when it is not, and the
metric cannot tell. So: a small negative from `part_bulge` on a part whose wall
is flat under it (`body gave 0.0000` in `?fit=1`) is the objective being blind,
not the prop being wrong. Act on 0.03 and up. The corollary is the one
`depth_scale.py` opens with — the outline objective is monotone in the stand-off
and would end with every button a sticker if you let it drive.

## The first explanation of a fault is usually the wrong generalisation of it

`screen_bezel_bottom`, 187×28, failed an aspect band of 0.99..1.79. The
explanation was immediate and wrong twice over:

- **"`role_of` matches `screen` before `bezel`, and a bezel is trim."** Swept:
  eleven parts in the corpus carry both a role word and a shape qualifier and
  **ten of them pass** — `screen_bezel` runs 1.05 to 1.42 on six props, because
  a bezel *around* a screen is screen-shaped. The fix disables ten working
  checks to repair one.
- **"Then skip the check when the name carries a side word."** 405 parts carry
  one and **393 pass.** The same trade, forty times over.

What the failures actually shared was invisible from the failing part alone:
each is one of a **mirror pair** the segmenter cut down the middle, and the
union lands inside its band in five different roles against percentiles
measured long before. Eight of ten failures, no threshold fitted to anything.

Both wrong answers came from generalising the property the failing case happens
to *have* (it contains "bezel"; it contains "bottom"). The right one came from
asking what the failing cases share **that the passing ones do not** — which is
a different question, and only the sweep can answer it.

So: when a fault suggests a rule, run the rule over the corpus and count the
parts it would newly reject *before* believing it. A rule that fires on 405
parts to fix one is not a fix.

**And prefer a rescue to a reclassification.** This one runs only after the
ordinary check has already failed, so it can turn a FAIL into a PASS and never
the reverse — no prop that passes today can break on it. A change shaped that
way needs no sweep to prove it is safe, only to prove it is useful.

## A benchmark is only as good as the shapes it asks for

`image_bench.py` scores image models on the same arithmetic that decides
whether a drawing is composited, and reports dollars per *accepted* drawing
rather than per call — which is the right question, and it still got the answer
wrong. It scored `gpt-5-image-mini` **8 of 8** and put it at the head of
`OR_LADDER`. On the next six live `wide_art` purchases that model was refused
**six times out of six**, every one for returning a 1.00 square against a canvas
of 7.53:1, 7.26:1, 2.49:1, 8.71:1 or 21.10:1, while `gemini-3.1-flash-lite-image`
was accepted on the very next attempt every time. It cost **$0.177 of a $0.74
run — 24% of the bill — for nothing.**

The bench's cases were near-square. Every ask this pipeline actually makes is a
non-square canvas with magenta to fill — *the canvas IS the request*, which is
the entire mechanism of `wide_art`, `tall_body` and `paint_out`. A model that
cannot hold an aspect ratio is infinitely expensive here whatever its per-token
rate says, and no price table can show that.

So: **benchmark on the extremes of the corpus, not its middle.** The widest and
tallest canvases anything really asks for are the ones that separate the
candidates; the median ones are the ones every candidate passes.

And the reason it took a human question to find: **the price and the verdict
lived in different files and were never joined.** `concept_sheet` printed the
per-call cost to scrollback and counted it in a dict that died with the process;
`wide_art` knew whether the drawing survived and never said what it had cost.
`image_ledger.py` now appends both to one JSONL — the model, the price, the
canvas aspect asked for, the aspect that arrived, the calling tool, and the
caller's own accept-or-refuse — so `--by model` answers "which is cheaper" from
a real run in a second. A billed call that returned no picture gets a row too;
leaving those out is precisely how a model comes to look cheap.

The next time the ladder's order is argued about, argue it from `--by model`.

## Count what a renderer change breaks, across all of them

`geometry_sweep.py` re-audits all 98 props and diffs against a saved baseline in
about eight minutes. Until it existed there was nothing that counted, and three
changes in one session each looked right on the prop that motivated them.

It decided two of them against the median. `alreadyDrawn`'s neighbourhood band
scaled to the part's own height scored **0.0003 better** on the side median than
the local band that replaced it, and bought that by telling a jukebox's bubble
tubes they were already part of the cabinet; it also broke four props where the
other broke two. Growing the alpha cut to cover the lofted outline fixed one
prop's fringe and cost twelve props on the front.

Read the diff and the pictures, not the median. A change that moves the median
up by flattening every part made the props worse and the median cannot say so.

## The renderer's bounds are part of the design — and they are not the quality bar

`MAX_REPS` is 10. A band that needs more copies than that silently falls back to
the flat carcass tile, which reads as a slab where artwork should be. Any change
that makes growth bands shorter must be checked against the copy count it
implies at the scales the judges actually render (1.5× taller, 2× wider), not
just against how bare the band is.

**But MAX_REPS is where the renderer gives up, not where a repeat becomes
visible, and conflating the two was the largest single fault in the corpus.**
`strip_slice` sized its bands for nine copies on the reasoning that anything
under the bound is fine. Rendering all 98 props at 1× and 1.5× tall says
otherwise:

```
copies needed    props banding      median rise
  0 - 4            2 of 20            -0.001
  4 - 6           17 of 23            +0.408
  6 - 8           26 of 27            +0.503
  over 8          11 of 12            +0.572
corr(copies, rise) = +0.731
```

Six copies of a 27-row strip is a stripe pattern whatever the strip is made of.
`COPY_TARGET` is now 4, and the room was already there — bands totalled a median
46 rows while 110 bare rows went spare. Corpus effect: **57 of 98 props banding
→ 31, median rise +0.380 → +0.119, 50 better and 4 worse, with the 1× render
bit-identical.**

The axes were never equally healthy and nothing had measured them separately:
**tall 57 of 98 banding, wide 4 of 98.** When a resize fault is reported, ask
which axis before reaching for the renderer.

## "Bare" must mean bare in the artwork, not bare in the part list

`strip_slice`'s occupancy tally is built from part boxes, so a row is bare when
the *segmenter* put nothing there. That is a different claim from the drawing
being bare, and the gap is a whole fault class.

v48_arcade_cabinet's first part is `speaker_grille` at row 83. Rows 0–83 carry
no box, so all of them read bare and three of its four growth bands went there.
What is drawn across rows 29–62 is the word ARCADE. The cabinet grew four
stacked marquees — the fault the grader section above opens with — and every
arithmetic gate in the pipeline said those rows were empty.

The test is horizontal contrast against the prop's **own** median row, because a
sign is letters and letters are horizontal structure. Over 205 bands: median
0.63, p90 1.05, max 2.44 — and the max is v48's marquee band. A bar at 1.5×
rejects 5% of bands and takes the worst offender first.

**And the score went the wrong way, which is the lesson.** Before: 4 stacked
signs, rise +0.725. Copy target alone: 3 stacked signs, rise **+0.151, which
passes the blocking bar**. With the artwork test: **one** sign, rise **+0.669,
the worst of the three.** The picture is plainly best where the number is worst,
because the growth moved into a louvre band that autocorrelates strongly — and
louvres repeating is correct.

So **`repeat_score` cannot see a duplicated sign**, the fault class it was built
for, and its docstring's claim to separate every case judged by eye now has a
counterexample. The artwork test was kept on the pictures, not on the score.

## Open faults, deliberately left

- **Phantom fittings.** A cabinet's right-hand panel carries a vent, a coin slot
  and two buttons over blank wall. Unmeasurable by everything tried; see above.
- **Side and back graphics cannot be lifted.** The growth band is measured on
  the front and applied to every face, so a prop bare across some rows at the
  front and carrying artwork across the same rows on its flank stacks that
  artwork down a taller prop. Painting it off the side was tried and reverted
  (see `paint_out.py`): with no `parts_side.json` there are no holes to
  composite through, and a band of reply composited into the original seams at
  both ends. What it needs is for `decal_sheet` to record *where* the decals
  were, so they can be lifted and re-applied as planes.
- **The segmenter boxes a cabinet's joysticks onto the flanks**, so the deck
  reads sparse and the two-player layout never appears.
- **25 parts carry a span rule the geometry cannot act on** — no measured band
  and no plain flank, so the part holds its drawn size. That is the honest
  answer for the PART and it still means the PROP promises something it will not
  do. `scale_check.py` lists them; the levers are `wide_art` (buy the wider
  artwork), `tall_body` (grow the carcass instead), or writing the rule down as
  `fixed`. 12 are `spany_repeat`, 9 `spanx_center`, 4 `spanx_repeat`.
- **Three boxes the acceptance gate calls gross outliers, deliberately left.**
  v48_vending_machine's `vent_grille` is 211×4 — a shadow line under a panel,
  with no louvres in it; v50's `push_bar_slot` is 155×8 along the top rim of the
  delivery flap; v26_arcade_cabinet's `screen_bezel_bottom` is 187×28 across the
  bottom of the screen glass. Two of the three are a strip tracing the rim of
  the part they sit inside, and the rule for dropping those was written, swept
  and reverted: of the seven parts in the corpus it matches, **five are real
  fittings** — a price strip across a shelf, a label across a coin panel, a
  marquee across a decal — because a caption on a panel has exactly the geometry
  of a rim. See `settle_parts.py`. They are a question for whoever segments.
  They matter more once the openings operator lands: a 211×4 `grille` is a
  `NEEDS_OPENING` role, and cutting it would slit the machine.
- **Three props can still be seen through**, worst 0.99% of the drawing: a
  fringe where the traced polyline and the art it was traced from disagree by a
  pixel or two. Growing the alpha cut to cover it was measured and reverted (see
  `layer_build.sheet_mask`); it belongs to whoever builds the polyline.

## Closed, so you do not re-derive them

- **Body growth where the model has no usable answer.** Now closed: the
  bareness check runs inside `scale_rules`, where the question is asked, and a
  refused place is quoted back to the model with the part names that are drawn
  across it. The jukebox named three places under its own decals, was told so,
  and answered "the base panel and the foot get longer" — 41 verified rows
  where it had none.
- **Every part mask is a rectangle.** Measured false: 9 of 22 on the cabinet,
  22 of 29 on the vending machine, 13 of 25 on the pinball. Rather more than
  half of all masks carry real shape, and the renderer alpha-cuts them at 0.5,
  so a round button reads round. Do not go looking for this one.

## The four files, and which one to open

- **`ARCHITECTURE.md`** — how the Astra findings graft onto the pipeline that
  works, and the model split. Read first.
- **`PROGRESS.md`** — what exists, what it measured, and which tools are
  actually wired into the loop rather than merely built.
- **`MISTAKES.md`** — the specific errors that produced the practices in this
  file, with their numbers. Eight shapes recur: a number that describes the
  method rather than the subject, a unit confusion nothing converts explicitly,
  a signal that reaches nothing, a correction that can return nothing where
  nothing wins, a property checked only where it cannot fail, a test that
  rejects every candidate and gets blamed on the candidates, ONE SAMPLE STANDING
  IN FOR A DISTRIBUTION in a function whose every other estimate is robust, AN
  ALLOWANCE APPLIED PAST THE THING IT IS AN ALLOWANCE FOR, and A VERDICT
  COMPARED AGAINST ZERO WHEN ITS CHECK HAS A KNOWN BASE RATE.
- **`ROADMAP.md`** — what to do next, in order, with what "done" means for each.

The rule these four exist to enforce: **a measurement is not finished when it
measures, it is finished when something acts on it.** Four measurement tools
were built in one session and one was wired in. Name the lever before writing
the check.

And its twin, learned the same way: **a lever is not finished when it writes,
it is finished when what it writes survives.** The judges' resize patches were
applied to `parts_front.json` and then overruled by `layer_build` on 265 parts
across 76 props, so the loop re-reported faults it had already been handed the
fix for — round after round, by its own verdict logs. When you add a channel,
patch something through it end to end and check the far end changed.
