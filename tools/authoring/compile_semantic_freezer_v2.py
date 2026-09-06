"""Compile aligned paintovers into world-scale microfields and exact-size fittings."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v2"
PAINT = LOCK / "paintovers"
PUBLIC = ROOT / "public" / "textures"
MICRO_ATLAS = PUBLIC / "semantic-freezer-microfields-v2.png"
FITTING_ATLAS = PUBLIC / "semantic-freezer-fittings-v2.png"
MANIFEST = PUBLIC / "semantic-freezer-v2.json"
MICRO = 64

SOURCES = {
    "iso": PAINT / "iso-paintover-gpt.png",
    "side": PAINT / "side-paintover-gpt.png",
    "back": PAINT / "back-paintover-gpt.png",
}

# Quiet, face-aligned samples. These repeat in world units; fixed seams and wear
# remain separate semantic programs and therefore never smear when resized.
MICROFIELDS = (
    # Edge-authority crops deliberately include sparse chips and small value
    # clusters.  The shader applies them weakly in face interiors and strongly
    # only inside fixed-world rim/bottom bands.
    ("enamel", "iso", (395, 230, 445, 280), 8),
    ("sideMetal", "side", (610, 180, 750, 330), 14),
    ("darkCavity", "iso", (305, 330, 585, 410), 10),
    ("shelfMetal", "iso", (300, 500, 620, 548), 12),
    ("medicinePaper", "iso", (370, 430, 405, 505), 10),
    ("medicineTan", "iso", (550, 430, 610, 520), 10),
    ("bottleAmber", "iso", (315, 590, 350, 675), 10),
    ("coilMetal", "back", (565, 360, 830, 430), 12),
)

# Crops are converted to approximately their final on-screen source resolution,
# avoiding nearest-neighbour minification from a universal 32x32 fitting cell.
FITTINGS = (
    ("medicalIdentity", "iso", (244, 170, 390, 286), (32, 24), (0, 0)),
    ("digitalStatus", "iso", (514, 188, 642, 302), (36, 16), (40, 0)),
    ("sideRating", "side", (395, 314, 510, 384), (18, 12), (84, 0)),
    ("rearWarning", "back", (578, 520, 836, 610), (36, 14), (110, 0)),
    ("rearDoNot", "back", (582, 846, 829, 915), (32, 10), (154, 0)),
    ("fanGrille", "back", (365, 990, 535, 1195), (28, 28), (192, 0)),
    ("cartonCovid", "iso", (311, 418, 392, 532), (16, 20), (0, 32)),
    ("cartonMmr", "iso", (400, 418, 476, 532), (16, 20), (20, 32)),
    ("cartonFlu", "iso", (478, 418, 555, 532), (16, 20), (40, 32)),
    ("cartonBooster", "iso", (478, 638, 575, 735), (16, 20), (60, 32)),
    ("vialCovid", "iso", (313, 610, 357, 686), (10, 14), (84, 32)),
    ("vialMmr", "iso", (365, 610, 409, 686), (10, 14), (98, 32)),
    ("vialFlu", "iso", (415, 610, 460, 686), (10, 14), (112, 32)),
    ("vialPolio", "iso", (313, 792, 360, 885), (10, 14), (126, 32)),
)

# These are not surface textures.  Only locally contrasting chip pixels survive
# compilation; the resulting transparent patches are mounted at named corners
# at fixed texel sizes.
WEAR_FITTINGS = (
    ("sideBottomWear", "side", (340, 1090, 500, 1240), (28, 18), (150, 32)),
    ("sideTopWear", "side", (650, 180, 760, 295), (28, 18), (182, 32)),
    ("frontBaseWear", "iso", (250, 1170, 580, 1240), (32, 12), (214, 32)),
)


def quantized(image, colors, size):
    small = image.resize(size, Image.Resampling.BOX)
    return small.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGBA")


def masked_wear(image, bounds, size):
    source = image.crop(bounds).resize(size, Image.Resampling.BOX).convert("RGB")
    quant = source.quantize(
        colors=10, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE,
    ).convert("RGBA")
    blurred = source.filter(ImageFilter.GaussianBlur(radius=1.15))
    output = Image.new("RGBA", size, (0, 0, 0, 0))
    for y in range(size[1]):
        for x in range(size[0]):
            here = source.getpixel((x, y))
            local = blurred.getpixel((x, y))
            if (here[0] > 120 and here[2] > 110
                    and here[0] > here[1] * 1.25
                    and here[2] > here[1] * 1.20):
                continue
            here_luma = sum(here) / 3
            local_luma = sum(local) / 3
            # Dark authored chips and seams survive; low-contrast base paint is
            # transparent so a patch never reads as a rectangular sticker.
            if local_luma - here_luma >= 7.0:
                output.putpixel((x, y), quant.getpixel((x, y)))
    return output


def main():
    images = {name: Image.open(path).convert("RGB") for name, path in SOURCES.items()}
    PUBLIC.mkdir(parents=True, exist_ok=True)
    micro = Image.new("RGBA", (MICRO * len(MICROFIELDS), MICRO), (0, 0, 0, 0))
    fitting = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    micro_records = []
    fitting_records = []

    for index, (name, source, bounds, colors) in enumerate(MICROFIELDS):
        cell = quantized(images[source].crop(bounds), colors, (MICRO, MICRO))
        micro.paste(cell, (index * MICRO, 0))
        counts = Counter(cell.convert("RGB").getdata())
        micro_records.append({
            "name": name, "source": source, "sourceBoundsPx": list(bounds),
            "atlasRectPx": [index * MICRO, 0, MICRO, MICRO],
            "paletteSize": len(counts),
            "largestColorShare": round(counts.most_common(1)[0][1] / (MICRO * MICRO), 4),
        })

    for name, source, bounds, size, origin in FITTINGS:
        sprite = quantized(images[source].crop(bounds), 16, size)
        fitting.paste(sprite, origin)
        fitting_records.append({
            "name": name, "source": source, "sourceBoundsPx": list(bounds),
            "atlasRectPx": [origin[0], origin[1], size[0], size[1]],
            "logicalSourceSizePx": list(size),
        })

    for name, source, bounds, size, origin in WEAR_FITTINGS:
        sprite = masked_wear(images[source], bounds, size)
        fitting.paste(sprite, origin, sprite)
        opaque = sum(pixel[3] > 0 for pixel in sprite.getdata())
        fitting_records.append({
            "name": name, "source": source, "sourceBoundsPx": list(bounds),
            "atlasRectPx": [origin[0], origin[1], size[0], size[1]],
            "logicalSourceSizePx": list(size),
            "semantic": "transparent fixed-size corner wear",
            "opaqueShare": round(opaque / (size[0] * size[1]), 4),
        })

    micro.save(MICRO_ATLAS, optimize=False)
    fitting.save(FITTING_ATLAS, optimize=False)
    micro.resize((1536, 192), Image.Resampling.NEAREST).save(LOCK / "microfields-preview-v2.png")
    fitting.resize((1024, 256), Image.Resampling.NEAREST).save(LOCK / "fittings-preview-v2.png")
    payload = {
        "schemaVersion": 2,
        "authoring": "geometry-locked paintovers; built-in GPT image editor after Nano 429",
        "sources": {
            name: {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(path.read_bytes()).hexdigest(),
            } for name, path in SOURCES.items()
        },
        "microAtlasSizePx": list(micro.size),
        "fittingAtlasSizePx": list(fitting.size),
        "microfields": micro_records,
        "fittings": fitting_records,
        "rules": {
            "microfields": "repeat in fixed world texels with alternating mirror phase",
            "edges": "fixed semantic role margins",
            "panelSeams": "proportional band anchors",
            "fittings": "fixed world size on named front/side/back planes",
        },
    }
    text = json.dumps(payload, indent=2) + "\n"
    MANIFEST.write_text(text, encoding="utf-8")
    (LOCK / "compile-audit-v2.json").write_text(text, encoding="utf-8")
    print(f"PASS micro={MICRO_ATLAS} fitting={FITTING_ATLAS}")


if __name__ == "__main__":
    main()
