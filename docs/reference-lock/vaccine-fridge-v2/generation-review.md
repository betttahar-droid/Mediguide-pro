# Nano Banana 2 generation review

Authority: `docs/concept/vaccine-fridge-turnaround-v1.png`

No generated measurement is allowed into the production specification unless
it is independently supported by the authority image. The canonical geometry
remains `../vaccine-fridge-v1/geometry-authority.json`.

## Accepted as guidance

- `gemini-source-geometry-correction-v2.jpg`: accepted for the overall
  silhouette, crown steps, front depth stack, empty cavity, shelf lips, handle
  mount concept and geometry-versus-texture separation. It proposes no accepted
  dimension that was not already present in the canonical specification.
- `gemini-source-texture-decomposition-v2.jpg`: accepted as a semantic texture
  guide. Its fixed corners, repeatable strips, glass reflection, display,
  handle, grille and shelf groupings match the intended runtime architecture.
- `gemini-part-shell-v3.jpg`: accepted as a structural assembly illustration.
  Its displayed dimensions repeat the supplied canonical values. It adds no new
  production measurements.
- `gemini-runtime-atlas-v3.jpg`: accepted as texture source material only. Its
  4x4 grouping and source palette are useful for authoring a deterministic
  atlas.

## Rejected for production measurements

- All v2 isolated part sheets: rejected because they invented dimensions and
  unsupported construction.
- `gemini-part-opening-v3.jpg`: useful for communicating the front-to-back
  layer idea, but rejected as geometry authority because shelf positions and
  several labels are inconsistent and it changes the door presentation.
- `gemini-part-hardware-v3.jpg`: rejected as geometry and texture authority. It
  changes the grille into an unsupported ornamental pattern and truncates some
  supplied socket coordinates.
- `gemini-runtime-atlas-v3.jpg` is not a runtime atlas. The model returned JPEG
  and painted checkerboards instead of alpha; cell boundaries and seamlessness
  must be reconstructed and verified deterministically before use.

## Result

The experiment supports a hybrid workflow: use Nano Banana 2 for whole-object
correction, semantic decomposition and texture source material; use the locked
turnaround plus the canonical JSON for dimensions, topology, sockets and final
assembly. Independently generated part sheets are not reliable enough to drive
mesh coordinates without a deterministic acceptance gate.

