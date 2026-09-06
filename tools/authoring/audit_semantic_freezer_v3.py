"""Audit v3 scale-class behavior across independent axis changes."""
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "docs/reference-lock/semantic-freezer-v3/runtime/audit.json"
OUTPUT_PATH = ROOT / "docs/reference-lock/semantic-freezer-v3/adaptive-audit-v3.json"


def as_map(items):
    return dict(items)


def main():
    runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
    records = runtime["records"]
    normal = next(item for item in records if item["scale"] == [1, 1, 1])
    x_scale = next(item for item in records if item["scale"] == [1.45, 1, 1])
    y_scale = next(item for item in records if item["scale"] == [1, 1.5, 1])
    z_scale = next(item for item in records if item["scale"] == [1, 1, 1.3])

    checks = {
        "allRuntimeRecordsClean": all(not item["errors"] for item in records),
        "fixedFittingsInvariantEveryAxis": all(
            item["fixedFittingSizes"] == normal["fixedFittingSizes"] for item in records
        ),
        "rigidHandleInvariantEveryAxis": all(
            item["rigidPartSizes"] == normal["rigidPartSizes"] for item in records
        ),
        "widthAddsRearRails": (
            as_map(x_scale["repeatedStructureCounts"])["rear_coil_rail"]
            > as_map(normal["repeatedStructureCounts"])["rear_coil_rail"]
        ),
        "depthAddsPanelColumns": (
            as_map(y_scale["adaptiveSurfaceCounts"])["side_panel_column"]
            > as_map(normal["adaptiveSurfaceCounts"])["side_panel_column"]
        ),
        "heightAddsPanelRows": (
            as_map(z_scale["adaptiveSurfaceCounts"])["side_panel_row"]
            > as_map(normal["adaptiveSurfaceCounts"])["side_panel_row"]
        ),
        "heightAddsShelves": z_scale["shelfCount"] > normal["shelfCount"],
        "heightAddsRearRuns": (
            as_map(z_scale["repeatedStructureCounts"])["rear_coil_run"]
            > as_map(normal["repeatedStructureCounts"])["rear_coil_run"]
        ),
    }
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "normal": {
                "surface": normal["adaptiveSurfaceCounts"],
                "structure": normal["repeatedStructureCounts"],
            },
            "width1.45": {
                "surface": x_scale["adaptiveSurfaceCounts"],
                "structure": x_scale["repeatedStructureCounts"],
            },
            "depth1.5": {
                "surface": y_scale["adaptiveSurfaceCounts"],
                "structure": y_scale["repeatedStructureCounts"],
            },
            "height1.3": {
                "surface": z_scale["adaptiveSurfaceCounts"],
                "structure": z_scale["repeatedStructureCounts"],
            },
        },
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
