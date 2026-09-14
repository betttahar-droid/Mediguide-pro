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

AND WHEN THE DIRECT ENDPOINT HAS NO CREDIT, THE SAME FAMILY IS BOUGHT THROUGH
OPENROUTER. The 429 that stopped nine drawing tools stopped this one too, and it
is the more expensive loss: a fault either judge calls blocking is blocking, so
losing one does not make the loop slower, it makes it laxer, and it does so
SILENTLY -- `make_prop` catches the failure and prints "second opinion
unavailable" beside a prop that is now being graded by one model with one set of
blind spots. CLAUDE.md's rule about a blocking channel needing a correcting
channel has a twin here: a channel that can go quiet needs somewhere to go.

The substitute has to stay in the GEMINI family. The whole value of this judge
is that it is not glm -- "two graders from different families disagree in
different places" -- so falling back to the cheapest vision model on OpenRouter
would keep the call and throw away the reason for it.
"""
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import (ENDPOINT, MIME, OR_ENDPOINT, load_key,  # noqa: E402
                           _openrouter_key, _spent)

# text-out models, tried in order: the image model answers text too, but a
# dedicated one is steadier at long structured replies
MODELS = ("gemini-flash-latest", "gemini-2.5-flash", "gemini-3.1-flash-image")

# The same family on OpenRouter, cheapest first. A judge call here is a few
# renders and about 1500 tokens of reply, so these run $0.002-$0.01 against the
# $0.034 of a single drawing -- the judges were never the expensive half, and
# `auto_prop`'s own critic benchmark says so in as many words ("cost was never
# the problem").
#
# CHECKED ON THE REAL JUDGE PROMPT AND THE REAL RENDERS, because the thing that
# breaks a judge in this loop is not bad taste, it is failing to return the
# schema -- a judge that answers in prose is a judge whose faults never reach
# the patch merge, and make_prop swallows that as "second opinion unavailable".
# Asked the actual JUDGE prompt about v52_jukebox's four r0 renders:
#
#   google/gemini-3.1-flash-lite    5.8s   schema OK    4 faults,  7 patched
#   google/gemini-2.5-flash        16.5s   schema OK   12 faults, 41 patched
#   google/gemini-2.5-flash-lite   30.7s   TRUNCATED at 37k chars, finish=length
#
# 2.5-flash-lite is dropped: it does not run out of room, it runs on, and no
# budget this loop can afford gets a closing brace out of it.
#
# WHAT IS NOT SETTLED is which of the two survivors judges BETTER. They differ
# by a factor of three in faults and six in parts patched on the same prop, and
# nothing here says whether that is thoroughness or noise. It matters, because
# this repo's measured complaint about its judges is that they are too LAX --
# both scored a cabinet carrying five stacked marquees level with the corrected
# one beside it. Settling it needs renders whose faults are known independently,
# which `repeat_score` supplies for the commonest fault class. Until then the
# order is by price among models that answer, and the cheaper one leads.
OR_MODELS = (
    "google/gemini-3.1-flash-lite",     # $0.25/$1.50 per Mtok
    "google/gemini-2.5-flash",          # $0.30/$2.50, slower, much more verbose
)
_DIRECT_DEAD = {}


def _via_openrouter(prompt, images, timeout, models=OR_MODELS):
    """The same question, same family, bought from OpenRouter."""
    key = _openrouter_key()
    if not key:
        raise RuntimeError("the vision endpoint is out of credit and there is "
                           "no OPENROUTER_API_KEY in .env to fall back to")
    content = []
    for img in images:
        path = Path(img)
        mime = MIME.get(path.suffix.lower(), "image/png")
        content.append({"type": "image_url", "image_url": {
            "url": f"data:{mime};base64,"
                   + base64.b64encode(path.read_bytes()).decode()}})
    content.append({"type": "text", "text": prompt})
    # ASK FOR ROOM. At the 4096 this file was written with, google/gemini-2.5-
    # flash and -flash-lite both came back TRUNCATED -- a reply that opens `{`
    # and never closes it, which the extractor below reports as "JSON did not
    # parse" and which reads exactly like a model that cannot follow the schema.
    # It is not: this judge is asked to list every fault AND patch every part,
    # and on a 78-part jukebox that is 15k characters. `auto_prop.glm` carries
    # this same finding in its docstring, one file over, and asks for 12000.
    #
    # The cost of being wrong here is asymmetric and silent: make_prop catches
    # the failure, prints "second opinion unavailable", and grades the prop with
    # one judge. Two models were about to be written off for a budget fault.
    body = json.dumps({
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 12000, "temperature": 0.2,
    })

    last = None
    for model in models:
        req = urllib.request.Request(
            OR_ENDPOINT,
            data=json.dumps(dict(json.loads(body), model=model)).encode(),
            method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
        except Exception as e:
            last = f"{model}: {type(e).__name__}"
            continue
        msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
        # A REASONING MODEL CAN LEAVE THE ANSWER IN THE REASONING CHANNEL, which
        # `auto_prop.glm` learned the hard way and this would have re-learned.
        text = (msg.get("content") or "") or (msg.get("reasoning") or "")
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            last = f"{model}: no JSON in reply"
            continue
        try:
            return json.loads(m.group(0)), model
        except Exception as e:
            # SAY WHICH FAILURE IT WAS. "JSON did not parse" covers a model that
            # cannot follow a schema and a model that ran out of room, and those
            # want opposite responses -- drop it, or give it more room. The
            # finish reason distinguishes them and was being thrown away.
            fin = (ch.get("finish_reason") or ch.get("native_finish_reason")
                   or "?") if (ch := (d.get("choices") or [{}])[0]) else "?"
            last = (f"{model}: JSON did not parse (finish={fin}, "
                    f"{len(text)} chars, {e})")
    raise RuntimeError(f"openrouter vision failed: {last}")


def vision_json(prompt, images, key=None, models=MODELS, timeout=180):
    """Ask Gemini about some images and get JSON back."""
    if _DIRECT_DEAD.get("why"):
        return _via_openrouter(prompt, images, timeout)
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
        except urllib.error.HTTPError as e:
            detail = e.read()[:400].decode(errors="replace")
            last = RuntimeError(f"{model}: HTTP {e.code}")
            # OUT OF CREDIT IS NOT "TRY THE NEXT MODEL". Every model on the
            # direct endpoint bills the same account, so the loop below spent
            # three round trips rediscovering one 429 and then raised, and
            # make_prop printed "second opinion unavailable" and graded the
            # prop with one judge.
            if _spent(e.code, detail):
                _DIRECT_DEAD["why"] = f"HTTP {e.code}"
                print(f"  ! vision API: HTTP {e.code} -- second opinion via "
                      f"OpenRouter for the rest of this run")
                return _via_openrouter(prompt, images, timeout)
        except Exception as e:                       # try the next model
            last = e
    raise RuntimeError(f"gemini vision failed: {last}")


if __name__ == "__main__":
    got, model = vision_json(
        'Describe this image in one short sentence. JSON only: {"desc": "..."}',
        [sys.argv[1]])
    print(model, got)
