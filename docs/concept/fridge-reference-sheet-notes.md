# Vaccine fridge reference-sheet decisions

Generated from the five user-supplied style references and the fixed prompt in
`docs/concept-prompts.md`. These sheets are modeling references only; they are
not runtime assets.

## Form to build

- Proud cream structural cage around a darker recessed glass-door assembly.
- A real hollow carcass: separate side cheeks, rear wall, floor and roof.
- Slightly tapered upper body with clipped shoulder corners.
- Layered oversailing cap, deep condenser base, and heavy corner feet.
- Four empty shelf slabs; products remain a separate population layer.
- Separate handle, readout housing, grille module and door assembly.
- Pixel detail belongs to textures, never pixel-shaped geometry.

## Resize behavior

- Width is a repeat axis. Door bays are rebuilt at thresholds rather than
  stretching one door.
- Rails use repeatable trim strips at a constant texel density.
- Readout, hinges, grille marks, glass streak and decals occupy fixed-size atlas
  islands and are re-anchored when dimensions change.
- Side and rear panels may tile or add repeat sections; their texels never
  scale with the carcass.

## Texture architecture: layered pixel nine-slice

The common material atlas is not sufficient for this asset. It knows what a
surface is made from, but it cannot know where a fridge panel ends or where its
specific bolts and baked corner shadows belong. The fridge therefore uses five
composited layers, evaluated in this order:

1. **Material tile** — a constant-density, nearest-filtered material field in
   part-local metres (target: one texel per 0.02 m). It repeats and never scales.
2. **Baked face value** — three flat albedo values for top/light, front/mid and
   side/dark. This is authored shading in the texture, not a smooth lighting
   gradient. Runtime lighting must remain weak enough not to overwrite it.
3. **Panel nine-slice** — fixed-size corner cells and edge strips containing
   corner highlights, inset borders and terminal seams. Only the deliberately
   blank centre tiles when a panel grows.
4. **Anchored decals** — fixed-resolution islands for bolts, hinges, glass
   streaks, the temperature display and grille endpoints. Their world size is
   invariant; resize logic repositions or repeats them per door bay.
5. **Geometry** — only details that affect silhouette, produce a real opening,
   or need functional depth: carcass, door/frame, glass, shelves, handle,
   readout housing, cap, base and condenser recess.

Each generated panel texture must use integer texel dimensions calculated from
its physical dimensions. Width or height changes allocate more texels rather
than resampling the old image. This makes the system resolution-independent and
prevents stretching by construction.

### Shader/geometry data required

- `aPartUv`: normalized 0–1 coordinates within the individual part face.
- `aPartSize`: physical width and height of that face in metres.
- `aFaceClass`: top, front, side, underside or interior.
- `aDetailId`: panel, glass, grille, screen, rail or undecorated material.
- Pixel coordinates are derived as `floor(localMetres / 0.02)` before atlas
  lookup; sampling remains nearest-neighbour.
- The panel nine-slice border is specified in texels, never as a normalized
  percentage, so it remains the same thickness at every size.

### Variant rules

- One-door master: approximately **2.30–2.40 height/width**, measured from the
  approved turnaround rather than the current squat Blender pass.
- Two-door: one wider carcass, two complete fixed-width door-detail regions,
  one cap, one condenser base and one thermostat.
- Three-door threshold: a 2+1 structural composition on one continuous plinth;
  no stretched third of a two-door texture.
- Bolts repeat only at structural corners. They do not tile through the centre.
- The grille centre strip repeats horizontally, while both grille end caps stay
  fixed.

## Topology target

- Flat normals, no subdivision and no smooth curved surfaces.
- One narrow chamfer segment only where it changes the silhouette.
- Approximately 270 triangles excluding four shelves for the single-door base
  version; shelves add roughly 80 triangles in the generated topology guide.
- Painted seams, fasteners, screen graphics, glass reflection and grille slots
  remain texture-only.
