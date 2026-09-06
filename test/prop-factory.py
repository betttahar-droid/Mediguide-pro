"""Unit and regression tests for the deterministic prop factory."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/prop-factory/prop_factory.py"
SPEC_PATH = ROOT / "tools/prop-factory/examples/semantic-freezer/asset-spec.json"
RUNTIME_PATH = ROOT / "docs/reference-lock/semantic-freezer-v7/factory-runtime/audit.json"

module_spec = importlib.util.spec_from_file_location("prop_factory", MODULE_PATH)
factory = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(factory)

source = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
compiled = factory.compile_spec(source)
assert compiled["status"] == "PASS"
assert len(compiled["cases"]) == 4

base = next(case for case in compiled["cases"] if case["id"] == "base")
width = next(case for case in compiled["cases"] if case["id"] == "width")
height = next(case for case in compiled["cases"] if case["id"] == "height")
base_field = base["adaptiveFields"][0]
assert factory.close_list(base_field["sizeTexels"], [38.828, 71.154])
assert base_field["repeatCounts"] == [15, 8]
assert width["adaptiveFields"][0]["repeatCounts"] == [23, 8]
assert height["adaptiveFields"][0]["repeatCounts"] == [15, 12]

runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
audit = factory.audit_runtime(compiled, runtime)
assert audit["status"] == "PASS"
assert not audit["mismatches"]
assert len(audit["visualEvidence"]) == 4

broken = copy.deepcopy(runtime)
vent = next(item for item in broken["records"][0]["fittingPlacements"] if item["id"] == "sideVentPanel")
vent["centerTexels"][0] += 2
failed = factory.audit_runtime(compiled, broken)
assert failed["status"] == "FAIL"
assert any(item.get("fitting") == "sideVentPanel" for item in failed["mismatches"])

invalid = copy.deepcopy(source)
invalid["scaleCases"] = [case for case in invalid["scaleCases"] if case["id"] != "depth"]
try:
    factory.validate(invalid)
except factory.SpecError:
    pass
else:
    raise AssertionError("missing independent depth scale case was accepted")

with tempfile.TemporaryDirectory(prefix="prop-factory-test-") as directory:
    destination = Path(directory) / "cheap-prop"
    factory.command_init(SimpleNamespace(id="cheap-prop", label="Cheap Prop", out=str(destination)))
    assert (destination / "asset-spec.json").exists()
    assert (destination / "model.js").exists()
    assert (destination / "README.md").exists()
    scaffold = json.loads((destination / "asset-spec.json").read_text(encoding="utf-8"))
    assert scaffold["runtime"]["rendererScript"] == "SET_RENDERER_SCRIPT"
    assert scaffold["runtime"]["outputDir"].endswith("cheap-prop/audit-runtime")

print("PASS prop factory: compile, scale contracts, pixel probes, failure localization")
