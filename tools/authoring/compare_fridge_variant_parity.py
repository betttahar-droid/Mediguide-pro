"""Fail when the generated one-door asset drifts from source truth."""
from pathlib import Path
import json

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "variants"
SOURCE = Image.open(FOLDER / "parity-source.png").convert("RGBA")
GENERATED = Image.open(FOLDER / "parity-generated-1door.png").convert("RGBA")
if SOURCE.size != GENERATED.size:
    raise SystemExit(f"Parity render sizes differ: {SOURCE.size} != {GENERATED.size}")

diff = ImageChops.difference(SOURCE, GENERATED)
histogram = diff.histogram()
channel_samples = SOURCE.width * SOURCE.height * 4
absolute_error = sum((index % 256) * count for index, count in enumerate(histogram))
different_pixels = sum(1 for rgba in diff.getdata() if rgba != (0, 0, 0, 0))
metrics = {
    "source": "vaccine-fridge-source-true.glb",
    "generated": "vaccine-fridge-voxel-1door.glb",
    "meanAbsoluteChannelError": absolute_error / channel_samples,
    "differentPixels": different_pixels,
    "totalPixels": SOURCE.width * SOURCE.height,
}
(FOLDER / "one-door-parity-metrics.json").write_text(
    json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
diff.save(FOLDER / "one-door-parity-diff.png")
print(json.dumps(metrics, indent=2))
if metrics["meanAbsoluteChannelError"] > 0.01 or different_pixels > 16:
    raise SystemExit("Generated one-door fridge drifted from the accepted source-true asset")
