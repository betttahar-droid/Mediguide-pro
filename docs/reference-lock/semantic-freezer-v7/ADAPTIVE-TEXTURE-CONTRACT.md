# Adaptive texture contract V7

This pass separates four properties that older passes accidentally treated as one:

1. **Anchor** — the fixed world-space distance from a named edge or mounting plane.
2. **Extent** — whether the occupied region stays fixed or expands between fixed margins.
3. **Pitch** — the world-space spacing and line width inside an expanding region.
4. **Layer** — which mark is physically in front when two semantic regions overlap.

## Runtime rules

- Fittings such as vents, labels, fans and handles keep a fixed texel size.
- A fitting is anchored to a named edge, never to a percentage of the resized face.
- A large structural field, such as the rear condenser, expands between independently measured margins.
- Its repeated marks are evaluated in model texels. Scaling adds repeats; it does not stretch existing marks.
- Face orientation follows one explicit basis per face. Runtime checker mirroring is prohibited.
- Overlap is accepted only when the frontmost owner is explicit. The side vent physically occludes the wear decal beneath it; rear labels intentionally sit above the condenser field.

## Required audit matrix

Every future asset must be rendered at base scale and with width, depth and height changed independently. The audit must reject the asset if any of these conditions fails:

- fixed fitting dimensions change;
- a contracted edge distance changes;
- an adaptive field pitch or line width changes;
- an expanding axis does not increase repeat count;
- fixed margins change;
- a texture/support unit conversion creates an implausible extent;
- a label is behind its support or an unintended decal is in front;
- the face basis is incomplete or a shader mirrors alternate tiles;
- a fixed-camera screenshot shows a changed pixel frequency;
- any correspondence is unconsumed, any magenta key leaks, or the runtime reports an error.

## Current measured evidence

- Side vent rear offset: `12.513 tx` at depth `1.0` and `1.5`.
- Condenser base extent: `38.828 × 71.154 tx`.
- Condenser width-scaled extent: `58.628 × 71.154 tx`.
- Condenser height-scaled extent: `38.828 × 101.4492 tx`.
- Condenser repeat counts: `15 × 8`, `23 × 8`, and `15 × 12`.
- Fixed-camera rail pitch: `15 px` before and after width scaling.

Run the gate with:

```powershell
npm.cmd run compile:semantic-freezer-v7
node tools/semantic-freezer/shoot.mjs docs/reference-lock/semantic-freezer-v7/audit-runtime "texture=v7&view=back&fit=0" "texture=v7&view=side&fit=0&sy=1.5" "texture=v7&view=back&fit=0&sx=1.45" "texture=v7&view=back&fit=0&sz=1.3"
npm.cmd run audit:semantic-freezer-v7
npm.cmd run test:semantic-freezer-v7
```
