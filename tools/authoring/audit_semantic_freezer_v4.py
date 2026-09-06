"""Audit v4 evidence and independent-axis scaling invariants."""
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v4"


def as_map(items):
    return dict(items)


def main():
    runtime = json.loads((LOCK / "runtime/audit.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "public/textures/semantic-freezer-v4.json").read_text(encoding="utf-8"))
    records = runtime["records"]
    normal = next(item for item in records if item["scale"] == [1, 1, 1])
    x_scale = next(item for item in records if item["scale"] == [1.45, 1, 1])
    y_scale = next(item for item in records if item["scale"] == [1, 1.5, 1])
    z_scale = next(item for item in records if item["scale"] == [1, 1, 1.3])
    checks = {
        "evidenceCompilerPasses": manifest["status"] == "PASS" and all(manifest["checks"].values()),
        "allRuntimeRecordsClean": all(not item["errors"] for item in records),
        "allRuntimeRecordsUseV4": all(item["textureVersion"] == "v4" for item in records),
        "fixedFittingsInvariantEveryAxis": all(item["fixedFittingSizes"] == normal["fixedFittingSizes"] for item in records),
        "rigidHandleInvariantEveryAxis": all(item["rigidPartSizes"] == normal["rigidPartSizes"] for item in records),
        "widthAddsRearRails": as_map(x_scale["repeatedStructureCounts"])["rear_coil_rail"] > as_map(normal["repeatedStructureCounts"])["rear_coil_rail"],
        "depthAddsPanelColumns": as_map(y_scale["adaptiveSurfaceCounts"])["side_panel_column"] > as_map(normal["adaptiveSurfaceCounts"])["side_panel_column"],
        "heightAddsPanelRows": as_map(z_scale["adaptiveSurfaceCounts"])["side_panel_row"] > as_map(normal["adaptiveSurfaceCounts"])["side_panel_row"],
        "heightAddsShelves": z_scale["shelfCount"] > normal["shelfCount"],
        "heightAddsRearRuns": as_map(z_scale["repeatedStructureCounts"])["rear_coil_run"] > as_map(normal["repeatedStructureCounts"])["rear_coil_run"],
    }
    payload = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    (LOCK / "adaptive-audit-v4.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
