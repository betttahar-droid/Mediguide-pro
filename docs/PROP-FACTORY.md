# Affordable repeatable prop generation

The reusable tool is [Prop Factory](../tools/prop-factory/README.md). It converts measured prop recipes into exact multi-scale contracts, short tasks for low-cost coding models, render commands, and deterministic runtime audits.

For prompt-driven use, launch the local web Studio:

```powershell
npm.cmd run prop-factory:studio
```

Open [Prop Factory Studio](http://127.0.0.1:5197/), choose an installed Ollama builder model, add references when useful, and iterate in the embedded adaptive 3D viewer. All generation stays local and every revision is retained separately.

The complete freezer recipe is [asset-spec.json](../tools/prop-factory/examples/semantic-freezer/asset-spec.json). Its latest generated proof is [runtime-audit.json](reference-lock/semantic-freezer-v7/prop-factory/runtime-audit.json).

Run the proven example:

```powershell
npm.cmd run prop-factory:example
```

Start another prop:

```powershell
python tools/prop-factory/prop_factory.py init --id my-prop --out work/props/my-prop
```

The essential production rule is: models propose bounded code, while scripts own measurements, anchors, scaling contracts, orientation, layers, and acceptance.
