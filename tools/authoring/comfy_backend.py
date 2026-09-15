#!/usr/bin/env python3
"""Draw through a local ComfyUI instead of a paid image API.

    export PROP_IMAGE_BACKEND=comfy
    export COMFY_URL=http://127.0.0.1:8188
    export COMFY_WORKFLOW=tools/authoring/comfy/inpaint.json   # yours
    python3 tools/authoring/make_prop.py "arcade cabinet" ...

    python3 tools/authoring/comfy_backend.py --check     # is it reachable?

Authoring tool. NOT a build, CI or runtime dependency.

WHY THIS IS A SMALL CHANGE AND NOT A REWRITE. Every image this project has ever
bought goes through ONE function -- `concept_sheet.generate_image(prompt,
out_path, refs)`. Nine tools call it and none of them knows what is on the other
side; that is the same seam the OpenRouter fallback was hung on. A second
backend is a branch in one place.

AND THE ASKS ARE ALREADY SHAPED FOR IT, which is the part worth understanding
before judging whether this can work. `paint_out`, `wide_art` and `tall_body`
all build their request the same way: take the elevation, paint the region the
model must supply in PURE MAGENTA (255, 0, 255), and ask for the magenta to be
filled. That is an inpainting mask expressed in-band -- the file already carries
exactly the information a ComfyUI inpainting graph wants, and this module only
has to separate the two channels again:

    magenta pixels  ->  the mask     (what the model may draw)
    everything else ->  the latent   (what it must leave alone)

Those three tools are the biggest line in the bill -- `paint_out` alone is 1.07
calls per prop against a total of 3.32 -- and `paint_out` is also the stage a
corpus audit just found accepting a redrawn fitting in 20% of its holes. A hard
mask is a stronger guarantee than a sentence asking nicely: an inpainting graph
CANNOT touch a pixel outside the mask, which is precisely what paint_out's
docstring says it wants and could not enforce.

WHAT WILL NOT WORK, SAID PLAINLY. `ps1_sheet` asks for four orthographic
elevations of one invented object, side by side, at one scale, sharing a
baseline. That is a multi-view consistency problem and diffusion models are bad
at it; expect to keep buying that one, or to draw it once per asset by hand and
reuse it. `segment_sheet` is not generation at all -- it asks which region is
which fitting -- and belongs to a local vision-language model (Ollama, LM Studio)
rather than to ComfyUI. Same for the two judges.

So the realistic split, per prop, from the corpus:

    paint_out   1.07  ->  ComfyUI inpaint      local
    wide_art    0.12  ->  ComfyUI outpaint     local
    tall_body   0.05  ->  ComfyUI outpaint     local
    other_side  0.34  ->  ComfyUI img2img      local, needs checking
    ps1_sheet   1.00  ->  stays paid, or hand-drawn once per asset
    segment     0.65  ->  a local VLM, not this

THE WORKFLOW IS YOURS, NOT MINE. Every ComfyUI install has different
checkpoints, different node ids and different samplers, so hardcoding a graph
here would be a graph that works on one machine. Instead you export a workflow
from ComfyUI (Workflow -> Export (API)) and mark the places this tool should
fill in, with these four placeholders anywhere in any string value:

    {PROMPT}        the text the calling tool wrote
    {IMAGE}         filename of the uploaded init image  (LoadImage.image)
    {MASK}          filename of the uploaded mask        (LoadImage.image)
    {SEED}          a fresh integer each call

A graph with no {MASK} is used for the asks that have no magenta in them.
`--check` reports what it found and prints the placeholders it will substitute.

NO SILENT FALLBACK TO A PAID API. If you asked for local, a failure here raises
rather than quietly spending money on OpenRouter -- the opposite choice would
turn a broken ComfyUI into a bill. That is deliberate and is the one place this
module differs from the OpenRouter fallback it sits beside.
"""
import argparse
import io
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MAGENTA = (255, 0, 255)
# How far from pure magenta still counts as mask. The three tools write the
# constant exactly, but a PNG that has been through a resize on the way in has
# soft edges, and a hard equality test would leave a one-pixel rind of unmasked
# magenta all round every hole -- which is the fault paint_out already guards
# against with its own `magenta left` check.
MAGENTA_TOL = 60


def url():
    return os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")


def enabled():
    return os.environ.get("PROP_IMAGE_BACKEND", "").lower() in ("comfy", "comfyui")


def _get(path, timeout=15):
    with urllib.request.urlopen(f"{url()}{path}", timeout=timeout) as r:
        return r.read()


def reachable(timeout=6):
    """(ok, detail). Never raises: --check wants to report, not crash."""
    try:
        d = json.loads(_get("/system_stats", timeout))
        dev = (d.get("devices") or [{}])[0]
        return True, (f"{dev.get('name', 'device?')} "
                      f"{int(dev.get('vram_total', 0) / 2**30)}GB vram")
    except Exception as e:                                    # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:90]}"


def split_magenta(path):
    """(init, mask) for an ask that carries a magenta region, else (img, None).

    The mask is WHITE where the model may draw, which is ComfyUI's convention
    for a LoadImage used as a mask via ImageToMask/InvertMask -- and the one
    that matches "white is what you fill" in every inpainting graph people
    actually export.
    """
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    hit = ((abs(a[..., 0] - MAGENTA[0]) < MAGENTA_TOL)
           & (abs(a[..., 1] - MAGENTA[1]) < MAGENTA_TOL)
           & (abs(a[..., 2] - MAGENTA[2]) < MAGENTA_TOL))
    if not hit.any():
        return im, None
    # THE MAGENTA IS REPLACED, NOT LEFT UNDER THE MASK. A sampler that is
    # given magenta as its starting latent will happily return magenta-tinted
    # fill at low denoise. Flooding the hole with the mean of what surrounds it
    # is the same trick the arithmetic fill uses and gives the sampler a
    # neutral, in-palette place to start.
    out = a.copy()
    if (~hit).any():
        out[hit] = a[~hit].reshape(-1, 3).mean(0).astype(int)
    init = Image.fromarray(out.astype("uint8"))
    mask = Image.fromarray((hit * 255).astype("uint8"), mode="L")
    return init, mask


def upload(im, name):
    """POST an in-memory image to ComfyUI's input folder; return its filename."""
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    body, bnd = [], f"----prop{uuid.uuid4().hex}"
    body.append(f"--{bnd}\r\nContent-Disposition: form-data; name=\"image\"; "
                f"filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n"
                .encode())
    body.append(buf.getvalue())
    body.append(f"\r\n--{bnd}\r\nContent-Disposition: form-data; "
                f"name=\"overwrite\"\r\n\r\ntrue\r\n--{bnd}--\r\n".encode())
    data = b"".join(body)
    req = urllib.request.Request(
        f"{url()}/upload/image", data=data, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={bnd}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["name"]


def load_workflow(need_mask):
    """The user's exported API graph, as a dict."""
    p = os.environ.get("COMFY_WORKFLOW")
    if not p:
        raise RuntimeError(
            "set COMFY_WORKFLOW to an API-format workflow exported from "
            "ComfyUI (Workflow -> Export (API)), with {PROMPT}, {IMAGE}, "
            "{MASK} and {SEED} written into the fields this tool should fill")
    g = json.loads(Path(p).read_text())
    if need_mask and "{MASK}" not in json.dumps(g):
        raise RuntimeError(
            f"{p} has no {{MASK}} placeholder, but this ask carries a magenta "
            f"region to fill. Export an INPAINTING workflow, or point "
            f"COMFY_WORKFLOW at one for these calls.")
    return g


def fill(graph, prompt, image_name, mask_name, seed):
    """Substitute the placeholders through every string in the graph."""
    sub = {"{PROMPT}": prompt, "{IMAGE}": image_name or "",
           "{MASK}": mask_name or "", "{SEED}": str(seed)}

    def walk(v):
        if isinstance(v, str):
            for k, r in sub.items():
                if k in v:
                    # a lone {SEED} becomes a real int, not the string of one
                    if v == "{SEED}":
                        return int(r)
                    v = v.replace(k, r)
            return v
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(graph)


def run(graph, timeout=600):
    """Queue the graph, wait for it, return the first output image's bytes."""
    cid = uuid.uuid4().hex
    body = json.dumps({"prompt": graph, "client_id": cid}).encode()
    req = urllib.request.Request(f"{url()}/prompt", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            pid = json.load(r)["prompt_id"]
    except urllib.error.HTTPError as e:
        # ComfyUI answers a bad graph with a long, genuinely useful validation
        # body. Passing it through is the difference between "it failed" and
        # "node 12 wants a model you do not have".
        raise RuntimeError(f"ComfyUI rejected the graph: "
                           f"{e.read()[:600].decode(errors='replace')}")
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1.0)
        try:
            hist = json.loads(_get(f"/history/{pid}"))
        except Exception:                                     # noqa: BLE001
            continue
        if pid not in hist:
            continue
        entry = hist[pid]
        st = (entry.get("status") or {})
        if st.get("status_str") == "error" or st.get("completed") is False:
            raise RuntimeError(f"ComfyUI run failed: {json.dumps(st)[:400]}")
        for out in (entry.get("outputs") or {}).values():
            for img in (out.get("images") or []):
                q = (f"/view?filename={urllib.parse.quote(img['filename'])}"
                     f"&subfolder={urllib.parse.quote(img.get('subfolder',''))}"
                     f"&type={img.get('type','output')}")
                return _get(q, timeout=120)
        if entry.get("outputs"):
            raise RuntimeError("ComfyUI finished with no image in its outputs "
                               "-- does the graph end in SaveImage?")
    raise RuntimeError(f"ComfyUI did not finish within {timeout}s")


def generate(prompt, out_path, refs=()):
    """The `generate_image` contract, served locally. Writes out_path."""
    from PIL import Image
    init = mask = None
    if refs:
        init, mask = split_magenta(refs[0])
    stem = uuid.uuid4().hex[:10]
    iname = upload(init, f"prop_{stem}.png") if init is not None else None
    mname = upload(mask, f"prop_{stem}_mask.png") if mask is not None else None
    # TWO UPLOADS MUST NOT COME BACK AS ONE FILE. ComfyUI answers with the name
    # it actually saved under, and a server that dedupes or rewrites names
    # could hand back the same one twice -- after which the graph would use the
    # elevation as its own mask and inpaint the entire canvas, silently. It is
    # two lines to refuse, and the failure is invisible otherwise.
    if mname is not None and mname == iname:
        raise RuntimeError(
            f"ComfyUI returned the same filename for the image and the mask "
            f"({iname!r}); the graph would use the elevation as its own mask")
    g = fill(load_workflow(mask is not None), prompt, iname, mname,
             random.randint(1, 2**31 - 1))
    data = run(g)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    # AND BACK TO THE SIZE THAT WAS ASKED FOR. Every caller measures the reply
    # against the canvas it sent -- wide_art and tall_body refuse at 12% off
    # the asked aspect -- and a sampler works at its own multiple of 8. Sending
    # it back at the ref's exact size turns a guaranteed refusal into a fair
    # test of what was drawn.
    if init is not None:
        im = Image.open(out_path)
        if im.size != init.size:
            im.convert("RGB").resize(init.size, Image.LANCZOS).save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ref", default=None,
                    help="an ask image, to report the mask it would derive")
    args = ap.parse_args()
    print(f"  backend enabled : {enabled()}  "
          f"(PROP_IMAGE_BACKEND={os.environ.get('PROP_IMAGE_BACKEND','unset')})")
    print(f"  COMFY_URL       : {url()}")
    ok, detail = reachable()
    print(f"  reachable       : {'yes' if ok else 'NO'}  {detail}")
    wf = os.environ.get("COMFY_WORKFLOW")
    print(f"  COMFY_WORKFLOW  : {wf or 'unset'}")
    if wf and Path(wf).exists():
        txt = Path(wf).read_text()
        found = [k for k in ("{PROMPT}", "{IMAGE}", "{MASK}", "{SEED}")
                 if k in txt]
        print(f"  placeholders    : {' '.join(found) or 'NONE FOUND'}")
        if "{MASK}" not in found:
            print("    ! no {MASK}: paint_out, wide_art and tall_body will "
                  "refuse, because their ask is an inpaint")
    elif wf:
        print("  placeholders    : file not found")
    if args.ref:
        init, mask = split_magenta(args.ref)
        if mask is None:
            print(f"  {args.ref}: no magenta -- would run as txt2img/img2img")
        else:
            import numpy as np
            f = (np.asarray(mask) > 127).mean()
            print(f"  {args.ref}: {init.size[0]}x{init.size[1]}, "
                  f"{100*f:.1f}% of it is mask")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
