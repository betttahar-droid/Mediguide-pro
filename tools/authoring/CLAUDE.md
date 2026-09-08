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

In both cases a threshold picked anyway would delete real work. The answer is to
stop asking for the thing that cannot be made (`detail_sheet.py` no longer asks
for strips longer than 5:1) or to leave the fault standing and write down that
it is standing. Do not ship a threshold you cannot defend with numbers.

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

## The renderer's bounds are part of the design

`MAX_REPS` is 10. A band that needs more copies than that silently falls back to
the flat carcass tile, which reads as a slab where artwork should be. Any change
that makes growth bands shorter must be checked against the copy count it
implies at the scales the judges actually render (1.5× taller, 2× wider), not
just against how bare the band is.

## Open faults, deliberately left

- **Phantom fittings.** A cabinet's right-hand panel carries a vent, a coin slot
  and two buttons over blank wall. Unmeasurable by everything tried; see above.
- **Body growth on a densely-fitted prop.** No single band is at once tall
  enough to repeat, bare, quiet and body-coloured. `strip_slice.py` says what
  the structural fix would be. Do not attempt it as another weight.
- **Every part mask is a rectangle** on the props measured, so a round button is
  modelled as a rectangular cap. The mask pipeline can carry a real shape; the
  segmentation draws boxes.
