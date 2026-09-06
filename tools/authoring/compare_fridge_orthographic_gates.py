"""Write per-view silhouette overlays and one combined metrics report."""
from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
metrics = {}
for view in ("front", "side", "back"):
    reference = Image.open(FOLDER / f"{view}-mask-candidate.png").convert("L")
    candidate = Image.open(FOLDER / f"candidate-{view}.png").convert("RGBA").getchannel("A")
    overlay = Image.new("RGBA", reference.size, (0, 0, 0, 0))
    r, c, o = reference.load(), candidate.load(), overlay.load()
    intersection = union = reference_count = candidate_count = 0
    for y in range(reference.height):
        for x in range(reference.width):
            rv, cv = r[x, y] >= 128, c[x, y] >= 128
            reference_count += rv
            candidate_count += cv
            intersection += rv and cv
            union += rv or cv
            if rv and cv:
                o[x, y] = (255, 255, 255, 180)
            elif rv:
                o[x, y] = (255, 40, 40, 220)
            elif cv:
                o[x, y] = (40, 255, 80, 220)
    overlay.save(FOLDER / f"{view}-silhouette-overlay.png")
    metrics[view] = {
        "referencePixels": reference_count,
        "candidatePixels": candidate_count,
        "intersectionOverUnion": intersection / union if union else 0,
        "differentPixels": union - intersection,
    }
(FOLDER / "orthographic-gate-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))
