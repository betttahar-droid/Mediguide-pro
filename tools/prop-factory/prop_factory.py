"""Deterministic compiler and auditor for affordable adaptive retro props."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).resolve().parent / "templates" / "asset-spec.template.json"
MODEL_TEMPLATE = Path(__file__).resolve().parent / "templates" / "model.template.js"
TOLERANCE = 1e-5


class SpecError(ValueError):
    pass


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpecError(f"Cannot read JSON {path}: {error}") from error


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise SpecError(message)


def validate(spec):
    require(spec.get("schemaVersion") == 1, "schemaVersion must be 1")
    require(spec.get("asset", {}).get("id"), "asset.id is required")
    dimensions = spec.get("dimensions", {})
    for axis in ("width", "depth", "height"):
        require(isinstance(dimensions.get(axis), (int, float)) and dimensions[axis] > 0,
                f"dimensions.{axis} must be positive")
    require(spec.get("texelWorldSize", 0) > 0, "texelWorldSize must be positive")
    cases = spec.get("scaleCases", [])
    require(any(case.get("scale") == [1, 1, 1] for case in cases), "scaleCases must contain [1,1,1]")
    require(len({case.get("id") for case in cases}) == len(cases), "scale case ids must be unique")
    for case in cases:
        require(len(case.get("scale", [])) == 3 and min(case["scale"]) > 0, f"invalid scale case {case.get('id')}")
    for axis in range(3):
        require(any(case["scale"][axis] != 1 and all(case["scale"][other] == 1 for other in range(3) if other != axis) for case in cases),
                f"scaleCases must change axis {axis} independently")
    require(set(spec.get("faceBasis", {})) == {"front", "back", "left", "right", "top"}, "faceBasis must define all five visible faces")
    field_ids = set()
    for field in spec.get("adaptiveFields", []):
        require(field.get("id") not in field_ids, f"duplicate adaptive field {field.get('id')}")
        field_ids.add(field.get("id"))
        repeat = field.get("repeat", {})
        for key in ("uPitchTexels", "vPitchTexels", "uLineWidthTexels", "vLineWidthTexels"):
            require(repeat.get(key, 0) > 0, f"{field.get('id')}.repeat.{key} must be positive")
        require(repeat["uLineWidthTexels"] < repeat["uPitchTexels"], f"{field.get('id')} u line width must be smaller than pitch")
        require(repeat["vLineWidthTexels"] < repeat["vPitchTexels"], f"{field.get('id')} v line width must be smaller than pitch")
    fitting_ids = set()
    for item in spec.get("fixedFittings", []):
        require(item.get("id") not in fitting_ids, f"duplicate fixed fitting {item.get('id')}")
        fitting_ids.add(item.get("id"))
        require(item.get("face") in {"front", "back", "left", "right", "top"}, f"invalid face for {item.get('id')}")
        require(len(item.get("sizeTexels", [])) == 2 and min(item["sizeTexels"]) > 0, f"invalid size for {item.get('id')}")
        require(item.get("uAnchor"), f"uAnchor required for {item.get('id')}")
        require(item.get("zAnchor"), f"zAnchor required for {item.get('id')}")
    layer_order = spec.get("layers", {}).get("order", [])
    require(len(layer_order) == len(set(layer_order)) and layer_order, "layers.order must be non-empty and unique")
    require(set(layer_order) == set(spec.get("layers", {}).get("renderOrder", {})), "layers.renderOrder must cover every layer")
    for item in [*spec.get("adaptiveFields", []), *spec.get("fixedFittings", [])]:
        require(item.get("layer") in layer_order, f"unknown layer {item.get('layer')} on {item.get('id')}")
    for item in spec.get("fixedFittings", []):
        for anchor_name in ("uAnchor", "zAnchor"):
            anchor = item[anchor_name]
            require("fraction" not in anchor and "percentage" not in anchor, f"{item['id']} may not use proportional placement")
            if anchor.get("field"):
                require(anchor["field"] in field_ids, f"{item['id']} references unknown field {anchor['field']}")
    return spec


def scaled_dimensions(spec, scale):
    source = spec["dimensions"]
    return {
        "width": source["width"] * scale[0],
        "depth": source["depth"] * scale[1],
        "height": source["height"] * scale[2],
    }


def resolve_references(spec, dimensions):
    result = {"bottom": 0.0}
    for name, rule in spec.get("references", {}).items():
        result[name] = dimensions[rule["axis"]] * rule.get("factor", 1) + rule.get("offsetTexels", 0)
    return result


def resolve_field(item, dimensions, references):
    horizontal = item["horizontal"]
    vertical = item["vertical"]
    left = -dimensions["width"] / 2 + horizontal["leftMarginTexels"]
    right = dimensions["width"] / 2 - horizontal["rightMarginTexels"]
    bottom = vertical["bottomTexels"]
    top = references[vertical["topReference"]] - vertical["topMarginTexels"]
    width, height = right - left, top - bottom
    minimum = item.get("minimumSizeTexels", [0, 0])
    require(width >= minimum[0] and height >= minimum[1], f"{item['id']} does not fit at this scale")
    repeat = item["repeat"]
    return {
        "id": item["id"], "face": item["face"], "layer": item["layer"],
        "boundsTexels": [left, bottom, right, top],
        "centerTexels": [(left + right) / 2, (bottom + top) / 2],
        "sizeTexels": [width, height],
        "pitchTexels": [repeat["uPitchTexels"], repeat["vPitchTexels"]],
        "lineWidthTexels": [repeat["uLineWidthTexels"], repeat["vLineWidthTexels"]],
        "repeatCounts": [math.floor(width / repeat["uPitchTexels"]), math.floor(height / repeat["vPitchTexels"])],
        "marginsTexels": [horizontal["leftMarginTexels"], horizontal["rightMarginTexels"],
                            vertical["bottomTexels"], vertical["topMarginTexels"]],
        "renderOrder": spec_render_order(item),
        "visualProbe": item.get("visualProbe"),
    }


def spec_render_order(item):
    return item.get("renderOrder", 0)


def resolve_u(anchor, face, dimensions, fields):
    span = dimensions["depth"] if face in {"left", "right"} else dimensions["width"]
    if anchor.get("edge") == "front":
        return -span / 2 + anchor["offsetTexels"]
    if anchor.get("edge") == "back":
        return span / 2 - anchor["offsetTexels"]
    if anchor.get("edge") == "left":
        return -span / 2 + anchor["offsetTexels"]
    if anchor.get("edge") == "right":
        return span / 2 - anchor["offsetTexels"]
    if anchor.get("edge") == "center" and "field" not in anchor:
        return anchor.get("offsetTexels", 0)
    if anchor.get("field"):
        field = fields[anchor["field"]]
        edge_index = {"left": 0, "right": 2}.get(anchor.get("edge"))
        base = field["centerTexels"][0] if anchor.get("edge") == "center" else field["boundsTexels"][edge_index]
        direction = -1 if anchor.get("edge") == "right" else 1
        return base + direction * anchor.get("offsetTexels", 0)
    raise SpecError(f"unsupported horizontal anchor: {anchor}")


def resolve_z(anchor, references, fields):
    if anchor.get("field"):
        field = fields[anchor["field"]]
        if anchor.get("edge") == "top":
            return field["boundsTexels"][3] - anchor.get("offsetTexels", 0)
        if anchor.get("edge") == "bottom":
            return field["boundsTexels"][1] + anchor.get("offsetTexels", 0)
        if anchor.get("edge") == "center":
            return field["centerTexels"][1] + anchor.get("offsetTexels", 0)
    if anchor.get("reference"):
        base = references[anchor["reference"]]
        return base - anchor.get("offsetTexels", 0) if anchor.get("edge") == "top" else base + anchor.get("offsetTexels", 0)
    if anchor.get("edge") == "bottom":
        return anchor.get("centerTexels", anchor.get("offsetTexels", 0))
    raise SpecError(f"unsupported vertical anchor: {anchor}")


def compile_spec(spec):
    validate(spec)
    cases = []
    for case in spec["scaleCases"]:
        dimensions = scaled_dimensions(spec, case["scale"])
        references = resolve_references(spec, dimensions)
        fields = {}
        for item in spec.get("adaptiveFields", []):
            resolved = resolve_field(item, dimensions, references)
            resolved["renderOrder"] = spec["layers"]["renderOrder"][item["layer"]]
            fields[item["id"]] = resolved
        fittings = {}
        for item in spec.get("fixedFittings", []):
            fittings[item["id"]] = {
                "id": item["id"], "runtimeId": item.get("runtimeId", item["id"]),
                "face": item["face"], "layer": item["layer"], "sizeTexels": item["sizeTexels"],
                "centerTexels": [resolve_u(item["uAnchor"], item["face"], dimensions, fields),
                                  resolve_z(item["zAnchor"], references, fields)],
                "renderOrder": spec["layers"]["renderOrder"][item["layer"]],
            }
        cases.append({
            "id": case["id"], "scale": case["scale"], "dimensions": dimensions,
            "references": references, "adaptiveFields": list(fields.values()),
            "fixedFittings": list(fittings.values()),
        })
    return {
        "compiler": "prop-factory-v1", "schemaVersion": 1, "status": "PASS",
        "asset": spec["asset"], "texelWorldSize": spec["texelWorldSize"],
        "faceBasis": spec.get("faceBasis", {}), "layers": spec["layers"],
        "visualAudit": spec.get("visualAudit"),
        "correspondenceIds": sorted(spec.get("correspondenceIds", [])),
        "fixedGeometryRoles": sorted(spec.get("fixedGeometryRoles", [])),
        "overlapRules": spec.get("overlapRules", []), "cases": cases,
    }


def close_list(actual, expected, tolerance=TOLERANCE):
    return len(actual) == len(expected) and all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


def find_record(records, scale):
    return next((item for item in records if close_list(item.get("scale", []), scale)), None)


def find_runtime(items, identifier):
    return next((item for item in items if item.get("id") == identifier), None)


def frontmost(face, first_plane, second_plane):
    if face in {"front", "left"}:
        return first_plane < second_plane
    if face in {"back", "right", "top"}:
        return first_plane > second_plane
    return False


def dark_runs(values, expected_pitch, threshold):
    mask = [max(pixel) < threshold for pixel in values]
    centers, start = [], None
    for index, value in enumerate(mask + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            centers.append((start + index - 1) / 2)
            start = None
    spacings = [b - a for a, b in zip(centers, centers[1:]) if expected_pitch * .5 <= b - a <= expected_pitch * 1.5]
    return {"runs": len(centers), "medianPitchPixels": sorted(spacings)[len(spacings) // 2] if spacings else 0}


def project_x(value_texels, image_width, config, texel_world_size):
    half = config["orthographicWidth"] / config["zoom"] / 2
    return round(((value_texels * texel_world_size + half) / (2 * half)) * image_width)


def project_y(value_texels, image_height, config, texel_world_size, dimensions):
    half = config["orthographicHeight"] / config["zoom"] / 2
    target = dimensions["height"] * texel_world_size * config["targetHeightFactor"]
    return round(((half - (value_texels * texel_world_size - target)) / (2 * half)) * image_height)


def pixel_probe(compiled, expected_case, actual_record, expected_field, axis):
    config = compiled["visualAudit"]
    probe = expected_field.get("visualProbe") or {}
    image = Image.open(actual_record["output"]).convert("RGB")
    width, height = image.size
    left, bottom, right, top = expected_field["boundsTexels"]
    threshold = config.get("darkThreshold", 105)
    if axis == "u":
        row = project_y(probe["uScanAtVTexels"], height, config, compiled["texelWorldSize"], expected_case["dimensions"])
        x0 = max(0, project_x(left, width, config, compiled["texelWorldSize"]) + 3)
        x1 = min(width - 1, project_x(right, width, config, compiled["texelWorldSize"]) - 3)
        expected_pitch = expected_field["pitchTexels"][0] * compiled["texelWorldSize"] / (config["orthographicWidth"] / config["zoom"]) * width
        result = dark_runs([image.getpixel((x, row)) for x in range(x0, x1 + 1)], expected_pitch, threshold)
    else:
        column_texels = left + probe["vScanAtUOffsetTexels"]
        column = project_x(column_texels, width, config, compiled["texelWorldSize"])
        y0 = max(0, project_y(top, height, config, compiled["texelWorldSize"], expected_case["dimensions"]) + 3)
        y1 = min(height - 1, project_y(bottom, height, config, compiled["texelWorldSize"], expected_case["dimensions"]) - 3)
        expected_pitch = expected_field["pitchTexels"][1] * compiled["texelWorldSize"] / (config["orthographicHeight"] / config["zoom"]) * height
        result = dark_runs([image.getpixel((column, y)) for y in range(y0, y1 + 1)], expected_pitch, threshold)
    result.update({"axis": axis, "expectedPitchPixels": expected_pitch, "output": actual_record["output"]})
    return result


def audit_runtime(compiled, runtime):
    checks, details, visual_evidence = {}, [], []
    records = runtime.get("records", [])
    checks["runtimeProducedEveryScaleCase"] = len(records) >= len(compiled["cases"])
    base_record = find_record(records, [1, 1, 1])
    checks["baseRuntimeExists"] = base_record is not None
    for case in compiled["cases"]:
        actual = find_record(records, case["scale"])
        case_ok = actual is not None
        if actual:
            case_ok = case_ok and not actual.get("errors")
            for expected in case["adaptiveFields"]:
                observed = find_runtime(actual.get("adaptiveTexturePanels", []), expected["id"])
                ok = bool(observed) and all([
                    close_list(observed["sizeTexels"], expected["sizeTexels"]),
                    close_list(observed["pitchTexels"], expected["pitchTexels"]),
                    close_list(observed["lineWidthTexels"], expected["lineWidthTexels"]),
                    observed["repeatCounts"] == expected["repeatCounts"],
                    close_list(observed["marginsTexels"], expected["marginsTexels"]),
                    observed.get("layer") == expected["layer"],
                ])
                case_ok = case_ok and ok
                if not ok:
                    details.append({"case": case["id"], "field": expected["id"], "expected": expected, "actual": observed})
            for expected in case["fixedFittings"]:
                observed = find_runtime(actual.get("fittingPlacements", []), expected["runtimeId"])
                ok = bool(observed) and close_list(observed["centerTexels"], expected["centerTexels"]) \
                    and close_list(observed["sizeTexels"], expected["sizeTexels"]) \
                    and observed.get("face") == expected["face"] and observed.get("layer") == expected["layer"]
                case_ok = case_ok and ok
                if not ok:
                    details.append({"case": case["id"], "fitting": expected["id"], "expected": expected, "actual": observed})
        checks[f"case:{case['id']}"] = case_ok
    if base_record:
        checks["allCorrespondencesConsumed"] = sorted(base_record.get("correspondenceIds", [])) == compiled["correspondenceIds"]
        checks["faceBasisMatches"] = base_record.get("faceBasis") == compiled["faceBasis"]
        checks["textureLayersMatch"] = base_record.get("textureLayers") == compiled["layers"]["order"]
        checks["fixedFittingSizesInvariant"] = all(item.get("fixedFittingSizes") == base_record.get("fixedFittingSizes") for item in records)
        checks["fixedGeometryInvariant"] = all(item.get("rigidPartSizes") == base_record.get("rigidPartSizes") for item in records)
        for rule in compiled.get("overlapRules", []):
            front = find_runtime(base_record.get("fittingPlacements", []), rule["frontmost"])
            behind = find_runtime(base_record.get("fittingPlacements", []), rule["behind"])
            checks[f"overlap:{rule['frontmost']}>{rule['behind']}"] = bool(front and behind) and frontmost(rule["face"], front["planeTexels"], behind["planeTexels"])
    if compiled.get("visualAudit"):
        base_case = next(case for case in compiled["cases"] if case["scale"] == [1, 1, 1])
        width_case = next(case for case in compiled["cases"] if case["scale"][0] != 1 and case["scale"][1:] == [1, 1])
        height_case = next(case for case in compiled["cases"] if case["scale"][2] != 1 and case["scale"][:2] == [1, 1])
        visual_results = []
        for expected_field in base_case["adaptiveFields"]:
            if not expected_field.get("visualProbe"):
                continue
            width_field = find_runtime(width_case["adaptiveFields"], expected_field["id"])
            height_field = find_runtime(height_case["adaptiveFields"], expected_field["id"])
            probes = [
                pixel_probe(compiled, base_case, find_record(records, base_case["scale"]), expected_field, "u"),
                pixel_probe(compiled, width_case, find_record(records, width_case["scale"]), width_field, "u"),
                pixel_probe(compiled, base_case, find_record(records, base_case["scale"]), expected_field, "v"),
                pixel_probe(compiled, height_case, find_record(records, height_case["scale"]), height_field, "v"),
            ]
            tolerance = compiled["visualAudit"].get("pitchTolerancePixels", 1.25)
            ok = all(probe["runs"] >= 3 and abs(probe["medianPitchPixels"] - probe["expectedPitchPixels"]) <= tolerance for probe in probes)
            ok = ok and abs(probes[0]["medianPitchPixels"] - probes[1]["medianPitchPixels"]) <= tolerance
            ok = ok and abs(probes[2]["medianPitchPixels"] - probes[3]["medianPitchPixels"]) <= tolerance
            checks[f"pixelFrequency:{expected_field['id']}"] = ok
            visual_results.extend(probes)
        visual_evidence.extend(visual_results)
    checks["runtimeClean"] = all(not item.get("errors") for item in records)
    return {
        "status": "PASS" if checks and all(checks.values()) else "FAIL",
        "checks": checks, "mismatches": details, "visualEvidence": visual_evidence,
    }


def audit_plan(spec, compiled):
    runtime = spec.get("runtime", {})
    renderer = runtime.get("rendererScript", "tools/semantic-freezer/shoot.mjs")
    output = runtime.get("outputDir", f"docs/reference-lock/{spec['asset']['id']}/audit-runtime")
    defaults = runtime.get("queryDefaults", {})
    query_prefix = "&".join(f"{key}={value}" for key, value in defaults.items())
    commands = [
        f"node {renderer} {output} "
        + " ".join(f'\"{query_prefix}&view={case.get("view", "iso")}'
                   + "".join(f'&{axis}={value}' for axis, value in zip(("sx", "sy", "sz"), case["scale"]) if value != 1)
                   + '\"' for case in spec["scaleCases"]),
        f"python tools/prop-factory/prop_factory.py audit --compiled <compiled-contract.json> --runtime {output}/audit.json",
    ]
    return {
        "assetId": spec["asset"]["id"], "scaleCases": [case["scale"] for case in compiled["cases"]],
        "requiredChecks": ["fixed-size", "edge-anchor", "adaptive-extent", "fixed-pitch", "repeat-count", "layer-order", "correspondence", "runtime-errors"],
        "commands": commands,
    }


def low_cost_tasks(spec, compiled):
    asset = spec["asset"]["label"]
    implementation_target = spec.get("implementationTarget", "model.js")
    field_ids = ", ".join(item["id"] for item in spec.get("adaptiveFields", [])) or "none"
    fitting_ids = ", ".join(item["id"] for item in spec.get("fixedFittings", [])) or "none"
    return f"""# Low-cost task pack — {asset}

Give one phase at a time to a small coding model. Do not send prior chat history, reference brainstorming, or failed generations.

## Shared contract

- Read `asset-spec.json` as authority. Do not invent measurements.
- Use axis-aligned low-poly structure. Small visual detail belongs in fixed decals or adaptive semantic fields.
- Never scale a fixed fitting. Never stretch repeated marks.
- Preserve the declared face basis and layer order.
- A phase is complete only when its deterministic command passes.

## Task 1 — geometry shell

Implement only the named structural masses and mounting planes in `{implementation_target}`. Use the dimensions and measured fractions from the spec. Do not write texture code. Return the changed file and triangle count.

## Task 2 — fixed fittings

Implement only these fixed fittings: {fitting_ids}. Resolve their positions from the compiled centers. Do not use face percentages. Report each resulting size and anchor edge.

## Task 3 — adaptive fields

Implement only these fields: {field_ids}. Bounds may expand, but pitch and line width must remain in texels. Scaling must increase repeat counts.

## Task 4 — correction

Read `runtime-audit.json`. Change only the items named in `mismatches`. Do not restyle passing regions or change measured constants.

## Completion gate

Run the compile, four independent scale renders, runtime audit, and project smoke tests. Stop only on `PASS`.
"""


def command_compile(args):
    spec = validate(load_json(Path(args.spec)))
    compiled = compile_spec(spec)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "asset-spec.json", spec)
    write_json(output / "compiled-contract.json", compiled)
    write_json(output / "audit-plan.json", audit_plan(spec, compiled))
    (output / "LOW-COST-TASKS.md").write_text(low_cost_tasks(spec, compiled), encoding="utf-8")
    print(f"PASS compiled {spec['asset']['id']} -> {output}")


def command_audit(args):
    compiled = load_json(Path(args.compiled))
    runtime = load_json(Path(args.runtime))
    result = audit_runtime(compiled, runtime)
    output = Path(args.out) if args.out else Path(args.runtime).with_name("prop-factory-audit.json")
    write_json(output, result)
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


def command_init(args):
    destination = Path(args.out)
    require(not destination.exists() or not any(destination.iterdir()), f"destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    spec = load_json(TEMPLATE)
    spec["asset"] = {"id": args.id, "label": args.label or args.id.replace("-", " ").title()}
    spec["runtime"]["outputDir"] = f"docs/reference-lock/{args.id}/audit-runtime"
    write_json(destination / "asset-spec.json", spec)
    shutil.copyfile(MODEL_TEMPLATE, destination / "model.js")
    (destination / "README.md").write_text(
        f"# {spec['asset']['label']}\n\n1. Replace template measurements in `asset-spec.json`.\n"
        "2. Run `python tools/prop-factory/prop_factory.py compile --spec asset-spec.json --out generated`.\n"
        "3. Give `generated/LOW-COST-TASKS.md` to a small coding model one task at a time.\n",
        encoding="utf-8",
    )
    print(f"PASS scaffolded {args.id} -> {destination}")


def render_queries(spec):
    defaults = spec.get("runtime", {}).get("queryDefaults", {})
    result = []
    for case in spec["scaleCases"]:
        values = {**defaults, "view": case.get("view", "iso")}
        for axis, value in zip(("sx", "sy", "sz"), case["scale"]):
            if value != 1:
                values[axis] = value
        result.append("&".join(f"{key}={value}" for key, value in values.items()))
    return result


def command_build(args):
    spec_path, output = Path(args.spec), Path(args.out)
    spec = validate(load_json(spec_path))
    compiled = compile_spec(spec)
    output.mkdir(parents=True, exist_ok=True)
    compiled_path = output / "compiled-contract.json"
    write_json(compiled_path, compiled)
    write_json(output / "asset-spec.json", spec)
    write_json(output / "audit-plan.json", audit_plan(spec, compiled))
    (output / "LOW-COST-TASKS.md").write_text(low_cost_tasks(spec, compiled), encoding="utf-8")
    runtime = spec.get("runtime", {})
    require(runtime.get("rendererScript") and runtime.get("outputDir"), "build requires runtime.rendererScript and runtime.outputDir")
    require(runtime["rendererScript"] != "SET_RENDERER_SCRIPT", "set runtime.rendererScript after connecting the model to a renderer")
    require((ROOT / runtime["rendererScript"]).exists(), f"renderer does not exist: {runtime['rendererScript']}")
    command = ["node", runtime["rendererScript"], runtime["outputDir"], *render_queries(spec)]
    rendered = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if rendered.returncode:
        print(rendered.stdout)
        print(rendered.stderr)
        raise SystemExit(rendered.returncode)
    runtime_path = ROOT / runtime["outputDir"] / "audit.json"
    result = audit_runtime(compiled, load_json(runtime_path))
    write_json(output / "runtime-audit.json", result)
    print(f"{result['status']} built {spec['asset']['id']} -> {output}")
    if result["status"] != "PASS":
        raise SystemExit(1)


def parser():
    result = argparse.ArgumentParser(description="Affordable deterministic adaptive-prop factory")
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="scaffold a new prop recipe")
    init.add_argument("--id", required=True)
    init.add_argument("--label")
    init.add_argument("--out", required=True)
    init.set_defaults(run=command_init)
    compile_command = commands.add_parser("compile", help="validate and compile an asset spec")
    compile_command.add_argument("--spec", required=True)
    compile_command.add_argument("--out", required=True)
    compile_command.set_defaults(run=command_compile)
    audit = commands.add_parser("audit", help="compare compiled contracts with runtime evidence")
    audit.add_argument("--compiled", required=True)
    audit.add_argument("--runtime", required=True)
    audit.add_argument("--out")
    audit.set_defaults(run=command_audit)
    build = commands.add_parser("build", help="compile, render all scale cases, and audit")
    build.add_argument("--spec", required=True)
    build.add_argument("--out", required=True)
    build.set_defaults(run=command_build)
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    try:
        arguments.run(arguments)
    except SpecError as error:
        print(f"FAIL {error}")
        raise SystemExit(1) from error
