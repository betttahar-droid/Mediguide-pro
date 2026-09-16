# Mistakes, and what to do instead

`CLAUDE.md` holds the practices. This file holds the specific errors that
produced them, with the numbers, so a future session can recognise the shape of
one before repeating it.

Entries were first written in order of cost, and keep their numbers once
assigned because the closing section refers to them. A new entry goes at the
end however expensive it was; #11 belongs at the top.

---

## 1. Building a measurement and wiring it to nothing

**Closed.** `intent_gate` is the correcting channel: `apply_resize_policy`
rewrites contradictory rules for the roles whose policy is unambiguous,
`segmentation_verdict` forces a re-draw before anything is built on a bad
decomposition, and `acceptance` reaches the judge loop as faults.

Four measurement tools existed; one was wired into the loop. `feature_intent`,
`resize_policy` and `segment_audit` between them found 230 role contradictions,
33 under-segmented props and 291 unverified thicknesses, and **nothing in the
pipeline read any of it.**

That was the exact failure Astra diagnosed, in a new costume: the system knew a
great deal more than it did before and behaved identically. It also broke the
repo's own rule that anything which can block must be able to correct.

I did the same thing in miniature one commit after writing `repeat_score`:
appended its findings *after* both judges had already replied, which made it a
blocking channel with no correcting one. Caught and fixed by moving it in
front of them, as evidence.

**Instead:** a measurement is not done when it measures. It is done when
something acts on it. Name the lever before writing the check.

---

## 2. Thresholds that are tautologies

`ROLE_ASPECT` was first derived at the 10th/90th percentile. A band drawn at
p10/p90 excludes a fifth of its own data **by definition**, and that is exactly
what it did — 19–25% of every single role (decal 20%, button 19%, screen 22%,
member 25%). That is the percentile's arithmetic and says nothing about any
prop. At p2/p98 the same corpus rejects 3–8% and what falls outside is a gross
outlier.

Related, same file: rounding a bound to *nearest* moved it past the very
instance that defined it — a grille measuring 8.574 set the p98 and then failed
`8.57 outside 0.27..8.57` on its own number. Bounds round **outward**.

**Instead:** before believing a derived threshold, ask what fraction of the
source data it rejects. If that number is the percentile you chose, you have
measured nothing.

---

## 3. Confusing normalised local units with real ones

`Feature.region` is normalised inside its host, so `f.w/f.h` is the real aspect
times the host's *inverse* aspect. A screen with a 244×171 pixel box — real
aspect 1.427 — returned 3.429, because the face is 263×632 and
1.427 × (632/263) = 3.429 exactly. Checked against ranges derived from real
aspects that scored **83 of 95 props REJECTED**, and 335 of the 506 failures
were the artefact rather than a bad part.

This is the Astra finding — face-local dimensions confused with world axes —
reproduced *inside the module written to prevent it*. The docstring said w and
h are not world axes; the same discipline says a normalised local length is not
a real one either, and only `local_size()` converts. `check_aspect` never
called it.

**Instead:** any value that is a ratio must carry the extent it was normalised
against, or nothing can be recovered from it. A `Feature` now carries `extent`.

---

## 4. Overclaiming in the direction you are guarding against

Having written a module whose whole purpose is to refuse to say "accepted"
without evidence, I set thickness to `0` and failed every opening for "being
paint" — scoring **86 props REJECTED**. But the renderer *does* build a
stand-off from the depth adjective, so the geometry is there; it simply isn't
measured. The true verdict is DRAFT.

**Instead:** the overclaim has two directions. Guarding one does not protect
the other, and the vocabulary you built to be honest can be used to be wrong.
`DEPTH_ADJECTIVE` now quotes the renderer's real constants so they cannot drift.

---

## 5. Fixing one prop and breaking twenty

Estimating the sheet background from a k×k *patch* at each crop corner reads as
"the same idea measured properly". It is worse, for the reason the single-pixel
version was nearly right: a tight crop's corner patch is mostly **prop**. Swept
across the work tree it moved the estimate to near-black on ~20 props whose
sheet is mid grey, and every one then read as solid to its own bounding box.

One prop fixed, twenty broken. The fix was to take the colour from the
*uncropped* image, where a corner is unambiguously sheet.

**Instead:** sweep before believing. The sweep is one command and it has caught
this class three times now.

---

## 6. Moving a fault instead of fixing it

A pinball put all its added height into its legs and stood on stilts. Two
arithmetic fixes were tried and both reverted:

- capping what a member may absorb → pulled in a measured run that stacked
  **five speaker panels** down the backbox
- sharing the growth by capacity → only changed how much went to that same bad
  supplement

The missing thing was not a weight. It was a **place**, and the model is what
knows where places are. `scale_rules` now re-asks when every place it gets back
is a member.

**Instead:** when two consecutive changes move a fault from one prop to
another, the count of broken props is flat and the fix is structural. Revert
and say so. (This is `CLAUDE.md`'s rule; it was re-derived the hard way anyway.)

---

## 7. Theorising instead of identifying

Six theories about a white band — vertex tint, cap chamfer, shelf material,
carcass swatch, missing texture, atlas, decal — each tested by rendering. A
raycast named `control_deck` at uv 0.24,0.50 in a minute.

It happened again this session: I spent several renders theorising about a grey
slab before raycasting it, which returned world-space UVs of −0.17 and −5.56 —
the quad's own coordinates divided by `tileWorld`, naming the carcass fill and
killing a theory about the front face in one call.

`raycast.mjs` now exists so nobody writes it in a scratch file again. A trap is
baked into it: a multi-material mesh hands back the material **array**, and
`Array.prototype` has a `.map`, so "does this have a texture" answers yes for
everything until you index by `face.materialIndex`.

**Instead:** ask the scene first. It is always cheaper than a theory.

---

## 8. Assumptions that were never measured

`ROLE_POLICY` gave every window, grille, vent and drawer `FRAME` on both axes.
Measured: of 154 frame-role features in the corpus, **only 11 contain two or
more countable children.** The assumption was wrong for 93% of them.

The fix composed two tools rather than picking a threshold: a frame-role
feature with no children that `segment_audit` independently flags as a
swallowed box has contents that were never lifted, and no policy is decidable
until they are — an `UNVERIFIED`, not a guess. Disagreements fell 286 → 230,
and the drop landed exactly where the assumption was weakest (grille 85 → 38).

**Instead:** when you write a rule that applies to a whole category, count the
category first.

---

## 9. Trusting a grader that cannot see the fault it reports

Both language judges scored a cabinet carrying **five stacked ARCADE marquees**
at two blocking faults — exactly what they gave the corrected cabinet beside
it. They passed a pinball standing on stilts at **zero**. Meanwhile 181 of 306
blocking faults across three runs were that same class.

A judge's pass is not evidence. `repeat_score` exists because of this, and a
free model (`openrouter/free`) got the call right where both paid judges did not.

**Instead:** when a grader reports a fault class constantly and cannot rank the
worst case above the best, it is not measuring that class. Measure it directly.

---

## 10. Small operational ones, kept because they cost real time

- `pkill -f "make_prop.py"` matches its own shell. Use `[m]ake_prop.py`.
- A filename pattern `w-1-h-1-` is also the prefix of `w-1-h-1-5-`, so the
  as-drawn column showed the *taller* render and the sheet compared a prop
  against itself. Parse the numbers; do not match patterns.
- A mask is not always its box. `segment_sheet` writes it at the region's size
  and a later pass may move the box; indexing by the box walks off the end. The
  box is the authority.
- Reading `front.png` raw instead of `object_crop` made a whole stage silently
  a no-op — right picture, wrong size, size check failed quietly.
- Two retries back to back hit the same transient failure. Space them; one
  failed segmentation draw cost a prop 58 fittings against 11 and five rounds
  were built on the wrong decomposition.

---

## 11. A correcting channel where NOTHING outranks what it replaced

**The most expensive single line so far.** `scale_rules` re-asks the model when
every `taller_at` place is a member that lengthens, because a prop cannot put
all of its height into its legs. The best of the three attempts is kept, ranked
`(0 if members else 1, room)`.

`members` is `bool(taller_at) and all(...)`. For an **empty** list it is False —
there is no member in it to be all of — so a reply whose every place was refused
ranked `(1, 0)` and beat two perfectly good legs at `(0, 286)`. Every prop that
reached the re-ask shipped `taller_at: []` afterwards. Three for three:
`v49_arcade_cabinet`, `v49_pinball`, `v50_vending_machine`.

The channel existed only to improve a members-only answer and made it strictly
worse **every time it fired**.

What made it expensive is what empty means downstream. It does not mean "grow
nowhere"; it means "the renderer decides", and the renderer's per-strip fallback
is the one path in the chain that never checks what it is about to repeat.
`free_frac` scores a whole strip, and the band it lays copies of is a sub-run of
that strip — the pinball's winning strip is rows 160..621 at 10% bare, and the
band inside it is rows 263..378, **85% of the playfield.** A 1.6× pinball came
out with four playfields stacked diagonally up its cabinet. Swept: **33 of the
65 props** reaching that fallback had a band more than half covered by fittings.

**Instead:** when a fallback ranks candidate answers, check what an EMPTY
candidate scores. Write the tiers out as tiers rather than as a boolean, and
order them by what each costs downstream — here: a body place, then members
only, then nothing, which is worse than both.

**And:** an empty result handed to a consumer is a decision delegated, not a
decision deferred. Name what the consumer will do with it.

---

## 12. `repeat_score` cannot see a repeat that moves sideways

Recorded as a measured blind spot, with its numbers, because the fix for #11 was
a precondition rather than a better detector and the detector is still blind.

On the pinball's four stacked playfields — as gross an instance of the class as
the corpus contains — every autocorrelation channel reported the broken render
as *less* periodic than the correct one:

| render | row luminance | silhouette width | left edge |
|---|---|---|---|
| as drawn | 0.53 | 0.53 | 0.53 |
| 1.5× wide (good) | — | 0.31 | 0.59 |
| 1.6× tall (**four stacked playfields**) | **0.31** | 0.46 | 0.34 |

A *negative* rise, on all three. The copies climb diagonally and each sits at a
different x, so no row-indexed profile is periodic: row luminance mixes a
growing share of background, the silhouette width changes as the zigzag widens,
and the left edge is the zigzag itself.

**Not fixed by a fourth channel.** The cause is now caught before the render —
a growth band must be bare, which is checked in `strip_slice` from the parts
file with no render and no model. Adding a detector for the effect after fixing
the cause is the second mechanism this repo keeps being bitten by.

**Instead:** prefer a precondition on the input to a detector on the output when
both are available. The precondition is cheaper, earlier, and cannot disagree
with the thing that produced the fault.

---

## 13. A rule for an axis it does not name

`rule_y` answered "how does this part grow DOWN" with the part's ACROSS rule
whenever nothing more specific applied. That reads as a harmless default and is
not one: `faceQuads` gives `ny = 1` to every rule that is not `spany_repeat`,
and a nine-slice with `ny = 1` **stretches** its middle band to make up the
difference. So `screen: resize_y = spanx_center` does not mean "hold", it means
"stretch", and a 1.5× taller cabinet grew a screen half again as tall.

The comment "a taller cabinet is more cabinet, not a bigger screen" is twenty
lines from the code that did this. It was written about the body. The parts were
never held to it, so the fault the whole growth-band design exists to prevent
came back through the other axis.

121 parts across 65 props carried a stretching Y rule they should not have: 56
signs, 28 buttons, 17 decals, 11 slots, 8 screens, 1 light.

**Instead:** an enum whose values name one axis must not be used as the default
for the other. When a field falls back to a sibling's value, check what the
CONSUMER does with it — "the same rule" and "no rule" are different, and the
consumer decides which one a copied value means.

---

## 14. Two parts can own the same pixels, and it only shows when they move

`layer_build` cuts each part straight out of the elevation at its own box, so
wherever two boxes overlap, both textures carry the same artwork. A 1.7× jukebox
rendered its song list **three times**; `raycast` named the copies
`arch_lights_mesh`, `title_strip_mesh` and `speaker_grille_mesh`. 88 props have
at least one such pair, 1462 pairs in all.

It survived because it is invisible at 1×, where the copies land exactly on each
other — the size every "is this lossless?" check is run at.

**Instead:** a correctness property checked only at the identity transform is
not checked. Ask what the invariant is under the transforms the thing exists to
support, and check it there.

---

## 15. An answer to one axis reused as the answer to the other

Twice in one afternoon, in two files.

`rule_y` (#13) answered "how does this grow DOWN" with the across-rule, and a
nine-slice stretches every Y rule that is not `spany_repeat`.

`hostSpan`'s body fallback returns the prop's own width at the part's height —
correct, measured, and its note argues only about WIDTH. It carries `v: [0, 1]`
because that is the honest answer to "how wide". Read as a TIER span it says the
shelves repeat down the whole machine, and `v50_vending_machine` rendered its
bottom row of drinks below the push bar, outside the glass, on the base panel.
`raycast` named it `product_window_8_tier1_mesh` in one call.

The count had the same shape: `tiers = round(FH)` is the PROP's growth, right
only while the host grows with the prop — which was always true while the
fallback host *was* the whole prop.

**Instead:** when a value is reused across axes, check the consumer on both. A
field that is a correct answer to one question is not thereby a safe default for
the other, and "it was already there" is how it gets reused.

---

## 16. A bar a part cannot get out of the way of

`strip_slice`'s occupancy tally counted every part against every row it stands
in, including parts that LENGTHEN with the prop. `v50_vending_machine`'s
`frame_left` and `frame_right` run all 517 rows at `spany_repeat`, 63 px of a
297-wide face, so every row read 21% occupied against a 10% bar and **no row on
the prop was ever bare**. It named no place, found no run, and fell through to
the stretch.

The reasoning against it was already written, three hundred lines away in the
same file, for the `side == "itself"` branch: "a lengthening member's rows are
not meant to be bare, they are full of the member; what has to be true there is
that nothing ELSE is."

**Instead:** when a test comes back empty for every candidate, suspect the test
before the candidates. And when a file already argues a case in one branch,
check whether the other branches know.

---

## 17. One sample standing in for a distribution

`surfacePlane` estimates four things about the surface under a part. Three of
them are robust by construction and carry long comments explaining why: the
slope is the **median** of the pairwise slopes, because "a contaminated
estimator cannot be used to find its own contamination"; the trim is a **median**
of residuals; the clearance is cut at a **median absolute deviation**, because
"a minority on a cliff must not move the answer".

The fourth was `zAt(0, 0)` — whatever happens to be directly under the part's
middle.

On a surface the fit has already REFUSED as a step that sample means nothing.
v44_pinball's right leg spans the break between the playfield and the floor, the
fit came back "step, not a slope", and the one sample at its centre sits at
−0.132 while the surface under it runs to 0.253. The leg was hung off the back
of the machine, and once the mesh followed the wall and the old clearance no
longer accidentally rescued it, that one part took the prop's side outline from
0.935 to **0.657** — the worst number this audit has ever produced.

The median of the same samples costs one sort. It had been argued for three
times in the same function, forty lines up.

**Instead:** when a function reaches for a robust estimator anywhere, check every
other quantity it computes from the same samples.

---

## 18. An allowance applied past the thing it is an allowance for

Two parts left their props when the props were resized, and they looked like
unrelated bugs until both were written down.

`bh = h / cos(rotX)` is the cover allowance — "a slope is longer than its
shadow", so a bezel drawn 0.30 tall covers 0.30/cos of actual slope. Correct,
and unbounded: v52_jukebox's base trim sits on the floor, and on a cabinet twice
as wide the allowance for the steep bit of profile it lies in pushed it 0.026
BELOW the floor.

`oh + (FH - 1)` is the enclosure rule — a case grows to hold a shelf the body
knows nothing about, so it takes the whole of the prop's added height. Also
correct, and also unbounded: v46_vending_machine's drink window covers 53% of
the drawn machine, and half again as tall it came out 1.03 units high on a prop
1.5 high and rose 0.054 clear of its own roof.

Neither allowance is wrong. Both were applied without the one statement that
bounds them: the prop is 1 by FH by BODY_D and nothing mounted on it is outside
that. Clamping the BUILT extent rather than the position keeps each part's near
edge where it was drawn and takes the overhang off the far one, and at the drawn
size it is a no-op — mean change across 98 props, +0.00006 side.

**Instead:** every allowance needs the invariant that bounds it written at the
same place, or it will be correct in the small and absurd in the large.

---

## 19. A grader reporting its own percentile

`ROLE_ASPECT` is a 2nd/98th percentile band per role, and its docstring says
plainly why it is not the 10th/90th: a p10/p90 band "excludes a fifth of the
data it was derived from BY DEFINITION, so it is a tautology rather than a
defect detector". It then records that p2/p98 rejects 3-8% of every role.

Nothing asked what that does to a verdict taken over a whole PROP.

Measured: every failed check in the entire work tree is `aspect` -- 60 of 1830
parts, 3.28%. At that rate a prop with the median twelve parts has a 33% chance
of carrying one outlier from the band alone, and 43% of props carry one. Of the
42 props called REJECTED, **31 had exactly one failing part**. The acceptance
gate was a restatement of the percentile with a prop's name attached.

It is the same fault as entry 2 one level up: a number that describes the
method rather than the subject. What makes it worse is that the method's own
documentation states the rate -- the arithmetic needed to see this was written
down forty lines above the check, in the file that does it.

**Instead:** when a check has a KNOWN base failure rate, a verdict built on it
must compare against that rate, not against zero. A binomial tail costs ten
lines and took the corpus from 42 REJECTED to 9 -- and the 9 are specific: four
props with more outliers than their part count explains, and six with a single
part so far outside its band that it is a segmentation error rather than an
unusual fitting.

---

## 20. A reply that returns the whole document overwrites what you did not ask about

**Shape:** an ask aimed at *one* field, answered with a *whole* record, written
back whole — so every other field silently takes the new model's opinion too.

`scale_rules.json` carries `max_wider`, `max_taller`, `per_bay`, `per_tier`,
`spans`, `wider_means` and `taller_at`. A batch was run to fill in `taller_at`
on the 42 props where the paid model had returned null, using a free vision
model. That trade is sound — `strip_slice` verifies the places and rejects bad
ones, so the model authors and arithmetic checks. The reply was written back as
the whole file.

Checked after five props, against the paid baseline:

```
v14_arcade_cabinet   max_wider 2.0 -> 1.5   max_taller 1.5 -> 1.3
v16_arcade_cabinet   max_wider 2.0 -> 1.5   per_bay 3 -> 8, ZERO overlap
                     per_bay kept 7 of 15 entries across the five props
```

The tool was quietly promising **less resize than before**, bought with a call
meant to *add* one field. And it would have gone unnoticed: every downstream
check would have passed, because a prop that promises 1.5× and delivers 1.5× is
correct. The loss is invisible to everything except a comparison with what the
prop used to promise.

Nothing was wrong with the free model's places. What went wrong is that its
answer was allowed to speak to questions it had not been asked to improve on.

**The fix is not a better model, it is a narrower write.** Take
`taller_at`/`taller_means` from the new reply; restore every other field from
the answer already there. Generally: when a cheap source is introduced to
supplement an expensive one, merge the field you went for and keep the rest —
an overwrite makes the cheap source authoritative on everything it happened to
mention.

This is the twin of *a lever is not finished when it writes, it is finished when
what it writes survives*. Here what survived was too much.

**It then happened a second time, which is what made it structural.** The batch
grew the merge; a one-off script written later to redo a single prop did not
carry it, and `v15_arcade_cabinet` lost `max_taller` 1.6 → 1.5, two `per_bay`
entries and its `wider_means` — to a call made only to restore one place.

Twice is not a discipline problem. The merge now lives in `scale_rules.py`
itself, behind `--only-places`, at the point where the file is written, so no
caller can forget it. **When a rule has to be remembered by every caller, move
it to the one place they all pass through.**

## The pattern underneath most of these

Nearly every entry is one of these shapes:

1. **A number that describes the method, not the subject** (2, 8).
2. **A unit confusion that survives because nothing converts explicitly** (3, 13, 15).
3. **A signal that exists and reaches nothing** (1, and the near-miss in 1).
4. **A correction that can return nothing, where nothing wins** (11).
5. **A property checked only where it cannot fail** (14).
6. **A test that rejects everything, blamed on the candidates** (16).
7. **One sample standing in for a distribution** (17).
8. **An allowance applied past the thing it is an allowance for** (18).
9. **A verdict compared against zero when the check has a known base rate** (19).

Checking for those nine directly is cheaper than rediscovering them.
