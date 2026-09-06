# Prop Factory

Prop Factory packages the successful V7 workflow into a deterministic, model-agnostic tool. It is designed so an inexpensive coding model can work reliably without receiving a long conversation or making global art-direction decisions.

## Local web studio

The easiest entry point is `studio/open-studio.cmd`. Double-click it to start the local server and open the Studio, or run:

```powershell
npm.cmd run prop-factory:studio
```

Then open `http://127.0.0.1:5197/`. The Studio discovers the models already installed in Ollama. Pick a builder model, optionally attach up to five reference images and pick a vision model, describe the prop, and generate. Completed props open in an embedded 3D viewer with independent width, depth, and height controls. Type a short change request to produce a non-destructive revision.

The browser never gives the language model filesystem access. The server requests schema-constrained JSON, normalizes it, performs deterministic anchor/scaling checks, and saves each revision under the gitignored `work/prop-factory-studio/` directory.

Recommended local roles:

- `qwen2.5:7b-instruct-q4_K_M` for the builder. A 3B model works for simple props, but the 7B model follows part/layer semantics more reliably.
- `gemma4:e4b` for reference-image analysis when installed with vision capability.
- No vision model or image upload is needed for prompt-only props.

## Why it costs less

- Measurement, placement, scaling behavior and layer ownership live in `asset-spec.json`.
- Compilation and auditing are ordinary Python; they use no model tokens and no image API.
- A small model receives one short task at a time: geometry, fittings, adaptive fields, or a specific failed audit.
- Nano Banana or another image model is optional and is used only to reconstruct genuinely missing visual evidence. It is never trusted with geometry, camera, layout or final atlas assembly.
- Failed regions are retried independently. Passing geometry and textures are not regenerated.

## Commands

Scaffold a recipe:

```powershell
python tools/prop-factory/prop_factory.py init --id pharmacy-cabinet --out work/props/pharmacy-cabinet
```

Compile a measured specification:

```powershell
python tools/prop-factory/prop_factory.py compile `
  --spec work/props/pharmacy-cabinet/asset-spec.json `
  --out work/props/pharmacy-cabinet/generated
```

This writes:

- `compiled-contract.json`: exact field bounds, fitting centers, sizes, pitches and counts for every scale case;
- `audit-plan.json`: the required render matrix and commands;
- `LOW-COST-TASKS.md`: four small, bounded prompts suitable for a low-cost coding model.

Audit runtime evidence:

```powershell
python tools/prop-factory/prop_factory.py audit `
  --compiled work/props/pharmacy-cabinet/generated/compiled-contract.json `
  --runtime docs/reference-lock/pharmacy-cabinet/audit-runtime/audit.json
```

Or compile, render every independent scale case, run numerical checks and run pixel-frequency probes with one command:

```powershell
python tools/prop-factory/prop_factory.py build `
  --spec tools/prop-factory/examples/semantic-freezer/asset-spec.json `
  --out docs/reference-lock/semantic-freezer-v7/prop-factory
```

## Cheap repeatable workflow

1. A human or vision pass measures the reference once and fills the spec.
2. The compiler rejects missing anchors, invalid layers, impossible sizes and bad pitch rules.
3. A small coding model implements one generated task packet and connects the model to a renderer that exposes the runtime evidence contract below.
4. The renderer produces base, width, depth and height evidence.
5. The deterministic audit compares actual runtime values with the compiled contract.
6. Only failed items are sent back to the small model.
7. The asset is accepted only after the runtime audit and visual render review both pass.

The semantic freezer example reproduces the current V7 anchors and condenser behavior:

```powershell
npm.cmd run prop-factory:example
```

Its source recipe is `examples/semantic-freezer/asset-spec.json`.

The generated freezer gate checks 14 contract groups. Its visual probes independently verify horizontal and vertical texture frequency, so a shader that reports the right numbers but actually smears on screen still fails.

## Cost tiers

- **Zero model cost:** compile recipes, calculate placements, render scale cases, and audit results.
- **Low-cost text model:** implement one generated geometry or placement task and repair named mismatches.
- **Vision/image model only when needed:** measure a difficult reference or reconstruct a hidden face with geometry-locked diagnostic inputs.
- **Higher-cost model:** reserve for ambiguous art direction or conflicting references, not ordinary asset production.

## What the small model is allowed to decide

- how to express already-measured box geometry cleanly;
- how to connect named mounting planes;
- how to implement the provided fixed fitting and adaptive field contracts;
- how to correct a mismatch named by the audit.

It is not allowed to invent measurements, move anchors by eye, change passing regions, stretch bitmaps, mirror face bases, or silently reorder layers.

## Runtime adapter contract

`compile` works immediately on a new scaffold. Before `build`, set `runtime.rendererScript` to the asset's screenshot runner. That runner must write an `audit.json` containing one record per requested scale case and expose:

- `scale`, `errors`, `faceBasis`, and `textureLayers`;
- `fittingPlacements` with ID, face, layer, center, fixed size and mounting plane;
- `adaptiveTexturePanels` with bounds, extent, pitch, line width, repeat counts and margins;
- `fixedFittingSizes`, `rigidPartSizes`, and `correspondenceIds`.

The existing semantic-freezer renderer is the complete working adapter. New models can copy its small stats block instead of inventing another audit format.

## Image-generation policy

Use direct reference pixels whenever visible. For missing surfaces, send the image model the raw locked render, part ID, face normal, depth and anchor guide. Ask for a geometry-locked paintover on magenta. Extract semantic regions from the approved paintover, then let deterministic scripts build the atlas or procedural field. Never ask the image model for a complete final atlas.
