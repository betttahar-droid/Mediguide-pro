"""Measure the pixel-material language of the user-supplied style references.

The output is deliberately deterministic.  It records palette/value ramps,
quantized run lengths (a proxy for authored pixel-block size), edge occupancy,
and a primary appliance crop.  Material compilers consume ratios from this
profile; they never resample a whole generated render onto the model.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "style-references"
ANALYSIS = REFS / "analysis"
PROFILE = REFS / "texture-style-profile-v1.json"

# Hand-verified semantic crops.  The fridge in inspo-2 is the closest material
# authority; the stove supplies the light enamel ramp.  Other images broaden
# the statistics without overriding those appliance-specific ramps.
CROPS = {
    "primary_fridge": ("inspo-2.jpg", (455, 34, 686, 523)),
    "light_enamel": ("inspo-2.jpg", (252, 137, 458, 433)),
    "industrial_props": ("inspo-4.jpg", (250, 70, 1080, 690)),
    "voxel_vehicles": ("big-inspo-3.jpg", (20, 20, 716, 394)),
    "appliance_set": ("inspo-1.jpg", (80, 45, 1120, 650)),
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * .2126 + rgb[..., 1] * .7152 + rgb[..., 2] * .0722


def quantized(image: Image.Image, colors: int = 16) -> Image.Image:
    return image.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT).convert("RGB")


def palette(image: Image.Image, colors: int = 12) -> list[dict]:
    q = quantized(image, colors)
    counts = Counter(map(tuple, np.asarray(q).reshape(-1, 3)))
    total = sum(counts.values())
    return [
        {"rgb": [int(channel) for channel in rgb], "luma": round(float(luma(np.array(rgb))), 3),
         "occupancy": round(count / total, 6)}
        for rgb, count in counts.most_common()
    ]


def run_lengths(image: Image.Image) -> dict:
    data = np.asarray(quantized(image, 12))
    lengths: list[int] = []
    for row in data:
        start = 0
        for index in range(1, len(row) + 1):
            if index == len(row) or not np.array_equal(row[index], row[start]):
                lengths.append(index - start)
                start = index
    for column in np.swapaxes(data, 0, 1):
        start = 0
        for index in range(1, len(column) + 1):
            if index == len(column) or not np.array_equal(column[index], column[start]):
                lengths.append(index - start)
                start = index
    small = [value for value in lengths if value <= 24]
    histogram = Counter(small)
    return {
        "modePx": histogram.most_common(1)[0][0],
        "medianPx": round(float(np.median(small)), 3),
        "p75Px": round(float(np.percentile(small, 75)), 3),
        "histogram1To12": {str(i): histogram[i] for i in range(1, 13)},
    }


def value_steps(image: Image.Image) -> dict:
    values = luma(np.asarray(quantized(image, 16), dtype=np.float32))
    # Reject near-black backdrop and specular extremes.
    values = values[(values > 28) & (values < 245)]
    q = np.percentile(values, [10, 25, 50, 75, 90])
    base = q[2]
    return {
        "lumaPercentiles": [round(float(value), 3) for value in q],
        "ratiosToMedian": [round(float(value / base), 4) for value in q],
    }


def detail_occupancy(image: Image.Image) -> float:
    data = np.asarray(quantized(image, 12), dtype=np.float32)
    values = luma(data)
    # A local 5x5 median-like approximation using neighbouring samples.  This
    # estimates deliberate marks while ignoring broad face shading.
    neighbours = np.stack([
        np.roll(values, shift, axis=axis)
        for axis in (0, 1) for shift in (-2, -1, 1, 2)
    ])
    local = np.median(neighbours, axis=0)
    mask = np.abs(values - local) >= 15
    return round(float(mask.mean()), 6)


def make_diagnostic(crops: dict[str, Image.Image]) -> None:
    width = 420
    panels = []
    for name, crop in crops.items():
        ratio = width / crop.width
        shown = quantized(crop, 16).resize((width, round(crop.height * ratio)), Image.Resampling.NEAREST)
        panel = Image.new("RGB", (width, shown.height + 28), (18, 19, 23))
        panel.paste(shown, (0, 28))
        ImageDraw.Draw(panel).text((8, 7), name, fill=(235, 235, 235))
        panels.append(panel)
    canvas = Image.new("RGB", (width * 2, max(sum(p.height for p in panels[::2]),
                                               sum(p.height for p in panels[1::2]))), (12, 13, 16))
    offsets = [0, 0]
    for index, panel in enumerate(panels):
        column = index % 2
        canvas.paste(panel, (column * width, offsets[column]))
        offsets[column] += panel.height
    canvas.save(ANALYSIS / "reference-material-crops-quantized.png", optimize=False)


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    opened: dict[str, Image.Image] = {}
    records = {}
    for role, (filename, box) in CROPS.items():
        source = REFS / filename
        crop = Image.open(source).convert("RGB").crop(box)
        opened[role] = crop
        records[role] = {
            "source": source.relative_to(ROOT).as_posix(),
            "sourceSha256": digest(source),
            "cropPx": list(box),
            "sizePx": list(crop.size),
            "palette": palette(crop),
            "valueSteps": value_steps(crop),
            "quantizedRunLengths": run_lengths(crop),
            "localDetailOccupancy": detail_occupancy(crop),
        }
    make_diagnostic(opened)
    primary = records["primary_fridge"]
    profile = {
        "schemaVersion": 1,
        "method": "semantic crops + deterministic median-cut quantization",
        "primaryAuthority": "primary_fridge",
        "materialRules": {
            "paletteSteps": primary["valueSteps"]["ratiosToMedian"],
            "preferredMarkWidthPx": primary["quantizedRunLengths"]["p75Px"],
            "targetLocalDetailOccupancy": primary["localDetailOccupancy"],
            "interpretation": "quiet centers; contrast concentrated in edge bands, seams, corners and sparse rectangular panel marks",
        },
        "crops": records,
        "diagnostic": (ANALYSIS / "reference-material-crops-quantized.png").relative_to(ROOT).as_posix(),
    }
    PROFILE.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    print(f"PASS wrote {PROFILE.relative_to(ROOT)} and quantized crop diagnostic")


if __name__ == "__main__":
    main()
