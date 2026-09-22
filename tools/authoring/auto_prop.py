#!/usr/bin/env python3
"""Author a prop end to end from ONE noun, with no human in the prompt.

    python3 tools/authoring/auto_prop.py "arcade cabinet"
    python3 tools/authoring/auto_prop.py "arcade cabinet" --out work/arcade

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS EXISTS. nano_views.py carries a hand-written SUBJECT and four
hand-written view instructions, so every new prop costs a person sitting down
to describe it -- and docs/BUILDING-A-PROP.txt 14.0 warns that the moment a
person is LOOKING at a generated image and typing what they see, the pipeline
has lost the property it was built for. This drives the same two models with
nobody in the middle:

    GLM 5.3          writes the SUBJECT brief and the per-view instructions,
                     and (as glm-5.3-flash, which takes images) reads the
                     rendered result back and names what is wrong with it
    Nano Banana 2    draws the turnaround those prompts ask for

The harness contributes no art direction. It supplies the STYLE block imported
verbatim from nano_views.py (the project's house style, not this file's), the
carver's hard preconditions (facts about voxel_carve.py, not taste), and a
deterministic gate that measures whether a view is carvable before spending a
carve on it.

FOUR VIEWS, NOT THREE. front+side leaves every far face unpainted and they
render black -- 46% of the side and 36% of a three-quarter in the till test.
A back view is the cheapest fix available.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
sys.path.insert(0, str(ROOT / "tools" / "voxel-fridge"))
from concept_sheet import generate_image, load_key  # noqa: E402
import nano_views  # noqa: E402  -- for STYLE, so the house style stays one string

# PIXELATION IS A POST EFFECT, NOT A SOURCE PROPERTY. nano_views.STYLE opens
# with "16-bit pixel art, hard-edged chunky pixels", so every reference this
# tool generated was pixel art -- and then the measurement stage read texels as
# if they were geometry, and the part list inherited a look that main.js
# already applies in the shader (palette snap, dither, outline). Asking for it
# twice bakes it into the model.
#
# A PlayStation-era asset is not that: it is a low-polygon mesh with visible
# flat facets carrying a small, low-resolution, hand-painted TEXTURE. The
# geometry is chunky; the detail lives in the texture. So the reference must
# show a clean render of exactly that, and the pixelation must be left to post.
PS1_STYLE = (
    "A single game prop rendered as a late-1990s PlayStation 1 game model. "
    "LOW POLYGON COUNT: visible flat angular facets, hard straight edges, no "
    "smooth shading, no bevels, no subdivision, no rounded corners. Surfaces "
    "carry LOW-RESOLUTION HAND-PAINTED TEXTURES -- coarse visible texels, "
    "baked-in shading, panel lines and grime painted into the texture rather "
    "than modelled -- in a muted, slightly desaturated palette. "
    "A CRISP CLEAN RENDER: this is NOT pixel art, NOT a sprite. No dithering, "
    "no black outline, no posterisation, no halftone. "
    "STRICT ORTHOGRAPHIC PROJECTION: no perspective, no foreshortening, no "
    "vanishing point. Absolutely flat single-colour background, NO drop "
    "shadow, NO ground plane, NO reflection. The object fills the frame with "
    "a small even margin. No text, no labels, no annotations, no watermark."
)

STYLES = {"pixel": nano_views.STYLE, "ps1": PS1_STYLE}
STYLE = PS1_STYLE

OR_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
# BENCHMARKED ON THIS TASK, not chosen. Six models authored the same measured
# arcade reference. The match scores landed between 24.0% and 27.3%, so the
# MODEL IS NOT THE BOTTLENECK -- but the cost spread across that 3-point band
# is 38x, and on the run that produced these numbers plain glm-5.3 returned
# invalid JSON while costing 20x more than the flash variant that worked.
#
#   model                    match  parts     cost  secs  match/cent
#   google/gemini-2.5-flash  27.30%    31  $0.0218    39      12.5
#   minimax/minimax-m2.5     27.29%    22  $0.0222   185      12.3
#   moonshotai/kimi-k2.5     27.25%    36  $0.0421   849       6.5
#   qwen/qwen3-max           24.54%    23  $0.0070    16      35.1
#   z-ai/glm-5.3-flash       24.04%    25  $0.0011    62     227.0
#   z-ai/glm-5.3             invalid JSON
#
# THE CRITIC, RE-BENCHMARKED. The first run said gpt-5.2 and was unfair: the
# anthropic models 400'd on the `reasoning` field and gemini was graded on
# formatting rather than sight. Fixing both and rerunning eight vision models
# on one reference/render pair reverses the answer.
#
#   model                     secs     cost  faults  notes
#   z-ai/glm-5.3-flash          11  $0.0002    7     all correct, and the only
#                                                    one to name the ROOT CAUSE
#                                                    (a UV/placement misplacement)
#   anthropic/claude-opus-5     20  $0.0381    7     strong, one hallucination
#   openai/gpt-5.2               7  $0.0077    5     good, one hallucination
#   anthropic/claude-sonnet-5    6  $0.0069    5     clean, all correct
#   qwen/qwen3-vl-235b           5  $0.0006    5     caught the band seams
#                                                    exactly, invented a
#                                                    missing marquee
#   anthropic/claude-haiku-4.5   4  $0.0029    4     vaguest, one misread
#   z-ai/glm-4.6v               44  $0.0024    4     thin
#   google/gemini-2.5-flash    142        -    0     prose, never JSON, twice
#
# glm-5.3-flash wins on accuracy AND costs 1/190th of opus, so CRITIC_MODEL
# below is already the right default and there is no premium tier worth
# buying. Note every model above hallucinated at least once except sonnet and
# glm-5.3-flash -- a judge's fault is a CLAIM, and project_score.py should
# confirm it before the loop spends a round on it.
AUTHOR_MODEL = "z-ai/glm-5.3-flash"    # cheapest of the cluster, and has vision
CRITIC_MODEL = "z-ai/glm-5.3-flash"    # best judge measured, at 1/190th of opus
SECOND_OPINION = "anthropic/claude-sonnet-5"   # clean and hallucination-free

ORDER = ["front", "side", "back", "top"]

# Facts about voxel_carve.py, quoted to the author model so its prompts ask for
# something carvable. These are constraints, not art direction -- every one of
# them is a line in voxel_carve.crop_to_object or PARTS.md.
CARVER_RULES = """\
The images will be fed to a shape-from-silhouette voxel carver, which imposes
hard requirements. A view that breaks any of these is useless to it:
- absolutely flat single-colour background; the silhouette is found by
  difference from the corner pixel, so a gradient or a textured ground makes
  the whole frame count as object
- no drop shadow, no ground plane, no reflection; a shadow is solid as far as
  a silhouette is concerned
- strict orthographic projection, no perspective and no foreshortening
- the object fills the frame with a small even margin, and must not touch or
  run off any edge; the voxel grid is derived from the object's own aspect
- it must be the SAME object at the SAME size in every view, or intersecting
  the silhouettes produces nonsense
- the front and back views must be the same width, the side view the same
  height as the front, and the top view's width must match the front and its
  depth match the side"""


# ----------------------------------------------------------------- OpenRouter

# Zero-priced vision models that serve at a zero balance, in the order they are
# tried. Verified by asking each to judge a real render: openrouter/free answered
# in 4s with usable JSON; nex-agi took 46s; gemma and inkling returned 429/403.
FREE_VISION = ["openrouter/free", "nex-agi/nex-n2.5-pro:free"]
_RETRY = {}


GEMINI_TEXT_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/"
                        "models/{model}:generateContent")
# gemini-2.5-flash is retired for new keys and the API says so in the 404:
# "no longer available to new users ... use models/gemini-3.6-flash". Taking
# the name the server hands over beats pinning one that dies quietly.
GEMINI_TEXT_MODEL = "gemini-3.6-flash"


def _gemini_key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "GEMINI_API_KEY" and v.strip():
                    return v.strip()
    return os.environ.get("GEMINI_API_KEY", "").strip() or None


def _gemini_text(messages, max_tokens=12000, temperature=0.3):
    """One completion from Gemini, returned as TEXT like every other branch.

    The OpenAI message shape is flattened: Gemini wants parts, and every caller
    of glm() that lands here sends text-only turns.
    """
    key = _gemini_key()
    if not key:
        raise RuntimeError("PROP_TEXT_BACKEND=gemini but no GEMINI_API_KEY")
    parts = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            parts.append({"text": c})
        else:
            for piece in c:
                if piece.get("type") == "text":
                    parts.append({"text": piece["text"]})
    model = os.environ.get("GEMINI_TEXT_MODEL", GEMINI_TEXT_MODEL)
    body = json.dumps({
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature,
                             "maxOutputTokens": max_tokens},
    }).encode()
    req = urllib.request.Request(
        GEMINI_TEXT_ENDPOINT.format(model=model) + f"?key={key}",
        data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    cands = d.get("candidates") or []
    if not cands:
        raise RuntimeError(f"gemini: no candidates -- {json.dumps(d)[:300]}")
    out = "".join(p.get("text", "")
                  for p in (cands[0].get("content") or {}).get("parts", []))
    if not out.strip():
        # A THINKING MODEL BILLS ITS THINKING AGAINST maxOutputTokens, so a
        # budget sized for the answer comes back with an empty content block
        # and finishReason=MAX_TOKENS -- the same trap glm() documents for GLM.
        raise RuntimeError(
            f"gemini: empty reply (finishReason={cands[0].get('finishReason')}"
            f", usage={d.get('usageMetadata')}). Raise max_tokens.")
    return out


def glm(messages, model, key, max_tokens=12000, temperature=0.3, effort="low"):
    """GLM 5.3 is a REASONING model and its thinking is billed against
    max_tokens, so a budget sized for the answer alone comes back with
    content=None and finish_reason=length. Ask for room, and if the answer
    still lands in the reasoning channel, read it from there.

    PIN THE REASONING EFFORT. Left unpinned, OpenRouter routed this to a
    provider that thought for over ten minutes on a prompt-writing task and
    never returned; effort=low answers the same prompt in about eleven
    seconds. None of the calls here need deep reasoning -- they are "write
    four prompts" and "name what is wrong in this picture"."""
    # A LOCAL OLLAMA, WHEN ONE IS ASKED FOR. Same seam, same reasoning as the
    # image backend: fifteen tools call this and none of them should know.
    # See local_llm -- the calls whose replies arithmetic VERIFIES are the ones
    # safe to move local; the judges, which nothing grades, are not.
    try:
        import local_llm
    except Exception:                                         # noqa: BLE001
        local_llm = None
    # A GEMINI TEXT PATH, BECAUSE THE BRIEF IS THE ONE ASK THAT NEEDS A CAPABLE
    # MODEL AND THE KEY FOR ONE IS ALREADY HERE. The end-to-end trace in
    # ROADMAP section 0 ends with "neither segmentation nor measurement produced
    # parts" -- correct, because a 3B author had described a cube. Everything
    # downstream is verified and behaved; the subject is the only ask nothing
    # can check, so it is the only one that has to be bought.
    #
    # `concept_sheet` has spoken to Gemini for images since the beginning and
    # `glm()` could only reach OpenRouter or Ollama, so a box with a GEMINI key
    # and no OPENROUTER key had no capable author at all. That was a missing
    # seam, not a missing key. Same contract as every other branch here: return
    # TEXT.
    if (os.environ.get("PROP_TEXT_BACKEND", "").lower() == "gemini"
            or (not key and _gemini_key())):
        return _gemini_text(messages, max_tokens=max_tokens,
                            temperature=temperature)
    if local_llm is not None and local_llm.enabled():
        has_img = any(not isinstance(m.get("content"), str) for m in messages)
        # UNWRAP IT THE SAME WAY THE PAID PATH DOES. glm() returns TEXT -- every
        # caller does as_json(glm(...)) -- and this branch was returning the
        # whole OpenAI envelope, so `dict.strip()` raised AttributeError on the
        # first line of as_json. Fifteen tools call glm; all fifteen failed that
        # way the moment PROP_LLM_BACKEND was set, and the failure is invisible
        # because it looks like the model talking nonsense: scale_rules caught
        # it as "reply unusable (AttributeError)", retried three times, and then
        # wrote its defaults over a prop's real rules. LOCAL.md says the local
        # backend needs no caller to change, and this is the line that made that
        # false.
        ld = local_llm.chat(messages, max_tokens=max_tokens,
                            temperature=temperature, has_images=has_img)
        if isinstance(ld, str):
            return ld
        lch = (ld.get("choices") or [{}])[0]
        ltext = ((lch.get("message") or {}).get("content") or "").strip()
        if not ltext:
            raise RuntimeError(
                f"local model returned no content "
                f"(finish_reason={lch.get('finish_reason')}, "
                f"keys={sorted(ld)[:6]})")
        return ltext

    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature,
                       "reasoning": {"effort": effort}}).encode()
    req = urllib.request.Request(
        OR_ENDPOINT, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read()[:600].decode(errors="replace")
        # A 402 IS A BUDGET, AND IT SAYS WHAT THE BUDGET IS.
        #
        # "You requested up to 14000 tokens, but can only afford 6428" ended
        # four runs in this session -- two of them mid-loop, after the sheets
        # and the segmentation had already been bought. The account was not
        # empty; the ASK was too big, and the reply named the number that
        # would have worked. Raising SystemExit on that is throwing away an
        # answer the server has already handed over.
        #
        # So take it: retry once at what it says it can afford, less a small
        # margin, and never below a floor where the reply could not be a
        # complete JSON object anyway. A judge with less room to think is a
        # worse judge -- the note above is about exactly that -- so this is a
        # degradation, not a fix, and it says so out loud rather than
        # pretending the round was normal.
        m402 = re.search(r"can only afford (\d+)", detail) if e.code == 402 else None
        if m402 and not _RETRY.get("in"):
            afford = int(m402.group(1))
            room = max(0, afford - 200)
            if room >= 1500:
                print(f"  ! {model}: out of budget for {max_tokens} tokens, "
                      f"retrying at {room} -- the reply will be shorter than "
                      f"this judge normally gets")
                _RETRY["in"] = True
                try:
                    return glm(messages, model, key, max_tokens=room,
                               temperature=temperature, effort=effort)
                finally:
                    _RETRY["in"] = False
        # AND WHEN THERE IS NO BUDGET AT ALL, DROP TO A FREE MODEL.
        #
        # glm-5.3-flash is not expensive -- the benchmark above puts a judge
        # call at $0.0002, a 190th of opus -- so a run never ends because a
        # call cost too much. It ends because the balance reached zero, which
        # is a different thing and happened four times in one session, twice
        # mid-loop after the sheets and the segmentation had already been paid
        # for. Losing the round there wastes work that was already bought.
        #
        # OpenRouter carries a handful of genuinely zero-priced vision models
        # that serve at a zero balance, and they are not a token gesture: asked
        # to judge the cabinet with five stacked ARCADE marquees, openrouter/free
        # returned blocking=2, "duplicated sign", "tiling repeat" -- which is
        # the call BOTH paid judges got wrong on that exact image, scoring it
        # level with the corrected cabinet beside it.
        #
        # It is still a fallback and not a default: it is slower, it leaks
        # reasoning instead of JSON unless given room, and it has not been
        # benchmarked across the whole judge prompt. It says out loud which
        # model answered, so a round graded this way is never mistaken for a
        # normal one.
        if e.code == 402 and not _RETRY.get("in") and model not in FREE_VISION:
            for alt in FREE_VISION:
                print(f"  ! {model}: no budget left -- falling back to {alt}")
                _RETRY["in"] = True
                try:
                    return glm(messages, alt, key,
                               max_tokens=max(6000, max_tokens),
                               temperature=temperature, effort=effort)
                except Exception:
                    continue
                finally:
                    _RETRY["in"] = False
        raise SystemExit(f"{model}: HTTP {e.code} {detail[:400]}")
    if not d.get("choices"):
        # An OpenRouter error comes back 200 with an "error" body and no
        # choices; indexing it raised KeyError and hid the reason.
        raise SystemExit(f"{model}: no choices in reply -- "
                         f"{json.dumps(d)[:400]}")
    ch = d["choices"][0]
    msg = ch.get("message", {})
    text = msg.get("content") or ""
    if not text.strip():
        text = msg.get("reasoning") or ""
        if not text.strip():
            raise SystemExit(
                f"{model}: empty reply (finish_reason={ch.get('finish_reason')}, "
                f"usage={d.get('usage')}). Raise --max-tokens.")
    return text


def as_json(text):
    """GLM wraps JSON in prose or fences often enough to be worth handling."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        raise SystemExit(f"no JSON in model reply:\n{text[:600]}")
    return json.loads(m.group(0))


def data_uri(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


# --------------------------------------------------------------------- author

def author_brief(asset, key, feedback=None):
    """GLM writes the SUBJECT and the four view instructions. We write none."""
    ask = f"""You are writing prompts for a pixel-art image generator, to produce a
four-view orthographic turnaround of this game asset: "{asset}".

{CARVER_RULES}

Write:
1. "subject": ONE sentence describing the asset as a physical object, in the
   register of a modelling brief -- overall proportion first, then each part
   with its explicit colour. Name a colour for every part; a part whose colour
   you leave out will be guessed differently in each view. Do not mention
   style, pixels, projection or background; those are added separately.
2. "views": an object with keys "front", "side", "back", "top". Each value is
   the instruction for that one elevation: which face it shows, what must line
   up with the views already drawn, and what must NOT appear in it.

Reply with JSON only: {{"subject": "...", "views": {{"front": "...", "side": "...", "back": "...", "top": "..."}}}}"""
    if feedback:
        ask += f"\n\nA previous attempt failed these checks. Fix them:\n{feedback}"
    out = glm([{"role": "user", "content": ask}], AUTHOR_MODEL, key)
    b = as_json(out)
    if "subject" not in b or "views" not in b:
        raise SystemExit(f"brief missing keys: {list(b)}")
    missing = [v for v in ORDER if v not in b["views"]]
    if missing:
        raise SystemExit(f"brief missing views: {missing}")

    # THE BRIEF IS THE ONE ASK NOTHING CHECKED, AND IT COMMISSIONS THE MOST
    # EXPENSIVE STAGE. CARVER_RULES says "strict orthographic projection, no
    # perspective and no foreshortening"; a weak model cheerfully writes the
    # opposite into the per-view instruction and the image model obeys THAT:
    #
    #   front: "The sides and bottom must be visible and not hidden by the
    #           cabinet."
    #
    # which came back as a three-quarter drawing of a squat box. `gate()`
    # passed all four -- it measures fill and bounding box, and perspective
    # passes both (22%, 0.399..0.836) -- and only the cross-view footprint
    # check noticed, on the top view alone. Measured: the obvious silhouette
    # test (a true elevation has vertical left and right edges) does NOT
    # separate them, 0.0057 against a corpus median of 0.0031 with two corpus
    # sheets scoring worse, because a box drawn at an angle still has a
    # near-vertical front face in outline.
    #
    # So check the ASK instead of the drawing, which is cheap, deterministic
    # and exactly where the fault is. Same shape as scale_rules: name the
    # fault, quote it back, ask again -- and if the second reply still asks for
    # perspective, strike the offending sentence rather than buy four images
    # against it.
    bad = brief_faults(b["views"])
    if bad and feedback is None:
        print("  brief asks for perspective -- re-asking:")
        for f in bad:
            print(f"    {f}")
        return author_brief(asset, key, feedback=chr(10).join(bad))
    if bad:
        for v in ORDER:
            b["views"][v] = strip_perspective(b["views"][v])
        print("  brief still asked for perspective; struck those sentences")

    # AND SAY WHAT AN ELEVATION IS, EVERY TIME, IN THE VIEW INSTRUCTION ITSELF.
    #
    # Striking the bad sentence is not enough and the reason is worth keeping:
    # PS1_STYLE already carries "STRICT ORTHOGRAPHIC PROJECTION: no perspective,
    # no foreshortening, no vanishing point", and four elevations bought against
    # it still came back as three-quarter drawings. The conclusion drawn from
    # that -- "the ask is correct and the model disobeys" -- WAS WRONG, and one
    # image disproved it. The style prefix is preamble; the VIEW INSTRUCTION is
    # the request, and a request that says only "the front view shows the front
    # face" leaves the projection to the model's prior, which for an arcade
    # cabinet is a hero shot.
    #
    # The briefs that DID produce usable elevations say it per view, in the
    # instruction: "Show the left side ELEVATION as a FLAT red panel", "the top
    # face LOOKING STRAIGHT DOWN", "the marquee, screen, joystick and buttons
    # must NOT appear". That is specificity, not model strength -- so it can be
    # appended deterministically and a weak author is then safe, which is this
    # repo's whole division of labour.
    #
    # Verified with one image before wiring: same subject, same style prefix,
    # clause appended -> a flat square-on front elevation with no top face and
    # no receding sides.
    for v in ORDER:
        b["views"][v] = f'{b["views"][v].rstrip()} {ELEVATION[v]}'
    return b


# What the drawing model is actually being asked for, per view. Phrased from
# the briefs that worked: name the projection, name the face, and name what
# must NOT appear.
ELEVATION = {
    "front": "Draw the FRONT ELEVATION only: the front face seen dead straight "
             "on, flat and square to the camera. The left and right sides, the "
             "top face and the underside must NOT appear -- no other face is "
             "visible in an elevation. The object fills the frame with a small "
             "even margin.",
    "side":  "Draw the SIDE ELEVATION only: the left flank seen dead straight "
             "on, flat and square to the camera. The front face, the back face "
             "and the top face must NOT appear. Its height must match the front "
             "elevation exactly.",
    "back":  "Draw the BACK ELEVATION only: the rear face seen dead straight "
             "on, flat and square to the camera. The sides and the top must NOT "
             "appear. Its width and height must match the front elevation "
             "exactly.",
    "top":   "Draw the TOP ELEVATION only: the plan, looking straight down from "
             "directly above. No front, back or side face may appear. Its width "
             "must match the front elevation and its depth must match the side "
             "elevation.",
}


# A view instruction may not ask for any face but its own to SHOW. The phrasing
# varies; what does not vary is a visibility word aimed at another face, or a
# projection word. "shows" alone is not it -- "the front view shows the front
# face" is correct, and so is "the same width as the front", which the ask
# explicitly requires for alignment. Only visibility and projection fire.
_OTHER_FACE = ("side", "sides", "top", "bottom", "back", "front", "rear",
               "underside", "flank")
_VISIBLE = ("visible", "must be seen", "can be seen", "should be seen",
            "appear", "not be hidden", "not hidden")
_PROJECTION = ("perspective", "three-quarter", "three quarter", "angled",
               "at an angle", "foreshorten", "isometric", "3/4")


# "The top and bottom faces must NOT appear in this view" is the instruction we
# WANT, and the first version of this check struck it -- it saw "appear" and a
# face name and fired. A rule that deletes the correct sentence is worse than no
# rule, so negation is tested before the fault is raised.
_NEGATED = ("not appear", "never appear", "must not", "must never", "no other",
            "not be visible", "not visible", "not be seen", "not shown",
            "should not", "cannot", "excluded", "omit", "without",
            # a bare "no X may appear" negates without the word "not"
            "no front", "no back", "no side", "no top", "no bottom",
            "no rear", "no underside", "no flank", "none of",
            "not show", "never show", "no perspective", "no foreshorten",
            "avoid", "free of", "without any")


def _negated(low):
    return any(n in low for n in _NEGATED)


def _sentences(text):
    return [t.strip() for t in re.split(r"(?<=[.;])\s+", text or "") if t.strip()]


def brief_faults(views):
    """Which view instructions contradict the orthographic rule, and how."""
    out = []
    for v, text in views.items():
        own = v.lower()
        for sent in _sentences(text):
            low = sent.lower()
            why = None
            if any(w in low for w in _PROJECTION) and not _negated(low):
                why = "names a projection that is not orthographic"
            elif any(w in low for w in _VISIBLE) and not _negated(low):
                others = [f for f in _OTHER_FACE
                          if f in low and not own.startswith(f[:3])
                          and not f.startswith(own[:3])]
                if others:
                    why = f"asks for another face ({', '.join(sorted(set(others)))}) to show"
            if why:
                out.append(f'"{v}" {why}: "{sent}" -- every view is a STRICT '
                           f"ORTHOGRAPHIC ELEVATION of that face alone. No "
                           f"other face may appear in it.")
    return out


def strip_perspective(text):
    """Drop the sentences that break the rule, keep the rest."""
    keep = []
    for sent in _sentences(text):
        low = sent.lower()
        bad = (any(w in low for w in _PROJECTION) and not _negated(low)) or (
            any(w in low for w in _VISIBLE) and not _negated(low)
            and any(f in low for f in _OTHER_FACE))
        if not bad:
            keep.append(sent)
    return " ".join(keep) or text


# ----------------------------------------------------------------------- gate

def gate(path):
    """Deterministic carvability check, mirroring voxel_carve.crop_to_object."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = Counter(corners).most_common(1)[0][0]

    def is_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    # MEASURE WHAT THE CARVER WILL ACTUALLY DO, not corner spread. Rejecting on
    # "corners differ by more than 40" threw out four usable views in a row over
    # a gentle gradient. crop_to_object picks the majority corner and calls
    # everything within 40 of it background, so the question that matters is how
    # much of the border ring that rule MISSES.
    ring = [px[x, y] for x in range(0, w, 4) for y in (0, 1, h - 2, h - 1)] + \
           [px[x, y] for y in range(0, h, 4) for x in (0, 1, w - 2, w - 1)]
    spread = sum(1 for c in ring if not is_bg(c)) / max(1, len(ring))

    fg = [(x, y) for x in range(0, w, 2) for y in range(0, h, 2) if not is_bg(px[x, y])]
    frac = len(fg) / ((w // 2) * (h // 2))
    if not fg:
        return {"ok": False, "why": ["no object found at all"], "fill": 0.0,
                "ring_miss": round(spread, 4)}
    xs = [p[0] for p in fg]
    ys = [p[1] for p in fg]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    touches = x0 <= 2 or y0 <= 2 or x1 >= w - 3 or y1 >= h - 3
    box_w, box_h = (x1 - x0) / w, (y1 - y0) / h

    why = []
    if spread > 0.03:
        why.append(f"{spread:.0%} of the border ring does not read as background; "
                   "the ground must be one flat colour edge to edge")
    if frac > 0.75:
        why.append(f"{frac:.0%} of the frame reads as object -- background not separating")
    if frac < 0.04:
        why.append(f"only {frac:.1%} of the frame is object -- object too small")
    if touches:
        why.append("object touches the frame edge; it needs an even margin")
    if max(box_w, box_h) < 0.45:
        why.append(f"object fills only {box_w:.0%}x{box_h:.0%} of the frame")
    return {"ok": not why, "why": why, "fill": frac, "ring_miss": round(spread, 4),
            "box": (round(box_w, 3), round(box_h, 3)), "size": (w, h),
            "obj_px": (x1 - x0 + 1, y1 - y0 + 1)}


def components(path, step=3):
    """Connected blobs of object, biggest first, as (size, w, h).

    A DETACHED SECOND OBJECT IS THE EXPENSIVE ONE. The gate above measures the
    whole frame's bounding box, so a stray vent square drawn beside the
    cabinet widened the front silhouette until the carver derived a grid 2.8x
    too wide from it -- and every per-view check still passed.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = Counter([px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]).most_common(1)[0][0]
    W, H = w // step, h // step
    sol = [[sum(abs(a - b) for a, b in zip(px[x * step, y * step], bg)) >= 40
            for y in range(H)] for x in range(W)]
    seen = [[False] * H for _ in range(W)]
    out = []
    for sx in range(W):
        for sy in range(H):
            if not sol[sx][sy] or seen[sx][sy]:
                continue
            stack = [(sx, sy)]
            seen[sx][sy] = True
            xs, ys, n = [], [], 0
            while stack:
                x, y = stack.pop()
                xs.append(x); ys.append(y); n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = x + dx, y + dy
                    if 0 <= a < W and 0 <= b < H and sol[a][b] and not seen[a][b]:
                        seen[a][b] = True
                        stack.append((a, b))
            out.append((n, (max(xs) - min(xs) + 1) * step, (max(ys) - min(ys) + 1) * step))
    out.sort(reverse=True)
    return out


def cross_view(paths, tol=0.10):
    """Do the four elevations describe ONE object? Arithmetic, no model.

    An orthographic set is over-determined, and that is the whole value of it:
      front width  == back width      (the same edge, drawn twice)
      front height == back == side    (the same edge again)
      top aspect   == side w / front w (plan of the same footprint)
    A three-quarter view cannot satisfy these, which is what makes this the
    check that catches one. On the arcade cabinet the front came back 390 wide
    against a back of 278 -- a 40% disagreement -- because the front is
    generated FIRST with no reference attached, so nothing anchors it.
    """
    dim, why = {}, {}
    for name, p in paths.items():
        comps = components(p)
        if not comps:
            why.setdefault(name, []).append("no object found")
            continue
        if len(comps) > 1 and comps[1][0] > 0.02 * comps[0][0]:
            why.setdefault(name, []).append(
                f"{len(comps)} separate objects in frame; the largest is "
                f"{comps[0][1]}x{comps[0][2]} and a stray {comps[1][1]}x{comps[1][2]} "
                f"sits beside it. Draw ONE object only.")
        dim[name] = (comps[0][1], comps[0][2])

    def off(a, b):
        return abs(a - b) / max(a, b)

    if "front" in dim and "back" in dim:
        fw, bw = dim["front"][0], dim["back"][0]
        if off(fw, bw) > tol:
            worse = "front" if fw > bw else "back"
            why.setdefault(worse, []).append(
                f"front is {fw}px wide but back is {bw}px ({100*off(fw, bw):.0f}% apart). "
                "They are the same edge. A view showing two faces at once is not an "
                "elevation -- draw it dead on, with only one face visible.")
    for a in ("back", "side"):
        if "front" in dim and a in dim and off(dim["front"][1], dim[a][1]) > tol:
            why.setdefault(a, []).append(
                f"{a} is {dim[a][1]}px tall, front is {dim['front'][1]}px. Same height.")
    if all(k in dim for k in ("front", "side", "top")):
        want = dim["side"][0] / dim["front"][0]
        got = dim["top"][1] / dim["top"][0]
        if off(want, got) > tol * 1.5:
            why.setdefault("top", []).append(
                f"top view is {dim['top'][0]}x{dim['top'][1]} (1:{got:.2f}) but the "
                f"footprint from front and side is 1:{want:.2f}. Match the plan.")
    return dim, why


# --------------------------------------------------------------------- critic

def critique(asset, refs, shots, key):
    """glm-5.3-flash reads the render back against the reference views."""
    content = [{"type": "text", "text": f"""These images concern a pixel-art game asset: "{asset}".

The first {len(refs)} are the REFERENCE elevations it was modelled from
({', '.join(r[0] for r in refs)}). The remaining {len(shots)} are RENDERS of the
3D model that a voxel carver built from those references
({', '.join(s[0] for s in shots)}).

Compare them and report what is WRONG with the model. Report only categorical
faults you can name and locate -- a wrong or missing colour, a part on the
wrong side, a face reading black, a part that is missing, a proportion that is
plainly off. Do NOT report a numeric measurement; the harness measures.

Reply with JSON only:
{{"faults": [{{"view": "...", "part": "...", "fault": "...", "fix": "..."}}],
  "verdict": "one sentence: is this a usable match?"}}"""}]
    for name, p in list(refs) + list(shots):
        content.append({"type": "text", "text": f"[{name}]"})
        content.append({"type": "image_url", "image_url": {"url": data_uri(p)}})
    out = glm([{"role": "user", "content": content}], CRITIC_MODEL, key, max_tokens=16000)
    return as_json(out)


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset", help='the thing to build, e.g. "arcade cabinet"')
    ap.add_argument("--out", default=None)
    ap.add_argument("--style", choices=sorted(STYLES), default="ps1",
                    help="ps1: low-poly textured render (default). "
                         "pixel: the old 16-bit sprite look.")
    ap.add_argument("--retries", type=int, default=2,
                    help="regeneration attempts per view that fails the gate")
    args = ap.parse_args()

    out = Path(args.out or (ROOT / "tools" / "img2threejs-work" /
                            re.sub(r"\W+", "_", args.asset.lower())))
    out.mkdir(parents=True, exist_ok=True)
    global STYLE
    STYLE = STYLES[args.style]
    gkey = load_key()
    okey = _openrouter_key()

    print(f"== {args.asset} ==\n-> {out}\n")
    print(f"[1/4] {AUTHOR_MODEL} writing the brief ...", flush=True)
    brief = author_brief(args.asset, okey)
    (out / "brief.json").write_text(json.dumps(brief, indent=1))
    print(f"  subject: {brief['subject'][:200]}\n")

    print(f"[2/4] {nano_views.__name__}-style turnaround via Nano Banana 2 ...", flush=True)
    gates = {}
    for name in ORDER:
        refs = [out / f"{n}.png" for n in ORDER[:ORDER.index(name)]
                if (out / f"{n}.png").exists()]
        prompt = f"{STYLE}\n\nSubject: {brief['subject']}\n\n{brief['views'][name]}"
        for attempt in range(1 + args.retries):
            tag = "" if not attempt else f" (retry {attempt})"
            print(f"  {name}{tag} refs={[r.stem for r in refs] or 'none'}", flush=True)
            try:
                generate_image(prompt, out / f"{name}.png", gkey, refs=refs)
            except Exception as exc:
                print(f"    FAILED: {str(exc)[:160]}")
                continue
            g = gate(out / f"{name}.png")
            gates[name] = g
            if g["ok"]:
                print(f"    gate PASS  fill={g['fill']:.0%} box={g['box']}")
                break
            print(f"    gate FAIL  {'; '.join(g['why'])}")
            prompt += ("\n\nThe previous attempt was rejected: "
                       + "; ".join(g["why"]) + ". Fix it.")
    (out / "gates.json").write_text(json.dumps(gates, indent=1, default=str))

    ok = [n for n in ORDER if gates.get(n, {}).get("ok")]
    print(f"\n[3/4] per-view gate: {len(ok)}/{len(ORDER)} pass -> {ok}")

    # CROSS-VIEW GATE. Every per-view check can pass on a set that does not
    # describe one object -- that is exactly what happened on the arcade
    # cabinet. Regenerate an offender with ALL the other views attached, which
    # also repairs the reason it drifted: the first view is made with nothing
    # to anchor it, so it is the one that comes back three-quarter.
    for rnd in range(1 + args.retries):
        paths = {n: out / f"{n}.png" for n in ORDER if (out / f"{n}.png").exists()}
        dim, bad = cross_view(paths)
        print(f"\n  cross-view round {rnd}: "
              + "  ".join(f"{n}={dim[n][0]}x{dim[n][1]}" for n in ORDER if n in dim))
        if not bad:
            print("  cross-view PASS -- the four views describe one object")
            break
        for name, why in bad.items():
            print(f"  {name} FAIL: {' | '.join(why)}")
        if rnd == args.retries:
            print("  cross-view still failing; proceeding on the consistent views")
            break
        for name in list(bad):
            refs = [out / f"{n}.png" for n in ORDER if n != name and (out / f"{n}.png").exists()]
            prompt = (f"{STYLE}\n\nSubject: {brief['subject']}\n\n{brief['views'][name]}"
                      + "\n\nThe attached images are the other elevations of this SAME "
                        "object; match their dimensions exactly. The previous attempt was "
                        "rejected: " + "; ".join(why) + ".")
            print(f"    regenerating {name} against {[r.stem for r in refs]}", flush=True)
            try:
                generate_image(prompt, out / f"{name}.png", gkey, refs=refs)
                gates[name] = gate(out / f"{name}.png")   # keep both gates in step
            except Exception as exc:
                print(f"    FAILED: {str(exc)[:160]}")

    ok = [n for n in ORDER if gates.get(n, {}).get("ok")]
    if "front" not in ok or "side" not in ok:
        raise SystemExit("front and side are the minimum; cannot carve.")
    print(f"\n[4/4] carve with: voxel_carve.py --front {out}/front.png "
          f"--side {out}/side.png"
          + (f" --top {out}/top.png" if "top" in ok else ""))
    print("     then render, then: auto_prop.critique(...)")


def _openrouter_key():
    """The OpenRouter key, or None when nothing is going to OpenRouter.

    A GATE WHERE IT CANNOT MATTER. Nineteen tools open with `key =
    _openrouter_key()` and hand the result to `glm()`, which -- since the local
    backend landed -- ignores it entirely when PROP_LLM_BACKEND is set: the
    reply comes from Ollama and the key is never read. The exit below still
    fired, so every one of those tools refused to run on a machine with no paid
    account, which is the exact configuration LOCAL.md tells you to build and
    the one `scale_rules` most needs -- its reply is verified by `strip_slice`,
    so it is the safest ask in the repo to give a free model.

    Same shape as the faults in MISTAKES.md: a check placed where the thing it
    checks for is not used. It raises only when a call really is going out.
    """
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "OPENROUTER_API_KEY":
                    return v.strip()
    try:
        import local_llm
        if local_llm.enabled():
            return None
    except Exception:                                         # noqa: BLE001
        pass
    raise SystemExit("No OPENROUTER_API_KEY in .env")


if __name__ == "__main__":
    main()
