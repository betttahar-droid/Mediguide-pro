# Voxel fridge prototype

An exact-match attempt at the pixel-art vaccine fridge reference, built the
way the reference's own texture kit is built. Not wired into the game — it is
a technique proof, to be folded back into the catalogue if the look holds.

    npm run dev
    open http://localhost:5173/tools/voxel-fridge/index.html
    ...?w=40        widen the cabinet
    ...?yaw=30&pitch=18   camera

## What it demonstrates

**Geometry from the coordinate table.** Every part is an axis-aligned box read
straight off the reference's FINAL IMMUTABLE COORDINATE TABLE, mapped from
Blender (z-up, front -y) to three (y-up, front -z). No mesh files.

**Texturing in layers, not UVs.** Each face gets its own canvas composited at
exactly 32 px per Blender unit — the kit's own grid — from named layers:

    fill        tileable centre field
    speckle     sparse flecks, the kit's "tileable centre"
    bevel       edge strips: dark outline, light top/left, dark bottom/right
    cornerBolts fixed corner islands
    grille      fixed end caps + slots tiled horizontally between them
    display     fixed decal, pixel glyphs
    glass       fixed diagonal reflection streak

Because the canvas is sized from the part's real dimensions at a FIXED texel
density, a wider part gets a wider canvas — more texture, not stretched
texture. Corners, bolts, the display and the handle are drawn at fixed pixel
sizes from the edges, so they never scale; only the centre fields and the
grille's slot run tile. That is the whole adaptability argument, and it needs
no UV work at all.

**Shading baked, not lit.** The reference paints its shading per face, so
every material is MeshBasicMaterial and the face orientation picks a tint
factor (front 1.0, sides 0.90, top 1.05, bottom 0.82). Nothing in the scene
is a light.

**Pixel output.** Rendered at ~380x500 and CSS-upscaled x2 with
image-rendering: pixelated, so the screen grid is the texture grid.


## The atlas is a nine-slice sprite kit

`make_atlas.py` writes `atlas.png` + `atlas.json`. The reference sheet labels
its own regions — tileable centres, FIXED corners and edge strips, FIXED decal
islands, a grille that is "END CAPS (FIXED) + SLOTS (TILEABLE HORIZONTAL)" —
and that labelling *is* the architecture. Every surface is one patch with a
fixed outer ring and a tiling middle; `sliceAxis` in the fragment shader
reconstructs any part size from it.

No UV attribute is read anywhere. A fragment asks how many texels it is from
its own face's edge (from position and the part's half-extents), and the
nine-slice map answers with a corner texel inside the ring and a tiling centre
texel outside it. So geometry can be any size, including fractional, and
nothing stretches — corners stay native, centres tile further.

### Three rules this technique runs on

1. **A patch's pixel size is the part's world size** on any axis it does not
   tile. The grille tiles on x only, so its height must be exactly
   `patchHeight / texelsPerUnit`. Left at 7 units against a 3-unit patch it
   tiled vertically too and the slots collapsed into a mesh.
2. **A fixed decal has no tiling centre**, so its geometry size must come FROM
   the atlas — `decalBox()` enforces this. Sizing one by hand reads outside its
   own rect and renders garbage.
3. **Texel density must match render density.** Authored at 32 texels/unit and
   rendered at ~4 px/unit, the grille aliased into moire: six texels fighting
   over every screen pixel. The sheet is now 8 texels/unit and the renderer
   draws 8 px/unit — one texel, one pixel.

Two more traps worth recording: three sets `flipY` on upload by default, which
put every sample in the sheet's dark background and rendered the whole cabinet
black; and each face needs a *signed* basis, not just a pair of axes, or the
two faces of an axis mirror each other and the temperature display reads
backwards.
