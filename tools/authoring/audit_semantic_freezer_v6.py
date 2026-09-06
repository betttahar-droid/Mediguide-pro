"""Audit V6 texture orientation, support ownership, placement and scaling."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v6"
MANIFEST = ROOT / "public/textures/semantic-freezer-v6.json"
STYLE = ROOT / "tools/voxel-fridge/style.js"


def by_scale(records, scale):
    return next(item for item in records if item["scale"] == scale)


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    runtime = json.loads((LOCK / "runtime/audit.json").read_text(encoding="utf-8"))
    records = runtime["records"]
    normal = by_scale(records, [1, 1, 1])
    depth = by_scale(records, [1, 1.5, 1])
    height = by_scale(records, [1, 1, 1.3])
    expected_ids = {
        "front_control_band", "medicalIdentity", "digitalStatus", "front_door_opening",
        "side_upper_panel", "side_lower_panel", "side_panel_row_seed",
        "side_upper_column_seed", "side_lower_column_seed", "sideRating", "side_vent",
        "side_bottom_wear", "rear_condenser_field", "rearWarning", "rearDoNot",
        "fanGrille", "rear_machine_bay",
    }
    supports = {item["id"]: item for item in normal["semanticSupports"]}
    placements = {item["id"]: item for item in normal["fittingPlacements"] if item["id"] in {
        "condenserField", "sideVentPanel", "fanGrille", "rearWarning", "rearDoNot",
    }}
    atlas = Image.open(ROOT / "public/textures/semantic-freezer-fittings-v6.png").convert("RGBA")
    magenta = sum(a > 0 and r > 200 and b > 200 and g < 70 for r, g, b, a in atlas.get_flattened_data())
    style = STYLE.read_text(encoding="utf-8")
    normal_counts = dict(normal["adaptiveSurfaceCounts"])
    checks = {
        "compilerPasses": manifest["status"] == "PASS" and all(manifest["checks"].values()),
        "allSeventeenCorrespondencesConsumed": set(normal["correspondenceIds"]) == expected_ids,
        "measuredSupportsExist": set(supports) == {"condenserField", "fanGrille", "rearMachineBay", "sideVentPanel"},
        "condenserSupportExact": supports["condenserField"]["sizeTexels"] == [38.828, 71.169],
        "sideVentSupportExact": supports["sideVentPanel"]["sizeTexels"] == [21.431, 24.512],
        "fanContainedByHousing": placements["fanGrille"]["sizeTexels"][0] <= supports["fanGrille"]["sizeTexels"][0]
            and placements["fanGrille"]["sizeTexels"][1] <= supports["fanGrille"]["sizeTexels"][1],
        "labelsLayerAboveCondenser": placements["rearWarning"]["renderOrder"] > placements["condenserField"]["renderOrder"]
            and placements["rearDoNot"]["planeTexels"] > placements["condenserField"]["planeTexels"],
        "noMagentaKeyLeak": magenta == 0,
        "noDirectionalTileMirroring": "cell.x = 63.0 - cell.x" not in style and "cell.y = 63.0 - cell.y" not in style,
        "explicitFaceBasis": set(manifest["faceBasis"]) == {"front", "back", "left", "right", "top"},
        "legacyChunkyRearGridRemoved": dict(normal["repeatedStructureCounts"])["rear_coil_run"] == 0
            and dict(normal["repeatedStructureCounts"])["rear_coil_rail"] == 0,
        "baseSideTopologyExact": normal_counts["side_panel_row"] == 1 and normal_counts["side_panel_column"] == 2,
        "depthAddsPanelColumns": dict(depth["adaptiveSurfaceCounts"])["side_panel_column"] > normal_counts["side_panel_column"],
        "heightAddsPanelRows": dict(height["adaptiveSurfaceCounts"])["side_panel_row"] > normal_counts["side_panel_row"],
        "fixedTexturePartsRemainFixed": all(item["fixedFittingSizes"] == normal["fixedFittingSizes"] for item in records),
        "handleRemainsFixed": all(item["rigidPartSizes"] == normal["rigidPartSizes"] for item in records),
        "runtimeClean": all(not item["errors"] for item in records),
    }
    payload = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "magentaPixels": magenta}
    (LOCK / "AUDIT.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (LOCK / "AUDIT.md").write_text(
        "# Semantic freezer V6 audit\n\nStatus: **" + payload["status"] + "**\n\n"
        + "\n".join(f"- {name}: **{'PASS' if value else 'FAIL'}**" for name, value in checks.items()) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
