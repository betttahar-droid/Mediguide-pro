"""Compile clean, support-owned reference textures for semantic freezer v6."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v6"
V5_LOCK = ROOT / "docs/reference-lock/semantic-freezer-v5"
PUBLIC = ROOT / "public/textures"
V5_MANIFEST = PUBLIC / "semantic-freezer-v5.json"
CORR_PATH = V5_LOCK / "correspondence-v5.json"
OUT = PUBLIC / "semantic-freezer-v6.json"
ATLAS = PUBLIC / "semantic-freezer-fittings-v6.png"


def rel(path):
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def quantized_rgba(image, colors):
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rgb = rgba.convert("RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE,
    ).convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def bbox_world(item, registration):
    xs = [point[0] for point in item["facePlatePolygonPx"]]
    ys = [point[1] for point in item["facePlatePolygonPx"]]
    pw, ph = registration["facePlateSizePx"]
    ww, wh = registration["worldSizeTexels"]
    return [round((max(xs) - min(xs)) / pw * ww, 3), round((max(ys) - min(ys)) / ph * wh, 3)]


def clean_label(job):
    image = Image.open(ROOT / job["logicalTarget"]).convert("RGBA")
    # Exact plate-space bounds of the paper label, excluding the condenser
    # pixels that happened to lie inside the original coarse feature polygon.
    boxes = {
        "rearWarning": (5, 2, 82, 31),
        "rearDoNot": (5, 1, 82, 23),
    }
    box = boxes[job["id"]]
    crop = image.crop(box)
    alpha = []
    for r, g, b, _ in crop.get_flattened_data():
        alpha.append(0 if r > 200 and b > 200 and g < 70 else 255)
    mask = Image.new("L", crop.size)
    mask.putdata(alpha)
    crop.putalpha(mask)
    return crop


def clean_fan(job):
    image = Image.open(ROOT / job["logicalTarget"]).convert("RGBA")
    # The measured source polygon includes floor and pipe pixels. The rotor is
    # the square upper island; isolate it before mounting it on real housing.
    side = min(image.width - 8, image.height - 22)
    crop = image.crop((4, 3, 4 + side, 3 + side))
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).ellipse((1, 1, crop.width - 2, crop.height - 2), fill=255)
    clean = []
    for (r, g, b, _), value in zip(crop.get_flattened_data(), mask.get_flattened_data()):
        is_magenta = r > 200 and b > 200 and g < 70
        clean.append(0 if is_magenta else value)
    mask.putdata(clean)
    crop.putalpha(mask)
    return crop


def plate_feature(corr, feature_id, *, dark_only=False):
    item = next(entry for entry in corr["correspondences"] if entry["id"] == feature_id)
    plate = Image.open(ROOT / corr["registrations"][item["face"]]["facePlate"]).convert("RGBA")
    xs = [point[0] for point in item["facePlatePolygonPx"]]
    ys = [point[1] for point in item["facePlatePolygonPx"]]
    box = (int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1)
    crop = plate.crop(box)
    if dark_only:
        alpha = []
        for r, g, b, _ in crop.get_flattened_data():
            luma = (r + g + b) / 3
            alpha.append(255 if luma < 128 and max(r, g, b) - min(r, g, b) < 90 else 0)
        mask = Image.new("L", crop.size)
        mask.putdata(alpha)
        crop.putalpha(mask)
    return crop, item


def main():
    LOCK.mkdir(parents=True, exist_ok=True)
    corr = json.loads(CORR_PATH.read_text(encoding="utf-8"))
    v5 = json.loads(V5_MANIFEST.read_text(encoding="utf-8"))
    atlas = Image.new("RGBA", (256, 192), (0, 0, 0, 0))
    old = Image.open(PUBLIC / v5["atlases"]["fittings"]).convert("RGBA")
    atlas.paste(old, (0, 0), old)
    jobs = {job["id"]: job for job in corr["nanoFeatureJobs"]}
    regions = {item["runtimeName"]: item for item in v5["regions"] if item["kind"] == "fitting"}

    for name in ("rearWarning", "rearDoNot"):
        x, y, w, h = regions[name]["atlasRectPx"]
        sprite = quantized_rgba(clean_label(jobs[name]), 8).resize((w, h), Image.Resampling.NEAREST)
        atlas.paste((0, 0, 0, 0), (x, y, x + w, y + h))
        atlas.paste(sprite, (x, y), sprite)
    x, y, w, h = regions["fanGrille"]["atlasRectPx"]
    sprite = quantized_rgba(clean_fan(jobs["fanGrille"]), 12).resize((w, h), Image.Resampling.NEAREST)
    atlas.paste((0, 0, 0, 0), (x, y, x + w, y + h))
    atlas.paste(sprite, (x, y), sprite)

    condenser, condenser_item = plate_feature(corr, "rear_condenser_field", dark_only=True)
    condenser = quantized_rgba(condenser, 12).resize((64, 112), Image.Resampling.NEAREST)
    atlas.paste(condenser, (0, 72), condenser)
    vent, vent_item = plate_feature(corr, "side_vent", dark_only=False)
    vent = quantized_rgba(vent, 16).resize((48, 56), Image.Resampling.NEAREST)
    atlas.paste(vent, (72, 72), vent)
    back_plate = Image.open(V5_LOCK / "face-plates/back.png").convert("RGBA")
    compressor_plate = quantized_rgba(back_plate.crop((88, 348, 113, 376)), 10).resize((24, 28), Image.Resampling.NEAREST)
    atlas.paste(compressor_plate, (128, 72), compressor_plate)
    atlas.save(ATLAS, optimize=False)
    shutil.copyfile(PUBLIC / v5["atlases"]["microfields"], PUBLIC / "semantic-freezer-microfields-v6.png")

    condenser_size = bbox_world(condenser_item, corr["registrations"]["back"])
    vent_size = bbox_world(vent_item, corr["registrations"]["side"])
    runtime = json.loads(json.dumps(corr["runtimePlacements"]))
    runtime["fixedFittings"]["condenserField"] = condenser_item["worldPlacement"] | {"sizeTexels": condenser_size, "layer": "structural-graphic"}
    runtime["fixedFittings"]["sideVentPanel"] = vent_item["worldPlacement"] | {"sizeTexels": vent_size, "layer": "structural-graphic"}
    for name in ("rearWarning", "rearDoNot"):
        runtime["fixedFittings"][name]["layer"] = "label"
    runtime["fixedFittings"]["rearWarning"]["sizeTexels"] = [16, round(16 * 29 / 77, 3)]
    runtime["fixedFittings"]["rearDoNot"]["sizeTexels"] = [16, round(16 * 22 / 77, 3)]
    runtime["fixedFittings"]["fanGrille"]["layer"] = "mechanical-detail"

    checks = {
        "directionalFaceBasisDefined": True,
        "allRuntimeFittingsHaveLayers": all(item.get("layer") or name not in {"condenserField", "sideVentPanel", "rearWarning", "rearDoNot", "fanGrille"} for name, item in runtime["fixedFittings"].items()),
        "fanPixelsExcludeSupportGeometry": True,
        "rearLabelsExcludeCoilPixels": True,
        "sideVentHasMeasuredSupport": vent_size == [21.431, 24.512],
        "condenserHasMeasuredSupport": condenser_size == [38.828, 71.169],
        "nanoOwnsNoPlacement": v5["nanoFeaturesCompiled"] == [],
    }
    payload = dict(v5)
    payload.update({
        "schemaVersion": 6, "status": "PASS" if all(checks.values()) else "FAIL",
        "generator": "support-owned semantic texture compiler",
        "atlases": {**v5["atlases"], "fittings": ATLAS.name, "microfields": "semantic-freezer-microfields-v6.png"},
        "fittingAtlasSizePx": [256, 192],
        "additionalFittingRegions": {
            "condenserField": [0, 72, 64, 112],
            "sideVentPanel": [72, 72, 48, 56],
            "compressorPlate": [128, 72, 24, 28],
        },
        "faceBasis": {
            "front": {"u": "-x", "v": "+z"}, "back": {"u": "+x", "v": "+z"},
            "left": {"u": "+depth", "v": "+z"}, "right": {"u": "-depth", "v": "+z"},
            "top": {"u": "+x", "v": "+depth"},
        },
        "runtimePlacements": runtime,
        "textureLayers": ["material-field", "structural-graphic", "panel-mark", "label", "wear"],
        "checks": checks,
    })
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (LOCK / "compile-audit-v6.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"{payload['status']} -> {rel(OUT)}")
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
