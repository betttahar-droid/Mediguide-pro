"""Validate and compile the guided Nano Banana 2 board into a runtime atlas."""
from collections import deque
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "nano-banana-v10"
SOURCE = LOCK / "adaptive-decals-v10-source.png"
OUTPUT = ROOT / "public" / "textures" / "vaccine-fridge-nano-adaptive-decals-v10.png"
PREVIEW = LOCK / "adaptive-decals-v10-compiled-preview.png"
AUDIT = LOCK / "adaptive-decals-v10.audit.json"
LOGICAL, SLOT, GRID = 16, 24, 4

PALETTES = {
    "steel": ((97, 122, 128), (118, 148, 156), (74, 93, 98)),
    "cream": ((217, 201, 168), (255, 244, 204), (168, 154, 129)),
    "teal": ((13, 64, 59), (16, 78, 72), (10, 49, 45)),
    "glass": ((11, 48, 45), (13, 58, 55), (8, 37, 34)),
    "ochre": ((195, 139, 77), (235, 177, 96), (133, 82, 42)),
    "plum": ((70, 55, 80), (106, 80, 116), (43, 31, 53)),
    "dark": ((20, 43, 42), (27, 57, 55), (10, 29, 28)),
}

SPECS = (
    ("steel_top_left", "steel", (8, 8)), ("steel_bottom_right", "steel", (8, 8)),
    ("steel_horizontal_seam", "steel", (10, 4)), ("steel_vertical_seam", "steel", (4, 10)),
    ("steel_fastener_pair", "steel", (9, 4)), ("cream_corner_catch", "cream", (8, 8)),
    ("cream_pressed_seam", "cream", (10, 4)), ("teal_recessed_patch", "teal", (9, 7)),
    ("teal_mechanical_seam", "teal", (10, 4)), ("glass_stair_glint", "glass", (6, 10)),
    ("shelf_end_cap", "steel", (8, 6)), ("grille_bracket", "ochre", (8, 8)),
    ("handle_end_cap", "plum", (8, 6)), ("caution_bars", "ochre", (9, 6)),
    ("control_status_glyph", "steel", (8, 5)), ("vent_notch", "dark", (8, 6)),
)


def magenta_mask(rgb):
    data = rgb.astype(np.int16)
    return ((data[..., 0] > 190) & (data[..., 2] > 170) & (data[..., 1] < 115)
            & (np.abs(data[..., 0] - data[..., 2]) < 105))


def connected(mask):
    seen = np.zeros(mask.shape, bool)
    groups = []
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            queue, group = deque(((x, y),)), []
            seen[y, x] = True
            while queue:
                px, py = queue.popleft(); group.append((px, py))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; queue.append((nx, ny))
            groups.append(group)
    return sorted(groups, key=len, reverse=True)


def compile_cell(cell, name, role, maximum):
    data = np.asarray(cell.convert("RGB"), dtype=np.uint8)
    groups = [group for group in connected(~magenta_mask(data)) if len(group) >= 20]
    if not groups:
        raise ValueError(f"{name}: no substantial connected motif")
    points = groups[0]
    xs, ys = zip(*points)
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    # Reject copied grid lines and captions before they can enter the atlas.
    if (x1 - x0) > cell.width * .97 or (y1 - y0) > cell.height * .97:
        raise ValueError(f"{name}: dominant component resembles guide contamination")
    source = data[y0:y1, x0:x1]
    source_mask = np.zeros((y1-y0, x1-x0), np.uint8)
    for x, y in points: source_mask[y-y0, x-x0] = 255
    scale = min(maximum[0] / source_mask.shape[1], maximum[1] / source_mask.shape[0])
    target = (max(1, round(source_mask.shape[1]*scale)), max(1, round(source_mask.shape[0]*scale)))
    mask = np.asarray(Image.fromarray(source_mask).resize(target, Image.Resampling.BOX)) >= 96
    sampled = np.asarray(Image.fromarray(source).resize(target, Image.Resampling.BOX), dtype=np.uint8)
    luma = sampled[..., 0]*.2126 + sampled[..., 1]*.7152 + sampled[..., 2]*.0722
    active = luma[mask]
    low, high = np.percentile(active, (34, 70))
    colors = np.asarray(PALETTES[role], np.uint8)
    rgba = np.zeros((target[1], target[0], 4), np.uint8)
    rgba[..., :3] = colors[0]
    rgba[..., :3][luma <= low] = colors[2]
    rgba[..., :3][luma >= high] = colors[1]
    rgba[..., 3] = mask * 255
    motif = Image.new("RGBA", (LOGICAL, LOGICAL))
    motif.alpha_composite(Image.fromarray(rgba), ((LOGICAL-target[0])//2, (LOGICAL-target[1])//2))
    bbox = motif.getchannel("A").getbbox()
    margin = min(bbox[0], bbox[1], LOGICAL-bbox[2], LOGICAL-bbox[3])
    if margin < 3: raise ValueError(f"{name}: compiled margin {margin}px below 3px")
    return motif, {"sourceComponents": len(groups), "sourceBounds": [x0,y0,x1,y1],
                   "compiledBounds": list(bbox), "internalMarginPx": margin,
                   "coverage": round(np.asarray(motif.getchannel('A')).astype(bool).mean(), 4)}


def main():
    board = Image.open(SOURCE).convert("RGB")
    if board.width != board.height: raise ValueError(f"Expected square board, got {board.size}")
    cell_size = board.width // GRID
    atlas = Image.new("RGBA", (SLOT*GRID, SLOT*GRID))
    entries = []
    for index, (name, role, maximum) in enumerate(SPECS):
        column, row = index % GRID, index // GRID
        cell = board.crop((column*cell_size, row*cell_size, (column+1)*cell_size, (row+1)*cell_size))
        motif, metrics = compile_cell(cell, name, role, maximum)
        atlas.alpha_composite(motif, (column*SLOT+4, row*SLOT+4))
        entries.append({"name": name, "role": role,
                        "atlasRectPx": [column*SLOT+4, row*SLOT+4, 16, 16], **metrics})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(OUTPUT, optimize=False)
    atlas.resize((576,576), Image.Resampling.NEAREST).save(PREVIEW, optimize=False)
    payload = {"schemaVersion": 10, "model": "gemini-3.1-flash-image (Nano Banana 2)",
               "sourceSha256": sha256(SOURCE.read_bytes()).hexdigest(),
               "output": OUTPUT.relative_to(ROOT).as_posix(), "atlasSizePx": [96,96],
               "checks": {"allCellsCompiled": len(entries)==16,
                          "allMarginsAtLeast3": all(item['internalMarginPx'] >= 3 for item in entries)},
               "decals": entries}
    AUDIT.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(f"PASS compiled {len(entries)} guided Nano Banana 2 decals -> {OUTPUT}")


if __name__ == "__main__": main()
