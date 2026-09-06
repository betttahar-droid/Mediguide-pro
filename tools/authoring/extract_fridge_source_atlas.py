"""Extract the locked turnaround views into the 32-pixels-per-unit atlas."""
from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
OUT = ROOT / "public" / "textures" / "vaccine-fridge-source-atlas.png"
GLASS_OVERLAY = ROOT / "public" / "textures" / "vaccine-fridge-glass-reflection.png"
TOP_TEXTURE = ROOT / "public" / "textures" / "vaccine-fridge-top.png"
SHELF_TEXTURE = ROOT / "public" / "textures" / "vaccine-fridge-shelf.png"
HANDLE_TEXTURE = ROOT / "public" / "textures" / "vaccine-fridge-handle.png"

manifest = json.loads((LOCK / "source-manifest.json").read_text(encoding="utf-8"))
placements = {
    "front": (0, 0, 39, 96),
    "side": (40, 0, 37, 96),
    "back": (78, 0, 37, 96),
}
atlas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
for view, (ax, ay, width, height) in placements.items():
    bounds = manifest["views"][view]["candidateObjectBoundsPx"]
    color = Image.open(LOCK / f"{view}.png").convert("RGBA").crop(bounds)
    mask = Image.open(LOCK / f"{view}-mask-candidate.png").convert("L").crop(bounds)
    color = color.resize((width, height), Image.Resampling.NEAREST)
    mask = mask.resize((width, height), Image.Resampling.NEAREST)
    if view == "front":
        # Compensate only the pale enamel, which otherwise receives the
        # reference's baked shadow and the real scene lighting a second time.
        pixels = color.load()
        for py in range(height):
            for px in range(width):
                red, green, blue, alpha = pixels[px, py]
                if red > 150 and green > 140 and blue > 115:
                    pixels[px, py] = (min(255,int(red*1.15)), min(255,int(green*1.12)), min(255,int(blue*1.08)), alpha)
        # The source front is a flat illustration.  Remove its glass pixels so
        # the GLB's real cavity remains visible, then retain only the cyan
        # diagonal highlight as an independent fixed-scale glass decal.
        glass_box = (8, 17, 32, 69)
        glass = color.crop(glass_box)
        reflection = Image.new("RGBA", glass.size, (0, 0, 0, 0))
        source_pixels = glass.load()
        reflection_pixels = reflection.load()
        for gy in range(glass.height):
            for gx in range(glass.width):
                red, green, blue, _ = source_pixels[gx, gy]
                if gy < 22 and green - red >= 22 and blue - red >= 16 and green >= 135:
                    reflection_pixels[gx, gy] = (red, green, blue, 190)
        # Keep only the largest connected component: the diagonal reflection.
        candidates = {(gx, gy) for gy in range(glass.height) for gx in range(glass.width)
                      if reflection_pixels[gx, gy][3] > 0}
        components = []
        while candidates:
            stack = [candidates.pop()]
            component = []
            while stack:
                point = stack.pop()
                component.append(point)
                gx, gy = point
                for neighbor in ((gx-1,gy),(gx+1,gy),(gx,gy-1),(gx,gy+1)):
                    if neighbor in candidates:
                        candidates.remove(neighbor)
                        stack.append(neighbor)
            components.append(component)
        keep = set(max(components, key=len)) if components else set()
        for gy in range(glass.height):
            for gx in range(glass.width):
                if (gx, gy) not in keep:
                    reflection_pixels[gx, gy] = (0, 0, 0, 0)
                elif reflection_pixels[gx, gy][3]:
                    red, green, blue, _ = reflection_pixels[gx, gy]
                    reflection_pixels[gx, gy] = (int(red*.35), int(green*.85), int(blue*.85), 145)
        reflection.save(GLASS_OVERLAY)
        color.crop((4, 34, 7, 54)).save(HANDLE_TEXTURE)
        cut = mask.load()
        for gy in range(glass_box[1], glass_box[3]):
            for gx in range(glass_box[0], glass_box[2]):
                cut[gx, gy] = 0
    elif view == "side":
        # The orthographic side sheet is much brighter than the locked iso
        # panel.  Remove the baked exposure while retaining every source mark.
        pixels = color.load()
        for py in range(height):
            for px in range(width):
                red, green, blue, alpha = pixels[px, py]
                if py < 9:
                    factors = (.90, .90, .90)
                elif py < 76:
                    factors = (.68, .73, .74)
                else:
                    factors = (.88, .88, .88)
                pixels[px, py] = (int(red*factors[0]), int(green*factors[1]), int(blue*factors[2]), alpha)
    color.putalpha(mask)
    atlas.alpha_composite(color, (ax, ay))
OUT.parent.mkdir(parents=True, exist_ok=True)
atlas.save(OUT)

# Rectify source-proven planes from the locked isometric panel.  QUAD order is
# upper-left, lower-left, lower-right, upper-right in the source image.
iso = Image.open(LOCK / "iso.png").convert("RGBA")
top = iso.transform(
    (32, 28), Image.Transform.QUAD,
    (157, 33, 69, 78, 267, 140, 356, 96),
    Image.Resampling.NEAREST,
)
top_pixels = top.load()
for py in range(top.height):
    for px in range(top.width):
        red, green, blue, alpha = top_pixels[px, py]
        top_pixels[px, py] = (min(255,int(red*1.18)), min(255,int(green*1.11)), min(255,int(blue*1.03)), alpha)
top.save(TOP_TEXTURE)
iso.transform(
    (24, 14), Image.Transform.QUAD,
    (112, 290, 93, 304, 194, 338, 215, 323),
    Image.Resampling.NEAREST,
).save(SHELF_TEXTURE)
print(OUT)
