#!/usr/bin/env python3
"""Which image model to buy, measured on this pipeline's own bars.

    python3 tools/authoring/image_bench.py --cases 4
    python3 tools/authoring/image_bench.py --models google/gemini-3.1-flash-image,...

Authoring tool. NOT a build, CI or runtime dependency.

WHY. `concept_sheet` falls back to OpenRouter when the direct endpoint has no
credit, and it has to pick a model. The first version picked by argument -- the
same model the corpus was measured on, full price, on the grounds that a
cheaper artist is a different artist. That is a reasonable argument and it is
still an argument. This measures it.

WHAT IT SCORES WITH is the thing that already decides whether a drawing is used:
`wide_art.check` and `tall_body.check`, the arithmetic each tool runs on every
reply before compositing it. Nothing new is invented to judge models by, which
matters twice over -- a bar written for a benchmark is a bar nothing downstream
enforces, and the question here is not "which model draws better" but "which
model's drawings this pipeline ACCEPTS".

AND THE METRIC IS DOLLARS PER ACCEPTED DRAWING, not dollars per call. A model at
half price that is refused twice as often costs the same and takes three times
as long, and both tools re-ask up to three times on refusal, so a refusal is not
free -- it is another call at the same price. Price per call is the number that
makes a cheap model look good; price per drawing that survives the check is the
number that decides.

HONEST LIMITS. These are small samples -- the corpus offers 21 wide_art parts
and 17 tall_body props in total, and a run over all of them is real money. A
model that wins here by one drawing has not won. What the table can settle is a
factor-of-two difference; what it cannot settle is a close one, and when it is
close the tie goes to the model the corpus was measured on, because changing the
artist invalidates comparisons that are already written down.
"""
import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))

OR_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Every image-output model OpenRouter carries that is not priced like a studio.
# `image_output` is per token and a drawing is ~1100 of them, so the third
# column is what one picture actually costs.
#
#   google/gemini-3.1-flash-image        $0.00006/tok   ~$0.067   Nano Banana 2
#   google/gemini-3.1-flash-lite-image   $0.00003/tok   ~$0.034   Nano Banana 2 Lite
#   google/gemini-2.5-flash-image        $0.00003/tok   ~$0.034   Nano Banana
DEFAULT_MODELS = [
    "google/gemini-3.1-flash-image",
    "google/gemini-3.1-flash-lite-image",
    "google/gemini-2.5-flash-image",
]


def _key():
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("No OPENROUTER_API_KEY in .env")


def draw(model, prompt, ref_png, key, timeout=300):
    """One drawing, with what it cost. Returns (PIL.Image|None, usd, note)."""
    from PIL import Image
    import io
    body = json.dumps({
        "model": model,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64,"
                       + base64.b64encode(Path(ref_png).read_bytes()).decode()}},
            {"type": "text", "text": prompt},
        ]}],
    }).encode()
    req = urllib.request.Request(
        OR_ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        return None, 0.0, f"HTTP {e.code} {e.read()[:120].decode(errors='replace')}"
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}"
    usd = float((d.get("usage") or {}).get("cost") or 0.0)
    for ch in d.get("choices", []):
        for im in ch.get("message", {}).get("images") or []:
            url = im.get("image_url", {}).get("url", "")
            if "," in url:
                return (Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))),
                        usd, "")
    msg = (d.get("choices") or [{}])[0].get("message", {})
    return None, usd, "refused: " + str(msg.get("refusal") or msg.get("content"))[:90]


# ------------------------------------------------------------------ the cases

def wide_cases(limit):
    """Real wide_art asks: a part composed on a magenta canvas of the width the
    prop needs, judged by wide_art.check."""
    from PIL import Image
    import wide_art as wa
    out = []
    for lj in sorted((ROOT / "tools/img2threejs-work").glob("*/layers_front.json")):
        d = lj.parent
        names, wide = wa.candidates(d, "front")
        if not names or wide < wa.MIN_WIDE:
            continue
        for n in names:
            src = d / "parts" / f"{n}.png"
            if not src.exists():
                continue
            crop = Image.open(src).convert("RGBA")
            W2 = max(crop.width + 8, int(round(crop.width * wide)))
            pad = (W2 - crop.width) // 2
            if pad < 4:
                continue
            ask = Image.new("RGB", (W2, crop.height), wa.MAGENTA)
            ask.paste(crop.convert("RGB"), (pad, 0))
            out.append({
                "id": f"{d.name}/{n}",
                "kind": "wide",
                "ask": ask,
                "prompt": wa.PROMPT.format(asset=d.name.split("_", 1)[-1].replace("_", " "),
                                           part=n.replace("_", " ")),
                "check": lambda got, crop=crop, pad=pad, W2=W2: wa.check(
                    crop, got.convert("RGB").resize((W2, crop.height), Image.LANCZOS),
                    pad, W2),
            })
            if len(out) >= limit:
                return out
    return out


def tall_cases(limit):
    """Real tall_body asks: a magenta band opened across the body at the cut the
    tool chose, judged by tall_body.check."""
    from PIL import Image
    import tall_body as tb
    out = []
    for sj in sorted((ROOT / "tools/img2threejs-work").glob("*/strips_front.json")):
        d = sj.parent
        band, hx = tb.needs(d, "front")
        if not band or hx < tb.MIN_TALL:
            continue
        bg = d / "bg_front.png"
        if not bg.exists():
            continue
        rgba = Image.open(bg).convert("RGBA")
        W, H = rgba.size
        flat = Image.alpha_composite(
            Image.new("RGBA", rgba.size, (0, 0, 0, 255)), rgba).convert("RGB")
        cut, _cover, _edge = tb.place_cut(d, band, H, "front")
        if cut is None:
            continue                 # no row wide enough: this prop stretches
        extra = max(8, int(round(H * (hx - 1))))
        ask = Image.new("RGB", (W, H + extra), tb.MAGENTA)
        ask.paste(flat.crop((0, 0, W, cut)), (0, 0))
        ask.paste(flat.crop((0, cut, W, H)), (0, cut + extra))
        out.append({
            "id": f"{d.name}/band",
            "kind": "tall",
            "ask": ask,
            "prompt": tb.PROMPT.format(
                asset=d.name.split("_", 1)[-1].replace("_", " ")),
            "check": lambda got, flat=flat, cut=cut, extra=extra, W=W, H=H: tb.check(
                flat, got.convert("RGB").resize((W, H + extra), Image.LANCZOS),
                cut, extra, W, H),
        })
        if len(out) >= limit:
            return out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--cases", type=int, default=3,
                    help="how many of each kind (wide, tall)")
    ap.add_argument("--out", default=str(ROOT / "tools/authoring/image_bench.json"))
    args = ap.parse_args()

    key = _key()
    cases = wide_cases(args.cases) + tall_cases(args.cases)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"{len(cases)} case(s) x {len(models)} model(s) = "
          f"{len(cases) * len(models)} drawing(s)\n")
    for c in cases:
        print(f"  {c['kind']:5} {c['id']}")
    print()

    scratch = Path("/tmp/image_bench")
    scratch.mkdir(exist_ok=True)
    rows = {}
    for m in models:
        ok = n = 0
        usd = 0.0
        secs = 0.0
        why = []
        for c in cases:
            p = scratch / "ask.png"
            c["ask"].save(p)
            t0 = time.time()
            got, cost, note = draw(m, c["prompt"], p, key)
            secs += time.time() - t0
            usd += cost
            n += 1
            if got is None:
                why.append(f"{c['id']}: {note}")
                print(f"  {m:38} {c['id']:34} NO IMAGE  {note[:40]}")
                continue
            try:
                bad = c["check"](got)
            except Exception as e:
                bad = f"check raised {type(e).__name__}: {e}"
            if bad:
                why.append(f"{c['id']}: {bad}")
                print(f"  {m:38} {c['id']:34} refused   {str(bad)[:60]}")
            else:
                ok += 1
                print(f"  {m:38} {c['id']:34} ACCEPTED")
        rows[m] = {"accepted": ok, "asked": n, "usd": round(usd, 4),
                   "secs": round(secs, 1),
                   "usd_per_accepted": round(usd / ok, 4) if ok else None,
                   "refusals": why}

    print(f"\n  {'model':38} {'accepted':>10} {'$ total':>9} {'$/accepted':>11} {'s/call':>8}")
    for m, r in rows.items():
        pa = f"{r['usd_per_accepted']:.4f}" if r["usd_per_accepted"] else "  never"
        print(f"  {m:38} {r['accepted']:>4}/{r['asked']:<5} {r['usd']:>9.4f} "
              f"{pa:>11} {r['secs'] / max(1, r['asked']):>8.1f}")
    Path(args.out).write_text(json.dumps(rows, indent=1))
    print(f"\n  -> {args.out}")


if __name__ == "__main__":
    main()
