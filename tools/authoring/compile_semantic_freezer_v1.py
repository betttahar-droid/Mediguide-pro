"""Compile reviewed Nano regions into deterministic 32-texel runtime atlases."""
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v1"
FACE_SOURCE = LOCK / "semantic-freezer-faces-source.png"
FITTING_SOURCE = LOCK / "semantic-freezer-fittings-source.png"
FACE_ATLAS = ROOT / "public" / "textures" / "semantic-freezer-faces-v1.png"
FITTING_ATLAS = ROOT / "public" / "textures" / "semantic-freezer-fittings-v1.png"
MANIFEST = ROOT / "public" / "textures" / "semantic-freezer-v1.json"
TEXELS = 32
LEVELS = (32, 96, 128, 192, 240)

# Manually reviewed bounds. The image model supplied every requested role but
# ignored the grid; named selection is safer than accepting its composition.
FACE_CELLS = (
    ("roofTop", (36, 31, 495, 326), 4, (0, 0)),
    ("crownFront", (528, 34, 836, 157), 4, (1, 0)),
    ("cabinetSide", (529, 191, 836, 496), 4, (0, 0)),
    ("doorFrame", (869, 34, 989, 495), 4, (0, 0)),
    ("shelfTop", (36, 528, 495, 746), 3, (1, 1)),
    ("shelfLip", (529, 569, 989, 683), 3, (1, 0)),
    ("baseFront", (36, 789, 495, 992), 4, (0, 0)),
    ("ventField", (530, 726, 989, 992), 3, (1, 1)),
)
FITTING_CELLS = (
    ("medicalBadge", (20, 20, 297, 310)),
    ("digitalStatus", (318, 62, 694, 205)),
    ("statusStrip", (716, 81, 1006, 174)),
    ("sideRating", (716, 266, 1002, 497)),
    ("rearWarning", (20, 533, 299, 731)),
    ("cartonLabel", (318, 531, 501, 738)),
    ("vialLabel", (317, 814, 498, 989)),
    ("fanGrille", (537, 527, 990, 1000)),
)
REJECTED = (
    {"boundsPx": [20, 345, 298, 486], "reason": "duplicate rating/warning vocabulary"},
    {"boundsPx": [318, 340, 694, 493], "reason": "duplicate status strip"},
    {"boundsPx": [89, 794, 227, 988], "reason": "bottle illustration; geometry already supplies bottle"},
)


def magenta(rgb):
    p = rgb.astype(np.int16)
    return ((p[..., 0] > 180) & (p[..., 2] > 160) & (p[..., 1] < 135)
            & (np.abs(p[..., 0] - p[..., 2]) < 125))


def face_mask(image, bounds):
    small = np.asarray(image.crop(bounds).resize((TEXELS, TEXELS), Image.Resampling.BOX), np.uint8)
    bg = magenta(small)
    luma = small[..., 0] * .2126 + small[..., 1] * .7152 + small[..., 2] * .0722
    result = np.full((TEXELS, TEXELS), 128, np.uint8)
    result[luma < 63] = 32
    result[(luma >= 63) & (luma < 109)] = 96
    result[(luma >= 156) & (luma < 214)] = 192
    result[luma >= 214] = 240
    result[bg] = 128
    return result


def fitting(image, bounds):
    rgba = image.crop(bounds).convert("RGBA").resize((TEXELS, TEXELS), Image.Resampling.BOX)
    data = np.asarray(rgba, np.uint8).copy()
    background = magenta(data[..., :3])
    # Keep the authored semantic colors, but collapse them onto a controlled
    # pixel-art palette so interpolation cannot introduce hundreds of shades.
    palette = np.asarray([
        [26, 32, 35], [48, 57, 60], [78, 91, 94], [119, 130, 129],
        [174, 188, 184], [218, 224, 215], [49, 91, 125], [79, 128, 162],
        [158, 62, 61], [87, 143, 84], [213, 151, 62],
    ], np.int16)
    rgb = data[..., :3].astype(np.int16)
    delta = rgb[..., None, :] - palette[None, None, ...]
    nearest = np.argmin(np.sum(delta * delta, axis=-1), axis=-1)
    data[..., :3] = palette[nearest].astype(np.uint8)
    data[..., 3] = np.where(background, 0, 255).astype(np.uint8)
    return data


def enforce_measured_structure(name, mask):
    """Preserve authority-critical lines if image resampling erased them."""
    result = mask.copy()
    if name == "cabinetSide":
        # Three measured horizontal bands and staggered access-panel joins.
        result[6, 2:30] = 96
        result[17, 2:30] = 96
        result[6:18, 23] = 96
        result[17:30, 20] = 96
        result[1, 2:15] = 240
        result[2:5, 1] = 192
        result[28:31, 28:31] = 32
    elif name == "roofTop":
        # The authority roof has sparse wear concentrated at opposite corners.
        result[1, 2:18] = 240
        result[2:5, 1] = 192
        result[3:6, 27:30] = 96
        result[27:30, 3:7] = 96
    return result


def main():
    face_source = Image.open(FACE_SOURCE).convert("RGB")
    fitting_source = Image.open(FITTING_SOURCE).convert("RGB")
    face_atlas = Image.new("L", (TEXELS * len(FACE_CELLS), TEXELS), 128)
    fitting_atlas = Image.new("RGBA", (TEXELS * len(FITTING_CELLS), TEXELS), (0, 0, 0, 0))
    profiles = []
    fittings = []

    for index, (name, bounds, margin, repeat) in enumerate(FACE_CELLS):
        mask = enforce_measured_structure(name, face_mask(face_source, bounds))
        counts = {str(level): int(np.sum(mask == level)) for level in LEVELS}
        if sum(counts.values()) != TEXELS * TEXELS or counts["128"] == 0:
            raise ValueError(f"{name}: invalid mask {counts}")
        face_atlas.paste(Image.fromarray(mask, "L"), (index * TEXELS, 0))
        profiles.append({
            "name": name, "sourceBoundsPx": list(bounds),
            "atlasRectPx": [index * TEXELS, 0, TEXELS, TEXELS],
            "marginTexels": margin, "repeatMiddle": list(repeat),
            "toneCounts": counts,
        })

    for index, (name, bounds) in enumerate(FITTING_CELLS):
        cell = fitting(fitting_source, bounds)
        fitting_atlas.paste(Image.fromarray(cell, "RGBA"), (index * TEXELS, 0), Image.fromarray(cell[..., 3], "L"))
        fittings.append({
            "name": name, "sourceBoundsPx": list(bounds),
            "atlasRectPx": [index * TEXELS, 0, TEXELS, TEXELS],
            "opaqueTexels": int(np.sum(cell[..., 3] > 0)),
        })

    FACE_ATLAS.parent.mkdir(parents=True, exist_ok=True)
    face_atlas.convert("RGB").save(FACE_ATLAS, optimize=False)
    fitting_atlas.save(FITTING_ATLAS, optimize=False)
    face_atlas.resize((1536, 192), Image.Resampling.NEAREST).save(LOCK / "semantic-faces-compiled-preview.png")
    fitting_atlas.resize((1536, 192), Image.Resampling.NEAREST).save(LOCK / "semantic-fittings-compiled-preview.png")
    payload = {
        "schemaVersion": 1,
        "generator": "Nano Banana 2 / gemini-3.1-flash-image via concept_sheet.py",
        "sources": {
            "faces": str(FACE_SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "fittings": str(FITTING_SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "faceSha256": sha256(FACE_SOURCE.read_bytes()).hexdigest(),
            "fittingSha256": sha256(FITTING_SOURCE.read_bytes()).hexdigest(),
        },
        "profiles": profiles,
        "fittings": fittings,
        "rejectedSourceRegions": list(REJECTED),
        "checks": {
            "eightFaceRoles": len(profiles) == 8,
            "eightFittings": len(fittings) == 8,
            "allFacesIndexed": all(sum(item["toneCounts"].values()) == TEXELS * TEXELS for item in profiles),
            "generationLayoutAccepted": False,
            "reviewedSelectionCompiled": True,
        },
    }
    text = json.dumps(payload, indent=2) + "\n"
    MANIFEST.write_text(text, encoding="utf-8")
    (LOCK / "compile-audit.json").write_text(text, encoding="utf-8")
    print(f"PASS faces={FACE_ATLAS} fittings={FITTING_ATLAS}")


if __name__ == "__main__":
    main()
