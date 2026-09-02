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
