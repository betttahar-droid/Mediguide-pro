#!/usr/bin/env python3
"""Route the reading and writing calls to a local Ollama instead of OpenRouter.

    export PROP_LLM_BACKEND=ollama
    export OLLAMA_URL=http://127.0.0.1:11434
    export LOCAL_TEXT_MODEL=qwen3:8b
    export LOCAL_VISION_MODEL=qwen2.5vl:7b

    python3 tools/authoring/local_llm.py --check

Authoring tool. NOT a build, CI or runtime dependency.

WHY IT IS A SEAM AND NOT A REWRITE. Every non-image model call in this project
goes through one of two functions -- `auto_prop.glm(messages, model, key)` for
chat and `gemini_judge.vision_json(prompt, images)` for a picture plus a schema
-- and fifteen tools call them without knowing what is behind. Ollama serves the
same OpenAI chat shape at /v1/chat/completions, images included as data URIs, so
the change is a base URL and a model name.

WHICH CALLS A LOCAL MODEL CAN SAFELY TAKE, which is the whole question and this
repo already has the answer written down in a different form.

The rule is "the model authors and names; arithmetic measures and verifies".
Where that holds, the reply is CHECKED before anything is built on it, and a
weaker model costs a retry rather than a bad prop:

    scale_rules      names where a taller prop gains body -- strip_slice then
                     verifies those rows are actually bare and drops the rest.
                     MEASURED TODAY: a free 8B vision model produced a usable
                     place on a prop where the paid model returned null, and
                     the prop's repeat score went +0.480 -> +0.102.
    region_parts     names which region is which fitting -- settle_parts,
                     feature_intent and the acceptance gate all re-check it.
    side/top_profile the traced outline is scored against the drawing by
                     geometry_audit, per prop, as a number.

Where nothing checks the reply, a weaker model degrades silently and you will
not find out from the logs:

    the two judges   nothing grades the grader. And they are already the weak
                     link on the paid models -- CLAUDE.md records both of them
                     scoring a cabinet with FIVE STACKED MARQUEES level with the
                     corrected cabinet beside it, and judge_bench puts both at
                     chance on the one fault class it can score. A local model
                     here is not obviously worse than what is there; it is
                     equally unmeasured, which is the real problem either way.

So: move the authored-and-verified calls local first. They are most of the
traffic and the arithmetic catches a bad answer. Keep whatever you trust for the
judges, or accept that the judge channel is unmeasured in both worlds.

MODEL SIZES THAT ACTUALLY FIT THE ASKS. These are not creative-writing calls;
they are "look at this elevation and name the fittings" and "reply in this JSON
schema". A 7-8B vision model does that. What it must do well is FOLLOW A SCHEMA,
because `as_json` throws away anything it cannot parse -- so prefer a model with
solid instruction-following over a bigger one that rambles, and keep the
temperature where the callers set it.

NO SILENT FALLBACK. If you asked for local and the local endpoint is down, this
raises rather than quietly billing OpenRouter, the same choice comfy_backend
makes for images and for the same reason.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp"}


def url():
    return os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def enabled():
    return os.environ.get("PROP_LLM_BACKEND", "").lower() in ("ollama", "local")


def text_model():
    return os.environ.get("LOCAL_TEXT_MODEL", "qwen3:8b")


def vision_model():
    return os.environ.get("LOCAL_VISION_MODEL", "qwen2.5vl:7b")


def installed(timeout=6):
    """(ok, [model names]) from the local server. Never raises."""
    try:
        with urllib.request.urlopen(f"{url()}/api/tags", timeout=timeout) as r:
            d = json.load(r)
        return True, [m["name"] for m in d.get("models", [])]
    except Exception as e:                                    # noqa: BLE001
        return False, [f"{type(e).__name__}: {str(e)[:90]}"]


def chat(messages, model=None, max_tokens=12000, temperature=0.3,
         has_images=False, timeout=600):
    """One completion, OpenAI shape, from the local server.

    `reasoning` is dropped: it is an OpenRouter routing hint and Ollama has no
    use for it. `num_ctx` is raised instead, because the real risk locally is
    the opposite one -- Ollama's default context is 4096 tokens and this
    project's prompts run to 7k characters with four images attached, so the
    default silently truncates the question rather than the answer.
    """
    body = json.dumps({
        "model": model or (vision_model() if has_images else text_model()),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        "options": {"num_ctx": 16384},
    }).encode()
    req = urllib.request.Request(
        f"{url()}/v1/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read()[:500].decode(errors="replace")
        raise RuntimeError(f"ollama HTTP {e.code}: {detail}")
    except Exception as e:                                    # noqa: BLE001
        raise RuntimeError(f"ollama unreachable at {url()}: "
                           f"{type(e).__name__} {str(e)[:120]}")


def as_content(prompt, images=()):
    """The OpenAI multimodal content array, images first, as the callers send."""
    import base64
    from pathlib import Path
    out = []
    for p in images:
        p = Path(p)
        out.append({"type": "image_url", "image_url": {"url":
                    f"data:{MIME.get(p.suffix.lower(), 'image/png')};base64,"
                    + base64.b64encode(p.read_bytes()).decode()}})
    out.append({"type": "text", "text": prompt})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ask", default=None, help="send one test prompt")
    args = ap.parse_args()
    print(f"  backend enabled : {enabled()}  "
          f"(PROP_LLM_BACKEND={os.environ.get('PROP_LLM_BACKEND','unset')})")
    print(f"  OLLAMA_URL      : {url()}")
    ok, names = installed()
    print(f"  reachable       : {'yes' if ok else 'NO'}")
    if not ok:
        print(f"    {names[0]}")
        return 1
    print(f"  models installed: {len(names)}")
    for n in names[:12]:
        print(f"    {n}")
    for role, want in (("text", text_model()), ("vision", vision_model())):
        have = any(n.split(":")[0] == want.split(":")[0] for n in names)
        print(f"  {role:6} model    : {want}  {'OK' if have else 'NOT PULLED'}")
        if not have:
            print(f"    ollama pull {want}")
    if args.ask:
        r = chat([{"role": "user", "content": args.ask}], max_tokens=200)
        msg = (r.get("choices") or [{}])[0].get("message", {})
        print(f"\n  reply: {(msg.get('content') or '')[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
