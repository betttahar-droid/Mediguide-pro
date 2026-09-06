"""Deterministically compile reviewed Nano face-role cells into a five-level atlas."""
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "semantic-v13"
SOURCE = LOCK / "semantic-faces-v13-source.png"
ATLAS = ROOT / "public" / "textures" / "vaccine-fridge-semantic-faces-v13.png"
MANIFEST = ROOT / "public" / "textures" / "vaccine-fridge-semantic-faces-v13.json"
PREVIEW = LOCK / "semantic-faces-v13-compiled-preview.png"
AUDIT = LOCK / "semantic-faces-v13.audit.json"
TEXELS = 32
LEVELS = (32, 96, 128, 192, 240)

# Reviewed cells from the generated 3x3 output. Nano ignored the requested 4x2
# layout. The extra quiet bottom-middle cell and two detached decorative bars
# are explicitly rejected instead of silently entering the runtime atlas.
CELLS = (
    ("roofTop", (41, 40, 328, 318), 4, (0, 0)),
    ("crownFront", (369, 41, 665, 318), 4, (1, 0)),
    ("cabinetSide", (706, 40, 984, 318), 4, (0, 0)),
    ("doorFrame", (41, 368, 328, 676), 4, (0, 0)),
    ("shelfTop", (379, 369, 655, 676), 3, (1, 1)),
    ("shelfLip", (696, 358, 983, 676), 3, (1, 0)),
    ("baseFront", (41, 778, 328, 983), 4, (0, 0)),
    ("ventField", (696, 778, 984, 983), 3, (1, 1)),
)
REJECTED = (
    {"boundsPx": [379, 727, 655, 983], "reason": "unrequested extra quiet cell"},
    {"boundsPx": [41, 727, 328, 768], "reason": "detached decorative bar outside baseFront"},
    {"boundsPx": [696, 717, 983, 768], "reason": "detached decorative bar outside ventField"},
)


def magenta(rgb):
    p = rgb.astype(np.int16)
    return ((p[..., 0] > 180) & (p[..., 2] > 160) & (p[..., 1] < 135)
            & (np.abs(p[..., 0] - p[..., 2]) < 125))


def quantize(cell):
    small = np.asarray(cell.resize((TEXELS, TEXELS), Image.Resampling.BOX), np.uint8)
    bg = magenta(small)
    luma = small[..., 0] * .2126 + small[..., 1] * .7152 + small[..., 2] * .0722
    result = np.full((TEXELS, TEXELS), 128, np.uint8)
    result[luma < 63] = 32
    result[(luma >= 63) & (luma < 109)] = 96
    result[(luma >= 156) & (luma < 214)] = 192
    result[luma >= 214] = 240
    result[bg] = 128
    return result


def main():
    source = Image.open(SOURCE).convert("RGB")
    atlas = Image.new("L", (TEXELS * len(CELLS), TEXELS), 128)
    profiles = []
    for index, (name, bounds, margin, repeat) in enumerate(CELLS):
        mask = quantize(source.crop(bounds))
        counts = {str(level): int(np.sum(mask == level)) for level in LEVELS}
        quiet = counts["128"] / mask.size
        if counts["128"] == 0 or sum(counts.values()) != mask.size:
            raise ValueError(f"{name}: invalid indexed mask counts {counts}")
        atlas.paste(Image.fromarray(mask, "L"), (index * TEXELS, 0))
        profiles.append({
            "name": name,
            "sourceBoundsPx": list(bounds),
            "atlasRectPx": [index * TEXELS, 0, TEXELS, TEXELS],
            "marginTexels": margin,
            "repeatMiddle": list(repeat),
            "toneCounts": counts,
            "quietShare": round(quiet, 4),
        })
        print(f"{index + 1} {name:12s} quiet={quiet:.3f} tones={counts} repeat={repeat}")

    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    atlas.convert("RGB").save(ATLAS, optimize=False)
    atlas.resize((1536, 192), Image.Resampling.NEAREST).save(PREVIEW, optimize=False)
    payload = {
        "schemaVersion": 13,
        "generator": "Nano Banana 2 / gemini-3.1-flash-image via concept_sheet.py",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "sourceSha256": sha256(SOURCE.read_bytes()).hexdigest(),
        "atlas": ATLAS.relative_to(ROOT).as_posix(),
        "atlasSizePx": [TEXELS * len(CELLS), TEXELS],
        "logicalTileSizePx": [TEXELS, TEXELS],
        "toneLevels": list(LEVELS),
        "profiles": profiles,
        "rejectedSourceRegions": list(REJECTED),
        "checks": {
            "requestedProfileCount": len(profiles) == 8,
            "allIndexed": all(sum(item["toneCounts"].values()) == TEXELS * TEXELS for item in profiles),
            "allHaveBase": all(item["toneCounts"]["128"] > 0 for item in profiles),
            "generationLayoutAccepted": False,
            "reviewedSelectionCompiled": True,
        },
    }
    text = json.dumps(payload, indent=2) + "\n"
    MANIFEST.write_text(text, encoding="utf-8")
    AUDIT.write_text(text, encoding="utf-8")
    print(f"PASS reviewed semantic atlas -> {ATLAS}")


if __name__ == "__main__":
    main()
