"""Build canonical face plates and feature correspondences for freezer v5.

Reference pixels are rectified deterministically. Nano may repaint only inside a
feature mask; it never determines a feature's position, size, face, or anchor.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "docs/reference-lock/semantic-freezer-v4"
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v5"
AUTHORITY = LOCK / "authority"
PLATES = LOCK / "face-plates"
MASKS = LOCK / "feature-masks"
JOBS = LOCK / "nano-feature-jobs"
OVERLAYS = LOCK / "registration-overlays"

# QUAD order is upper-left, lower-left, lower-right, upper-right in the source.
REGISTRATIONS = {
    "front": {
        "authority": "ref_front_view.png",
        "quad": [(285, 166), (285, 800), (625, 895), (625, 257)],
        "plateSizePx": (176, 416),
        "worldSizeTexels": (44, 104),
        "renderView": "iso",
    },
    "side": {
        "authority": "ref_right_side_view.png",
        "quad": [(376, 226), (376, 910), (687, 910), (687, 226)],
        "plateSizePx": (172, 404),
        "worldSizeTexels": (43, 101),
        "renderView": "side",
    },
    "back": {
        "authority": "ref_back_view.png",
        "quad": [(285, 257), (285, 800), (625, 895), (625, 354)],
        "plateSizePx": (176, 404),
        "worldSizeTexels": (44, 101),
        "renderView": "backIso",
    },
    "roof": {
        "authority": "ref_front_view.png",
        "quad": [(464, 59), (285, 166), (625, 257), (804, 169)],
        "plateSizePx": (176, 172),
        "worldSizeTexels": (44, 43),
        "renderView": "iso",
    },
}

# Polygons are measured directly in the 1024-square locked authorities.
FEATURES = [
    {"id": "front_control_band", "face": "front", "polygon": [(285, 166), (285, 255), (625, 354), (625, 257)], "behavior": "segment-owned", "part": "control_crown"},
    {"id": "medicalIdentity", "face": "front", "polygon": [(290, 181), (290, 244), (414, 278), (414, 214)], "behavior": "edge-fixed", "part": "control_crown", "runtimeSize": [13, 8], "nano": True},
    {"id": "digitalStatus", "face": "front", "polygon": [(518, 242), (518, 294), (610, 320), (610, 267)], "behavior": "edge-fixed", "part": "control_crown", "runtimeSize": [13, 5.8], "nano": True},
    {"id": "front_door_opening", "face": "front", "polygon": [(287, 257), (287, 798), (610, 887), (610, 349)], "behavior": "expand", "part": "door_frame"},
    {"id": "side_upper_panel", "face": "side", "polygon": [(377, 227), (377, 428), (686, 428), (686, 227)], "behavior": "segment-owned", "part": "shell_left"},
    {"id": "side_lower_panel", "face": "side", "polygon": [(377, 431), (377, 909), (686, 909), (686, 431)], "behavior": "expand", "part": "shell_left"},
    {"id": "side_panel_row_seed", "face": "side", "polygon": [(377, 426), (377, 432), (686, 432), (686, 426)], "behavior": "count-adaptive", "part": "shell_left"},
    {"id": "side_upper_column_seed", "face": "side", "polygon": [(520, 227), (520, 428), (526, 428), (526, 227)], "behavior": "segment-owned", "part": "shell_left"},
    {"id": "side_lower_column_seed", "face": "side", "polygon": [(600, 431), (600, 909), (606, 909), (606, 431)], "behavior": "segment-owned", "part": "shell_left"},
    {"id": "sideRating", "face": "side", "polygon": [(394, 233), (394, 291), (475, 291), (475, 233)], "behavior": "edge-fixed", "part": "shell_left", "runtimeSize": [8, 5.3], "nano": True},
    {"id": "side_vent", "face": "side", "polygon": [(519, 718), (519, 884), (674, 884), (674, 718)], "behavior": "edge-fixed", "part": "side_vent_panel"},
    {"id": "side_bottom_wear", "face": "side", "polygon": [(377, 815), (377, 909), (516, 909), (516, 815)], "behavior": "edge-fixed", "part": "shell_left"},
    {"id": "rear_condenser_field", "face": "back", "polygon": [(310, 289), (310, 668), (610, 751), (610, 371)], "behavior": "count-adaptive", "part": "rear_coil_run"},
    {"id": "rearWarning", "face": "back", "polygon": [(383, 410), (383, 474), (525, 514), (525, 450)], "behavior": "center-fixed", "part": "rear_coil_run", "runtimeSize": [16, 6.2], "nano": True},
    {"id": "rearDoNot", "face": "back", "polygon": [(383, 610), (383, 651), (526, 690), (526, 650)], "behavior": "center-fixed", "part": "rear_coil_run", "runtimeSize": [16, 5], "nano": True},
    {"id": "fanGrille", "face": "back", "polygon": [(315, 690), (315, 786), (414, 814), (414, 718)], "behavior": "edge-fixed", "part": "rear_fan", "runtimeSize": [12, 12], "nano": True},
    {"id": "rear_machine_bay", "face": "back", "polygon": [(310, 676), (310, 795), (610, 878), (610, 757)], "behavior": "segment-owned", "part": "rear_machine_bay"},
]

COLORS = {
    "edge-fixed": "#ff5c5c", "center-fixed": "#ffb84d",
    "segment-owned": "#4dd6ff", "count-adaptive": "#bd7cff", "expand": "#65dc8d",
}
NANO_CANVAS = 1024


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def homography(source, target):
    rows = []
    values = []
    for (x, y), (u, v) in zip(source, target):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        values.extend([u, v])
    solved = np.linalg.solve(np.asarray(rows, dtype=float), np.asarray(values, dtype=float))
    return np.asarray([*solved, 1.0], dtype=float).reshape(3, 3)


def transform_point(matrix, point):
    value = matrix @ np.asarray([point[0], point[1], 1.0], dtype=float)
    return [round(float(value[0] / value[2]), 3), round(float(value[1] / value[2]), 3)]


def polygon_center(polygon):
    return [sum(p[0] for p in polygon) / len(polygon), sum(p[1] for p in polygon) / len(polygon)]


def place_on_nano_canvas(image, *, background, max_scale=12, resample=Image.Resampling.NEAREST):
    """Place a logical crop on a fixed square without changing its aspect/grid."""
    scale = max(1, min(max_scale, (NANO_CANVAS - 96) // max(image.size)))
    size = (image.width * scale, image.height * scale)
    resized = image.resize(size, resample)
    canvas = Image.new(image.mode, (NANO_CANVAS, NANO_CANVAS), background)
    origin = ((NANO_CANVAS - size[0]) // 2, (NANO_CANVAS - size[1]) // 2)
    canvas.paste(resized, origin)
    return canvas, [origin[0], origin[1], size[0], size[1]], scale


def world_placement(feature, plate_polygon, registration):
    width, height = registration["plateSizePx"]
    world_width, world_height = registration["worldSizeTexels"]
    px, py = polygon_center(plate_polygon)
    face = feature["face"]
    if face == "front":
        u = world_width / 2 - px / width * world_width
        z = world_height - py / height * world_height
        return {"face": "front", "uTexels": round(u, 3), "zTexels": round(z, 3), "anchorMode": "top-fixed", "topOffsetTexels": round(world_height - z, 3)}
    if face == "side":
        along = px / width * world_width
        z = world_height - py / height * world_height
        return {"face": "left", "fromFrontTexels": round(along, 3), "zTexels": round(z, 3), "anchorMode": "side-face"}
    if face == "back":
        u = -world_width / 2 + px / width * world_width
        z = world_height - py / height * world_height
        return {"face": "back", "uTexels": round(u, 3), "zTexels": round(z, 3), "anchorMode": "back-face"}
    return {"face": face, "anchorMode": "plate-only"}


def make_feature_job(feature, plate, plate_polygon, authority, registration):
    min_x = max(0, math.floor(min(p[0] for p in plate_polygon)) - 6)
    min_y = max(0, math.floor(min(p[1] for p in plate_polygon)) - 6)
    max_x = min(plate.width, math.ceil(max(p[0] for p in plate_polygon)) + 6)
    max_y = min(plate.height, math.ceil(max(p[1] for p in plate_polygon)) + 6)
    crop_box = (min_x, min_y, max_x, max_y)
    crop = plate.crop(crop_box).convert("RGBA")
    local_polygon = [(round(x - min_x), round(y - min_y)) for x, y in plate_polygon]
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).polygon(local_polygon, fill=255)
    target = Image.new("RGBA", crop.size, (255, 0, 255, 255))
    target.paste(crop, (0, 0), mask)

    job_dir = JOBS / feature["id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    logical_target_path = job_dir / "target-logical.png"
    logical_mask_path = job_dir / "edit-mask-logical.png"
    target_path = job_dir / "target.png"
    mask_path = job_dir / "edit-mask.png"
    context_path = job_dir / "face-context.png"
    source_crop_path = job_dir / "source-evidence.png"
    target.convert("RGB").save(logical_target_path, optimize=False)
    mask.save(logical_mask_path, optimize=False)
    target_canvas, canvas_rect, canvas_scale = place_on_nano_canvas(
        target.convert("RGB"), background=(255, 0, 255),
    )
    mask_canvas, mask_rect, mask_scale = place_on_nano_canvas(mask, background=0)
    assert canvas_rect == mask_rect and canvas_scale == mask_scale
    target_canvas.save(target_path, optimize=False)
    mask_canvas.save(mask_path, optimize=False)
    context_canvas, _, _ = place_on_nano_canvas(
        plate, background=(255, 0, 255), max_scale=4,
    )
    context_canvas.save(context_path, optimize=False)
    source_bounds = (
        max(0, min(p[0] for p in feature["polygon"]) - 8),
        max(0, min(p[1] for p in feature["polygon"]) - 8),
        min(authority.width, max(p[0] for p in feature["polygon"]) + 8),
        min(authority.height, max(p[1] for p in feature["polygon"]) + 8),
    )
    source_crop = authority.crop(tuple(map(round, source_bounds)))
    source_canvas, _, _ = place_on_nano_canvas(
        source_crop, background=(255, 0, 255), max_scale=10,
    )
    source_canvas.save(source_crop_path, optimize=False)
    prompt = f"""Use case: precise-object-edit
Asset type: one rectified pixel-art fitting for a procedural 3D prop.
Feature ID: {feature['id']}

Image 1 is the immutable rectified TARGET. Paint only its existing non-magenta feature island.
Image 2 is the binary EDIT MASK: white may change, black is locked.
Image 3 is direct SOURCE EVIDENCE from the original reference.
Image 4 is the full rectified FACE CONTEXT.

Preserve Image 1 dimensions, silhouette, margins, pixel grid, feature position and orientation exactly. Reconstruct the source feature front-on with crisp PS1-era square texels. Preserve directly evidenced wording, panel divisions, colors and wear placement. Do not add surrounding geometry or new marks. Pure #FF00FF outside the feature. No antialiasing, blur, gradients, shadows, caption, legend or watermark. If evidence is unclear, retain Image 1 rather than inventing.
"""
    prompt_path = job_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return {
        "id": feature["id"],
        "prompt": rel(prompt_path),
        "inputsInOrder": [rel(target_path), rel(mask_path), rel(source_crop_path), rel(context_path)],
        "output": rel(job_dir / "nano-output.png"),
        "cropInFacePlatePx": list(crop_box),
        "logicalTarget": rel(logical_target_path),
        "logicalEditMask": rel(logical_mask_path),
        "logicalSizePx": list(crop.size),
        "nanoCanvasSizePx": [NANO_CANVAS, NANO_CANVAS],
        "canvasRectPx": canvas_rect,
        "canvasScale": canvas_scale,
        "approval": "pending",
    }


def main():
    for directory in (AUTHORITY, PLATES, MASKS, JOBS, OVERLAYS):
        directory.mkdir(parents=True, exist_ok=True)
    for name in {item["authority"] for item in REGISTRATIONS.values()}:
        source = V4 / "authority" / name
        target = AUTHORITY / name
        if not target.exists() or digest(target) != digest(source):
            shutil.copyfile(source, target)

    plates = {}
    matrices = {}
    registrations = {}
    for name, definition in REGISTRATIONS.items():
        authority_path = AUTHORITY / definition["authority"]
        authority = Image.open(authority_path).convert("RGB")
        width, height = definition["plateSizePx"]
        flattened_quad = tuple(value for point in definition["quad"] for value in point)
        plate = authority.transform(
            (width, height), Image.Transform.QUAD, flattened_quad, Image.Resampling.NEAREST,
        )
        plate_path = PLATES / f"{name}.png"
        plate.save(plate_path, optimize=False)
        destination = [(0, 0), (0, height), (width, height), (width, 0)]
        matrix = homography(definition["quad"], destination)
        plates[name] = plate
        matrices[name] = matrix
        registrations[name] = {
            "authority": rel(authority_path), "authoritySha256": digest(authority_path),
            "sourceQuadPx": [list(point) for point in definition["quad"]],
            "facePlate": rel(plate_path), "facePlateSizePx": [width, height],
            "worldSizeTexels": list(definition["worldSizeTexels"]),
            "renderView": definition["renderView"],
        }

    correspondences = []
    jobs = []
    for feature in FEATURES:
        definition = REGISTRATIONS[feature["face"]]
        plate_polygon = [transform_point(matrices[feature["face"]], point) for point in feature["polygon"]]
        mask = Image.new("L", definition["plateSizePx"], 0)
        ImageDraw.Draw(mask).polygon([(round(x), round(y)) for x, y in plate_polygon], fill=255)
        mask_path = MASKS / f"{feature['id']}.png"
        mask.save(mask_path, optimize=False)
        placement = world_placement(feature, plate_polygon, definition)
        correspondence = {
            "id": feature["id"], "face": feature["face"], "part": feature["part"],
            "referenceView": definition["authority"],
            "referencePolygonPx": [list(point) for point in feature["polygon"]],
            "facePlatePolygonPx": plate_polygon,
            "mask": rel(mask_path), "behavior": feature["behavior"],
            "runtimeSizeTexels": feature.get("runtimeSize"),
            "worldPlacement": placement,
            "evidence": "direct", "confidence": .98 if not feature.get("nano") else .95,
            "tolerance": {"positionTexels": 1.0, "sizeTexels": 1.0, "featureCount": "exact"},
            "nanoEligible": bool(feature.get("nano")), "approval": "approved-direct",
        }
        correspondences.append(correspondence)
        if feature.get("nano"):
            authority = Image.open(AUTHORITY / definition["authority"]).convert("RGB")
            jobs.append(make_feature_job(feature, plates[feature["face"]], plate_polygon, authority, definition))

    # Source-space and face-space evidence shown together for human review.
    for face, definition in REGISTRATIONS.items():
        source = Image.open(AUTHORITY / definition["authority"]).convert("RGB")
        source_draw = ImageDraw.Draw(source)
        for feature in [item for item in FEATURES if item["face"] == face]:
            color = COLORS[feature["behavior"]]
            source_draw.line([*feature["polygon"], feature["polygon"][0]], fill=color, width=3)
            source_draw.text(feature["polygon"][0], feature["id"], fill=color)
        plate = plates[face].resize((plates[face].width * 2, plates[face].height * 2), Image.Resampling.NEAREST)
        plate_draw = ImageDraw.Draw(plate)
        for item in [entry for entry in correspondences if entry["face"] == face]:
            points = [(round(x * 2), round(y * 2)) for x, y in item["facePlatePolygonPx"]]
            color = COLORS[item["behavior"]]
            plate_draw.line([*points, points[0]], fill=color, width=2)
        review = Image.new("RGB", (1024 + plate.width + 32, max(1024, plate.height)), (16, 17, 22))
        review.paste(source, (0, 0))
        review.paste(plate, (1024 + 32, 0))
        review.save(OVERLAYS / f"{face}.png", optimize=False)

    by_id = {item["id"]: item for item in correspondences}
    side_world = REGISTRATIONS["side"]["worldSizeTexels"]
    runtime = {
        "fixedFittings": {name: by_id[name]["worldPlacement"] | {"sizeTexels": by_id[name]["runtimeSizeTexels"]} for name in ("medicalIdentity", "digitalStatus", "sideRating", "rearWarning", "rearDoNot", "fanGrille")},
        "sidePanelSeeds": {
            "baseFaceWidthTexels": side_world[0], "baseFaceHeightTexels": side_world[1],
            "row": by_id["side_panel_row_seed"]["worldPlacement"],
            "upperColumn": by_id["side_upper_column_seed"]["worldPlacement"],
            "lowerColumn": by_id["side_lower_column_seed"]["worldPlacement"],
            "addedRowPitchTexels": 28, "addedColumnPitchTexels": 18,
            "thicknessTexels": .55,
        },
        "sideVent": by_id["side_vent"]["worldPlacement"],
    }
    payload = {
        "schemaVersion": 5,
        "policy": {
            "placementOwner": "deterministic correspondence compiler",
            "nanoRole": "masked pixel reconstruction only",
            "wholeViewGeneration": False,
            "unsupportedFeatures": "excluded",
        },
        "registrations": registrations,
        "correspondences": correspondences,
        "runtimePlacements": runtime,
        "nanoFeatureJobs": jobs,
    }
    path = LOCK / "correspondence-v5.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (LOCK / "nano-feature-jobs-v5.json").write_text(json.dumps({"schemaVersion": 5, "jobs": jobs}, indent=2) + "\n", encoding="utf-8")
    print(f"PASS faces={len(registrations)} features={len(correspondences)} nanoJobs={len(jobs)} -> {rel(path)}")


if __name__ == "__main__":
    main()
