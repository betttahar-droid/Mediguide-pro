"""Run the v2 reference-style metric against v3 renders."""
from pathlib import Path
import json

from audit_semantic_freezer_v2 import metrics


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT.parent / "Gemini version builder" / "img_gen"
RUNTIME = ROOT / "docs/reference-lock/semantic-freezer-v3/runtime"
OUTPUT = ROOT / "docs/reference-lock/semantic-freezer-v3/spatial-audit-v3.json"

PAIRS = {
    "front_iso": (
        AUTHORITY / "ref_front_view.png", RUNTIME / "view-iso-texture-v3.png",
        (273, 60, 804, 941),
    ),
    "right_side": (
        AUTHORITY / "ref_right_side_view.png", RUNTIME / "view-side-texture-v3.png",
        (326, 115, 689, 935),
    ),
    "back_iso": (
        AUTHORITY / "ref_back_view.png", RUNTIME / "view-backIso-texture-v3.png",
        (205, 60, 873, 948),
    ),
}


def main():
    records = {}
    for name, (authority_path, render_path, bounds) in PAIRS.items():
        authority = metrics(authority_path, bounds)
        render = metrics(render_path)
        ratio = render["hardEdgeDensity"] / max(authority["hardEdgeDensity"], .0001)
        delta = render["top5ColorShare"] - authority["top5ColorShare"]
        records[name] = {
            "authority": authority,
            "renderV3": render,
            "hardEdgeRatio": round(ratio, 3),
            "top5ShareDelta": round(delta, 3),
            "status": "PASS" if .30 <= ratio <= 1.70 and delta <= .45 else "FAIL",
        }
    payload = {
        "status": "PASS" if all(item["status"] == "PASS" for item in records.values()) else "FAIL",
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
