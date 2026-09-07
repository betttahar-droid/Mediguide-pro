#!/usr/bin/env python3
"""A second opinion, from the other model family, on the same renders.

Authoring tool. NOT a build, CI or runtime dependency.

WHY A SECOND JUDGE. glm-5.3-flash has graded every prop in this tool, and a
single grader is a single set of blind spots: it passed a prop while listing
"duplicated content blocks that read as a bug" in the same reply, and it has
never once objected to the geometry, because it was never shown any. Two
graders from different families disagree in different places, and a fault
either of them calls blocking is blocking. That is strictly harsher than one,
and it costs one call.

Gemini is already in this pipeline drawing sheets and segmentation maps, so it
is the natural second pair of eyes and needs no new credential. It is asked the
same question in the same schema, so the loop consumes both identically.
"""
import base64
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import ENDPOINT, MIME, load_key  # noqa: E402

# text-out models, tried in order: the image model answers text too, but a
# dedicated one is steadier at long structured replies
MODELS = ("gemini-flash-latest", "gemini-2.5-flash", "gemini-3.1-flash-image")


def vision_json(prompt, images, key=None, models=MODELS, timeout=180):
    """Ask Gemini about some images and get JSON back."""
    key = key or load_key()
    parts = []
    for img in images:
        path = Path(img)
        parts.append({"inline_data": {
            "mime_type": MIME.get(path.suffix.lower(), "image/png"),
            "data": base64.b64encode(path.read_bytes()).decode(),
        }})
    parts.append({"text": prompt})
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT"],
                             "maxOutputTokens": 4096, "temperature": 0.2},
    }).encode()

    last = None
    for model in models:
        try:
            req = urllib.request.Request(
                ENDPOINT.format(model=model) + f"?key={key}",
                data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.load(r)
            text = ""
            for cand in payload.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    text += part.get("text", "")
            if not text.strip():
                last = RuntimeError(f"{model}: empty reply")
                continue
            m = re.search(r"\{.*\}", text, re.S)
            if not m:
                last = RuntimeError(f"{model}: no JSON in reply")
                continue
            return json.loads(m.group(0)), model
        except Exception as e:                       # try the next model
            last = e
    raise RuntimeError(f"gemini vision failed: {last}")


if __name__ == "__main__":
    got, model = vision_json(
        'Describe this image in one short sentence. JSON only: {"desc": "..."}',
        [sys.argv[1]])
    print(model, got)
