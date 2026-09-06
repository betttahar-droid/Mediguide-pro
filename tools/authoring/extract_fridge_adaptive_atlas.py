"""Derive exact fixed decals and record the Nano/authority texture contract.

Identity pixels are lifted from the locked source. Clean material fields come
from the separately audited Nano board and are never allowed to replace a decal.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
AUTHORITY = json.loads((LOCK / "geometry-authority.json").read_text(encoding="utf-8"))
SOURCE = ROOT / "public" / "textures" / "vaccine-fridge-source-atlas.png"
ADAPTIVE = ROOT / "public" / "textures" / "vaccine-fridge-adaptive-source-atlas.png"
DISPLAY = ROOT / "public" / "textures" / "vaccine-fridge-display.png"
GRILLE = ROOT / "public" / "textures" / "vaccine-fridge-grille.png"
MANIFEST = LOCK / "adaptive-texture-manifest.json"
LEGACY_HYBRID = ROOT / "public" / "textures" / "vaccine-fridge-adaptive-gpt-v2.png"
NANO_TILES = {
    name: ROOT / "public" / "textures" / f"vaccine-fridge-nano-{name}-microtile-v5.png"
    for name in ("cream", "steel", "teal", "glass")
}
NANO_PANEL_TILE = ROOT / "public" / "textures" / "vaccine-fridge-nano-steel-panel-microtile-v5.png"
NANO_AUDIT = LOCK / "nano-banana-v5" / "nano-reference-material-primitives-v5.audit.json"


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing {SOURCE}; extract the source atlas first")

    atlas = Image.open(SOURCE).convert("RGBA")
    clean = atlas.copy()
    front_x, front_y = AUTHORITY["adaptive"]["sourceAtlasSegments"]["frontOriginPx"]
    dx, dy, width, height = AUTHORITY["adaptive"]["sourceAtlasSegments"]["fixedDisplayRectPx"]
    box = (front_x + dx, front_y + dy, front_x + dx + width, front_y + dy + height)
    display = atlas.crop(box)
    display.save(DISPLAY)
    grille_box = (front_x + 7, front_y + 80, front_x + 33, front_y + 91)
    atlas.crop(grille_box).save(GRILLE)

    # The fascia is horizontally continuous behind the display.  Copy the
    # nearest source column row-by-row so no generated/invented pixels enter
    # the repeatable layer.
    pixels = clean.load()
    sample_x = box[0] - 1
    for y in range(box[1], box[3]):
        replacement = pixels[sample_x, y]
        for x in range(box[0], box[2]):
            pixels[x, y] = replacement
    clean.save(ADAPTIVE)

    manifest = {
        "schemaVersion": 3,
        "authoritySha256": AUTHORITY["authoritySha256"],
        "sourceAtlas": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "adaptiveAtlas": str(ADAPTIVE.relative_to(ROOT)).replace("\\", "/"),
        "exportedMaterialMode": "embedded_nano_microtiles",
        "legacyAtlas": str(LEGACY_HYBRID.relative_to(ROOT)).replace("\\", "/"),
        "nanoAudit": str(NANO_AUDIT.relative_to(ROOT)).replace("\\", "/"),
        "generatedMaterialTiles": {
            name: str(path.relative_to(ROOT)).replace("\\", "/")
            for name, path in NANO_TILES.items()
        },
        "generatedPanelTile": str(NANO_PANEL_TILE.relative_to(ROOT)).replace("\\", "/"),
        "logicalTexelPolicy": {
            "ordinaryMaterials": {"tilePx": [16, 16], "worldPeriodPx": [16, 16]},
            "largePanels": {"tilePx": [32, 32], "worldPeriodPx": [32, 32]},
            "accentClusterMaxPx": 2,
            "sampling": "nearest_no_mipmaps",
        },
        "fixedDecals": {
            "display": {
                "path": str(DISPLAY.relative_to(ROOT)).replace("\\", "/"),
                "sourceRectPx": [dx, dy, width, height],
                "placementPx": AUTHORITY["frontFeaturesPx"]["display"],
                "policy": "FIXED_CENTER_1TO1",
            },
            "grille": {
                "path": str(GRILLE.relative_to(ROOT)).replace("\\", "/"),
                "sourceRectPx": [7, 80, 26, 11],
                "placementPx": AUTHORITY["frontFeaturesPx"]["grille"],
                "policy": "FIXED_PER_BAY_1TO1",
            }
        },
        "rules": {
            "doorBay": "repeat complete 32px source bay",
            "endCaps": "translate only; never scale",
            "fixedDetails": "separate image surface at one source pixel per model pixel",
            "crownAndTop": "fixed geometry borders plus Nano cream field at one texel per model pixel",
            "sideAndBack": "measured quiet steel field repeats every 32 model pixels; fixed seams and rectangular panel marks never scale",
            "generatedIdentityDetails": "reject and fall back to locked source crop",
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
