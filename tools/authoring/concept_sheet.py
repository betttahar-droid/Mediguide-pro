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
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "concept"
MODEL = "gemini-3.1-flash-image"  # Nano Banana 2, the model the brief names
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

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
    if not key:
        sys.exit("No GEMINI_API_KEY. Copy .env.example to .env and put your key in it.")
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


def generate_image(prompt, out_path, key, refs=(), model=MODEL, ref_instruction=REF_INSTRUCTION):
    """POST one prompt to the image model and write the PNG it returns.

    The single place this project talks to the image API. Everything else —
    concept sheets, texture atlases, shape references — is a prompt and an
    output path handed to this function, so there is one timeout, one response
    shape to get wrong, and one place to fix it.

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

    req = urllib.request.Request(
        ENDPOINT.format(model=model) + f"?key={key}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        payload = json.load(r)

    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob:
                out_path = Path(out_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(base64.b64decode(blob["data"]))
                return out_path
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
