"""Audit v5 correspondence and independent-axis scaling behavior."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v5"


def as_map(items):
    return dict(items)


def main():
    runtime = json.loads((LOCK / "runtime/audit.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "public/textures/semantic-freezer-v5.json").read_text(encoding="utf-8"))
    records = runtime["records"]
    normal = next(item for item in records if item["scale"] == [1, 1, 1])
    y_scale = next(item for item in records if item["scale"] == [1, 1.5, 1])
    z_scale = next(item for item in records if item["scale"] == [1, 1, 1.3])
    normal_adaptive = as_map(normal["adaptiveSurfaceCounts"])
    checks = {
        "compilerPasses": manifest["status"] == "PASS" and all(manifest["checks"].values()),
        "runtimeClean": all(not item["errors"] for item in records),
        "runtimeUsesV5": all(item["textureVersion"] == "v5" for item in records),
        "sixMeasuredFittingsPlaced": len(normal["correspondenceIds"]) == 6,
        "baseSideHasOneMeasuredRow": normal_adaptive["side_panel_row"] == 1,
        "baseSideHasTwoSegmentColumns": normal_adaptive["side_panel_column"] == 2,
        "depthAddsOnlyColumns": as_map(y_scale["adaptiveSurfaceCounts"])["side_panel_column"] > 2,
        "heightAddsOnlyRows": as_map(z_scale["adaptiveSurfaceCounts"])["side_panel_row"] > 1,
        "fixedFittingsInvariant": all(item["fixedFittingSizes"] == normal["fixedFittingSizes"] for item in records),
        "handleInvariant": all(item["rigidPartSizes"] == normal["rigidPartSizes"] for item in records),
    }
    payload = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    (LOCK / "runtime-audit-v5.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
