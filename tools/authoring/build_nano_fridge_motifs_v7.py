"""Compile the Nano v7 reference sheet into crisp, padded, fixed-size motifs."""
from __future__ import annotations

from collections import deque
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
NANO = LOCK / "nano-banana-v7"
SOURCE = next(path for path in (
    NANO / "nano-style-motifs-v7.png",
    NANO / "nano-style-motifs-v7.jpg",
    NANO / "nano-style-motifs-v7.webp",
) if path.exists())
V5_AUDIT = json.loads((LOCK / "nano-banana-v5" / "nano-reference-material-primitives-v5.audit.json").read_text())
OUTPUT = ROOT / "public" / "textures" / "vaccine-fridge-nano-style-motifs-v7.png"
PREVIEW = NANO / "nano-style-motifs-v7-compiled-preview.png"
AUDIT = NANO / "nano-style-motifs-v7.audit.json"
LOGICAL = 16
SLOT = 24
GRID = 4

SPECS = (
    {"name": "steel_top_left", "cell": (0, 0), "role": "steel", "max": (8, 8)},
    {"name": "steel_bottom_right", "cell": (1, 0), "role": "steel", "max": (8, 8)},
    {"name": "steel_double_seam", "cell": (2, 0), "role": "steel", "max": (9, 4)},
    {"name": "cream_top_left", "cell": (0, 1), "role": "cream", "max": (8, 8)},
    {"name": "cream_bottom_right", "cell": (1, 1), "role": "cream", "max": (8, 8)},
    {"name": "teal_top_left", "cell": (0, 2), "role": "teal", "max": (8, 9)},
    {"name": "teal_bottom_right", "cell": (1, 2), "role": "teal", "max": (8, 8)},
    {"name": "glass_glint", "cell": (2, 2), "role": "glass", "max": (6, 10)},
    {"name": "shelf_end", "cell": (3, 2), "role": "steel", "max": (8, 6)},
    {"name": "side_service_dashes", "cell": (0, 3), "role": "steel", "max": (10, 3), "components": 3},
    {"name": "grille_corner", "cell": (2, 3), "role": "ochre", "max": (8, 8)},
    {"name": "handle_cap", "cell": (3, 3), "role": "plum", "max": (8, 6)},
)

EXTRA_PALETTES = {
    "ochre": np.asarray(((195, 139, 77), (133, 82, 42), (235, 177, 96)), dtype=np.uint8),
    "plum": np.asarray(((70, 55, 80), (43, 31, 53), (106, 80, 116)), dtype=np.uint8),
}


def palette(role: str) -> np.ndarray:
    if role in EXTRA_PALETTES:
        return EXTRA_PALETTES[role]
    entry = next(item for item in V5_AUDIT["materials"] if item["role"] == role)
    return np.asarray(entry["paletteRgb"], dtype=np.uint8)


def is_magenta(data: np.ndarray) -> np.ndarray:
    rgb = data.astype(np.int16)
    return ((rgb[..., 0] > 190) & (rgb[..., 2] > 170) & (rgb[..., 1] < 110)
            & (np.abs(rgb[..., 0] - rgb[..., 2]) < 105))


def components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros(mask.shape, bool)
    result = []
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            queue = deque(((x, y),))
            seen[y, x] = True
            component = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            result.append(component)
    return result


def compile_cell(cell: Image.Image, spec: dict) -> tuple[Image.Image, dict]:
    width, height = cell.size
    # Nano added captions despite the prompt. Restrict analysis to the upper motif field.
    source = cell.crop((8, 8, width - 8, round(height * 0.80))).convert("RGB")
    data = np.asarray(source, dtype=np.uint8)
    foreground = ~is_magenta(data)
    found = [item for item in components(foreground) if len(item) >= 24]
    if not found:
        raise ValueError(f"{spec['name']}: no motif component")
    found.sort(key=len, reverse=True)
    selected = found[:spec.get("components", 1)]
    points = [point for component in selected for point in component]
    xs, ys = zip(*points)
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    crop = data[y0:y1, x0:x1]
    mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    for x, y in points:
        mask[y - y0, x - x0] = 255

    max_width, max_height = spec["max"]
    scale = min(max_width / mask.shape[1], max_height / mask.shape[0])
    target_width = max(1, round(mask.shape[1] * scale))
    target_height = max(1, round(mask.shape[0] * scale))
    mask_image = Image.fromarray(mask, "L").resize((target_width, target_height), Image.Resampling.BOX)
    target_mask = np.asarray(mask_image) >= 96
    sampled = np.asarray(
        Image.fromarray(crop, "RGB").resize((target_width, target_height), Image.Resampling.BOX),
        dtype=np.uint8,
    )
    luma = sampled[..., 0] * .2126 + sampled[..., 1] * .7152 + sampled[..., 2] * .0722
    active_luma = luma[target_mask]
    low, high = np.percentile(active_luma, (35, 70)) if len(active_luma) else (0, 255)
    colors = palette(spec["role"])
    rgba = np.zeros((target_height, target_width, 4), dtype=np.uint8)
    rgba[..., :3] = colors[0]
    rgba[..., :3][luma <= low] = colors[1]
    rgba[..., :3][luma >= high] = colors[2]
    rgba[..., 3] = target_mask.astype(np.uint8) * 255

    result = Image.new("RGBA", (LOGICAL, LOGICAL), (0, 0, 0, 0))
    px = (LOGICAL - target_width) // 2
    py = (LOGICAL - target_height) // 2
    result.alpha_composite(Image.fromarray(rgba, "RGBA"), (px, py))
    bbox = result.getchannel("A").getbbox()
    if not bbox:
        raise ValueError(f"{spec['name']}: motif disappeared during reduction")
    margin = min(bbox[0], bbox[1], LOGICAL - bbox[2], LOGICAL - bbox[3])
    if margin < 3:
        raise ValueError(f"{spec['name']}: internal margin {margin}px is below 3px")
    return result, {
        "sourceCell": list(spec["cell"]),
        "role": spec["role"],
        "sourceComponents": len(selected),
        "sourceForegroundPx": len(points),
        "compiledBoundsPx": list(bbox),
        "compiledExtentPx": [bbox[2] - bbox[0], bbox[3] - bbox[1]],
        "internalMarginPx": margin,
        "logicalCoverage": round(np.asarray(result.getchannel("A")).astype(bool).mean(), 4),
    }


def main() -> None:
    board = Image.open(SOURCE).convert("RGB")
    if board.width != board.height or board.width % GRID:
        raise ValueError(f"Expected square 4x4 Nano board, got {board.size}")
    cell_size = board.width // GRID
    atlas = Image.new("RGBA", (SLOT * GRID, SLOT * GRID), (0, 0, 0, 0))
    entries = []
    for index, spec in enumerate(SPECS):
        column, row = spec["cell"]
        cell = board.crop((column * cell_size, row * cell_size,
                           (column + 1) * cell_size, (row + 1) * cell_size))
        motif, metadata = compile_cell(cell, spec)
        slot_x, slot_y = (index % GRID) * SLOT, (index // GRID) * SLOT
        atlas.alpha_composite(motif, (slot_x + 4, slot_y + 4))
        entries.append({
            "name": spec["name"],
            "atlasRectPx": [slot_x + 4, slot_y + 4, LOGICAL, LOGICAL],
            "slotRectPx": [slot_x, slot_y, SLOT, SLOT],
            "atlasMarginPx": 4,
            **metadata,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(OUTPUT, optimize=False)
    atlas.resize((atlas.width * 6, atlas.height * 6), Image.Resampling.NEAREST).save(PREVIEW, optimize=False)
    quiet_share = round(1.0 - sum(item["logicalCoverage"] for item in entries) / len(entries), 4)
    payload = {
        "schemaVersion": 7,
        "generator": "gemini-3.1-flash-image + deterministic style-fit compiler",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "sourceSha256": sha256(SOURCE.read_bytes()).hexdigest(),
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "atlasSizePx": list(atlas.size),
        "policy": "caption-safe component extraction; locked ramps; 3px internal margin; 4px atlas gutter",
        "meanLogicalQuietShare": quiet_share,
        "decals": entries,
    }
    AUDIT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"PASS compiled {len(entries)} Nano style motifs; mean quiet share={quiet_share:.3f}")


if __name__ == "__main__":
    main()
