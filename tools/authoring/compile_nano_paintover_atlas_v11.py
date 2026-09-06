"""Compile the geometry-aware Nano paintover atlas through the locked decal gate."""
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
from PIL import Image

import compile_nano_adaptive_decals_v10 as compiler


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "paintover-v11"
SOURCE = LOCK / "paintover-atlas-v11-source.png"
OUTPUT = ROOT / "public" / "textures" / "vaccine-fridge-nano-paintover-atlas-v11.png"
PREVIEW = LOCK / "paintover-atlas-v11-compiled-preview.png"
AUDIT = LOCK / "paintover-atlas-v11.audit.json"

SPECS = (
    ("frame_top_left", "cream", (8, 8)), ("frame_bottom_right", "cream", (8, 8)),
    ("cream_pressed_seam", "cream", (10, 4)), ("crown_corner_cap", "cream", (8, 8)),
    ("side_access_seam", "steel", (10, 5)), ("side_fastener_pair", "steel", (9, 4)),
    ("base_access_seam", "teal", (10, 5)), ("base_corner_cap", "teal", (8, 8)),
    ("glass_wide_reflection", "glass", (10, 9)), ("glass_compact_glint", "glass", (6, 9)),
    ("shelf_lip", "steel", (10, 4)), ("shelf_end_cap", "plum", (7, 6)),
    ("control_bezel", "dark", (10, 5)), ("handle_highlight", "plum", (4, 10)),
    ("vent_grille", "ochre", (10, 9)), ("caution_plate", "ochre", (8, 6)),
)


def main():
    board = Image.open(SOURCE).convert("RGB")
    if board.width != board.height:
        raise ValueError(f"Expected square atlas board, got {board.size}")
    cell_size = board.width // 4
    atlas = Image.new("RGBA", (96, 96))
    entries = []
    for index, (name, role, maximum) in enumerate(SPECS):
        column, row = index % 4, index // 4
        cell = board.crop((column*cell_size, row*cell_size,
                           (column+1)*cell_size, (row+1)*cell_size))
        motif, metrics = compiler.compile_cell(cell, name, role, maximum)
        # Runtime atlases carry structure, never material colour. Encode the
        # three authored value bands as neutral indices so even dark glass and
        # teal motifs decode reliably into their destination material ramps.
        indexed = np.asarray(motif).copy()
        active = indexed[..., 3] > 0
        luma = indexed[..., 0] * .2126 + indexed[..., 1] * .7152 + indexed[..., 2] * .0722
        values = luma[active]
        low, high = np.percentile(values, (34, 70))
        indexed[..., :3][active] = 128
        indexed[..., :3][active & (luma <= low)] = 48
        indexed[..., :3][active & (luma >= high)] = 224
        motif = Image.fromarray(indexed, "RGBA")
        atlas.alpha_composite(motif, (column*24+4, row*24+4))
        entries.append({"name": name, "role": role,
                        "atlasRectPx": [column*24+4, row*24+4, 16, 16], **metrics})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(OUTPUT, optimize=False)
    atlas.resize((576, 576), Image.Resampling.NEAREST).save(PREVIEW, optimize=False)
    audit = {"schemaVersion": 11, "model": "gemini-3.1-flash-image (Nano Banana 2)",
             "method": "raw geometry -> semantic paintovers -> isolated atlas -> deterministic compiler",
             "sourceSha256": sha256(SOURCE.read_bytes()).hexdigest(),
             "output": OUTPUT.relative_to(ROOT).as_posix(), "atlasSizePx": [96, 96],
             "checks": {"allCellsCompiled": len(entries) == 16,
                        "allMarginsAtLeast3": all(entry['internalMarginPx'] >= 3 for entry in entries)},
             "decals": entries}
    AUDIT.write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    print(f"PASS compiled {len(entries)} paintover-derived decals -> {OUTPUT}")


if __name__ == '__main__':
    main()
