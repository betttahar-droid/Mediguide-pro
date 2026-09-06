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

STYLE = nano_views.STYLE

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
# For the critic, gpt-5.2 is the one worth paying for: on the same render it
# named five specific faults -- including a stepped profile we had missed and
# a black square we had ADDED -- where glm-5.3-flash named three and
# kimi-k2.5 named three bare ones for 58x the price and 43x the latency.
AUTHOR_MODEL = "z-ai/glm-5.3-flash"    # cheapest of the cluster, and has vision
CRITIC_MODEL = "z-ai/glm-5.3-flash"    # per-round reviewer
FINAL_CRITIC = "openai/gpt-5.2"        # 9s, ~1 cent, much the most specific

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
        raise SystemExit(f"{model}: HTTP {e.code} {e.read()[:400].decode(errors='replace')}")
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
    return b


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
    ap.add_argument("--retries", type=int, default=2,
                    help="regeneration attempts per view that fails the gate")
    args = ap.parse_args()

    out = Path(args.out or (ROOT / "tools" / "img2threejs-work" /
                            re.sub(r"\W+", "_", args.asset.lower())))
    out.mkdir(parents=True, exist_ok=True)
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
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "OPENROUTER_API_KEY":
                    return v.strip()
    raise SystemExit("No OPENROUTER_API_KEY in .env")


if __name__ == "__main__":
    main()
