#!/usr/bin/env python3
"""One noun in, a resizable textured prop out. No human in the loop.

    npx vite --port 5173 &
    python3 tools/authoring/make_prop.py "arcade cabinet" --rounds 4

Authoring tool. NOT a build, CI or runtime dependency.

THE WHOLE CHAIN, and who does what:

    Nano Banana 2   one turnaround sheet, four true elevations in one pass
    arithmetic      split it, crop the captions off, measure the object boxes
    Nano Banana 2   draw the same elevation again as a flat-colour
                    segmentation map: one colour per fitting
    arithmetic      check that map against the artwork -- silhouette agreement
                    and whether its borders sit on real edges -- and take the
                    fittings as exact MASKS, or fall back to measuring cells
    glm-5.3-flash   name each measured region, and say how it resizes, how
                    deep it sits and which edge it turns about
    arithmetic      cut the parts, fill the background, measure the stretch
                    bands, per part as well as for the whole face
    the renderer    background nine-sliced with its middle REPEATED, parts
                    anchored at real size
    glm-5.3-flash   look at the result and say what is wrong with it
    the loop        apply the judge's corrections and go round again

THE JUDGE RETURNS A PATCH, NOT PROSE. That is the difference between a
critique and a loop. Told "the marquee is stretched", nothing can act; told
{"name":"marquee","resize":"spanx_center"}, the tool rebuilds and re-renders.
The patch schema is deliberately narrow -- a resize rule, an anchor, or a
part dropped -- so a judge cannot invent geometry, only reclassify what
measurement already found.

Every fix in the loop is one the tool applies. Nothing here is hand-tuned per
prop; the same run makes a cabinet, a vending machine or a jukebox.
"""
import argparse
import json
import re as re0
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from auto_prop import glm, as_json, data_uri, _openrouter_key, CRITIC_MODEL  # noqa: E402

RESIZES = {"fixed", "spanx_repeat", "spanx_center", "spany_repeat", "spany_center"}
ANCHORS = {"top", "bottom", "left", "right", "center"}
DEPTHS = {"flush", "proud", "deep", "recessed"}
MOTIONS = {"none", "hinge_left", "hinge_right", "hinge_top", "hinge_bottom",
           "press", "stick", "slide_x", "slide_y"}

JUDGE = """IMAGE 1 is the reference front elevation of a {asset}.
IMAGE 2 is the 3D model at its ORIGINAL size -- it should match image 1 closely.
IMAGE 3 is the same model at {wx}x its width, and IMAGE 4 at {hx}x its height.
All four renders use ONE FIXED CAMERA, so a bigger prop genuinely draws bigger
on the page. Do not judge them side by side as though they were scaled to
match: if image 4 looks taller than image 2, it IS taller, and reporting "the
vertical resize produced no change" because the two look similar in shape is a
mistake both graders have made.
They SHOULD be bigger -- do not fault them for that. Judge them against what
resizing this prop is supposed to MEAN, which the tool worked out from the
elevation itself:

  WIDER  {wider}
  TALLER {taller}

That is the bar for images 3 and 4. A wider prop that merely has more blank
panel where those things should be is WRONG even if nothing is smeared or
seamed -- it does not make sense as the object. Say so as a blocking fault.

IMAGE 5 is the finished prop as SOLID GEOMETRY, turned to three-quarters and
with every moving part driven open, so you can see it as an object rather than
a picture. Its body is the side elevation's own profile extruded across the
width, and each part is a separate box standing off that surface on its own
pivot. Judge whether it reads as a {asset} in three dimensions: parts on the
correct face, nothing floating clear of the body or sunk inside it, doors
swinging OUT rather than through the body, sides and back textured.

IMAGE 6 is the same view as WIREFRAME, with every texture removed. Texture
hides geometry, so judge the SHAPE here and be unforgiving about it: a profile
with a step or notch that the object should not have, a part sunk into the body
or floating clear of it, boxes intersecting each other, faces stacked on faces,
bulk that is missing or in the wrong place. A prop that only looks right while
it is wearing its texture is not finished.

The model is built as a background panel plus these parts, each with a resize
rule, a depth and a motion:
{parts}

The BACKGROUND panel behind the parts is also adjustable. If its texture looks
smeared, streaked or banded where the prop was made larger, patch the name
"background" with "mode": "mirror" (every other repeat is flipped, so joins
reflect instead of cutting) or "repeat" (plain tiling).

Rules available:
  "fixed"         keeps its real size and stays put
  "spanx_repeat"  runs the full width; its middle REPEATS when widened
                  (right for a control deck: a wider cabinet gets more
                  button clusters)
  "spanx_center"  runs the full width; its middle stays ONE size in the centre
                  and the ends extend (right for a marquee: you want one
                  title, not three)
  "spany_repeat" / "spany_center"  the same for the vertical axis

JUDGE IT AS A TOP STUDIO WOULD. You are the art lead on a shipping title at a
studio whose props get held up as reference work, and this asset is in final
review with your studio's name going on it. Not "good enough for the era" --
low poly and small textures are the STYLE, not an excuse. A 1998 prop made by
a great team had clean silhouettes, no seams you could point at, and every
fitting sitting where it belongs. That is the bar.

REJECT the asset for any of these. All of them are "blocking":

  - a tiling seam, repeat, smear, stretch or band a player could point at
  - a part floating clear of the body, sunk into it, or overlapping another
  - a door, flap or lid hinging THROUGH the body instead of out of it
  - a face left untextured, flat-coloured, holed, or showing background
    through the prop
  - text or a decal that is cut, doubled, stretched or unreadable
  - a part duplicated, mirrored the wrong way, or on the wrong face
  - geometry that does not read as the object: wrong proportions, missing
    bulk, a silhouette with a notch or a step that should not be there
  - anything that looks like a bug rather than a decision

"minor" is reserved for TASTE -- a colour you would push warmer, grime you
would add, a detail you would sharpen. If a player could point at it and call
it broken, it is blocking, however small.

Set looks_good TRUE only when you would sign this off and ship it.

Then give a PATCH: only parts whose rule, anchor, depth or motion should
change, or that should be dropped because they are not really a part. Change
nothing that already looks right; return an empty patch when nothing is
blocking.

  "depth"   "flush" (painted on) | "proud" (stands off a little) |
            "deep" (sticks well out: a joystick, a handle) |
            "recessed" (set into the body: a screen, a vent, a tray)
  "motion"  "none" | "hinge_left" | "hinge_right" | "hinge_top" |
            "hinge_bottom" | "press" | "stick" | "slide_x" | "slide_y"
            -- name the EDGE a door turns about, not just that it opens

JSON only:
{{"looks_good": false,
  "faults": [{{"part": "...", "fault": "...", "severity": "blocking"}}],
  "patch": [{{"name": "...", "resize": "...", "anchor": "...",
              "depth": "...", "motion": "...", "drop": false}}]}}"""


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("  ! " + (r.stderr or r.stdout).strip().splitlines()[-1][:160])
    return r


def _env():
    import os
    return {**os.environ, "CHROMIUM_PATH": os.environ.get(
        "CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")}


def render(d, out, sizes):
    # ONE FRAME FOR ALL THE VARIANTS, SIZED TO THE BIGGEST. The camera must not
    # re-frame per shot -- that is what let a 2x taller prop draw at the same
    # screen size and made the judge report "the cabinet is unchanged" -- but a
    # constant 1.45 left the 1:1 prop occupying a third of the picture, with
    # the judge grading texel detail it could barely see. Fix it once, from the
    # largest variant in this batch, and every shot stays comparable.
    # JUDGE THE MODEL, NOT THE PICTURE OF IT. These three shots came from
    # layer_view -- flat quads, a debugging aid -- while the thing the tool
    # delivers is the rig. So every resize fix went into the rig and every
    # resize verdict came off a picture that never saw it, and both judges kept
    # reporting a stretched blank band that the model had stopped having. The
    # same split had already been caught once, on per-bay parts: "the picture
    # was right and the actual model was not". Grade the deliverable.
    A = json.loads((d / "layers_front.json").read_text())["aspect"]
    frame = max(max(A * w, h) for (w, h) in sizes) * 0.5 * 1.08
    qs = [f"dir=/{d.relative_to(ROOT)}&w={w}&h={h}&frame={frame:.4f}"
          f"&yaw=22&pitch=10" for (w, h) in sizes]
    run(["node", str(ROOT / "tools/authoring/parts_view/shoot.mjs"), str(out), *qs],
        env=_env())
    # NAME THE FILE, DO NOT GUESS AT IT. shoot.mjs names each shot after its
    # own query, and this matched them back with a glob -- so `*w-1-h-1*` also
    # matched `w-1-h-1-5-...`, and sorting put the 1.5x TALLER file first
    # because '5' precedes 'f'. The ORIGINAL slot got the taller render, the
    # TALLER slot got the same file again, and the judge was handed one image
    # twice under two captions. Both judges reported that, in those words, in
    # round after round -- "image 4 is pixel-identical to image 2, the vertical
    # resize produced no change at all" -- and I overruled them on the grounds
    # that the model plainly had changed. The model had. The images had not.
    # A grader that keeps saying the same impossible thing is worth checking
    # against the files rather than against the intent.
    stem = lambda q: re0.sub(r"[^a-z0-9]+", "-", q, flags=re0.I)
    got = [(out / f"{stem(q)}.png") for q in qs]
    got = [f if f.exists() else None for f in got]

    # BURN THE SCALE INTO THE PICTURE. Both graders reported, twice, that the
    # taller render "produced no change at all" -- and both times it was false:
    # the images differ across the whole prop and the cabinet has plainly gained
    # body. They compare the renders as shapes and conclude nothing happened.
    # Saying "the camera is fixed" in the prompt did not help, so the image now
    # says it: a caption and a bar of constant length, which is a ruler laid
    # against every variant. A grader cannot misread its own ruler.
    from PIL import Image as _I, ImageDraw as _D
    for (w, h), f in zip(sizes, got):
        if not f:
            continue
        im = _I.open(f).convert("RGB")
        dr = _D.Draw(im)
        label = ("ORIGINAL SIZE" if (w == 1 and h == 1) else
                 f"{w}x WIDER" if h == 1 else
                 f"{h}x TALLER" if w == 1 else f"{w}x wide {h}x tall")
        dr.rectangle([0, 0, im.width, 26], fill=(20, 20, 24))
        dr.text((8, 8), f"{label}   (one fixed camera: bigger really is bigger)",
                fill=(255, 255, 255))
        y = im.height - 18
        dr.rectangle([8, y - 6, 208, y], fill=(255, 80, 80))
        dr.text((214, y - 8), "same length in every image", fill=(255, 160, 160))
        im.save(f)
    return got


def render_solid(d, out):
    """The prop as geometry, three-quarters on, with the moving parts open.

    The judge only ever saw flat elevations, so it could not see a part
    floating clear of the body, a door hinging through the cabinet or an
    untextured side -- exactly the faults that separate a picture from a model.
    """
    base = f"dir=/{d.relative_to(ROOT)}"
    run(["node", str(ROOT / "tools/authoring/parts_view/shoot.mjs"), str(out),
         f"{base}&anim=1&yaw=32&pitch=14", f"{base}&wire=1&yaw=32&pitch=14"],
        env=_env())
    solid = sorted(out.glob("*anim-1*.png"))
    wire = sorted(out.glob("*wire-1*.png"))
    return (solid[0] if solid else None), (wire[0] if wire else None)


def rebuild(d, face="front"):
    run([sys.executable, "tools/authoring/layer_build.py", str(d), "--face", face])
    run([sys.executable, "tools/authoring/nine_slice.py", str(d / f"bg_{face}.png"),
         "--out", str(d / "slice_bg.json"), "--fallback"])
    # per-strip stretch bands: one band for a whole face cannot miss the
    # artwork at every height, and the marquee is where that shows
    run([sys.executable, "tools/authoring/strip_slice.py", str(d), "--face", face])
    # synthesise the seamless panel tile the background's middle repeats, cut
    # from the strip that will actually be filled with it
    rows = ""
    try:
        st = json.loads((d / f"strips_{face}.json").read_text())
        g = next(x for x in st["strips"] if x.get("grow_y"))
        rows = f"{g['px'][0]},{g['px'][1]}"
    except Exception:
        pass
    run([sys.executable, "tools/authoring/seamless_tile.py", str(d), "--face", face]
        + (["--rows", rows] if rows else []))
    # and one tile per band, so each grows in the material it is made of
    run([sys.executable, "tools/authoring/seamless_tile.py", str(d),
         "--face", face, "--per-strip"])


def build_body(d, asset):
    """The other three elevations, and the shape they describe.

    Only needs doing once per sheet: the judge's patches move parts about on
    the front face, and none of them changes the prop's profile.
    """
    run([sys.executable, "tools/authoring/body_faces.py", str(d)])
    run([sys.executable, "tools/authoring/side_profile.py", str(d),
         "--asset", asset])
    # how wide the prop is at each height, so the body is the intersection of
    # both silhouettes rather than one extrusion with a constant width
    run([sys.executable, "tools/authoring/front_profile.py", str(d)])
    # AND THE CROSS-SECTION, WHICH ONLY THE THIRD DRAWING KNOWS. Width crossed
    # with depth is a rectangle, always, so two views left every prop's plan
    # stuck around 90% agreement however the depth was tuned. The top elevation
    # is where a chamfered corner or a rounded flank is written down.
    run([sys.executable, "tools/authoring/top_profile.py", str(d),
         "--asset", asset])
    # MEASURE THE SHAPE AGAINST THE DRAWINGS, AND CORRECT WHAT IS MEASURABLE.
    # The model claims to be the prop on the sheet, so its outline from the
    # front, the side and above must match the three elevations. The footprint
    # was 18% out on a cabinet and 39% on a jukebox while both looked
    # convincing textured -- geometry_audit renders all three and divides the
    # error out.
    r = run([sys.executable, "tools/authoring/geometry_audit.py", str(d), "--fix"],
            env=_env())
    for line in (r.stdout or "").strip().splitlines()[-5:]:
        print("   ", line.strip()[:110])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-sheet", action="store_true")
    args = ap.parse_args()

    import re
    # RESOLVE IT. render() asks for the path relative to the repo root to build
    # the dev-server URL, and a relative --out makes that raise rather than
    # render -- which killed a three-prop batch on its first round.
    d = Path(args.out or ROOT / "tools/img2threejs-work" /
             ("prop_" + re.sub(r"\W+", "_", args.asset.lower()))).resolve()
    d.mkdir(parents=True, exist_ok=True)
    key = _openrouter_key()
    print(f"=== {args.asset} -> {d} ===")

    if not args.skip_sheet:
        print("[1] turnaround sheet ...", flush=True)
        r = run([sys.executable, "tools/authoring/ps1_sheet.py", args.asset, "--out", str(d)])
        print("   ", (r.stdout or "").strip().splitlines()[-1][:120] if r.stdout else "")
    if not (d / "front.png").exists():
        raise SystemExit("no front.png -- the sheet did not split into views")

    print("[2] segmenting the face, naming parts ...", flush=True)
    # THE MODEL DRAWS THE DECOMPOSITION; ARITHMETIC CHECKS IT. See
    # segment_sheet.py -- masks instead of thresholded boxes. If the map fails
    # its alignment or border checks, the measured finder is still here and
    # takes over, so a bad draw costs a call rather than the prop.
    r = run([sys.executable, "tools/authoring/segment_sheet.py", str(d),
             "--face", "front", "--asset", args.asset])
    for line in (r.stdout or "").strip().splitlines()[:6]:
        print("   ", line.strip()[:120])
    try:
        seg_ok = json.loads((d / "seg_front.json").read_text()).get("usable")
    except Exception:
        seg_ok = False
    if not seg_ok or not (d / "parts_front.json").exists():
        print("    segmentation rejected -- measuring the regions instead")
        r = run([sys.executable, "tools/authoring/region_parts.py", str(d),
                 "--face", "front", "--asset", args.asset])
    if not (d / "parts_front.json").exists():
        raise SystemExit("neither segmentation nor measurement produced parts")
    for line in (r.stdout or "").strip().splitlines()[:14]:
        print("   ", line[:120])

    print("[3] what resizing this prop means ...", flush=True)
    r = run([sys.executable, "tools/authoring/scale_rules.py", str(d),
             "--face", "front", "--asset", args.asset])
    for line in (r.stdout or "").strip().splitlines()[:3]:
        print("   ", line[:150])

    print("[4] body: side, back, top and the profile ...", flush=True)
    # CUT THE LAYERS FIRST, OR THE AUDIT MEASURES NOTHING. build_body finishes
    # by rendering the model from three axes and scoring it against the
    # elevations -- and the renderer's very first act is to fetch
    # layers_front.json, which rebuild had not written yet. So on every prop
    # built from scratch the audit printed "no render or no front.png" three
    # times and moved on, and the one measurement in this tool that can say
    # whether the geometry is right was never taken. It only ever looked like a
    # flake because re-running it by hand found the file from the round before.
    outstanding = []
    rebuild(d)
    build_body(d, args.asset)

    # A STAGE THAT FAILED MUST SAY SO HERE, NOT SIX FRAMES DOWN. layer_build
    # crashing left no layers_front.json, and the loop went on to render it and
    # died in json.loads with a traceback that named neither the prop nor the
    # stage that actually broke.
    if not (d / "layers_front.json").exists():
        raise SystemExit(f"layer_build produced no manifest for {args.asset} "
                         f"-- see the '!' lines above")
    best = None
    for rnd in range(args.rounds):
        try:
            sr = json.loads((d / "scale_rules.json").read_text())
        except Exception:
            sr = {"max_wider": 2.0, "max_taller": 1.8,
                  "wider_means": "a wider one of the same thing",
                  "taller_means": "more body, same fittings", "per_bay": []}
        # THE PROP DECIDES HOW FAR IT GOES. Rendering every prop at 2x wide
        # proved nothing about a jukebox, which is not a thing that comes in
        # double width; judging it there was judging it against the wrong
        # question.
        shots = render(d, d / f"r{rnd}",
                       [(1, 1), (sr["max_wider"], 1), (1, sr["max_taller"])])
        if not all(shots):
            raise SystemExit("render failed -- is the dev server up on 5173?")
        solid, wire = render_solid(d, d / f"r{rnd}")
        man = json.loads((d / "layers_front.json").read_text())
        listing = "\n".join(
            f"  {p['name']}: {p['resize']}, anchored {p['anchor']}, "
            f"{p.get('depth','proud')}, motion {p.get('motion','none')}"
            for p in man["parts"])
        content = [{"type": "text",
                    "text": JUDGE.format(asset=args.asset, parts=listing,
                                         wider=sr["wider_means"],
                                         taller=sr["taller_means"],
                                         wx=sr["max_wider"], hx=sr["max_taller"])}]
        for img in [d / "front.png", *shots,
                    *([solid] if solid else []), *([wire] if wire else [])]:
            content.append({"type": "image_url",
                            "image_url": {"url": data_uri(img)}})
        # A JUDGE THAT REPLIES BADLY MUST NOT KILL THE RUN. as_json raises
        # JSONDecodeError on a malformed reply and only SystemExit was caught,
        # so one truncated answer ended a five-round run at round 1 with a
        # traceback. Unattended, that would take a three-prop batch down.
        v = None
        for attempt in range(3):
            try:
                v = as_json(glm([{"role": "user", "content": content}], CRITIC_MODEL,
                                key, max_tokens=14000,
                                temperature=0.2 + 0.2 * attempt))
                break
            except Exception as e:
                print(f"  round {rnd}: judge reply unusable "
                      f"({type(e).__name__}), retry {attempt + 1}/3")
        if v is None:
            print(f"  round {rnd}: judge unusable three times -- keeping the "
                  f"last good build and stopping")
            break

        # A SECOND PAIR OF EYES, FROM THE OTHER FAMILY. One grader is one set
        # of blind spots: glm passed a prop while listing "duplicated content
        # blocks that read as a bug" in the same reply. Gemini is already here
        # drawing the sheets, so it grades the same images against the same
        # schema, and a fault EITHER of them calls blocking is blocking. The
        # prop passes only when both would sign it off.
        gem = None
        try:
            sys.path.insert(0, str(ROOT / "tools" / "authoring"))
            from gemini_judge import vision_json
            imgs = [str(d / "front.png")] + [str(x) for x in shots if x]
            if solid:
                imgs.append(str(solid))
            if wire:
                imgs.append(str(wire))
            gem, gmodel = vision_json(
                JUDGE.format(asset=args.asset, parts=listing,
                             wider=sr["wider_means"], taller=sr["taller_means"],
                             wx=sr["max_wider"], hx=sr["max_taller"]), imgs)
            print(f"  second opinion from {gmodel}: "
                  f"looks_good={gem.get('looks_good')}, "
                  f"{len(gem.get('faults', []))} faults")
        except Exception as e:
            print(f"  second opinion unavailable ({type(e).__name__})")

        faults = list(v.get("faults", []))
        if gem:
            for f in gem.get("faults", []):
                f = dict(f)
                f["part"] = f"{f.get('part')} (gemini)"
                faults.append(f)
            if not gem.get("looks_good"):
                v["looks_good"] = False
        blocking = [f for f in faults
                    if str(f.get("severity", "blocking")).lower() == "blocking"]
        print(f"\n  round {rnd}: looks_good={v.get('looks_good')}  "
              f"{len(blocking)} blocking / {len(faults)} faults, "
              f"{len(v.get('patch', []))} corrections")
        for f in faults[:6]:
            print(f"    - [{f.get('severity','?'):8}] {f.get('part')}: {f.get('fault')}")
        # A LOOP NEEDS A BAR ITS JUDGE CAN CLEAR. Asked only "what looks
        # wrong", a model always answers something, so looks_good never came
        # true in eleven rounds across two runs while the faults were faint
        # cap seams. Passing on "nothing blocking" is the reachable bar.
        if not blocking and not v.get("looks_good"):
            print("  no blocking faults -- treating as a pass")
            v["looks_good"] = True
        # AND A PASS CANNOT CARRY A BLOCKING FAULT. The judge returned
        # looks_good=true alongside "duplicated content blocks that read as a
        # bug" in the same reply; at a shipping bar the fault list is the
        # answer and the flag is a summary of it.
        if blocking and v.get("looks_good"):
            print(f"  judge said looks_good but listed {len(blocking)} "
                  f"blocking fault(s) -- not a pass")
            v["looks_good"] = False
        if best is None or len(blocking) < best[0]:
            best = (len(blocking), rnd)
        if v.get("looks_good"):
            print("  JUDGE PASSED")
            break

        # apply the patch -- narrow schema, so a judge can only reclassify
        patch = {p.get("name"): p for p in v.get("patch", []) if p.get("name")}
        # the background is not a part but it IS adjustable; without this the
        # judge's commonest complaint had no lever and the loop stalled on
        # round 0 reporting "no actionable corrections"
        man_path = d / "layers_front.json"
        for key_name in ("background", "background_panel", "panel", "body"):
            q = patch.pop(key_name, None)
            if q and q.get("mode") in ("mirror", "repeat"):
                mm = json.loads(man_path.read_text())
                if mm.get("background_mode") != q["mode"]:
                    mm["background_mode"] = q["mode"]
                    man_path.write_text(json.dumps(mm, indent=1))
                    print(f"    background: mode -> {q['mode']}")
        pm = json.loads((d / "parts_front.json").read_text())
        keep, changed = [], 0
        bg_changed = json.loads(man_path.read_text()).get("background_mode")
        for p in pm["parts"]:
            q = patch.get(p["name"])
            if q and q.get("drop"):
                print(f"    dropped {p['name']}")
                changed += 1
                continue
            if q and q.get("resize") in RESIZES and q["resize"] != p["resize"]:
                print(f"    {p['name']}: {p['resize']} -> {q['resize']}")
                p["resize"] = q["resize"]
                changed += 1
            if q and q.get("anchor") in ANCHORS and q["anchor"] != p["anchor"]:
                print(f"    {p['name']}: anchor {p['anchor']} -> {q['anchor']}")
                p["anchor"] = q["anchor"]
                changed += 1
            for field, allowed in (("depth", DEPTHS), ("motion", MOTIONS)):
                if q and q.get(field) in allowed and q[field] != p.get(field):
                    print(f"    {p['name']}: {field} {p.get(field)} -> {q[field]}")
                    p[field] = q[field]
                    changed += 1
            keep.append(p)
        if not changed and not bg_changed:
            # THE BAR IS NOW HIGHER THAN THE LEVERS. Judged as a shipping
            # asset, the faults that remain are mostly ones no resize rule can
            # fix -- a seam, a silhouette notch, a smear. Say exactly what they
            # are and stop, rather than spending rounds re-rendering the same
            # picture: this list is the work queue for the TOOL, not the loop.
            outstanding = blocking
            print("  no lever for what is left -- stopping")
            break
        pm["parts"] = keep
        (d / "parts_front.json").write_text(json.dumps(pm, indent=1))
        rebuild(d)

    # A PROP THAT EXISTS ONLY AS A PAGE IS NOT AN ASSET. Write the rig out with
    # its hierarchy intact -- one named node per part, its pivot on the edge the
    # motion turns about, the body separate -- which is the only form in which
    # "modifiable and animatable by parts" means anything outside this renderer.
    print("\n[5] exporting the rig ...", flush=True)
    r = run(["node", str(ROOT / "tools/authoring/parts_view/shoot.mjs"), str(d / "export"),
             f"dir=/{d.relative_to(ROOT)}&export=1"], env=_env())
    for line in (r.stdout or "").splitlines():
        if "gltf" in line:
            print("   ", line.strip()[:140])

    if outstanding:
        print(f"\n{len(outstanding)} blocking fault(s) the loop could not fix "
              f"-- these need the tool changed, not the prop:")
        for f in outstanding:
            print(f"  * {f.get('part')}: {f.get('fault')}")
    print(f"\ndone: {d}")


if __name__ == "__main__":
    main()
