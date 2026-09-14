#!/usr/bin/env python3
"""
Concept sheet generator — §11.1 step 2.

Authoring tool. NOT a build, CI or runtime dependency: the game never calls
this and never reads its key. What comes back into the repo is a reference
image you look at and, more importantly, the NUMBERS you read off it (§11.1
step 3), written into docs/style-bible.md and the part lists in
src/modules/catalogue/.

    cp .env.example .env      # then put your key in it
    python3 tools/authoring/concept_sheet.py dispensing_desk
    python3 tools/authoring/concept_sheet.py --all
    python3 tools/authoring/concept_sheet.py till_block --ref docs/reference/*.png

The --ref flag is the important one for a catalogue, and it takes several images
at once: one reference gives you one object's quirks, a set gives you the shared
style underneath them. §11.1 — feed the approved sheets back in for every module
after, and the catalogue stays coherent instead of drifting object by object.

Output carries an invisible SynthID watermark and C2PA credentials (§11.2).
Fine for reference you never ship — but know it is there.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "concept"
MODEL = "gemini-3.1-flash-image"  # Nano Banana 2, the model the brief names
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# The same model, bought from someone else. See `_via_openrouter` below.
OR_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OR_MODEL = {
    "gemini-3.1-flash-image": "google/gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image": "google/gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image": "google/gemini-2.5-flash-image",
}
# Cheaper stand-ins, tried in order if the first choice is itself out of budget.
# Both draw; both cost half. They are a different model and so a different
# drawing, which is why they are a fallback and not the default.
OR_CHEAPER = ["google/gemini-3.1-flash-lite-image", "google/gemini-2.5-flash-image"]

# The style block. Identical for every module on purpose — consistency across a
# catalogue comes from this prefix not drifting. Mirrors docs/concept-prompts.md.
#
# Written against the reference set in docs/reference/: hard-edged voxel props
# where the PIXEL TEXTURE carries the detail, not the geometry. The server tower
# in that set is a plain box; everything that makes it read is painted on.
STYLE = """\
Style: isometric low-poly voxel game prop, retro pixel-art textures.

FORM: blocky and hard-edged. Square corners, no rounded or bevelled edges, no \
smooth curves. A small number of large box-like masses. The silhouette should be \
simple and chunky.

DETAIL: all of the detail is in the TEXTURE painted onto flat faces, not in the \
geometry. Dense pixel-art surface detail — panel lines, seams, screw heads, \
vents and grille slots, small labels and readouts, hinges, catches, thin \
highlight and shadow lines along every panel edge. Large visible texels, crisp \
pixel edges, no blur, no gradients, no anti-aliasing.

COLOUR: use only this palette — cream #f9efdc, bone #ecdcc0, warm oak #dda265, \
dark oak #b0763e, walnut #835531, mint #9ad9b8, teal #57a98d, deep teal #356f5e, \
coral #f5804f, steel #b0bcbd, dark steel #77868a, pale glass #d2e8e4, \
plum #413353. Give the object two or three of these as its body colours, not \
one: a light frame against darker panels reads far better than a single tone. \
Then a few TINY saturated accent pixels — an indicator, a coloured label, a \
bright handle. The accents must be small, a handful of pixels each.

PRESENTATION: single object, isometric three-quarter view, centred on a plain \
flat background, with a soft light drop shadow beneath it.

No text or lettering, no logos, no watermarks, no people, no background scenery, \
no props other than the subject itself.

Do NOT draw a user interface, a phone screen, a browser window, buttons, icons \
or a website. Output the object alone, filling the frame."""

HEADER = """\
An isometric low-poly voxel model of {subject}."""

# The subject lines name the identifying FITTINGS, because those are what a
# sheet has to resolve. The rest of the shape is a box and needs no help.
SUBJECTS = {
    "dispensing_desk": "a single pharmacy dispensing bench bay, 0.9 m wide, with a thick overhanging worktop with a square front lip, a low back upstand, two stacked drawers of different depths with long horizontal pull handles and small label holders, framed by vertical side stiles and horizontal rails, on a recessed kick plinth",
    "dispensary_shelving": "one bay of shallow pharmacy dispensary shelving, open-fronted, with a thin label strip running along the front edge of each shelf and a small vertical divider at the back",
    "cd_cabinet": "a small steel controlled-drugs cabinet, floor standing on a plinth, one solid door with no glass, three heavy barrel hinges down one side, a keypad lock, a stubby vertical handle and a small warning plate near the top",
    "fridge_cabinet": "an upright pharmacy vaccine fridge with a full-height glass door, a slim vertical handle, horizontal rails top and bottom of the door, a small digital temperature readout above the door, and a condenser grille along the bottom",
    "sink_unit": "a stainless dispensary sink unit, one recessed rectangular basin set into a worktop, a tall mixer tap column with a single lever, two cupboard doors below, a recessed kick",
    "waste_station": "a pedal-operated clinical waste bin with a coloured lid, a foot pedal and visible linkage rod at the base, a hazard plate on the front, and a small separate sharps box sitting on the lid",
    "gondola_shelf": "one bay of free-standing retail gondola shelving, open both sides, a flat shelf board, two slim end posts, a back panel, and a price rail along the front edge of the shelf",
    "wall_shelving": "one bay of wall-mounted retail shelving, a single shelf board on two small triangular brackets, a slim back rail, and a price strip on the front edge",
    "serving_counter": "a pharmacy over-the-counter serving counter, a plain carcass with a thick overhanging worktop, a horizontal drawer band with a continuous pull rail across the front, a lower customer shelf projecting from the front face, on a recessed kick plinth",
    "till_block": "a small retail point-of-sale unit, a flat base, an angled screen on a short neck, a keypad on the base, and a small card reader on a short stalk beside it",
    "basket_stack": "a stack of five nesting plastic shopping baskets, open topped, with a folding handle bar across the top of the topmost basket",
    "promo_bin": "a free-standing retail promotional dump bin, a square open-topped bin with a thick rim, on a low base, with two slim posts at the back carrying a rectangular header card above it",
    "queue_barrier": "a retail queue barrier, two square posts with small square feet and one horizontal rail between them near the top",
    "consultation_booth": "a small free-standing pharmacy consultation booth, two solid walls meeting at a corner with a glazed upper panel in each, a door opening on the third side with a heavy door post and a header, a flat roof cap, a skirting at the base, and a small sign panel above the door",
    "consult_chair": "a simple consultation chair, a padded seat and padded back with piping around the edges, on four slim square steel legs with a stretcher between the front pair",
    "locker_bank": "one bay of a two-tier steel staff locker, an upper and a lower door, three horizontal vent slots near the top of each door, a stubby vertical handle and a small number plate on each door, a plinth at the base, and a sloped crown on top",
    "filing_cabinet": "a four-drawer steel filing cabinet, each drawer with a recessed horizontal pull and a small label holder, a plinth at the base and a thin top cap",
    "green_cross": "a wall-mounted illuminated pharmacy cross sign, a thick equal-armed cross on a square back plate, an inset lit face on the front of each arm, and a short stalk behind holding it off the wall",
    "aisle_sign": "a hanging retail aisle sign, a rectangular panel with a lettering band across it, a top rail, and two slim drop rods above it",
}

# Props are small enough that one sheet for the set beats one each.
PROPS_PROMPT = """\
A row of small pharmacy counter props, evenly spaced, all at the same scale, \
each shown three-quarter: a stack of loose paper; a clipboard with a metal clip; \
a mug with a handle; a pot of pens; a roll of till paper with a paper tail; a \
small counter weighing scale with a display; a pestle and mortar; a stapled \
paper prescription bag; an angled desk lamp; a stack of ring binders; a white \
cardboard dispensing pack with a printed label panel; an amber glass bottle with \
a white cap and a label; a stacking plastic tote. Plain flat background."""


def load_key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    # NO GEMINI KEY IS NOT NO IMAGE MODEL. This exited, which put the exit in
    # front of the fallback rather than behind it -- a run with only an
    # OpenRouter key would have died here without ever reaching the code that
    # can draw. Say which way the images are going and carry on.
    if not key:
        if not _openrouter_key():
            sys.exit("No GEMINI_API_KEY and no OPENROUTER_API_KEY. "
                     "Copy .env.example to .env and put a key in it.")
        _DIRECT_DEAD["why"] = "no GEMINI_API_KEY"
        print("  ! no GEMINI_API_KEY -- drawing through OpenRouter")
    return key


def prompt_for(name):
    if name == "props":
        return f"{PROPS_PROMPT}\n\n{STYLE}"
    subject = SUBJECTS.get(name)
    if not subject:
        sys.exit(f"Unknown module '{name}'. Known: {', '.join(sorted(SUBJECTS))}, props")
    return f"{HEADER.format(subject=subject)}\n\n{STYLE}"


MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


# The style-match instruction that precedes a prompt when references are given.
# Kept separate so callers that want a raw prompt (a texture atlas, say) can ask
# for the same references without also asking for a three-quarter hero shot.
REF_INSTRUCTION = (
    "The images above are the STYLE REFERENCE. Match their rendering style "
    "exactly: the same hard-edged blocky forms, the same dense pixel-art "
    "surface detail on flat faces, the same texel size, the same muted "
    "palette with small saturated accents. Do not copy their subject matter."
)


def _write(out_path, data_b64):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(data_b64))
    return out_path


def _openrouter_key():
    """The key `auto_prop` already loads. Read here rather than imported,
    because importing auto_prop from here would be a cycle."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "OPENROUTER_API_KEY":
                    return v.strip()
    return ""


# Set once the direct endpoint has said it has no credit, so the rest of a run
# does not spend a round trip per image rediscovering it. A depleted balance is
# not a transient.
_DIRECT_DEAD = {}


def _spent(code, detail):
    """Is this HTTP failure the account being out of money, rather than the
    request being wrong? 429 RESOURCE_EXHAUSTED covers both a depleted
    prepayment and a per-minute rate limit, and the two want the same thing
    here — draw it somewhere else — so they are not separated."""
    if code in (402, 429):
        return True
    return code == 403 and re.search(r"quota|billing|credit", detail, re.I) is not None


def _via_openrouter(prompt, out_path, refs, model, ref_instruction):
    """The same drawing, bought through OpenRouter instead of from Google.

    `google/gemini-3.1-flash-image` on OpenRouter IS Nano Banana 2 — the model
    named in the brief and the one every measurement in PROGRESS.md was taken
    against — so this fallback changes who is billed and nothing about what
    comes back. That is the reason it is the first choice here and the reason
    the cheaper models below are not: half the price for a different artist is
    a worse trade than full price for the same one, when the corpus numbers
    were measured on the same one.

    Measured: $0.067 an image at ~1120 completion tokens, against $0.0002 for a
    judge call. Images have always been the expensive half of a run.

    The response shape is OpenAI's, not Google's: the PNG comes back as a data
    URI in `choices[0].message.images[].image_url.url`, and the model will also
    write prose in `content` that nothing here reads.
    """
    key = _openrouter_key()
    if not key:
        raise RuntimeError("image API is out of credit and there is no "
                           "OPENROUTER_API_KEY in .env to fall back to")

    content = []
    for ref in refs:
        path = Path(ref)
        mime = MIME.get(path.suffix.lower(), "image/png")
        content.append({"type": "image_url", "image_url": {
            "url": f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()}})
    content.append({"type": "text",
                    "text": f"{ref_instruction}\n\n{prompt}" if refs else prompt})

    ladder = [OR_MODEL.get(model, f"google/{model}")]
    ladder += [m for m in OR_CHEAPER if m != ladder[0]]

    last = None
    for or_model in ladder:
        body = json.dumps({
            "model": or_model,
            "modalities": ["image", "text"],
            "messages": [{"role": "user", "content": content}],
        }).encode()
        req = urllib.request.Request(
            OR_ENDPOINT, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                payload = json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read()[:600].decode(errors="replace")
            last = f"{or_model}: HTTP {e.code} {detail}"
            if _spent(e.code, detail) and or_model != ladder[-1]:
                print(f"  ! {or_model}: no budget -- trying a cheaper model, "
                      f"which draws differently from the one the corpus was "
                      f"measured on")
                continue
            raise RuntimeError(last)

        for choice in payload.get("choices", []):
            for img in choice.get("message", {}).get("images") or []:
                url = img.get("image_url", {}).get("url", "")
                if "," in url:
                    return _write(out_path, url.split(",", 1)[1])
        # A refusal is a verdict on one drawing. Report it as one, with the
        # model's own words, so the caller's re-ask has something to quote.
        msg = payload.get("choices", [{}])[0].get("message", {})
        raise RuntimeError(f"no image from {or_model}: "
                           f"{(msg.get('refusal') or msg.get('content') or json.dumps(payload))[:400]}")
    raise RuntimeError(last or "no OpenRouter image model answered")


def generate_image(prompt, out_path, key, refs=(), model=MODEL, ref_instruction=REF_INSTRUCTION):
    """POST one prompt to the image model and write the PNG it returns.

    The single place this project talks to the image API. Everything else —
    concept sheets, texture atlases, shape references — is a prompt and an
    output path handed to this function, so there is one timeout, one response
    shape to get wrong, and one place to fix it.

    That is also why the out-of-credit fallback lives here and nowhere else.
    When the Gemini prepayment ran dry mid-session, NINE tools stopped at once —
    `tall_body`, `wide_art`, `quarter_view`, `paint_out`, `detail_sheet`,
    `segment_sheet`, `ps1_sheet`, `material_atlas`, `decal_sheet` — and not one
    of them had anything to do with billing. They all come through here, so one
    fallback restores all nine and none of them is changed. Adding a retry to
    any individual caller would have been the same fix nine times, eight of
    them wrong by the time the ninth was written.

    @param refs image paths used as STYLE reference, sent FIRST so the model
      reads them as context for the text. Several at once is the point: one
      image gives you one object's quirks, a set gives you the style underneath.
    """
    parts = []
    for ref in refs:
        path = Path(ref)
        parts.append({"inline_data": {
            "mime_type": MIME.get(path.suffix.lower(), "image/png"),
            "data": base64.b64encode(path.read_bytes()).decode(),
        }})
    parts.append({"text": f"{ref_instruction}\n\n{prompt}" if refs else prompt})

    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode()

    if _DIRECT_DEAD.get("why"):
        return _via_openrouter(prompt, out_path, refs, model, ref_instruction)

    req = urllib.request.Request(
        ENDPOINT.format(model=model) + f"?key={key}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read()[:600].decode(errors="replace")
        if not _spent(e.code, detail):
            raise
        _DIRECT_DEAD["why"] = f"HTTP {e.code}"
        print(f"  ! image API: HTTP {e.code} -- drawing through OpenRouter for "
              f"the rest of this run ({detail.strip()[:120]})")
        return _via_openrouter(prompt, out_path, refs, model, ref_instruction)

    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob:
                return _write(out_path, blob["data"])
    raise RuntimeError(f"no image in response: {json.dumps(payload)[:500]}")


def generate(name, key, refs=(), model=MODEL):
    """One module's concept sheet, into docs/concept/<name>.png."""
    return generate_image(
        prompt_for(name), OUT_DIR / f"{name}.png", key,
        refs=refs, model=model,
        ref_instruction=REF_INSTRUCTION + " Keep the same isometric presentation "
                        "on a plain background with a soft drop shadow.",
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate a concept sheet for a module.")
    ap.add_argument("module", nargs="*", help="module id, or 'props', or nothing with --all")
    ap.add_argument("--all", action="store_true", help="every module plus the prop sheet")
    ap.add_argument("--ref", nargs="*", default=[], help="style reference images; several is better than one")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    key = load_key()
    names = sorted(SUBJECTS) + ["props"] if args.all else args.module
    if not names:
        ap.error("name a module, or pass --all")

    for name in names:
        try:
            path = generate(name, key, refs=args.ref, model=args.model)
            print(f"  {name:22s} -> {path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")
        except Exception as exc:  # keep going; one refusal should not stop a batch
            print(f"  {name:22s} -> FAILED: {exc}", file=sys.stderr)
