"""Measure the supplied retro 3D references without treating JPEG noise as style."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "style-research-v7"
REFERENCES = [
    Path(r"C:\Users\mansour\Downloads\inspo 1.jpg"),
    Path(r"C:\Users\mansour\Downloads\inspo 4.jpg"),
    Path(r"C:\Users\mansour\Downloads\big inspo 3.jpg"),
    Path(r"C:\Users\mansour\Downloads\inspo 3.gif"),
    Path(r"C:\Users\mansour\Downloads\inspo 2.jpg"),
]


def quantized_metrics(image: Image.Image) -> dict:
    rgb = image.convert("RGB")
    quantized = rgb.quantize(colors=24, method=Image.Quantize.MEDIANCUT).convert("RGB")
    counts = Counter(quantized.getdata())
    total = rgb.width * rgb.height
    palette = [
        {"hex": "#%02x%02x%02x" % color, "share": round(count / total, 4)}
        for color, count in counts.most_common(12)
    ]

    # Ignore one-pixel JPEG variation: measure exact runs after 24-color quantization.
    rows = list(quantized.getdata())
    horizontal_runs = []
    vertical_runs = []
    for y in range(rgb.height):
        start = y * rgb.width
        run = 1
        for x in range(1, rgb.width):
            if rows[start + x] == rows[start + x - 1]:
                run += 1
            else:
                if 2 <= run <= 64:
                    horizontal_runs.append(run)
                run = 1
    for x in range(rgb.width):
        run = 1
        for y in range(1, rgb.height):
            if rows[y * rgb.width + x] == rows[(y - 1) * rgb.width + x]:
                run += 1
            else:
                if 2 <= run <= 64:
                    vertical_runs.append(run)
                run = 1

    # Adjacent-color transitions approximate hard cluster boundaries.
    h_edges = sum(
        rows[y * rgb.width + x] != rows[y * rgb.width + x - 1]
        for y in range(rgb.height) for x in range(1, rgb.width)
    )
    v_edges = sum(
        rows[y * rgb.width + x] != rows[(y - 1) * rgb.width + x]
        for y in range(1, rgb.height) for x in range(rgb.width)
    )

    def percentile(values, ratio):
        if not values:
            return 0
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(len(ordered) * ratio))]

    return {
        "sizePx": [rgb.width, rgb.height],
        "quantizedPaletteSize": 24,
        "topPalette": palette,
        "runLengthPx": {
            "horizontalMedian": percentile(horizontal_runs, 0.5),
            "horizontalP75": percentile(horizontal_runs, 0.75),
            "verticalMedian": percentile(vertical_runs, 0.5),
            "verticalP75": percentile(vertical_runs, 0.75),
        },
        "hardTransitionDensity": {
            "horizontal": round(h_edges / max(1, rgb.height * (rgb.width - 1)), 4),
            "vertical": round(v_edges / max(1, (rgb.height - 1) * rgb.width), 4),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    gif_frames = []
    for path in REFERENCES:
        image = Image.open(path)
        frame_count = getattr(image, "n_frames", 1)
        sample_indices = sorted({0, frame_count // 2, max(0, frame_count - 1)})
        samples = []
        for index in sample_indices:
            image.seek(index)
            frame = image.convert("RGB")
            samples.append({"frame": index, **quantized_metrics(frame)})
            if path.suffix.lower() == ".gif":
                thumb = frame.copy()
                thumb.thumbnail((384, 384), Image.Resampling.NEAREST)
                gif_frames.append((index, thumb))
        records.append({
            "path": str(path),
            "frameCount": frame_count,
            "samples": samples,
        })

    if gif_frames:
        width = sum(frame.width for _, frame in gif_frames)
        height = max(frame.height for _, frame in gif_frames) + 28
        sheet = Image.new("RGB", (width, height), "#202229")
        draw = ImageDraw.Draw(sheet)
        x = 0
        for index, frame in gif_frames:
            sheet.paste(frame, (x, 28))
            draw.text((x + 8, 7), f"GIF frame {index}", fill="#f1f0df")
            x += frame.width
        sheet.save(OUT_DIR / "inspo-3-gif-samples.png")

    payload = {
        "schemaVersion": 7,
        "method": "24-color median-cut before run/edge measurement to suppress JPEG noise",
        "references": records,
    }
    (OUT_DIR / "reference-measurements.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
