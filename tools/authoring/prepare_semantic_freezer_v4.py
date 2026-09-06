"""Render and package evidence-first Nano Banana paintover jobs for freezer v4.

The image model is never asked for an atlas. Each job contains an immutable raw
render plus four diagnostic passes and reference authority. A later compiler
may extract only reviewed regions from the returned view paintover.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v4"
DIAGNOSTICS = LOCK / "diagnostics"
AUTHORITY = LOCK / "authority"
JOBS = LOCK / "jobs"
SOURCE_AUTHORITY = Path(
    r"C:\Users\mansour\Documents\Modular builder\Gemini version builder\img_gen"
)

VIEWS = {
    "iso": {
        "renderView": "iso",
        "authority": "ref_front_view.png",
        "support": ["ref_right_side_view.png", "ref_back_view.png"],
        "visible": "front, open cavity, roof, and right service side",
    },
    "side": {
        "renderView": "side",
        "authority": "ref_right_side_view.png",
        "support": ["ref_front_view.png", "ref_back_view.png"],
        "visible": "orthographic service side only",
    },
    "back": {
        "renderView": "backIso",
        "authority": "ref_back_view.png",
        "support": ["ref_right_side_view.png", "ref_front_view.png"],
        "visible": "rear machinery, condenser, roof, and right service side",
    },
}

PASS_QUERIES = {
    "raw": "",
    "part-id": "&diagnostic=part-id",
    "face-normal": "&diagnostic=face-normal",
    "depth": "&diagnostic=linear-depth",
    "anchor-id": "&diagnostic=anchor-id",
}

COMMON_PROMPT = """Use case: precise-object-edit
Asset type: geometry-locked surface paintover for evidence extraction; never an atlas or final model.

INPUT CONTRACT — obey image roles exactly:
- Image 1 RAW TARGET is the only editable raster. Its camera, framing, silhouette, depth ordering, openings, shelves, contents, handle, vents, condenser, machinery, panel divisions, and every part boundary are immutable.
- Image 2 MATCHING AUTHORITY is direct visual evidence for colors, labels, wear placement, pixel density, and material language.
- Images 3–4 CROSS-VIEW AUTHORITIES may resolve material identity only. Do not copy their camera, silhouette, or hidden structure.
- Image 5 PART-ID identifies immutable physical parts. Never merge colors across different IDs and never invent an ID.
- Image 6 FACE-NORMAL encodes face orientation. Painted marks must remain on one physically valid face and may not cross a normal discontinuity.
- Image 7 LINEAR DEPTH encodes occlusion. Never paint through an occluder or move a boundary to expose hidden material.
- Image 8 ANCHOR-ID divides each visible face into fixed corner/edge/center regions. Preserve meaningful fittings at their evidenced anchor.

PAINTING TASK:
Paint only the visible surfaces in Image 1 using evidence from the authority images. Match the authority's retro PS1-era pixel-textured material language: crisp small square texels, quantized cool grey-green enamel, blue-grey service panels, dark construction seams, deliberate clustered edge wear, sparse one-to-four-pixel catches, and readable fixed labels where directly evidenced. Large faces need restrained material response, not random dirt.

HARD LOCKS:
- Preserve Image 1 pixel dimensions and every object boundary within one pixel.
- Preserve pure flat #FF00FF outside the object, with no shadow, halo, scenery, caption, legend, watermark, or antialiasing.
- Paint only existing surfaces. Do not add, remove, move, resize, round, straighten, or reinterpret geometry.
- Do not invent vents, screws, handles, hinges, labels, products, cables, panel seams, or mechanical structure.
- Do not bake perspective changes, new illumination, cast shadows, ambient occlusion, or soft gradients.
- Existing repeated depth-bearing parts remain geometry; only their surface material may be painted.
- If evidence is absent or conflicts between views, leave that region as the raw target color.

OUTPUT:
Return exactly one geometry-locked paintover of Image 1, same view and framing, on pure #FF00FF. No atlas and no alternate view.
"""


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def image_record(path: Path, role: str) -> dict:
    with Image.open(path) as image:
        size = list(image.size)
    return {"role": role, "path": rel(path), "sizePx": size, "sha256": digest(path)}


def normalized_pass(source: Path, target: Path) -> Path:
    """Letterbox a diagnostic to Nano's square canvas without deforming it."""
    with Image.open(source).convert("RGB") as image:
        scale = min(1024 / image.width, 1024 / image.height)
        size = (round(image.width * scale), round(image.height * scale))
        resized = image.resize(size, Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (1024, 1024), (255, 0, 255))
    canvas.paste(resized, ((1024 - size[0]) // 2, (1024 - size[1]) // 2))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, optimize=False)
    return target


def copy_authority() -> None:
    AUTHORITY.mkdir(parents=True, exist_ok=True)
    for name in {item for view in VIEWS.values() for item in [view["authority"], *view["support"]]}:
        source = SOURCE_AUTHORITY / name
        if not source.exists():
            raise FileNotFoundError(source)
        target = AUTHORITY / name
        if not target.exists() or digest(target) != digest(source):
            shutil.copyfile(source, target)


def render_diagnostics() -> dict:
    DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    queries = []
    for view in VIEWS.values():
        base = (
            f"view={view['renderView']}&texture=v3&surfaces=0&fittings=0"
            "&bg=magenta&fit=1"
        )
        queries.extend(base + suffix for suffix in PASS_QUERIES.values())
    subprocess.run(
        ["node", "tools/semantic-freezer/shoot.mjs", str(DIAGNOSTICS), *queries],
        cwd=ROOT,
        check=True,
    )
    audit = json.loads((DIAGNOSTICS / "audit.json").read_text(encoding="utf-8"))
    if audit["status"] != "PASS":
        raise RuntimeError("diagnostic render audit failed")
    return audit


def record_for(audit: dict, render_view: str, pass_name: str) -> dict:
    expected = PASS_QUERIES[pass_name].removeprefix("&diagnostic=") if pass_name != "raw" else ""
    for item in audit["records"]:
        if item["view"] == render_view and item.get("diagnostic", "") == expected:
            return item
    raise KeyError(f"missing diagnostic {render_view}:{pass_name}")


def build_jobs(audit: dict) -> dict:
    JOBS.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 4,
        "model": "gemini-3.1-flash-image",
        "policy": {
            "directFirst": True,
            "paintSpecificViewsNotAtlases": True,
            "geometryIsImmutable": True,
            "unsupportedHiddenStructure": "exclude",
            "requiredPasses": list(PASS_QUERIES),
        },
        "views": {},
    }
    for name, view in VIEWS.items():
        view_dir = JOBS / name
        view_dir.mkdir(parents=True, exist_ok=True)
        prompt = COMMON_PROMPT + f"\nVIEW SCOPE: Paint {view['visible']}.\n"
        prompt_path = view_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        matching = AUTHORITY / view["authority"]
        support = [AUTHORITY / item for item in view["support"]]
        ordered = []
        for role, pass_name in [
            ("raw-target", "raw"),
            ("matching-authority", None),
            ("cross-view-authority-a", None),
            ("cross-view-authority-b", None),
            ("part-id", "part-id"),
            ("face-normal", "face-normal"),
            ("linear-depth", "depth"),
            ("anchor-id", "anchor-id"),
        ]:
            if role == "matching-authority":
                path = matching
            elif role == "cross-view-authority-a":
                path = support[0]
            elif role == "cross-view-authority-b":
                path = support[1]
            else:
                rendered = Path(record_for(audit, view["renderView"], pass_name)["output"])
                path = normalized_pass(rendered, view_dir / "inputs" / f"{pass_name}.png")
            ordered.append(image_record(path, role))

        job = {
            "id": f"semantic-freezer-v4-{name}",
            "view": name,
            "renderView": view["renderView"],
            "prompt": rel(prompt_path),
            "inputsInOrder": ordered,
            "output": rel(LOCK / "paintovers" / f"{name}-paintover-nano.png"),
            "approval": "pending",
        }
        (view_dir / "job.json").write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
        manifest["views"][name] = job

    path = LOCK / "paintover-jobs-v4.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    LOCK.mkdir(parents=True, exist_ok=True)
    copy_authority()
    if args.skip_render:
        audit = json.loads((DIAGNOSTICS / "audit.json").read_text(encoding="utf-8"))
    else:
        audit = render_diagnostics()
    manifest = build_jobs(audit)
    print(f"PASS {len(manifest['views'])} evidence jobs -> {rel(LOCK / 'paintover-jobs-v4.json')}")


if __name__ == "__main__":
    main()
