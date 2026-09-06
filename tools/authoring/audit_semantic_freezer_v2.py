"""Compare material/detail statistics against the three authority views.

The audit intentionally ignores silhouettes: geometry has its own diagnostic
gate.  Here each object crop is normalized, quantized to 32 colours, and then
measured for pixel-edge density and palette concentration.  This catches the
two recurring failures in this pipeline: flat untextured slabs and full-face
wallpaper noise.
"""
from collections import Counter
from pathlib import Path
import json

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT.parent / "Gemini version builder" / "img_gen"
OUT = ROOT / "docs" / "reference-lock" / "semantic-freezer-v2" / "spatial-audit-v2.json"

PAIRS = {
    "front_iso": (
        AUTHORITY / "ref_front_view.png",
        ROOT / "docs/reference-lock/semantic-freezer-v2/runtime/view-iso-texture-v2.png",
        (273, 60, 804, 941),
    ),
    "right_side": (
        AUTHORITY / "ref_right_side_view.png",
        ROOT / "docs/reference-lock/semantic-freezer-v2/runtime/view-side-texture-v2.png",
        (326, 115, 689, 935),
    ),
    "back_iso": (
        AUTHORITY / "ref_back_view.png",
        ROOT / "docs/reference-lock/semantic-freezer-v2/runtime/view-backIso-texture-v2.png",
        (205, 60, 873, 948),
    ),
}


def render_bbox(image):
    rgb = image.convert("RGB")
    bg = (16, 17, 22)
    xs, ys = [], []
    for y in range(rgb.height):
        for x in range(rgb.width):
            pixel = rgb.getpixel((x, y))
            if max(abs(pixel[i] - bg[i]) for i in range(3)) > 12:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise ValueError("render contains no non-background pixels")
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def metrics(path, bounds=None):
    image = Image.open(path).convert("RGB")
    crop = image.crop(bounds or render_bbox(image))
    normalized = crop.resize((256, 384), Image.Resampling.BOX)
    indexed = normalized.quantize(
        colors=32, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE,
    ).convert("RGB")
    pixels = list(indexed.getdata())
    counts = Counter(pixels)
    comparisons = strong = hard = 0
    for y in range(indexed.height):
        for x in range(indexed.width):
            here = indexed.getpixel((x, y))
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if nx >= indexed.width or ny >= indexed.height:
                    continue
                there = indexed.getpixel((nx, ny))
                distance = sum((here[i] - there[i]) ** 2 for i in range(3)) ** .5
                comparisons += 1
                hard += distance >= 28
                strong += distance >= 72
    total = len(pixels)
    return {
        "bboxPx": list(bounds or render_bbox(image)),
        "hardEdgeDensity": round(hard / comparisons, 4),
        "strongEdgeDensity": round(strong / comparisons, 4),
        "top5ColorShare": round(sum(n for _, n in counts.most_common(5)) / total, 4),
        "largestColorShare": round(counts.most_common(1)[0][1] / total, 4),
    }


def main():
    records = {}
    passes = []
    for name, (authority_path, render_path, authority_bounds) in PAIRS.items():
        authority = metrics(authority_path, authority_bounds)
        render = metrics(render_path)
        edge_ratio = render["hardEdgeDensity"] / max(authority["hardEdgeDensity"], .0001)
        concentration_delta = render["top5ColorShare"] - authority["top5ColorShare"]
        record_pass = .30 <= edge_ratio <= 1.70 and concentration_delta <= .45
        passes.append(record_pass)
        records[name] = {
            "authority": authority,
            "renderV2": render,
            "hardEdgeRatio": round(edge_ratio, 3),
            "top5ShareDelta": round(concentration_delta, 3),
            "status": "PASS" if record_pass else "FAIL",
        }
    payload = {
        "status": "PASS" if all(passes) else "FAIL",
        "method": "tight object crops normalized to 256x384 and median-cut to 32 colors",
        "records": records,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not all(passes):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
