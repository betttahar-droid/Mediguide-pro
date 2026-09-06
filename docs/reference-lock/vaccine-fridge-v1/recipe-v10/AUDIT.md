# Adaptive decal texture v10 audit

Status: **PASS**

V10 keeps the accepted v9 macro geometry and replaces visually empty surfaces with controlled Nano-derived decal fields. It does not replace the approved v5 GLB.

## Placement classes

- **Rigid hardware:** the handle remains `3.2 × 2.55 × 18` texels under independent X/Y/Z resizing. Its anchor follows the opening, but its geometry never stretches.
- **Protected decals:** display, grille, lights, hinges, corner fittings, handle cap, and handle highlight keep the exact same texel dimensions and corner/plane relationship.
- **Adaptive fields:** shelf ends, panel joints, roof marks, side-panel marks, base marks, and glass accents remain fixed-size. Their count changes to cover additional area.

No random hash or continuous noise is used. Every mark belongs to a semantic surface region and respects a protected edge margin.

## Resize comparison

| View | Parts | Total decals | Adaptive decals | Triangles | Exact colours |
|---|---:|---:|---:|---:|---:|
| Front | 22 | 43 | 24 | 1,886 | 26 |
| Isometric | 22 | 43 | 24 | 1,886 | 25 |
| Resized isometric | 23 | 57 | 38 | 1,926 | 25 |

## Acceptance results

- Protected decal sizes unchanged: pass.
- Rigid handle dimensions unchanged: pass.
- Adaptive decal count increased from 24 to 38: pass.
- Structural part count increased from 22 to 23: pass.
- Palette range 25–60: pass.
- Triangle budget 300–5,000: pass.
- Shader, page, and console errors: none.

The side-plane visual check caught and corrected a mounting-plane error: the first pass placed the side motifs on the hidden cabinet side. They now mount to the visible frontmost side plane.
