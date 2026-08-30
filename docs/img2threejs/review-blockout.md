# Blockout review — pharmacy dispensing counter run

img2threejs stage 4, blockout pass. Render: `render-1x-and-3x.png` — the same
factory at 1× and 3×, in this project's renderer.

## Against the spec's own `featureReviewTargets`

| Target | Tier | Verdict |
| --- | --- | --- |
| `green-cross-plaque` | critical | **FAILED, then fixed.** It rendered CORAL. |
| `bay-repetition` | critical | Pass — 3× stretched only the middle band; ends rigid. |
| `worktop-oversail` | important | Pass — the top oversails and the shadow line reads. |

The cross failure is the one worth recording, because the gate caught exactly
what it was written to catch. The bridge was assigning accent slots **per
material**, and the plaque and the fascia band share `brass-fitting` while the
spec gives them different colours — so they collided on one slot and the plaque
took the fascia's brass. The spec's own failure-mode list says it: *"wrong hue —
a blue or grey cross reads as a hospital, not a pharmacy."* Slots are assigned
per distinct colour now, matched to the nearest palette entry so a regenerated
spec cannot drift outside the limited palette.

## Against the reference

Correct: the green-carcass / warm-timber split, the worktop oversail, the
proportions (0.90 × 0.95 × 0.66 per bay), the recessed plinth reading as a
shadow band, the drawer and door banks as separate timber fronts.

Approximate, and stated as such: this is **one bay of one run**, not the U-shaped
assembly in the reference. That was the intake decision (`intake-analysis.md`) —
the shelving and the loose props already exist here as `dispensary_shelving` and
the decor prop set, and rebuilding them into one rigid factory would duplicate
three modules and produce something that cannot be resized.

Not attempted at blockout: the lettered fascia is a plain band, not lettering.
Text at this texel density is two or three pixels tall and would read as noise.

## Two findings that outlived this object

**The generated factory's renderer is photoreal, and this is not.** It emits
`BoxGeometry(1, 1, 1, 12, 12, 12)` — ~1,700 triangles for a box whose every face
is flat, where 12 will do — with `flatShading` off unless asked, and a
presentation stack of RoomEnvironment, UnrealBloomPass and BokehPass. Bloom and
depth-of-field are both blur, and this style is defined by not blurring. The
same seven components through this project's `buildParts` come to **616
triangles**, non-indexed and faceted. So the bridge takes the reconstruction and
leaves the rendering: see `src/modules/fromSculptSpec.js`.

**The decor hash was not avalanching, and that was a real bug in shipped code.**
Nothing spawned on the counter at first. The slot keys are `s0`, `s1`, `s2` —
one character apart — and the raw FNV-1a values for eight sequential keys landed
inside a band **0.027 wide**. Every slot in a module therefore cleared or failed
its chance roll *together*, decided only by the seed: a 0.85 chance was firing
80.7% of the time and prop counts swung between runs. A murmur3 finalizer takes
the spread to 0.5–0.9 and the fire rate to 85.4%. That fix improves every
seeded layout in the game, not just this factory.

## Gate

Blockout accepted, and then immediately superseded — see below.

# Structural pass

Render: `render-structure-pass.png`.

The blockout was correct and it looked worse than the catalogue desk it sits
next to, which is the honest verdict on a blockout: seven boxes, one flat
"drawer bank" and one flat "door bank", no doors, no pulls, no frame. That is
what a blockout IS, and it is not something to ship.

The structural pass takes it to 21 components: two real drawer fronts and two
real DOOR LEAVES with a meeting stile, a pull on each of the four, stiles down
both sides, three rails, and a dark band under the worktop. 616 triangles to
1,188 — still an order of magnitude under the generated factory's ~12,000 for
the cruder version.

## The critical target failed again, differently

`bay-repetition` is listed critical with the failure mode *"length authored as
a stretch axis"*, and at 3× that is exactly what happened: every pull, plaque
and stile smeared along the run, because `AdaptivePropBase` only knew how to
9-slice. The spec had declared `repetitionSystems` from the start and nothing
was reading it.

It repeats now. Three bays at 3×, each at authored size, nothing distorted —
which is §1 of the brief and the same decision the dispensing bench makes.

## Known, and not fixed

A repeated bay repeats *everything*, so a three-bay run carries three green
cross plaques where a pharmacy has one. The catalogue modules avoid this by
keeping identity ornament off the repeated unit. Fixing it properly needs
per-bay variation — a first/middle/last distinction in the repeat system —
which is a real feature and not a tweak, so it is written down rather than
bodged.
