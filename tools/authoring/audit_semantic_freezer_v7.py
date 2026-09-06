"""Cross-scale audit for V7 anchors, adaptive fields, orientation and layers."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v7"
MANIFEST = ROOT / "public/textures/semantic-freezer-v7.json"
STYLE = ROOT / "tools/voxel-fridge/style.js"
MAIN = ROOT / "tools/semantic-freezer/main.js"
EPSILON = 1e-6


def close(a, b, tolerance=EPSILON):
    return abs(a - b) <= tolerance


def record(records, scale):
    return next(item for item in records if item["scale"] == scale)


def fitting(item, name, occurrence=0):
    matches = [entry for entry in item["fittingPlacements"] if entry["id"] == name]
    return matches[occurrence]


def field(item):
    return next(entry for entry in item["adaptiveTexturePanels"] if entry["id"] == "condenserField")


def rect(entry):
    u, z = entry["centerTexels"]
    w, h = entry["sizeTexels"]
    return (u - w / 2, z - h / 2, u + w / 2, z + h / 2)


def overlap(a, b):
    ar, br = rect(a), rect(b)
    return min(ar[2], br[2]) > max(ar[0], br[0]) and min(ar[3], br[3]) > max(ar[1], br[1])


def scan_vertical_pitch(image_path, item, sample_z=85.0):
    """Measure rail pitch in a fixed-camera, exact-back screenshot."""
    panel = field(item)
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    # Camera is fixed at zoom .83 with a 2.7 x 3.3 orthographic frustum.
    half_x = 1.35 / .83
    half_y = 1.65 / .83
    texel = 1 / 32
    target_y = item["scale"][2] * 104 * texel * .49
    left, _, right, _ = panel["boundsTexels"]
    x0 = round(((left * texel + half_x) / (2 * half_x)) * width) + 3
    x1 = round(((right * texel + half_x) / (2 * half_x)) * width) - 3
    world_y = sample_z * texel
    y = round(((half_y - (world_y - target_y)) / (2 * half_y)) * height)
    pixels = image.load()
    dark = []
    for x in range(max(0, x0), min(width, x1 + 1)):
        r, g, b = pixels[x, y]
        dark.append(max(r, g, b) < 105)
    centers = []
    start = None
    for index, value in enumerate(dark + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - start >= 1:
                centers.append(x0 + (start + index - 1) / 2)
            start = None
    spacings = [b - a for a, b in zip(centers, centers[1:]) if 7 <= b - a <= 24]
    return {"row": y, "runs": len(centers), "medianPitchPixels": median(spacings) if spacings else 0}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    runtime = json.loads((LOCK / "audit-runtime/audit.json").read_text(encoding="utf-8"))
    records = runtime["records"]
    base = record(records, [1, 1, 1])
    depth = record(records, [1, 1.5, 1])
    width = record(records, [1.45, 1, 1])
    height = record(records, [1, 1, 1.3])
    base_field, width_field, height_field = field(base), field(width), field(height)
    base_vent, depth_vent = fitting(base, "sideVentPanel"), fitting(depth, "sideVentPanel")
    base_rating, depth_rating = fitting(base, "sideRating"), fitting(depth, "sideRating")
    rear_warning, width_warning = fitting(base, "rearWarning"), fitting(width, "rearWarning")
    rear_do_not, height_do_not = fitting(base, "rearDoNot"), fitting(height, "rearDoNot")
    back_wear = fitting(base, "sideBottomWear", 1)
    style = STYLE.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    atlas = Image.open(ROOT / "public/textures/semantic-freezer-fittings-v7.png").convert("RGBA")
    magenta = sum(a > 0 and r > 200 and b > 200 and g < 70 for r, g, b, a in atlas.get_flattened_data())
    pitch_base = scan_vertical_pitch(LOCK / "audit-runtime/texture-v7-view-back-fit-0.png", base)
    pitch_width = scan_vertical_pitch(LOCK / "audit-runtime/texture-v7-view-back-fit-0-sx-1_45.png", width)
    expected_ids = {
        "front_control_band", "medicalIdentity", "digitalStatus", "front_door_opening",
        "side_upper_panel", "side_lower_panel", "side_panel_row_seed",
        "side_upper_column_seed", "side_lower_column_seed", "sideRating", "side_vent",
        "side_bottom_wear", "rear_condenser_field", "rearWarning", "rearDoNot",
        "fanGrille", "rear_machine_bay",
    }
    pitch_contract = manifest["adaptiveTextureContracts"]["condenserField"]
    checks = {
        "compilerContractPasses": manifest["schemaVersion"] == 7 and manifest["status"] == "PASS" and all(manifest["checks"].values()),
        "allCorrespondencesConsumed": set(base["correspondenceIds"]) == expected_ids,
        "runtimeUnitBoundarySane": base_field["sizeTexels"][0] < 100 and base_field["sizeTexels"][1] < 150,
        "baseCondenserMeasuredExtent": close(base_field["sizeTexels"][0], 38.828) and close(base_field["sizeTexels"][1], 71.154),
        "widthExpansionChangesOnlyExtent": close(width_field["sizeTexels"][0], 58.628) and close(width_field["sizeTexels"][1], base_field["sizeTexels"][1]),
        "heightExpansionChangesOnlyExtent": close(height_field["sizeTexels"][0], base_field["sizeTexels"][0]) and close(height_field["sizeTexels"][1], 101.4492),
        "condenserPitchNeverScales": all(entry["pitchTexels"] == base_field["pitchTexels"] for entry in (width_field, height_field)),
        "condenserLineWidthNeverScales": all(entry["lineWidthTexels"] == base_field["lineWidthTexels"] for entry in (width_field, height_field)),
        "condenserCountsGrow": width_field["repeatCounts"][0] > base_field["repeatCounts"][0] and height_field["repeatCounts"][1] > base_field["repeatCounts"][1],
        "condenserMarginsStayFixed": width_field["marginsTexels"] == base_field["marginsTexels"] == height_field["marginsTexels"],
        "condenserUsesSemanticProceduralField": "adaptiveCondenserField(condenserLayout" in main_source and "placeV5Fitting('condenserField'" in main_source,
        "sideVentBackAnchorFixed": close(base_vent["edgeDistancesTexels"]["back"], 12.513) and close(depth_vent["edgeDistancesTexels"]["back"], 12.513),
        "sideVentMovesWithRearEdge": close(depth_vent["centerTexels"][0] - base_vent["centerTexels"][0], 10.75),
        "sideRatingFrontAnchorFixed": close(base_rating["edgeDistancesTexels"]["front"], 8.088) and close(depth_rating["edgeDistancesTexels"]["front"], 8.088),
        "rearWarningTracksPanelTopAndCenter": close(rear_warning["edgeDistancesTexels"]["panelTop"], 25.14) and close(width_warning["edgeDistancesTexels"]["panelTop"], 25.14),
        "rearDoNotTracksPanelBottom": close(rear_do_not["edgeDistancesTexels"]["panelBottom"], 10.977) and close(height_do_not["edgeDistancesTexels"]["panelBottom"], 10.977),
        "fixedDecalsRemainFixed": all(item["fixedFittingSizes"] == base["fixedFittingSizes"] for item in records),
        "handleAndFixedGeometryRemainFixed": all(item["rigidPartSizes"] == base["rigidPartSizes"] for item in records),
        "rearLabelsLayerAboveField": rear_warning["renderOrder"] > base_field["renderOrder"] and rear_warning["planeTexels"] > base_field["planeTexels"],
        "ventOwnsOverlapInsteadOfWear": overlap(base_vent, back_wear) and base_vent["planeTexels"] < back_wear["planeTexels"],
        "faceOrientationContractComplete": set(manifest["faceBasis"]) == {"front", "back", "left", "right", "top"},
        "noDirectionFlippingOrCheckerMirroring": "cell.x = 63.0 - cell.x" not in style and "cell.y = 63.0 - cell.y" not in style,
        "fixedCameraPixelPitchStable": pitch_base["runs"] >= 10 and pitch_width["runs"] > pitch_base["runs"] and abs(pitch_base["medianPitchPixels"] - pitch_width["medianPitchPixels"]) <= 1.0,
        "shaderPitchMatchesContract": base_field["pitchTexels"] == [pitch_contract["railPitchTexels"], pitch_contract["rowPitchTexels"]],
        "noMagentaKeyLeak": magenta == 0,
        "runtimeClean": all(not item["errors"] for item in records),
    }
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "evidence": {
            "ventBackOffsets": [base_vent["edgeDistancesTexels"]["back"], depth_vent["edgeDistancesTexels"]["back"]],
            "condenserSizes": {"base": base_field["sizeTexels"], "width": width_field["sizeTexels"], "height": height_field["sizeTexels"]},
            "repeatCounts": {"base": base_field["repeatCounts"], "width": width_field["repeatCounts"], "height": height_field["repeatCounts"]},
            "pixelPitch": {"base": pitch_base, "width": pitch_width},
            "magentaPixels": magenta,
        },
    }
    (LOCK / "AUDIT.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (LOCK / "AUDIT.md").write_text(
        "# Semantic freezer V7 adaptive-texture audit\n\nStatus: **" + payload["status"] + "**\n\n"
        + "\n".join(f"- {name}: **{'PASS' if value else 'FAIL'}**" for name, value in checks.items())
        + "\n\n## Evidence\n\n```json\n" + json.dumps(payload["evidence"], indent=2) + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
