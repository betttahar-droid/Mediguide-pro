"""Compile Nano v6 suggestions into padded, fixed-size decal islands."""
from __future__ import annotations

from collections import Counter, deque
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
NANO = LOCK / "nano-banana-v6"
SOURCE = next(path for path in (
    NANO / "nano-fixed-decals-v6.png",
    NANO / "nano-fixed-decals-v6.jpg",
    NANO / "nano-fixed-decals-v6.webp",
) if path.exists())
V5_AUDIT = json.loads((LOCK / "nano-banana-v5" / "nano-reference-material-primitives-v5.audit.json").read_text())
OUTPUT = ROOT / "public" / "textures" / "vaccine-fridge-nano-decals-v6.png"
PREVIEW = NANO / "nano-fixed-decals-v6-compiled-preview.png"
AUDIT = NANO / "nano-fixed-decals-v6.audit.json"
LOGICAL = 16
SLOT = 24
GRID = 4

SPECS = (
    {"name": "cream_corner_chip", "cell": (0, 3), "role": "cream", "max": (6, 6), "edge": True},
    {"name": "steel_dark_mark", "cell": (1, 0), "role": "steel", "max": (6, 2)},
    {"name": "steel_light_mark", "cell": (1, 1), "role": "steel", "max": (6, 2)},
    {"name": "steel_fastener", "cell": (1, 3), "role": "steel", "max": (4, 4)},
    {"name": "teal_chip", "cell": (2, 0), "role": "teal", "max": (4, 4)},
    {"name": "teal_corner", "cell": (2, 2), "role": "teal", "max": (6, 6), "edge": True},
    {"name": "glass_stair", "cell": (3, 0), "role": "glass", "max": (5, 8), "edge": True},
    {"name": "shelf_end", "cell": (3, 1), "role": "steel", "max": (6, 3), "edge": True},
)


def palette(role: str) -> np.ndarray:
    entry = next(item for item in V5_AUDIT["materials"] if item["role"] == role)
    return np.asarray(entry["paletteRgb"], dtype=np.uint8)


def magenta(data: np.ndarray) -> np.ndarray:
    return ((data[..., 0] > 190) & (data[..., 2] > 170) &
            (data[..., 1] < 105) & (np.abs(data[..., 0].astype(int)-data[..., 2]) < 100))


def components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros(mask.shape, bool)
    result = []
    for y in range(mask.shape[0]):
        for x in range(mask.shape[1]):
            if not mask[y, x] or seen[y, x]:
                continue
            queue = deque([(x, y)])
            seen[y, x] = True
            component = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
                    nx, ny = px+dx, py+dy
                    if 0 <= nx < LOGICAL and 0 <= ny < LOGICAL and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = True
                        queue.append((nx,ny))
            result.append(component)
    return result


def compile_cell(cell: Image.Image, spec: dict) -> tuple[Image.Image, dict]:
    logical = cell.resize((LOGICAL, LOGICAL), Image.Resampling.BOX).convert("RGB")
    data = np.asarray(logical, dtype=np.uint8)
    background_mask = magenta(data)
    material_pixels = data[~background_mask]
    if not len(material_pixels):
        raise ValueError(f"{spec['name']}: no non-magenta source pixels")
    quantized = (material_pixels // 12) * 12
    base = np.asarray(Counter(map(tuple, quantized)).most_common(1)[0][0], dtype=np.int16)
    delta = np.linalg.norm(data.astype(np.int16) - base, axis=2)
    motif_mask = (~background_mask) & (delta >= 18)
    found = components(motif_mask)
    if not found:
        raise ValueError(f"{spec['name']}: no accent component survived base removal")
    if not spec.get("edge"):
        interior = [item for item in found if all(0 < x < 15 and 0 < y < 15 for x, y in item)]
        if interior:
            found = interior
    component = max(found, key=len)
    xs, ys = zip(*component)
    x0, x1, y0, y1 = min(xs), max(xs)+1, min(ys), max(ys)+1
    crop_mask = np.zeros((y1-y0, x1-x0), dtype=np.uint8)
    crop_rgb = data[y0:y1, x0:x1]
    for x, y in component:
        crop_mask[y-y0, x-x0] = 255

    max_w, max_h = spec["max"]
    scale = min(1.0, max_w / crop_mask.shape[1], max_h / crop_mask.shape[0])
    width = max(1, round(crop_mask.shape[1] * scale))
    height = max(1, round(crop_mask.shape[0] * scale))
    resized_mask = np.zeros((height, width), dtype=np.uint8)
    for x, y in component:
        rx = min(width - 1, int((x - x0) * width / max(1, x1 - x0)))
        ry = min(height - 1, int((y - y0) * height / max(1, y1 - y0)))
        resized_mask[ry, rx] = 255
    mask_image = Image.fromarray(resized_mask, "L")
    rgb_image = Image.fromarray(crop_rgb).resize((width, height), Image.Resampling.NEAREST)
    rgb = np.asarray(rgb_image, dtype=np.int16)
    values = rgb[...,0]*.2126 + rgb[...,1]*.7152 + rgb[...,2]*.0722
    base_luma = base[0]*.2126 + base[1]*.7152 + base[2]*.0722
    colors = palette(spec["role"])
    mapped = np.empty((height, width, 4), dtype=np.uint8)
    mapped[..., :3] = colors[1]
    mapped[..., :3][values >= base_luma + 8] = colors[2]
    mapped[..., 3] = np.asarray(mask_image)

    result = Image.new("RGBA", (LOGICAL, LOGICAL), (0,0,0,0))
    px = max(2, (LOGICAL-width)//2)
    py = max(2, (LOGICAL-height)//2)
    result.alpha_composite(Image.fromarray(mapped, "RGBA"), (px, py))
    bbox = result.getchannel("A").getbbox()
    if not bbox or min(bbox[0], bbox[1], LOGICAL-bbox[2], LOGICAL-bbox[3]) < 2:
        raise ValueError(
            f"{spec['name']}: internal safety margin failed bbox={bbox} size={width}x{height} "
            f"maskMax={np.asarray(mask_image).max()} mappedAlpha={mapped[...,3].max()}"
        )
    return result, {
        "sourceCell": list(spec["cell"]),
        "role": spec["role"],
        "sourceComponentPx": len(component),
        "compiledBoundsPx": list(bbox),
        "internalMarginPx": min(bbox[0], bbox[1], LOGICAL-bbox[2], LOGICAL-bbox[3]),
    }


def main() -> None:
    board = Image.open(SOURCE).convert("RGB")
    if board.width != board.height or board.width % GRID:
        raise ValueError(f"Expected square 4x4 Nano board, got {board.size}")
    cell_size = board.width // GRID
    atlas = Image.new("RGBA", (SLOT*GRID, SLOT*GRID), (0,0,0,0))
    entries = []
    for index, spec in enumerate(SPECS):
        column, row = spec["cell"]
        cell = board.crop((column*cell_size, row*cell_size,
                           (column+1)*cell_size, (row+1)*cell_size))
        decal, metadata = compile_cell(cell, spec)
        slot_x, slot_y = (index % GRID)*SLOT, (index // GRID)*SLOT
        atlas.alpha_composite(decal, (slot_x+4, slot_y+4))
        entries.append({
            "name": spec["name"],
            "atlasRectPx": [slot_x+4, slot_y+4, LOGICAL, LOGICAL],
            "slotRectPx": [slot_x, slot_y, SLOT, SLOT],
            "atlasMarginPx": 4,
            **metadata,
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(OUTPUT, optimize=False)
    atlas.resize((atlas.width*6, atlas.height*6), Image.Resampling.NEAREST).save(PREVIEW, optimize=False)
    audit = {
        "schemaVersion": 6,
        "generator": "gemini-3.1-flash-image (Nano Banana 2) + deterministic decal compiler",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "sourceSha256": sha256(SOURCE.read_bytes()).hexdigest(),
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "atlasSizePx": list(atlas.size),
        "policy": "dominant panel removed; largest deliberate component; locked v5 palette; 2px internal plus 4px atlas margin",
        "decals": entries,
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"PASS compiled {len(entries)} padded Nano decals to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
