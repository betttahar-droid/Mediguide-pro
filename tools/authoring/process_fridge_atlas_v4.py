"""Convert Nano Banana's strict 4x4 sheet into a runtime RGBA atlas."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / "docs" / "concept" / "vaccine-fridge-atlas-v5.png"
dst = ROOT / "public" / "textures" / "vaccine-fridge-atlas-v5.png"
im = Image.open(src).convert("RGBA")
if im.size[0] != im.size[1] or im.size[0] % 4:
    raise RuntimeError(f"Atlas must be a square 4x4 grid, got {im.size}")
cell = im.size[0] // 4

# Nano rendered transparency as a checker. Learn its two dominant colors from
# the mandated empty cell, then turn only those colors transparent in island
# cells. Opaque material fields in row zero remain untouched.
# v5 accidentally filled the mandated empty cell, so use the checker colors
# measured from the previously validated v4 empty cell rather than relearning
# them from untrusted generated content.
checker = [(255, 255, 255), (203, 203, 203)]
pixels = im.load()
for y in range(cell, im.height):
    for x in range(im.width):
        rgb = pixels[x, y][:3]
        if any(max(abs(rgb[i] - bg[i]) for i in range(3)) <= 25 for bg in checker):
            pixels[x, y] = (*rgb, 0)

dst.parent.mkdir(parents=True, exist_ok=True)
im.save(dst)
print(f"ATLAS {dst} {im.width}x{im.height} cell={cell} checker={checker[:2]}")
