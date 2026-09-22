# Mediguide-pro

Two things live here. Most sessions are about the second.

- `src/` — the game/app itself.
- `tools/authoring/` — **the prop maker**. This is where nearly all recent work
  has happened.

## The goal

**One prompt in — "arcade cabinet" — a game-ready asset out, with nobody in the
loop.** The tool draws its own references, decomposes them, builds the geometry,
renders itself, judges itself, and keeps going until the result is one a studio
would ship. A human types the prompt and comes back to a finished prop.

The asset has to be three things at once, and the third is what makes this hard:

1. **PS1-era.** Low-poly, hand-painted, texture-led. A look, deliberately.
2. **Animatable by parts.** Not one mesh. A coin door that hinges from its own
   edge, a joystick that moves, a flipper that flips — each a named node with
   its own pivot, in the glTF.
3. **Resizable, and still correct.** This is the whole difficulty. A cabinet at
   2× width must become a *two-player* cabinet — a second joystick, a second
   button set — not a stretched one. A vending machine 1.5× taller gains a shelf
   of product, not taller product. **The prop has to understand what a bigger
   one of itself is**, and no amount of scaling a mesh gets you that.

### What "done" means, as numbers

Not opinions — every one of these is measured by a tool in this directory:

| | measure | now | done |
|---|---|---|---|
| shape | outline IoU vs. its own elevations, all 3 axes | median ~0.98 | **≥0.97 every prop** |
| widening | `repeat_score` rise over the prop's own 1× | 4/98 over bar | **0 over bar** |
| heightening | same, on the tall axis | 24/98 over bar | **0 over bar** |
| promises | `scale_check`: does each part obey its own rule | 94/98 | **98/98** |
| evidence | `feature_intent` acceptance gate | 6 ACCEPTED | **ACCEPTED, not DRAFT** |
| asset | glTF: named nodes, pivots, 2 materials, clean normals | sound on 77 | **every prop** |

The gap between DRAFT and ACCEPTED is the honest one: a DRAFT complies with the
prompt, an ACCEPTED reconstruction *fits the reference*. Most props are drafts
because depth is unmeasurable from four elevations — see ROADMAP §2, which
records that as a fact about the format rather than a threshold to loosen.

## Read this before changing anything in tools/authoring

**`tools/authoring/CLAUDE.md` is the authority** on how to work in that
directory, and it is long because it is load-bearing. It records practices that
were each paid for by a real failure. Read it to the end before touching a
score, a weight or a threshold.

The other three, in the order they are useful:

| file | what it is for |
|---|---|
| `tools/authoring/PROGRESS.md` | what exists, what it measured, what is wired into the loop rather than merely built |
| `tools/authoring/MISTAKES.md` | 20 specific errors with their numbers. Ten shapes recur; recognising one costs minutes, repeating one costs a session |
| `tools/authoring/ROADMAP.md` | what to do next, in order, with what "done" means |

## The two rules that explain most of the code

1. **The model authors and names; arithmetic measures and verifies.** Never read
   proportions off pixels; never let a model's word stand without a measurement.
   A corollary discovered late and worth stating: an ask whose reply arithmetic
   *checks* can safely go to a much weaker (or free, or local) model. An ask
   nothing checks — the judges — cannot.
2. **Count the props your change breaks, not the one it fixes.**
   `tools/img2threejs-work/` holds 98 finished props and any threshold can be
   swept across all of them in seconds. A number fitted to one prop is not a
   result. `geometry_sweep.py` and `scale_check.py` exist for this.

Reverting is normal here. A reverted attempt with its numbers written down is
worth more than a change that moves a fault from one prop to another — that is
why the docstrings are full of them.

## Running it

Needs the dev server up (`npx vite --port 5173 &`) for anything that renders.

```bash
python3 tools/authoring/make_prop.py "arcade cabinet" --out work/test
python3 tools/authoring/geometry_sweep.py          # all 98 props, ~8 min
python3 tools/authoring/scale_check.py             # do the resize rules hold
```

**To run with no paid API** — ComfyUI for images, Ollama for reading and
writing — see `tools/authoring/LOCAL.md` and run:

```bash
bash tools/setup/local-setup.sh --pull
```

## Where things stand

Geometry is healthy (outline medians ~0.98–0.99 against the props' own
elevations). The open work is resizing and the stages that feed it:

- **Tall axis**: props that band when made 1.5× taller went **57/98 → 24/98**,
  median rise +0.380 → +0.069, in three steps — `strip_slice`'s copy target
  measured and corrected from 9 to 4, a bareness test that reads the *artwork*
  and not just the part list, and growth places authored by a free local vision
  model (which `strip_slice` verifies, so a weak model is safe there). 55 props
  better, 5 worse, and the 1× render never moved (max delta 0.0000).
- **Wide axis**: the judges' commonest complaint is a fitting duplicated and
  mirrored across a widened prop. Root cause found and gated, not yet repaired:
  `paint_out` was accepting a fill that had simply **redrawn** the fitting
  instead of removing it — 20% of 469 accepted holes — and the background plate
  is what a resize repeats. The gate is in (`--same-bar`); the built props keep
  their bad plates until `paint_out` is re-run on them, one image each.
- **Never rely on the verdict logs alone.** Only 22 of 98 props have ever been
  judged and those logs describe an older generation. Reasoning from them is how
  the wide axis was mis-reported as healthy.

## Security

`.env` at the repo root holds API keys, is gitignored and `chmod 600`. This is a
public repo. **It must never be committed**, and no key, token or secret belongs
in a commit message, a doc, or a code comment.
