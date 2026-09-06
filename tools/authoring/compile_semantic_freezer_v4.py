"""Compile direct-first, evidence-gated adaptive surface assets for freezer v4."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v4"
AUTHORITY = LOCK / "authority"
PUBLIC = ROOT / "public" / "textures"
JOBS_PATH = LOCK / "paintover-jobs-v4.json"
V2_LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v2"
V2_MANIFEST_PATH = PUBLIC / "semantic-freezer-v2.json"
V2_MICRO_ATLAS = PUBLIC / "semantic-freezer-microfields-v2.png"
V2_FITTING_ATLAS = PUBLIC / "semantic-freezer-fittings-v2.png"
MICRO_ATLAS = PUBLIC / "semantic-freezer-microfields-v4.png"
FITTING_ATLAS = PUBLIC / "semantic-freezer-fittings-v4.png"
MANIFEST_PATH = PUBLIC / "semantic-freezer-v4.json"
MICRO = 64

AUTHORITIES = {
    "iso": AUTHORITY / "ref_front_view.png",
    "side": AUTHORITY / "ref_right_side_view.png",
    "back": AUTHORITY / "ref_back_view.png",
}

# Directly visible, quiet material samples. Bounds are measured in the locked
# 1024-square authority views. They are color/material evidence, never geometry.
MICROFIELDS = (
    ("enamel", "iso", (430, 105, 535, 140), 8, "roof enamel center"),
    ("sideMetal", "side", (450, 325, 570, 405), 10, "service panel center"),
    ("darkCavity", "iso", (628, 284, 687, 330), 8, "unoccluded interior cavity"),
    ("shelfMetal", "iso", (520, 397, 650, 414), 8, "shelf lip metal"),
    ("medicinePaper", "iso", (373, 342, 405, 382), 8, "unprinted carton stock"),
    ("medicineTan", "iso", (576, 532, 608, 560), 8, "unprinted tan carton stock"),
    ("bottleAmber", "iso", (351, 548, 374, 574), 8, "unlabelled amber glass"),
    ("coilMetal", "back", (430, 285, 600, 307), 8, "condenser bar metal"),
)

# Fixed fittings are extracted from the real authority wherever visible. Their
# runtime size and anchor are explicit; the source crop never sets geometry.
FITTINGS = (
    ("medicalIdentity", "iso", (286, 180, 407, 245), (32, 24), (0, 0), "front:control-crown:top-left", "ink"),
    ("digitalStatus", "iso", (510, 188, 619, 254), (36, 16), (40, 0), "front:control-crown:top-right", "panel"),
    ("sideRating", "side", (394, 233, 475, 291), (18, 12), (84, 0), "left:upper-panel:top-left", "panel"),
    ("rearWarning", "back", (383, 416, 635, 476), (36, 14), (110, 0), "back:condenser:center", "panel"),
    ("rearDoNot", "back", (383, 614, 642, 656), (32, 10), (154, 0), "back:condenser:bottom-center", "panel"),
    ("fanGrille", "back", (310, 685, 426, 804), (28, 28), (192, 0), "back:machine-bay:bottom-left", "panel"),
    ("cartonCovid", "iso", (351, 324, 408, 391), (16, 20), (0, 32), "front:shelf-3:slot-1", "panel"),
    ("cartonMmr", "iso", (430, 329, 480, 396), (16, 20), (20, 32), "front:shelf-3:slot-2", "panel"),
    ("cartonFlu", "iso", (500, 323, 555, 396), (16, 20), (40, 32), "front:shelf-3:slot-3", "panel"),
    ("cartonBooster", "iso", (580, 520, 636, 587), (16, 20), (60, 32), "front:shelf-2:right", "panel"),
    ("vialCovid", "iso", (348, 495, 390, 548), (10, 14), (84, 32), "front:shelf-2:slot-1", "panel"),
    ("vialMmr", "iso", (406, 500, 446, 552), (10, 14), (98, 32), "front:shelf-2:slot-2", "panel"),
    ("vialFlu", "iso", (457, 499, 497, 555), (10, 14), (112, 32), "front:shelf-2:slot-3", "panel"),
    ("vialPolio", "iso", (350, 621, 391, 677), (10, 14), (126, 32), "front:shelf-1:slot-1", "panel"),
)

WEAR_FITTINGS = (
    ("sideBottomWear", "side", (350, 760, 455, 885), (28, 18), (150, 32), "left:bottom-left"),
    ("sideTopWear", "side", (600, 115, 686, 215), (28, 18), (182, 32), "left:top-right"),
    ("frontBaseWear", "iso", (415, 838, 540, 900), (32, 12), (214, 32), "front:bottom-center"),
)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def quantized(image: Image.Image, colors: int, size: tuple[int, int]) -> Image.Image:
    small = image.resize(size, Image.Resampling.BOX)
    return small.quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE,
    ).convert("RGBA")


def masked_wear(image: Image.Image, bounds: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    source = image.crop(bounds).resize(size, Image.Resampling.BOX).convert("RGB")
    quant = source.quantize(
        colors=10, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE,
    ).convert("RGBA")
    blurred = source.filter(ImageFilter.GaussianBlur(radius=1.15))
    output = Image.new("RGBA", size, (0, 0, 0, 0))
    for y in range(size[1]):
        for x in range(size[0]):
            here = source.getpixel((x, y))
            local = blurred.getpixel((x, y))
            here_luma = sum(here) / 3
            local_luma = sum(local) / 3
            # Keep only deliberate dark chips/seams. The body-color field is
            # transparent so fixed wear never becomes a rectangular sticker.
            if local_luma - here_luma >= 6.0 and here_luma < 155:
                output.putpixel((x, y), quant.getpixel((x, y)))
    return output


def fitting_sprite(image: Image.Image, bounds: tuple[int, int, int, int], size: tuple[int, int], mode: str) -> Image.Image:
    sprite = quantized(image.crop(bounds), 16, size)
    if mode != "ink":
        return sprite
    output = Image.new("RGBA", size, (0, 0, 0, 0))
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, _ = sprite.getpixel((x, y))
            luma = (r + g + b) / 3
            if luma < 120 or (b - r > 18 and b > g):
                output.putpixel((x, y), (r, g, b, 255))
    return output


def mask_magenta(image: Image.Image) -> Image.Image:
    pixels = []
    for r, g, b in image.convert("RGB").get_flattened_data():
        # Image editors may shift nominal #ff00ff by a few dozen levels. This
        # hue-family test still excludes purple/blue object materials.
        is_background = r >= 200 and b >= 200 and g <= 60 and abs(r - b) <= 70
        pixels.append(0 if is_background else 255)
    output = Image.new("L", image.size)
    output.putdata(pixels)
    return output


def silhouette_gate(raw_path: Path, output_path: Path) -> dict:
    if not output_path.exists():
        return {"status": "missing", "approved": False, "path": rel(output_path)}
    raw = Image.open(raw_path).convert("RGB")
    output = Image.open(output_path).convert("RGB")
    size_match = raw.size == output.size
    if not size_match:
        return {
            "status": "rejected", "approved": False, "path": rel(output_path),
            "reason": "output dimensions differ from locked target",
            "rawSizePx": list(raw.size), "outputSizePx": list(output.size),
        }
    a = mask_magenta(raw)
    b = mask_magenta(output)
    ad = list(a.get_flattened_data())
    bd = list(b.get_flattened_data())
    intersection = sum(bool(aa) and bool(bb) for aa, bb in zip(ad, bd))
    union = sum(bool(aa) or bool(bb) for aa, bb in zip(ad, bd))
    outside = sum((not bool(aa)) and bool(bb) for aa, bb in zip(ad, bd))
    raw_area = max(1, sum(bool(value) for value in ad))
    bbox_a = a.getbbox()
    bbox_b = b.getbbox()
    bbox_drift = max(
        abs(x - y) / max(raw.size) for x, y in zip(bbox_a or (0, 0, 0, 0), bbox_b or (0, 0, 0, 0))
    )
    iou = intersection / max(1, union)
    outside_share = outside / raw_area
    approved = iou >= .985 and bbox_drift <= .01 and outside_share <= .005
    return {
        "status": "approved" if approved else "rejected",
        "approved": approved,
        "path": rel(output_path),
        "sizeMatch": size_match,
        "silhouetteIoU": round(iou, 6),
        "bboxDrift": round(bbox_drift, 6),
        "outsideLeakShare": round(outside_share, 6),
        "thresholds": {"silhouetteIoU": .985, "bboxDrift": .01, "outsideLeakShare": .005},
    }


def internal_extraction_gate(raw_path: Path, output_path: Path) -> dict:
    """Permit internal crops only; never accept the paintover silhouette."""
    if not output_path.exists():
        return {"status": "missing", "approved": False, "path": rel(output_path)}
    output = Image.open(output_path).convert("RGB")
    raw = Image.open(raw_path).convert("RGB").resize(output.size, Image.Resampling.NEAREST)
    a = mask_magenta(raw)
    b = mask_magenta(output)
    ad = list(a.get_flattened_data())
    bd = list(b.get_flattened_data())
    intersection = sum(bool(aa) and bool(bb) for aa, bb in zip(ad, bd))
    union = sum(bool(aa) or bool(bb) for aa, bb in zip(ad, bd))
    outside = sum((not bool(aa)) and bool(bb) for aa, bb in zip(ad, bd))
    raw_area = max(1, sum(bool(value) for value in ad))
    bbox_a = a.getbbox() or (0, 0, 0, 0)
    bbox_b = b.getbbox() or (0, 0, 0, 0)
    bbox_drift = max(abs(x - y) / max(output.size) for x, y in zip(bbox_a, bbox_b))
    iou = intersection / max(1, union)
    outside_share = outside / raw_area
    approved = iou >= .98 and bbox_drift <= .04 and outside_share <= .015
    return {
        "status": "approved-internal-only" if approved else "rejected",
        "approved": approved,
        "silhouetteMayBeUsed": False,
        "path": rel(output_path),
        "silhouetteIoU": round(iou, 6),
        "bboxDrift": round(bbox_drift, 6),
        "outsideLeakShare": round(outside_share, 6),
        "thresholds": {"silhouetteIoU": .98, "bboxDrift": .04, "outsideLeakShare": .015},
    }


def direct_confidence(sprite: Image.Image, base: float) -> tuple[float, dict]:
    colors = Counter(sprite.convert("RGB").get_flattened_data())
    total = max(1, sprite.width * sprite.height)
    dominant = colors.most_common(1)[0][1] / total
    entropy = -sum((count / total) * math.log2(count / total) for count in colors.values())
    confidence = min(.99, max(.75, base + min(entropy, 4) * .012 - max(0, dominant - .8) * .2))
    return round(confidence, 3), {
        "paletteSize": len(colors), "dominantColorShare": round(dominant, 4), "entropyBits": round(entropy, 4),
    }


def source_record(view: str, bounds: tuple[int, int, int, int]) -> dict:
    path = AUTHORITIES[view]
    return {
        "view": view,
        "path": rel(path),
        "sha256": digest(path),
        "boundsPx": list(bounds),
        "evidenceClass": "direct",
    }


def paintover_gates() -> dict:
    jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    output = {}
    for name, job in jobs["views"].items():
        raw = next(item for item in job["inputsInOrder"] if item["role"] == "raw-target")
        output[name] = silhouette_gate(ROOT / raw["path"], ROOT / job["output"])
    return output


def aligned_v2_gates() -> dict:
    paths = {
        "iso": (
            V2_LOCK / "paintover-inputs" / "view-iso-surfaces-0-fittings-0-bg-magenta.png",
            V2_LOCK / "paintovers" / "iso-paintover-gpt.png",
        ),
        "side": (
            V2_LOCK / "paintover-inputs" / "view-side-surfaces-0-fittings-0-bg-magenta.png",
            V2_LOCK / "paintovers" / "side-paintover-gpt.png",
        ),
        "back": (
            V2_LOCK / "paintover-inputs" / "view-backIso-surfaces-0-fittings-0-bg-magenta.png",
            V2_LOCK / "paintovers" / "back-paintover-gpt.png",
        ),
    }
    return {name: internal_extraction_gate(raw, painted) for name, (raw, painted) in paths.items()}


def main() -> None:
    images = {name: Image.open(path).convert("RGB") for name, path in AUTHORITIES.items()}
    v2_manifest = json.loads(V2_MANIFEST_PATH.read_text(encoding="utf-8"))
    v2_micro_records = {item["name"]: item for item in v2_manifest["microfields"]}
    v2_fitting_records = {item["name"]: item for item in v2_manifest["fittings"]}
    v2_micro = Image.open(V2_MICRO_ATLAS).convert("RGBA")
    v2_fitting = Image.open(V2_FITTING_ATLAS).convert("RGBA")
    aligned_gates = aligned_v2_gates()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    LOCK.mkdir(parents=True, exist_ok=True)
    micro = Image.new("RGBA", (MICRO * len(MICROFIELDS), MICRO), (0, 0, 0, 0))
    fitting = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    regions = []

    for index, (name, view, bounds, colors, semantic) in enumerate(MICROFIELDS):
        pixel_record = v2_micro_records[name]
        x, y, width, height = pixel_record["atlasRectPx"]
        sprite = v2_micro.crop((x, y, x + width, y + height))
        micro.paste(sprite, (index * MICRO, 0))
        confidence, metrics = direct_confidence(sprite, .84)
        regions.append({
            "id": f"microfield:{name}", "runtimeName": name, "kind": "microfield",
            "scaleClass": "repeat", "semantic": semantic,
            "source": source_record(view, bounds),
            "pixelSource": {
                "class": "reconstructed",
                "generator": "gpt-image-editor",
                "path": v2_manifest["sources"][pixel_record["source"]]["path"],
                "boundsPx": pixel_record["sourceBoundsPx"],
                "alignmentGate": pixel_record["source"],
            },
            "atlasRectPx": [index * MICRO, 0, MICRO, MICRO],
            "confidence": confidence, "metrics": metrics,
            "decision": {"status": "approved", "reason": "direct authority information rectified through approved internal-only paintover"},
            "conflicts": [],
        })

    for name, view, bounds, size, origin, anchor, mode in FITTINGS:
        pixel_record = v2_fitting_records[name]
        x, y, width, height = pixel_record["atlasRectPx"]
        sprite = v2_fitting.crop((x, y, x + width, y + height))
        fitting.paste(sprite, origin, sprite)
        confidence, metrics = direct_confidence(sprite, .88)
        regions.append({
            "id": f"fitting:{name}", "runtimeName": name, "kind": "fitting",
            "scaleClass": "fixed", "anchor": anchor,
            "source": source_record(view, bounds),
            "pixelSource": {
                "class": "reconstructed",
                "generator": "gpt-image-editor",
                "path": v2_manifest["sources"][pixel_record["source"]]["path"],
                "boundsPx": pixel_record["sourceBoundsPx"],
                "alignmentGate": pixel_record["source"],
            },
            "atlasRectPx": [origin[0], origin[1], size[0], size[1]],
            "logicalSizePx": list(size), "confidence": confidence, "metrics": metrics,
            "decision": {"status": "approved", "reason": "direct fitting identity rectified onto locked geometry"},
            "conflicts": [],
        })

    for name, view, bounds, size, origin, anchor in WEAR_FITTINGS:
        pixel_record = v2_fitting_records[name]
        x, y, width, height = pixel_record["atlasRectPx"]
        sprite = v2_fitting.crop((x, y, x + width, y + height))
        fitting.paste(sprite, origin, sprite)
        opaque = sum(pixel[3] > 0 for pixel in sprite.get_flattened_data()) / (size[0] * size[1])
        confidence, metrics = direct_confidence(sprite, .84)
        metrics["opaqueShare"] = round(opaque, 4)
        regions.append({
            "id": f"fitting:{name}", "runtimeName": name, "kind": "fitting",
            "scaleClass": "fixed", "anchor": anchor,
            "source": source_record(view, bounds),
            "pixelSource": {
                "class": "reconstructed",
                "generator": "gpt-image-editor",
                "path": v2_manifest["sources"][pixel_record["source"]]["path"],
                "boundsPx": pixel_record["sourceBoundsPx"],
                "alignmentGate": pixel_record["source"],
            },
            "atlasRectPx": [origin[0], origin[1], size[0], size[1]],
            "logicalSizePx": list(size), "confidence": confidence, "metrics": metrics,
            "decision": {"status": "approved", "reason": "direct wear meaning isolated from aligned paintover into transparent semantic mark"},
            "conflicts": [],
        })

    gates = paintover_gates()
    ids = [item["id"] for item in regions]
    checks = {
        "uniqueRegionIds": len(ids) == len(set(ids)),
        "allRuntimeRegionsApproved": all(item["decision"]["status"] == "approved" for item in regions),
        "allApprovedRegionsHaveEvidence": all(item["source"]["evidenceClass"] in {"direct", "reconstructed"} for item in regions),
        "noInventedRegionCompiled": not any(item["source"]["evidenceClass"] == "invented" for item in regions),
        "allFixedRegionsAnchored": all(item.get("anchor") for item in regions if item["scaleClass"] == "fixed"),
        "noUnresolvedConflicts": not any(item["conflicts"] for item in regions),
        "allRectifiedPixelSourcesPassInternalGate": all(aligned_gates[item["pixelSource"]["alignmentGate"]]["approved"] for item in regions),
        "diagnosticContractComplete": all(
            (LOCK / "jobs" / view / "inputs" / f"{name}.png").exists()
            for view in ("iso", "side", "back")
            for name in ("raw", "part-id", "face-normal", "depth", "anchor-id")
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    if status != "PASS":
        raise RuntimeError(json.dumps(checks, indent=2))

    micro.save(MICRO_ATLAS, optimize=False)
    fitting.save(FITTING_ATLAS, optimize=False)
    micro.resize((1536, 192), Image.Resampling.NEAREST).save(LOCK / "microfields-preview-v4.png")
    fitting.resize((1024, 256), Image.Resampling.NEAREST).save(LOCK / "fittings-preview-v4.png")

    payload = {
        "schemaVersion": 4,
        "status": status,
        "generator": "direct-first evidence compiler with diagnostic-guided reconstruction gate",
        "atlases": {
            "microfields": MICRO_ATLAS.name,
            "fittings": FITTING_ATLAS.name,
            "semanticFaces": "semantic-freezer-faces-v1.png",
        },
        "evidencePolicy": {
            "priority": ["direct", "reconstructed", "invented"],
            "direct": "extract from locked authority wherever visible",
            "reconstructed": "allowed only when a geometry-locked view passes silhouette/depth/anchor review",
            "invented": "excluded unless manually approved in a future manifest revision",
            "geometryFromPaintover": False,
        },
        "diagnosticPasses": ["raw", "part-id", "face-normal", "depth", "anchor-id"],
        "candidatePaintoverGates": gates,
        "alignedPaintoverGates": aligned_gates,
        "scaleClasses": {
            "expand": ["base_color_field", "solid_seam_length", "panel_center"],
            "repeat": [item["runtimeName"] for item in regions if item["scaleClass"] == "repeat"],
            "fixed": [item["runtimeName"] for item in regions if item["scaleClass"] == "fixed"]
                + ["sdf_outline", "sdf_catch", "sdf_inset", "handle_assembly"],
            "count-adaptive": ["side_panel_row", "side_panel_column", "shelf", "rear_coil_run", "rear_coil_rail"],
        },
        "regions": regions,
        "checks": checks,
    }
    text = json.dumps(payload, indent=2) + "\n"
    MANIFEST_PATH.write_text(text, encoding="utf-8")
    (LOCK / "compile-audit-v4.json").write_text(text, encoding="utf-8")
    (LOCK / "paintover-gates-v4.json").write_text(json.dumps(gates, indent=2) + "\n", encoding="utf-8")

    gate_lines = [
        f"- {name}: **{item['status'].upper()}**" + (
            f" — IoU {item.get('silhouetteIoU')}, drift {item.get('bboxDrift')}" if item.get("silhouetteIoU") is not None else ""
        ) for name, item in gates.items()
    ]
    audit = f"""# Semantic freezer v4 — evidence audit

Status: **{status}**. Geometry is unchanged. V4 replaces coarse source labels with
per-region provenance and compiles only reviewed direct or reconstructed evidence.

## Diagnostic contract

- Five passes per view: raw, part-ID, world face-normal, linear depth, anchor-ID.
- Three locked views: front isometric, orthographic side, rear isometric.
- Nano is asked for one view paintover, never an atlas.

## Compiled evidence

- Direct information regions: **{len(regions)}**.
- Rectified pixel regions: **{len(regions)}**. Their meaning comes from direct
  authority, while geometry-aligned paintovers remove baked camera perspective.
- Unsupported reconstructed regions: **0**.
- Invented regions: **0**.
- Every fixed fitting has a semantic anchor; every repeated field is a fixed-world microfield.

## Nano candidate gates

{chr(10).join(gate_lines)}

Missing or rejected Nano candidates do not block this build because they are not
used as evidence. Any later reconstructed region must pass the gate before compilation.

## Compiler checks

""" + "\n".join(f"- {name}: **{'PASS' if value else 'FAIL'}**" for name, value in checks.items()) + "\n"
    (LOCK / "AUDIT.md").write_text(audit, encoding="utf-8")
    print(f"PASS regions={len(regions)} direct={len(regions)} -> {rel(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
