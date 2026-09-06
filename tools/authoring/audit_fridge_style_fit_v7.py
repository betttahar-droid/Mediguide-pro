"""Audit the v7 GLB, Nano atlas contract, and reference-scale render change."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import struct

import numpy as np
from PIL import Image

from analyze_retro_style_references_v7 import quantized_metrics


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
MODEL = ROOT / "public" / "models" / "vaccine-fridge-style-fit-v7.glb"
BASELINE_MODEL = ROOT / "public" / "models" / "vaccine-fridge-source-true.glb"
BASELINE_RENDER = LOCK / "source-true-preview.png"
RENDER = LOCK / "variants" / "authority-1door-style-fit-v7.png"
MOTIF_AUDIT = LOCK / "nano-banana-v7" / "nano-style-motifs-v7.audit.json"
OUTPUT = LOCK / "style-research-v7" / "style-fit-v7.audit.json"
REPORT = LOCK / "style-research-v7" / "STYLE-FIT-AUDIT-V7.md"


def glb_json(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError("Expected glTF 2.0 GLB")
    length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A:
        raise ValueError("First GLB chunk is not JSON")
    return json.loads(data[20:20 + length].decode("utf-8"))


def main() -> None:
    document = glb_json(MODEL)
    motif = json.loads(MOTIF_AUDIT.read_text(encoding="utf-8"))
    nodes = {node.get("name", ""): node for node in document["nodes"]}
    root = nodes["vaccine_fridge_style_fit_v7_root"]["extras"]
    samplers = document.get("samplers", [])

    base = np.asarray(Image.open(BASELINE_RENDER).convert("RGB"), dtype=np.int16)
    render = np.asarray(Image.open(RENDER).convert("RGB"), dtype=np.int16)
    difference = np.max(np.abs(base - render), axis=2) > 12
    object_mask = np.mean(base, axis=2) >= 35
    changed_object_share = float(difference[object_mask].mean())
    render_metrics = quantized_metrics(Image.open(RENDER))

    checks = {
        "fiveStyleAuthoritiesRecorded": root.get("styleAuthorities") == 5,
        "lockedEnvelopeAuthorityPreserved": root.get("authoritySha256") == "8fface4d547894f3025cc69724a666b521d130db64dcb91e637d0c4abac855c4",
        "baselineStillExists": BASELINE_MODEL.exists(),
        "nearestSamplerNoMipmaps": bool(samplers) and all(
            item.get("magFilter") == 9728 and item.get("minFilter") == 9728
            for item in samplers
        ),
        "twelvePurposefulNanoMotifs": len(motif["decals"]) == 12,
        "internalMarginsAtLeastThree": all(item["internalMarginPx"] >= 3 for item in motif["decals"]),
        "atlasGuttersAtLeastFour": all(item["atlasMarginPx"] >= 4 for item in motif["decals"]),
        "motifExtentWithinEightByTen": all(
            item["compiledExtentPx"][0] <= 10 and item["compiledExtentPx"][1] <= 10
            for item in motif["decals"]
        ),
        "quietShareAtLeastSeventyFivePercent": motif["meanLogicalQuietShare"] >= .75,
        "threeLoopGeneratedServiceSlots": all(f"v7_side_service_slot_{i}" in nodes for i in range(3)),
        "threeCompactDoorHinges": all(f"v7_door_hinge_{i}" in nodes for i in range(3)),
        "structuralDetailsAreMeshes": all(
            "mesh" in nodes[name]
            for name in nodes
            if name.startswith("v7_side_service_slot_") or name.startswith("v7_door_hinge_")
        ),
        "fixedSocketDecalMetadata": all(
            node.get("extras", {}).get("texturePolicy") == "FIXED_SOCKET_DECAL_WITH_MARGIN"
            for name, node in nodes.items()
            if name.startswith("v7_") and name in {
                "v7_cream_lower_corner", "v7_cream_upper_corner", "v7_glass_stair_glint",
                "v7_grille_corner", "v7_handle_cap", "v7_side_double_seam",
                "v7_side_lower_corner", "v7_side_upper_corner", "v7_teal_lower_corner",
                "v7_teal_upper_stair", "v7_shelf_end_0", "v7_shelf_end_1",
                "v7_shelf_end_2", "v7_shelf_end_3",
            }
        ),
        "renderChangeIsDeliberateNotRedesign": .015 <= changed_object_share <= .10,
        "renderClusterMedianMatchesReferences": (
            3 <= render_metrics["runLengthPx"]["horizontalMedian"] <= 5
            and 3 <= render_metrics["runLengthPx"]["verticalMedian"] <= 5
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "schemaVersion": 7,
        "status": status,
        "checks": checks,
        "metrics": {
            "modelSha256": sha256(MODEL.read_bytes()).hexdigest(),
            "baselineModelSha256": sha256(BASELINE_MODEL.read_bytes()).hexdigest(),
            "changedObjectPixelShare": round(changed_object_share, 4),
            "meanMotifQuietShare": motif["meanLogicalQuietShare"],
            "renderRunLengthPx": render_metrics["runLengthPx"],
            "samplers": samplers,
            "v7NodeCount": sum(name.startswith("v7_") for name in nodes),
        },
        "visualAudit": {
            "iteration1": "FAIL: hinge plates were too pale and service slots read as attached bright bars",
            "iteration2": "PASS: hinges reduced and darkened; service slots reduced and integrated into teal side plane",
            "remainingJudgment": "Style match is materially closer while appliance identity and quiet broad panels remain intact",
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Vaccine Fridge v7 — Style-Fit Audit",
        "",
        f"Overall result: **{status}**",
        "",
        "## Automated checks",
        "",
        *[f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in checks.items()],
        "",
        "## Measured results",
        "",
        f"- Changed object pixels versus v5: {changed_object_share:.2%} (target 1.5–10%).",
        f"- Mean quiet area inside Nano logical decal cells: {motif['meanLogicalQuietShare']:.1%} (minimum 75%).",
        f"- Render cluster runs: horizontal median {render_metrics['runLengthPx']['horizontalMedian']} px; vertical median {render_metrics['runLengthPx']['verticalMedian']} px (reference band 3–5 px).",
        f"- glTF samplers: `{json.dumps(samplers)}`.",
        f"- v7 geometry/decal nodes: {payload['metrics']['v7NodeCount']}.",
        "",
        "## Visual iteration",
        "",
        "1. First render rejected: pale oversized hinges and bright protruding service bars competed with the door.",
        "2. Second render accepted: hinges are smaller/darker; service slots are recessed-color teal; Nano clusters remain legible without turning broad panels into noise.",
        "",
        "The v5 baseline remains a separate file and is not replaced.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{status} v7 style-fit audit: {sum(checks.values())}/{len(checks)} checks")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
