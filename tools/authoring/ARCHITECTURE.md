# Merging the Astra lessons into the pipeline that works

Two things exist and both are worth keeping.

**The pipeline** turns one noun into a resizable textured prop with nobody in
the loop, and it carries fifty-odd finished props and about thirty recorded
failures — every one of them a thing that looked obviously correct and was
measured and reverted. That corpus is the expensive part. It cannot be
rewritten; it can only be re-earned.

**The Astra findings** are a diagnosis of how a system like this lies to
itself: it checked object counts and primitive types instead of design intent,
returned "draft" before rendered validation, synthesised missing parts and then
counted them as successes, and confused face-local width/height/thickness with
world XYZ.

This session confirmed the diagnosis on our own corpus, twice:

- Both language judges scored a cabinet carrying **five stacked ARCADE
  marquees** at two blocking faults — exactly what they gave the corrected
  cabinet beside it. They passed a pinball standing on stilts at zero. The
  loop's only gate could not separate the worst prop from the best.
- Typed as intents, **95 props and 1673 feature instances produce not one
  ACCEPTED.** All 95 are DRAFT, on 291 unverified thicknesses. No elevation
  measures depth, so every opening and every recess in this repo rests on a
  four-word adjective.

So: graft, do not rewrite.

## The graft

`feature_intent.Feature` becomes the spine. The stages stay exactly where they
are; what flows between them changes.

```
segment_sheet ─┐
region_parts  ─┴─► parts_front.json      measured pixels, unchanged
                        │
                        ▼
                   feature_intent.lift()  ← typed, face-local, evidenced
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
    operators       layer_build      validate()
   (geometry)       (textures)      per instance
        └───────────────┼────────────────┘
                        ▼
               reduce_acceptance()  REJECTED / DRAFT / ACCEPTED
                        │
                        ▼
                   the judge loop
```

Three rules govern the graft:

1. **Nothing measured is thrown away.** `parts_front.json` stays the record of
   what the pixels say. `lift()` adds type, host, surface and evidence on top
   of it; it never replaces a measurement with an assertion.
2. **Every new gate must be able to correct what it blocks.** The rule already
   written in CLAUDE.md, and the reason `repeat_score` runs *in front* of the
   judges rather than behind them. An acceptance verdict with no lever is a
   loop that cannot converge.
3. **A reverted idea stays reverted.** The failure lists in the docstrings are
   live constraints. Any Astra-shaped change that re-proposes one of them has
   to beat the numbers already recorded against it.

## What the three verdicts mean here

| verdict | meaning | what may claim it |
|---|---|---|
| `REJECTED` | an instance failed a check outright | never shippable |
| `DRAFT` | nothing failed; something rests on a guess | prompt-compliant, **not** a reconstruction |
| `ACCEPTED` | every instance passed on MEASURED evidence | fitted to the reference |

Today every prop is DRAFT and the honest sentence is *"this complies with the
prompt and has not been fitted to its reference."* Saying anything stronger is
the failure Astra named.

## The model split

Costs are from this repo's own benchmark in `auto_prop.py`.

| job | who | why |
|---|---|---|
| architecture, thresholds, what to revert | the expensive model, rarely | these are judgment calls, and the recorded failures show most of them are wrong on the first try |
| implementing a specified module | a cheaper model | bounded work against a written contract and a test |
| naming parts, scale rules, judging | `glm-5.3-flash`, $0.0002/call | benchmarked most accurate judge of eight, at 1/190th of opus |
| drawing | Nano Banana | there is no cheaper tier that draws |
| counting repeats, measuring bands, acceptance | **no model at all** | arithmetic, free, deterministic, and better than both judges at the fault they report most |

The last row is the one that matters. Every job moved out of a model and into
arithmetic is a job that stops costing money *and* stops being wrong in the
way models are wrong about pictures.

## Order of work

1. **Aspect ranges per role, measured from the corpus.** 1673 of the 1673
   unverified checks are aspect. Measuring them turns the largest single
   source of UNVERIFIED into evidence.
2. **Under-segmentation guard.** The cabinet's marquee was never lifted, which
   is *why* `ARCADE` stacked five times; the vending machine's products were
   never parts, which is why widening gave blank panel. Upstream of most
   remaining Track-A faults.
3. **Operators** — `slot_array`, `panel/window with rim and recessed backing`,
   `handle with a real opening`. Turns a role from a label into a requirement.
4. **Depth from the reference.** The only route to an ACCEPTED prop.
5. **Transactional repair**, then **staged fitting**.

Not yet: the full geometry compiler. It wants 3 and 4 to exist first or it
gets built twice.
