"""Create the spatial guide and exact prompt for the Nano Banana 2 decal sheet."""
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "nano-banana-v10"
OUT.mkdir(parents=True, exist_ok=True)

SIZE = 1024
CELL = SIZE // 4
guide = Image.new("RGB", (SIZE, SIZE), "#ff00ff")
draw = ImageDraw.Draw(guide)
for row in range(4):
    for column in range(4):
        x0, y0 = column * CELL, row * CELL
        # This is input-only scaffolding. Nano must remove it in the output.
        draw.rectangle((x0 + 42, y0 + 42, x0 + CELL - 43, y0 + CELL - 43),
                       outline="#7f7f7f", width=3)
        draw.line((x0 + CELL // 2 - 8, y0 + CELL // 2,
                   x0 + CELL // 2 + 8, y0 + CELL // 2), fill="#ffffff", width=2)
        draw.line((x0 + CELL // 2, y0 + CELL // 2 - 8,
                   x0 + CELL // 2, y0 + CELL // 2 + 8), fill="#ffffff", width=2)
guide.save(OUT / "adaptive-decals-v10-layout-guide.png", optimize=False)

prompt = """Use case: stylized-concept
Asset type: source decal atlas for a deterministic retro PS1/pixel-art 3D prop system

Images 1-5 are the style authorities. Match their deliberate chunky pixel clusters, stepped highlights, compact mechanical seams, restrained color ramps, and readable low-resolution character. Image 6 is the accepted vaccine-fridge geometry. Image 7 is a SPATIAL GUIDE ONLY showing sixteen safe zones. Do not copy its grey frames or white crosshairs.

Generate exactly one square 4-column by 4-row board. The whole unused background must be perfectly uniform #FF00FF magenta. No grid, frames, crosshairs, labels, text, numbers, shadows, captions, borders, watermark, or full appliance. Put exactly one isolated hard-edged pixel decal in the center of every cell, with a very wide magenta margin. Each decal occupies 30-50% of its cell and never touches a cell boundary.

Cell jobs, left-to-right and top-to-bottom:
1 steel stepped top-left panel joint
2 steel stepped bottom-right panel joint
3 steel short horizontal double seam
4 steel short vertical service seam
5 steel paired square fasteners connected by a short bar
6 cream enamel corner catch with one warm shadow pixel
7 cream short pressed-panel seam with asymmetric end caps
8 deep-teal recessed rectangular patch with one stepped corner
9 deep-teal short mechanical seam with a dark end cap
10 blue-green glass diagonal staircase reflection
11 pale-steel shelf end-cap and lip cluster
12 warm-ochre grille corner bracket
13 muted-purple handle end cap
14 tiny amber caution plate made only of abstract bars, no readable text
15 compact control-panel status glyph made of 3 connected colored squares
16 dark steel ventilation notch cluster

Style constraints:
- authentic low-resolution nearest-neighbour square pixels; no antialiasing, gradients, blur, glow, soft shadow, or photographic detail;
- 2-4 flat colors per decal, using only the material family implied by its cell;
- connected orthogonal clusters, normally 2-9 logical pixels long and 1-3 pixels thick;
- intentional stair steps and asymmetry; broad empty centers and generous magenta isolation;
- decals describe manufactured construction, not dirt: no scratches, rust, dust, random speckles, cracks, stains, or surface noise;
- no rectangular background tile behind a decal; only the decal pixels exist on magenta;
- preserve the reference's retro palette relationships and visual density, but do not redraw or modify the refrigerator.

The downstream compiler will remove magenta, keep the dominant connected component, reduce each cell to 16x16 logical pixels, quantize it into the locked material ramps, and reject insufficient margins or disconnected noise."""
(OUT / "adaptive-decals-v10-prompt.txt").write_text(prompt, encoding="utf-8")
print(f"GUIDE={OUT / 'adaptive-decals-v10-layout-guide.png'}")
print(f"PROMPT={OUT / 'adaptive-decals-v10-prompt.txt'}")
