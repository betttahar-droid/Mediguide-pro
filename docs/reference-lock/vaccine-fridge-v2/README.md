# Vaccine fridge v2 hybrid pipeline

The locked turnaround remains the only visual authority. Nano Banana 2 sheets
are measurement proposals, not production geometry. A generated change reaches
the GLB only after its accepted coordinates are written to
`../vaccine-fridge-v1/geometry-authority.json`.

## Prepare or generate the sheets

```powershell
# Save all exact prompts without making network requests.
powershell -ExecutionPolicy Bypass -File tools/authoring/gemini_fridge_source_v2.ps1 -Pass All -PrepareOnly

# Generate all sheets with Gemini 3.1 Flash Image / Nano Banana 2.
powershell -ExecutionPolicy Bypass -File tools/authoring/gemini_fridge_source_v2.ps1 -Pass All
```

The three part sheets always retain a faint full-fridge registration silhouette
and the same 32-pixel grid. This prevents independently generated parts from
silently changing scale or attachment position.

Generated output can be JPEG even when an image-oriented response is requested;
the script preserves the MIME-appropriate extension. See `generation-review.md`
before promoting any sheet or atlas into production.

## Accept, build, and gate

1. Compare a generated sheet with the locked turnaround.
2. Copy only accepted measurements into the canonical JSON specification.
3. Run `npm run build:fridge-source`.
4. Run `npm run gate:fridge-source`.

For a calibration-only measurement pass, run `npm run measure:fridge-grid`.
It converts raster silhouette bounds into model pixels using the known 96-pixel
height and records the measured width/depth, error, and one-raster-pixel
uncertainty in `source-grid-measurements.json`.

The gate regenerates front, side, and back silhouettes, writes overlays and
metrics, and verifies the GLB metadata, parts, shelf repetition, texture
sampling, and resize policy.

## Adaptive geometry and texture contract

- Width variants are `8 + doorCount * 32` model pixels: 40, 72, and 104 pixels
  for the current one-, two-, and three-door outputs.
- Geometry inserts complete door bays. It never stretches a door into another
  door count.
- Panel textures use integer target texel dimensions. Protected corner and edge
  texels map 1:1; only the center interval repeats.
- Grille end caps remain fixed while its middle repeats horizontally.
- Handles, hinges, bolts, wear marks, displays and glass-reflection decals are
  fixed-size islands attached to semantic sockets and duplicated per bay where
  appropriate.
- All runtime sampling uses nearest filtering without generated mipmaps.

Run `npm run build:fridge-variants` to regenerate and validate all three GLBs.
Run `npm run test:fridge-adaptive` to validate nine-slice texel mapping and the
one-, two-, and three-door allocation plans without launching Blender.
