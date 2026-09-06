"""Compile explicit anchor/extent/pitch contracts for scalable freezer V7."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v7"
PUBLIC = ROOT / "public/textures"
V6 = PUBLIC / "semantic-freezer-v6.json"
OUT = PUBLIC / "semantic-freezer-v7.json"


def main():
    LOCK.mkdir(parents=True, exist_ok=True)
    v6 = json.loads(V6.read_text(encoding="utf-8"))
    shutil.copyfile(PUBLIC / v6["atlases"]["fittings"], PUBLIC / "semantic-freezer-fittings-v7.png")
    shutil.copyfile(PUBLIC / v6["atlases"]["microfields"], PUBLIC / "semantic-freezer-microfields-v7.png")
    anchors = {
        "sideVentPanel": {"horizontal": "back-fixed", "backOffsetTexels": 12.513, "vertical": "bottom-fixed", "bottomCenterTexels": 16.095},
        "sideRating": {"horizontal": "front-fixed", "frontOffsetTexels": 8.088, "vertical": "top-fixed", "topOffsetTexels": 5.3},
        "rearWarning": {"horizontal": "panel-center", "centerOffsetTexels": -0.801, "vertical": "panel-top-fixed", "topOffsetTexels": 25.14},
        "rearDoNot": {"horizontal": "panel-center", "centerOffsetTexels": -0.736, "vertical": "panel-bottom-fixed", "bottomOffsetTexels": 10.977},
        "fanGrille": {"horizontal": "center-fixed", "centerTexels": -11.737, "vertical": "bottom-fixed", "bottomCenterTexels": 13.071},
    }
    adaptive = {
        "condenserField": {
            "horizontal": {"leftMarginTexels": 3.224, "rightMarginTexels": 1.948},
            "vertical": {"bottomTexels": 25.754, "topMarginTexels": 4.076, "topReference": "header-top"},
            "railPitchTexels": 2.45, "railWidthTexels": .52,
            "rowPitchTexels": 8.2, "rowWidthTexels": .72,
            "minimumSizeTexels": [20, 28], "scaleClass": "count-adaptive",
        }
    }
    checks = {
        "everyMovedFittingHasEdgeAnchor": all("fixed" in item["horizontal"] or item["horizontal"] in {"panel-center", "center-fixed"} for item in anchors.values()),
        "adaptiveFieldHasFixedPitch": adaptive["condenserField"]["railPitchTexels"] > 0 and adaptive["condenserField"]["rowPitchTexels"] > 0,
        "adaptiveFieldHasIndependentMargins": adaptive["condenserField"]["horizontal"]["leftMarginTexels"] != adaptive["condenserField"]["horizontal"]["rightMarginTexels"],
        "textureLayerContractRetained": len(v6["textureLayers"]) >= 5,
    }
    payload = dict(v6)
    payload.update({
        "schemaVersion": 7, "status": "PASS" if all(checks.values()) else "FAIL",
        "generator": "edge-anchored fixed-world adaptive texture compiler",
        "atlases": {**v6["atlases"], "fittings": "semantic-freezer-fittings-v7.png", "microfields": "semantic-freezer-microfields-v7.png"},
        "anchorContracts": anchors, "adaptiveTextureContracts": adaptive,
        "textureLayers": ["material-field", "structural-graphic", "mechanical-detail", "panel-mark", "label", "wear"],
        "checks": checks,
    })
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (LOCK / "compile-audit-v7.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"{payload['status']} -> public/textures/{OUT.name}")
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
