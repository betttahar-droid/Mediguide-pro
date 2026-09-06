"""Compile Nano Banana style art into exact, repeatable model-pixel textures.

Nano Banana owns palette, contrast, and motif placement. This compiler owns
cell coordinates, logical texel size, seam safety, sparsity, and output names.
Generated bitmaps can therefore influence appearance without becoming geometry
or changing an identity-bearing decal.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
NANO = LOCK / "nano-banana-v3"
SOURCE_BASENAME = "nano-microtexture-kit-v3"
OUTPUT_VERSION = "v3"
SOURCE_CANDIDATES = (
    NANO / f"{SOURCE_BASENAME}.png",
    NANO / f"{SOURCE_BASENAME}.jpg",
    NANO / f"{SOURCE_BASENAME}.webp",
)
OUTPUT = ROOT / "public" / "textures"
AUDIT = NANO / f"{SOURCE_BASENAME}.audit.json"

LOGICAL_SIZE = 16
MATERIALS = {
    "cream": {"column": 0, "dark": 3, "bright": 1},
    "steel": {"column": 1, "dark": 3, "bright": 1},
    "teal": {"column": 2, "dark": 3, "bright": 1},
    "glass": {"column": 3, "dark": 1, "bright": 1},
}
FACE_FACTORS = {
    "cream": {"top": 1.06, "side": 0.90},
    "steel": {"top": 1.08, "side": 0.84},
    "teal": {"top": 1.06, "side": 0.84},
    "glass": {"top": 1.04, "side": 0.88},
}
# Optional deterministic overrides used by later compiler profiles.  They keep
# the source image responsible for motif ranking while allowing measured style
# references (rather than a generated JPEG) to own the final color ramp.
PALETTE_OVERRIDES: dict[str, list[list[int]]] = {}
ACCENT_PATTERNS: dict[str, dict[str, list[tuple[int, int]]]] = {}
CLEAN_FACE_VARIANTS: dict[str, set[str]] = {}


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_path() -> Path:
    for candidate in SOURCE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing generated Nano source kit: {SOURCE_BASENAME}")


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def representative_color(pixels: np.ndarray, mask: np.ndarray) -> np.ndarray:
    selected = pixels[mask]
    if not len(selected):
        return np.median(pixels.reshape(-1, 3), axis=0)
    return np.median(selected, axis=0)


def select_sparse(scores: np.ndarray, count: int, used: set[tuple[int, int]]) -> list[tuple[int, int]]:
    candidates = [
        (float(scores[y, x]), x, y)
        for y in range(1, LOGICAL_SIZE - 1)
        for x in range(1, LOGICAL_SIZE - 1)
    ]
    candidates.sort(reverse=True)
    picked: list[tuple[int, int]] = []
    for _, x, y in candidates:
        if (x, y) in used:
            continue
        # Clusters in the style references are normally isolated or two pixels
        # long. Avoid procedural-looking blobs after the tile repeats.
        neighbours = sum(
            (x + dx, y + dy) in used
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
        )
        if neighbours > 0 and len(picked) != count - 1:
            continue
        picked.append((x, y))
        used.add((x, y))
        if len(picked) == count:
            break
    return picked


def logical_scores(cell: np.ndarray, base_luma: float) -> tuple[np.ndarray, np.ndarray]:
    height, width = cell.shape[:2]
    dark = np.zeros((LOGICAL_SIZE, LOGICAL_SIZE), dtype=np.float32)
    bright = np.zeros_like(dark)
    for y in range(LOGICAL_SIZE):
        y0 = round(y * height / LOGICAL_SIZE)
        y1 = round((y + 1) * height / LOGICAL_SIZE)
        for x in range(LOGICAL_SIZE):
            x0 = round(x * width / LOGICAL_SIZE)
            x1 = round((x + 1) * width / LOGICAL_SIZE)
            values = luminance(cell[y0:y1, x0:x1])
            dark[y, x] = base_luma - np.percentile(values, 8)
            bright[y, x] = np.percentile(values, 92) - base_luma
    return dark, bright


def make_microtile(cell: np.ndarray, dark_count: int, bright_count: int,
                   role: str | None = None) -> tuple[Image.Image, dict]:
    # Ignore a narrow border where neighbouring generated cells can bleed.
    inset = max(2, cell.shape[0] // 64)
    clean = cell[inset:-inset, inset:-inset]
    values = luminance(clean)
    median_luma = float(np.median(values))
    base = representative_color(clean, np.abs(values - median_luma) < 2.5)
    dark = representative_color(clean, values <= np.percentile(values, 5))
    bright = representative_color(clean, values >= np.percentile(values, 95))

    # Keep Nano's hue but prevent a single JPEG shadow/highlight from creating
    # an out-of-family speck.
    dark = base * 0.35 + dark * 0.65
    bright = base * 0.35 + bright * 0.65
    palette = np.clip(np.rint([base, dark, bright]), 0, 255).astype(np.uint8)
    if role in PALETTE_OVERRIDES:
        palette = np.asarray(PALETTE_OVERRIDES[role], dtype=np.uint8)

    dark_scores, bright_scores = logical_scores(clean, float(luminance(base)))
    result = np.tile(palette[0], (LOGICAL_SIZE, LOGICAL_SIZE, 1))
    used: set[tuple[int, int]] = set()
    pattern = ACCENT_PATTERNS.get(role or "")
    if pattern:
        dark_cells = [tuple(cell) for cell in pattern.get("dark", [])]
        bright_cells = [tuple(cell) for cell in pattern.get("bright", [])]
    else:
        dark_cells = select_sparse(dark_scores, dark_count, used)
        bright_cells = select_sparse(bright_scores, bright_count, used)
    for x, y in dark_cells:
        result[y, x] = palette[1]
    for x, y in bright_cells:
        result[y, x] = palette[2]

    # A one-pixel base-color perimeter is a deterministic periodic seam. The
    # motif remains entirely within the six-by-six safe center.
    result[0, :] = result[-1, :] = palette[0]
    result[:, 0] = result[:, -1] = palette[0]
    image = Image.fromarray(result, "RGB").convert("RGBA")
    return image, {
        "paletteRgb": palette.tolist(),
        "darkCells": dark_cells,
        "brightCells": bright_cells,
    }


def make_panel_tile(steel_tile: Image.Image) -> Image.Image:
    base = np.array(steel_tile.convert("RGBA"), dtype=np.uint8)
    panel = np.tile(base[0, 0], (32, 32, 1))
    unique = [color for color in np.unique(base.reshape(-1, 4), axis=0)
              if not np.array_equal(color, base[0, 0])]
    dark = min(unique, key=lambda color: float(luminance(color[:3])))
    bright = max(unique, key=lambda color: float(luminance(color[:3])))
    # Reuse two Nano-selected steel values at lower density. Their literal
    # one-model-pixel size is retained; only their repetition interval changes.
    accents = [(9, 11, dark), (23, 21, bright)]
    for x, y, color in accents:
        mixed = panel[y, x].astype(np.float32) * 0.35 + color.astype(np.float32) * 0.65
        panel[y, x] = np.rint(mixed).astype(np.uint8)
    return Image.fromarray(panel, "RGBA")


def value_variant(tile: Image.Image, factor: float) -> Image.Image:
    data = np.array(tile.convert("RGBA"), dtype=np.float32)
    data[..., :3] = np.clip(np.rint(data[..., :3] * factor), 0, 255)
    return Image.fromarray(data.astype(np.uint8), "RGBA")


def largest_nonbase_component(tile: Image.Image) -> int:
    data = np.array(tile.convert("RGBA"))
    base = data[0, 0, :3]
    mask = np.any(data[..., :3] != base, axis=2)
    visited = np.zeros(mask.shape, dtype=bool)
    largest = 0
    for y in range(mask.shape[0]):
        for x in range(mask.shape[1]):
            if not mask[y, x] or visited[y, x]:
                continue
            queue = deque([(x, y)])
            visited[y, x] = True
            size = 0
            while queue:
                px, py = queue.popleft()
                size += 1
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0] and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((nx, ny))
            largest = max(largest, size)
    return largest


def assert_periodic(tile: Image.Image, name: str) -> None:
    data = np.array(tile.convert("RGBA"))
    if not np.array_equal(data[:, 0], data[:, -1]):
        raise ValueError(f"{name}: left/right seam mismatch")
    if not np.array_equal(data[0, :], data[-1, :]):
        raise ValueError(f"{name}: top/bottom seam mismatch")


def main() -> None:
    source = source_path()
    board = Image.open(source).convert("RGB")
    if board.width != board.height or board.width % 4:
        raise ValueError(f"Nano kit must be square and divisible by four; got {board.size}")
    cell_size = board.width // 4
    OUTPUT.mkdir(parents=True, exist_ok=True)

    audit_entries = []
    material_images: dict[str, Image.Image] = {}
    for name, spec in MATERIALS.items():
        left = spec["column"] * cell_size
        cell = np.array(board.crop((left, 0, left + cell_size, cell_size)), dtype=np.float32)
        tile, metadata = make_microtile(cell, spec["dark"], spec["bright"], name)
        assert_periodic(tile, name)
        largest = largest_nonbase_component(tile)
        if largest > 2:
            raise ValueError(f"{name}: generated cluster grew to {largest} logical pixels")
        output = OUTPUT / f"vaccine-fridge-nano-{name}-microtile-{OUTPUT_VERSION}.png"
        tile.save(output, optimize=False)
        face_outputs = {}
        for face, factor in FACE_FACTORS[name].items():
            if face in CLEAN_FACE_VARIANTS.get(name, set()):
                base = np.array(tile.convert("RGBA"), dtype=np.uint8)[0, 0]
                clean = np.tile(base, (LOGICAL_SIZE, LOGICAL_SIZE, 1))
                variant = value_variant(Image.fromarray(clean, "RGBA"), factor)
            else:
                variant = value_variant(tile, factor)
            face_output = OUTPUT / f"vaccine-fridge-nano-{name}-{face}-microtile-{OUTPUT_VERSION}.png"
            variant.save(face_output, optimize=False)
            face_outputs[face] = face_output.relative_to(ROOT).as_posix()
        material_images[name] = tile
        audit_entries.append({
            "role": name,
            "sourceCell": [spec["column"], 0],
            "output": output.relative_to(ROOT).as_posix(),
            "logicalSizePx": [LOGICAL_SIZE, LOGICAL_SIZE],
            "worldPeriodPx": [LOGICAL_SIZE, LOGICAL_SIZE],
            "periodicEdges": True,
            "largestAccentClusterPx": largest,
            "faceVariants": face_outputs,
            "faceValueFactors": FACE_FACTORS[name],
            **metadata,
        })

    panel_tile = make_panel_tile(material_images["steel"])
    assert_periodic(panel_tile, "steel-panel")
    panel_output = OUTPUT / f"vaccine-fridge-nano-steel-panel-microtile-{OUTPUT_VERSION}.png"
    panel_tile.save(panel_output, optimize=False)

    style_files = sorted(path for path in (LOCK / "style-references").glob("*") if path.is_file())
    audit = {
        "schemaVersion": 3,
        "generator": "gemini-3.1-flash-image (Nano Banana 2)",
        "sourceBoard": source.relative_to(ROOT).as_posix(),
        "sourceSha256": file_sha(source),
        "sourceSizePx": list(board.size),
        "cellLayout": [4, 4],
        "compilerPolicy": "nano palette and motif scores; deterministic 16px logical grid; one-model-pixel accents; base-color periodic perimeter",
        "materials": audit_entries,
        "panelTile": {
            "output": panel_output.relative_to(ROOT).as_posix(),
            "logicalSizePx": [32, 32],
            "worldPeriodPx": [32, 32],
            "periodicEdges": True,
            "accentCount": 2,
        },
        "identityDecals": {
            "policy": "locked authority only",
            "display": "public/textures/vaccine-fridge-display.png",
            "grille": "public/textures/vaccine-fridge-grille.png",
        },
        "styleReferences": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": file_sha(path)}
            for path in style_files
        ],
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(
        f"PASS Nano microtexture compiler: {len(material_images)} 16x16 tiles, "
        "one sparse 32x32 panel tile, periodic seams and <=2px clusters"
    )


if __name__ == "__main__":
    main()
