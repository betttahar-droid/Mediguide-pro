# Geometry-aware Nano Banana 2 texture pipeline — v11

Status: **PASS**

## Corrected workflow

1. Rendered the accepted geometry with every decal hidden.
2. Supplied the raw front and isometric renders to Nano Banana 2 together with the five project style references.
3. Asked Nano to change surface treatment only and assign marks by real function.
4. Used the resulting paintovers as visual placement authorities, not as projected texture maps. Nano changed the camera and some silhouette details slightly, so directly projecting them would be inaccurate.
5. Asked Nano for a second, isolated 4×4 magenta atlas containing only the functional marks present in the paintovers.
6. Compiled all 16 cells to 16×16 logical motifs, removed magenta, kept dominant connected components, enforced a 3-pixel gutter, and converted colour into neutral shade/base/highlight indices.
7. Recoloured those indices through the runtime's locked material families and placed them on named geometry planes.

Model used: `gemini-3.1-flash-image`, Google's Nano Banana 2 endpoint.

## Semantic placement

- Cream: frame corners, pressed seam, crown cap.
- Steel: side access seams, paired fasteners, shelf lips.
- Teal: base access seam and corner cap.
- Glass: alternating staircase reflections inside the opening.
- Plum: shelf end caps and rigid-handle highlight.
- Ochre: front ventilation grille and caution plate.
- Controls: fixed bezel plus fixed status lights.

No generic surface scatter is placed. Repeated marks correspond only to shelves, glass reflection bands, or service-panel bands.

## Acceptance results

| View | Parts | Decals | Adaptive decals | Triangles | Exact colours |
|---|---:|---:|---:|---:|---:|
| Front | 22 | 33 | 19 | 1,866 | 26 |
| Isometric | 22 | 33 | 19 | 1,866 | 27 |
| Resized isometric | 23 | 49 | 35 | 1,910 | 27 |

- All 16 atlas cells compiled: pass.
- All compiled atlas gutters at least 3 pixels: pass.
- Protected fitting dimensions unchanged after independent axis resize: pass.
- Handle remains exactly `3.2 × 2.55 × 18` texels: pass.
- Adaptive decal count rises from 19 to 35: pass.
- Structural count rises from 22 to 23: pass.
- Palette and triangle budgets: pass.
- Shader, page, and console errors: none.
