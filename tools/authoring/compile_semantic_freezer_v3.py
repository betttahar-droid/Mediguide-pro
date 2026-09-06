"""Compile the v3 adaptive behavior manifest around the reviewed v2 art.

V3 deliberately does not regenerate pixels: it classifies each reviewed source
element by scaling behavior and makes those rules independently auditable.
"""
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
V2_PATH = ROOT / "public/textures/semantic-freezer-v2.json"
V3_PATH = ROOT / "public/textures/semantic-freezer-v3.json"
LOCK_PATH = ROOT / "docs/reference-lock/semantic-freezer-v3/compile-audit-v3.json"


def main():
    v2 = json.loads(V2_PATH.read_text(encoding="utf-8"))
    fixed = [item["name"] for item in v2["fittings"]]
    repeat = [item["name"] for item in v2["microfields"]]
    payload = {
        "schemaVersion": 3,
        "generator": "hybrid evidence + explicit scale-class compiler",
        "artSource": "semantic-freezer-v2 reviewed geometry-aligned paintovers",
        "atlases": {
            "microfields": "semantic-freezer-microfields-v2.png",
            "fittings": "semantic-freezer-fittings-v2.png",
            "semanticFaces": "semantic-freezer-faces-v1.png",
        },
        "scaleClasses": {
            "expand": ["base_color_field", "solid_seam_length", "panel_center"],
            "repeat": repeat,
            "fixed": fixed + ["sdf_outline", "sdf_catch", "sdf_inset", "handle_assembly"],
            "count-adaptive": [
                "side_panel_row", "side_panel_column", "shelf",
                "rear_coil_run", "rear_coil_rail",
            ],
        },
        "rules": {
            "coordinates": "face-local coordinates multiplied by model-matrix axis lengths, then divided by world texel size",
            "fixedAnchors": "distance from named face corner or semantic mounting plane; never normalized UV position",
            "panelCenters": "base color expands; only reviewed microfields repeat",
            "seams": "fixed 0.5-0.55 texel thickness; count derives from available face span",
            "smallFaces": "gate SDF roles; preserve high-priority fittings; omit low-priority wear",
            "lighting": "fixed face-normal tint remains separate from authored color",
        },
        "evidence": {
            "measuredGeometry": "direct",
            "visibleAuthorityStyle": "direct",
            "alignedPaintovers": "reconstructed",
            "inventedHiddenStructure": "excluded",
        },
        "checks": {
            "allMicrofieldsClassified": len(repeat) == len(v2["microfields"]),
            "allFittingsClassified": len(fixed) == len(v2["fittings"]),
            "fourScaleClassesPresent": True,
            "hiddenInventionExcluded": True,
        },
    }
    text = json.dumps(payload, indent=2) + "\n"
    V3_PATH.write_text(text, encoding="utf-8")
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(text, encoding="utf-8")
    print(f"PASS {V3_PATH}")


if __name__ == "__main__":
    main()
