# Running the prop maker entirely on your own machine

The honest headline: **the tool is already a local application.** It is Python,
a vite dev server and a headless Chromium — all of it runs on your PC today.
The only things that leave the machine are the model calls, and those go through
exactly three functions. Two backends now sit behind them.

```
images   concept_sheet.generate_image()  ->  comfy_backend  ->  your ComfyUI
chat     auto_prop.glm()                 ->  local_llm      ->  your Ollama
vision   gemini_judge.vision_json()      ->  local_llm      ->  your Ollama
```

Nine tools call the first, fifteen call the second and third, and none of them
changes.

## What actually moves local, and what does not

This is the part to read before deciding. The split is not "local vs paid", it
is **checked vs unchecked** — the repo's own rule, *the model authors and names;
arithmetic measures and verifies*.

### Moves cleanly (most of the bill)

| stage | calls/prop | why it fits |
|---|---|---|
| `paint_out` | 1.07 | It paints the hole magenta and asks for it filled. **That is an inpainting mask.** A ComfyUI graph *cannot* touch a pixel outside the mask — which is exactly what paint_out's docstring says it wants and could not enforce. An audit found it accepting a redrawn fitting in **20% of holes**; a hard mask makes that impossible rather than merely checked. |
| `wide_art` | 0.12 | Outpainting. Same magenta convention. |
| `tall_body` | 0.05 | Outpainting. Same convention. |
| `scale_rules` | vision | The reply is **verified**: `strip_slice` checks the named rows are really bare and drops the rest. Measured today — a free 8B vision model named a usable place where the paid model returned `null`, and that prop's repeat score went `+0.480 → +0.102`. |
| `region_parts` | vision | Re-checked by `settle_parts`, `feature_intent` and the acceptance gate. |
| `side_profile`, `top_profile` | vision | Scored against the drawing by `geometry_audit`, per prop, as a number. |

`comfy_backend.split_magenta()` does the conversion, verified on a real prop:
**67 of 67 fitting holes came back >90% masked**, and a plain elevation with no
magenta correctly yields no mask.

### Does not move cleanly

| stage | calls/prop | problem |
|---|---|---|
| `auto_prop.author_brief` | 1.00 | **The ask that commissions the sheet, and nothing checks it.** Run on a 3B model it wrote "the sides and bottom must be visible and not hidden by the cabinet" into the FRONT view instruction -- perspective, not elevation -- and Nano Banana drew exactly that. `gate()` passed all four (it measures fill and bounding box); only the cross-view footprint check noticed, and only on the top. Same class as the judges: unverified, so a weak model degrades it invisibly. |
| `ps1_sheet` | 1.00 | Four orthographic elevations of one **invented** object, side by side, one scale, shared baseline. Multi-view consistency is diffusion's known weak spot. Expect to keep buying this, or draw it once per asset and reuse it. |
| `segment_sheet` | 0.65 | Not generation at all — it asks *which region is which fitting*. Belongs to a local VLM, not ComfyUI. |
| the two judges | per round | **Nothing grades the grader.** A weak model here degrades silently. Note this is already true of the paid judges: `judge_bench` puts both at chance on the one fault class it can score, and CLAUDE.md records both scoring a cabinet with five stacked marquees level with the corrected one beside it. Running them locally is not obviously worse — it is the same unmeasured channel. |

## Hardware

The asks are small images (~250×620) and short schema replies, not 4K art.

- **8 GB VRAM** — SDXL inpainting + a 7B vision model, one at a time. Workable.
- **12–16 GB** — both resident, comfortable. This is the sweet spot.
- **24 GB+** — Flux Fill for inpainting, a larger VLM, no juggling.
- **CPU only** — Ollama will run (slowly); ComfyUI inpainting will be painful.
  The pipeline makes ~3 image calls per prop, so budget minutes per prop.

## Setup

```bash
# 1. Ollama — text and vision
ollama serve
ollama pull qwen2.5vl:7b        # vision: elevations, regions, judging
ollama pull qwen3:8b            # text: prompt authoring

# 2. ComfyUI — images. Any inpainting checkpoint; SDXL-inpaint or Flux Fill.
#    Build a graph in the UI, then Workflow -> Export (API).
#    Write these placeholders into the fields the tool should fill:
#      {PROMPT}  {IMAGE}  {MASK}  {SEED}
#    {IMAGE} and {MASK} go in the `image` field of two LoadImage nodes.

# 3. Point the tool at both
export PROP_IMAGE_BACKEND=comfy
export COMFY_URL=http://127.0.0.1:8188
export COMFY_WORKFLOW=~/comfy/inpaint_api.json

export PROP_LLM_BACKEND=ollama
export OLLAMA_URL=http://127.0.0.1:11434
export LOCAL_VISION_MODEL=qwen2.5vl:7b
export LOCAL_TEXT_MODEL=qwen3:8b

# 4. Check both before building anything
python3 tools/authoring/comfy_backend.py --check
python3 tools/authoring/local_llm.py --check

# 5. The dev server the renderer needs, as always
npx vite --port 5173 &
```

`--check` on the image backend reports which placeholders it found in your
workflow and warns if `{MASK}` is missing, because without it `paint_out`,
`wide_art` and `tall_body` will refuse — their ask *is* an inpaint.

## Two deliberate choices

**Neither backend falls back to a paid API.** If you set
`PROP_IMAGE_BACKEND=comfy` and ComfyUI is down, the call raises. Every caller
already handles a drawing that did not arrive — turning a misconfigured local
server into an OpenRouter bill is the opposite of what you asked for.

**The magenta is replaced before the latent is built.** A sampler handed pure
magenta as its starting point returns magenta-tinted fill at low denoise, so the
hole is flooded with the mean of the material around it first — the same trick
the arithmetic fill uses, giving the sampler a neutral, in-palette start.

## The realistic plan

1. Move `paint_out` local first. It is the biggest line in the bill, it is the
   stage the audit found broken, and a hard mask is a **stronger** guarantee
   than the paid path can give.
2. Add `wide_art` and `tall_body` — same convention, same graph.
3. Move the verified vision calls (`scale_rules`, `region_parts`, the profiles).
   Arithmetic catches a bad answer, so the downside is a retry.
4. Leave `ps1_sheet` paid until you have tried a multi-view approach, or draw
   the four elevations once per asset by hand. One good sheet is reusable.
5. The judges are a separate question in both worlds. Do not let "it is local
   now" be the reason you stop measuring them.

Nothing in the repo's checks changes: `paint_out`'s colour, grain and
*still-the-fitting* bars, `wide_art`'s aspect and resemblance bars,
`geometry_audit`, `scale_check` and the acceptance gate all run identically and
are backend-blind. That is the point — **you can swap the models precisely
because the arithmetic does not care who drew the picture.**
