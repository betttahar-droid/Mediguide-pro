"""Run geometry-registered freezer v5 feature-island jobs through Nano Banana."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error

from PIL import Image

from concept_sheet import generate_image, load_key, MODEL

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/reference-lock/semantic-freezer-v5"
JOBS = LOCK / "nano-feature-jobs-v5.json"
RESULTS = LOCK / "nano-feature-results-v5.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("features", nargs="*")
    args = parser.parse_args()
    manifest = json.loads(JOBS.read_text(encoding="utf-8"))
    known = {job["id"] for job in manifest["jobs"]}
    unknown = set(args.features) - known
    if unknown:
        parser.error(f"unknown features: {', '.join(sorted(unknown))}")
    selected = set(args.features) or known
    results = {
        "schemaVersion": 5, "model": MODEL,
        "generatedAt": datetime.now(timezone.utc).isoformat(), "features": {},
    }
    key = load_key()
    for job in manifest["jobs"]:
        if job["id"] not in selected:
            continue
        output = ROOT / job["output"]
        result = {"status": "failed", "output": job["output"]}
        try:
            generate_image(
                (ROOT / job["prompt"]).read_text(encoding="utf-8"), output, key,
                refs=tuple(ROOT / item for item in job["inputsInOrder"]), model=MODEL,
                ref_instruction=(
                    "Images 1 and 2 lock the canvas and editable island. Images 3 and 4 "
                    "are evidence only. Change pixels only inside the white edit mask."
                ),
            )
            with Image.open(output) as image:
                result.update({"status": "generated", "sizePx": list(image.size)})
            print(f"PASS {job['id']} -> {job['output']}")
        except urllib.error.HTTPError as exc:
            result.update({"errorType": "http", "httpStatus": exc.code, "message": str(exc)})
            print(f"FAILED {job['id']}: HTTP {exc.code}")
        except Exception as exc:
            result.update({"errorType": type(exc).__name__, "message": str(exc)})
            print(f"FAILED {job['id']}: {exc}")
        results["features"][job["id"]] = result
        RESULTS.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    if not any(item["status"] == "generated" for item in results["features"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
