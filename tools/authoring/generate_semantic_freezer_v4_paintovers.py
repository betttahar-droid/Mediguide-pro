"""Run prepared semantic-freezer v4 view jobs through Nano Banana 2."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import urllib.error

from PIL import Image

from concept_sheet import generate_image, load_key, MODEL


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v4"
JOBS = LOCK / "paintover-jobs-v4.json"
RESULTS = LOCK / "paintover-results-v4.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("views", nargs="*")
    args = parser.parse_args()
    unknown = set(args.views) - {"iso", "side", "back"}
    if unknown:
        parser.error(f"unknown views: {', '.join(sorted(unknown))}")
    manifest = json.loads(JOBS.read_text(encoding="utf-8"))
    selected = set(args.views) or set(manifest["views"])
    key = load_key()
    results = {
        "schemaVersion": 4,
        "model": MODEL,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "views": {},
    }

    for name, job in manifest["views"].items():
        if name not in selected:
            continue
        prompt = (ROOT / job["prompt"]).read_text(encoding="utf-8")
        refs = tuple(ROOT / item["path"] for item in job["inputsInOrder"])
        output = ROOT / job["output"]
        result = {"status": "failed", "output": job["output"]}
        try:
            generate_image(
                prompt,
                output,
                key,
                refs=refs,
                model=MODEL,
                ref_instruction=(
                    "The eight input images have strict roles defined in the prompt. "
                    "Edit Image 1 only; use Images 2-8 solely as evidence and constraints."
                ),
            )
            with Image.open(output) as image:
                size = list(image.size)
            result.update({"status": "generated", "sizePx": size, "sha256": digest(output)})
            print(f"PASS {name} -> {job['output']}")
        except urllib.error.HTTPError as exc:
            result.update({"errorType": "http", "httpStatus": exc.code, "message": str(exc)})
            print(f"FAILED {name}: HTTP {exc.code}")
        except Exception as exc:  # keep other view jobs available for review
            result.update({"errorType": type(exc).__name__, "message": str(exc)})
            print(f"FAILED {name}: {exc}")
        results["views"][name] = result
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        RESULTS.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    if not any(item["status"] == "generated" for item in results["views"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
