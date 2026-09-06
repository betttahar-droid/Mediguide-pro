"""Verify that v8 uses coarse macro geometry and decals for small detail."""
from __future__ import annotations

from pathlib import Path
import json
import struct


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
MODEL = ROOT / "public" / "models" / "vaccine-fridge-ps1-decals-v8.glb"
BASELINE = ROOT / "public" / "models" / "vaccine-fridge-source-true.glb"
RENDER = LOCK / "variants" / "authority-1door-ps1-decals-v8.png"
OUTPUT = LOCK / "style-research-v7" / "ps1-decals-v8.audit.json"
REPORT = LOCK / "style-research-v7" / "PS1-DECAL-AUDIT-V8.md"


def read_glb(path: Path) -> dict:
    data = path.read_bytes()
    length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A:
        raise ValueError("GLB JSON chunk missing")
    return json.loads(data[20:20 + length].decode("utf-8"))


def hull_vertices(document: dict) -> int:
    node = next(item for item in document["nodes"] if item.get("name") == "source_hull")
    mesh = document["meshes"][node["mesh"]]
    return sum(document["accessors"][primitive["attributes"]["POSITION"]]["count"]
               for primitive in mesh["primitives"])


def main() -> None:
    current = read_glb(MODEL)
    baseline = read_glb(BASELINE)
    nodes = {item.get("name", ""): item for item in current["nodes"]}
    root = nodes["vaccine_fridge_ps1_decals_v8_root"]["extras"]
    forbidden_small_geometry = (
        "v7_door_hinge_0", "v7_door_hinge_1", "v7_door_hinge_2",
        "v7_side_service_slot_0", "v7_side_service_slot_1", "v7_side_service_slot_2",
        "v7_crown_corner_catch_left", "v7_crown_corner_catch_right",
    )
    v8_decals = [node for name, node in nodes.items() if name.startswith("v8_decal_")]
    current_hull = hull_vertices(current)
    baseline_hull = hull_vertices(baseline)
    samplers = current.get("samplers", [])

    checks = {
        "styleVersionEight": root.get("styleFitVersion") == 8,
        "fourPixelGeometryThreshold": root.get("geometryDetailThresholdPx") == 4,
        "smallDetailPolicyIsDecals": root.get("smallDetailPolicy") == "nano_fixed_decals_not_geometry",
        "tenCoarseMacroProfileRings": root.get("macroProfileRings") == 10,
        "smallV7GeometryRemoved": all(name not in nodes for name in forbidden_small_geometry),
        "sixReplacementFittingDecals": len(v8_decals) == 6,
        "replacementDetailsCarryDecalPolicy": all(
            node.get("extras", {}).get("texturePolicy") == "PS1_FIXED_DETAIL_DECAL"
            for node in v8_decals
        ),
        "replacementDetailsRemainFixedScale": all(
            node.get("extras", {}).get("scalePolicy") == "anchor_translate_only_never_scale_fitting"
            for node in v8_decals
        ),
        "macroHullVertexCountReduced": current_hull < baseline_hull * .75,
        "nearestSamplerWithoutMipmaps": bool(samplers) and all(
            item.get("magFilter") == 9728 and item.get("minFilter") == 9728
            for item in samplers
        ),
        "renderExists": RENDER.exists(),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "schemaVersion": 8,
        "status": status,
        "checks": checks,
        "metrics": {
            "baselineHullVertices": baseline_hull,
            "v8HullVertices": current_hull,
            "hullVertexReduction": round(1 - current_hull / baseline_hull, 4),
            "macroProfileRings": root.get("macroProfileRings"),
            "replacementDecals": len(v8_decals),
            "samplers": samplers,
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# PS1 Decal/Geometry Audit — v8\n\n"
        f"Overall result: **{status}**\n\n"
        "- Small-detail geometry from v7: removed.\n"
        "- Replacement hinges/catches/service marks: six fixed decals.\n"
        f"- Macro hull vertices: {baseline_hull} → {current_hull} "
        f"({1-current_hull/baseline_hull:.1%} reduction).\n"
        f"- Coarse silhouette profile rings: {root.get('macroProfileRings')}.\n"
        "- Detail threshold: features below four model pixels become decals.\n"
        f"- Texture sampler: `{json.dumps(samplers)}`.\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(f"{status} PS1 decal audit: {sum(checks.values())}/{len(checks)} checks")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
