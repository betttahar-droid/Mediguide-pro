"""Compile exact correspondences and approved Nano feature islands for freezer v5."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v5"
PUBLIC = ROOT / "public/textures"
CORR = LOCK / "correspondence-v5.json"
V4 = PUBLIC / "semantic-freezer-v4.json"
OUT = PUBLIC / "semantic-freezer-v5.json"


def rel(path):
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def magenta(pixel):
    r, g, b = pixel[:3]
    return r >= 190 and b >= 190 and g <= 75 and abs(r - b) <= 85


def gate(job):
    output_path = ROOT / job["output"]
    if not output_path.exists():
        return {"status": "missing", "approved": False, "path": job["output"]}
    output = Image.open(output_path).convert("RGBA")
    target = Image.open(ROOT / job["inputsInOrder"][0]).convert("RGB")
    mask = Image.open(ROOT / job["inputsInOrder"][1]).convert("L")
    if output.size != target.size:
        return {"status": "rejected", "approved": False, "reason": "canvas-size", "outputSizePx": list(output.size), "expectedSizePx": list(target.size)}
    outside = [(p, m) for p, m in zip(output.get_flattened_data(), mask.get_flattened_data()) if m < 128]
    leak = sum(not magenta(p) for p, _ in outside) / max(1, len(outside))
    alpha = Image.new("L", output.size, 0)
    alpha.putdata([0 if magenta(p) else 255 for p in output.get_flattened_data()])
    expected = sum(m >= 128 for m in mask.get_flattened_data())
    actual = sum(v >= 128 for v in alpha.get_flattened_data())
    coverage = actual / max(1, expected)
    approved = leak <= .002 and .72 <= coverage <= 1.08
    return {"status": "approved" if approved else "rejected", "approved": approved,
            "outsideLeakShare": round(leak, 6), "maskCoverage": round(coverage, 6),
            "thresholds": {"outsideLeakShare": .002, "maskCoverage": [.72, 1.08]}, "path": job["output"]}


def logical_sprite(job, output):
    image = Image.open(output).convert("RGBA")
    x, y, width, height = job["canvasRectPx"]
    logical = image.crop((x, y, x + width, y + height)).resize(tuple(job["logicalSizePx"]), Image.Resampling.NEAREST)
    mask = Image.open(ROOT / job["logicalEditMask"]).convert("L")
    logical.putalpha(mask)
    box = mask.getbbox()
    return logical.crop(box) if box else logical


def direct_sprite(job):
    image = Image.open(ROOT / job["logicalTarget"]).convert("RGBA")
    mask = Image.open(ROOT / job["logicalEditMask"]).convert("L")
    image.putalpha(mask)
    if job["id"] == "medicalIdentity":
        # The identity mark is ink printed directly on enamel, not a sticker.
        # Preserve the blue/dark authority pixels and key out the neutral body.
        pixels = []
        for r, g, b, a in image.get_flattened_data():
            chroma = max(r, g, b) - min(r, g, b)
            luma = (r + g + b) / 3
            pixels.append(255 if a and (luma < 135 or chroma > 24) else 0)
        ink = Image.new("L", image.size)
        ink.putdata(pixels)
        image.putalpha(ink)
    box = mask.getbbox()
    return image.crop(box) if box else image


def main():
    corr = json.loads(CORR.read_text(encoding="utf-8"))
    v4 = json.loads(V4.read_text(encoding="utf-8"))
    jobs = {job["id"]: job for job in corr["nanoFeatureJobs"]}
    gates = {name: gate(job) for name, job in jobs.items()}
    v5_micro = PUBLIC / "semantic-freezer-microfields-v5.png"
    v5_fit = PUBLIC / "semantic-freezer-fittings-v5.png"
    shutil.copyfile(PUBLIC / v4["atlases"]["microfields"], v5_micro)
    atlas = Image.open(PUBLIC / v4["atlases"]["fittings"]).convert("RGBA")
    region_by_name = {item["runtimeName"]: item for item in v4["regions"] if item["kind"] == "fitting"}
    used = []
    direct_used = []
    for name, job in jobs.items():
        if name not in region_by_name:
            continue
        x, y, width, height = region_by_name[name]["atlasRectPx"]
        if gates[name]["approved"]:
            sprite = logical_sprite(job, ROOT / job["output"])
            used.append(name)
        else:
            # Visible reference pixels are already rectified by the measured
            # homography, so they are more authoritative than an AI repaint.
            sprite = direct_sprite(job)
            direct_used.append(name)
        sprite = sprite.resize((width, height), Image.Resampling.NEAREST)
        atlas.paste(sprite, (x, y), sprite)
    atlas.save(v5_fit, optimize=False)
    checks = {
        "allFourFacesRegistered": set(corr["registrations"]) == {"front", "side", "back", "roof"},
        "allCorrespondencesDirect": all(item["evidence"] == "direct" for item in corr["correspondences"]),
        "allCorrespondencesApproved": all(item["approval"] == "approved-direct" for item in corr["correspondences"]),
        "uniqueFeatureIds": len({item["id"] for item in corr["correspondences"]}) == len(corr["correspondences"]),
        "nanoCannotOwnPlacement": corr["policy"]["placementOwner"] == "deterministic correspondence compiler",
        "unsupportedFeaturesExcluded": corr["policy"]["unsupportedFeatures"] == "excluded",
        "runtimePlacementContractPresent": bool(corr["runtimePlacements"]["fixedFittings"] and corr["runtimePlacements"]["sidePanelSeeds"]),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = dict(v4)
    payload.update({
        "schemaVersion": 5, "status": status,
        "generator": "registered-face correspondence compiler with masked Nano feature reconstruction",
        "atlases": {**v4["atlases"], "microfields": v5_micro.name, "fittings": v5_fit.name},
        "correspondence": {"path": rel(CORR), "featureCount": len(corr["correspondences"]), "registrations": corr["registrations"]},
        "runtimePlacements": corr["runtimePlacements"], "nanoFeatureGates": gates,
        "directRectifiedFeaturesCompiled": direct_used,
        "nanoFeaturesCompiled": used, "checks": checks,
    })
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (LOCK / "compile-audit-v5.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [f"- `{name}`: **{gate['status'].upper()}**" for name, gate in gates.items()]
    audit = f"""# Semantic freezer v5 — exact feature correspondence audit

Status: **{status}**

- Registered authority faces: **{len(corr['registrations'])}**
- Measured semantic features: **{len(corr['correspondences'])}**
- Direct rectified feature islands compiled: **{len(direct_used)}**
- Nano feature islands accepted: **{len(used)}**
- Nano owns placement: **NO**
- Geometry changed by Nano: **NO**

## Nano island gates

{chr(10).join(lines)}

Missing/rejected candidates use exact rectified authority pixels; their measured v5 position remains active.

## Compiler checks

""" + "\n".join(f"- {name}: **{'PASS' if value else 'FAIL'}**" for name, value in checks.items()) + "\n"
    (LOCK / "AUDIT.md").write_text(audit, encoding="utf-8")
    print(f"{status} correspondences={len(corr['correspondences'])} nanoAccepted={len(used)} -> {rel(OUT)}")


if __name__ == "__main__":
    main()
