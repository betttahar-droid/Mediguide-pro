#!/usr/bin/env python3
"""Split an elevation into a background layer and part layers.

    python3 tools/authoring/layer_build.py work/ps1 --face front

Authoring tool. NOT a build, CI or runtime dependency.

WHY. extract_fittings.py produced a 52x267 sliver of panel and tiled it
everywhere, which is why every judge described the lower cabinet as "blank
flat brown" -- one small patch repeated cannot carry a painted panel's
variation. And its parts were full-width strips, so reassembling them at a new
size mapped the coin door onto the control deck.

This keeps the whole elevation instead:

  BACKGROUND  the elevation with every part REMOVED and the hole filled from
              the nearest clean panel above or below it. Full size, so it
              nine-slices with all its grime and streaking intact rather than
              tiling one swatch.
  PARTS       cut at their measured boxes, each carrying its anchor and its
              resize rule.

The test that matters is that this is LOSSLESS at the original size: lay the
parts back on the background at their own coordinates and you must get the
reference image back. If that does not hold, nothing at any other size will.
"""
import argparse
import json
from pathlib import Path

from PIL import Image

from identify_parts import object_crop


PANEL_PATCH = {}


def silhouette(ob, erode=3):
    """Which pixels are the PROP, as opposed to sheet behind it.

    object_crop returns a bounding box, and a prop is not a rectangle -- a
    jukebox has a domed top, a cabinet a sloped deck. The sheet showing through
    those corners is inside the crop, is covered by no part, and was therefore
    a candidate for "clean panel". On the jukebox it won: the chosen patch
    measured RGB(187,186,182), which is the sheet, so every hole in the
    background was filled with white and the judge reported "a blank whitish
    wash instead of the wood-grain side panels" for four rounds running.

    Eroding the mask drops the outline pixels too, which are trim rather than
    panel and would otherwise streak the tile.
    """
    W, H = ob.size
    px = ob.load()
    corners = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    from collections import Counter as _C
    bg = _C(corners).most_common(1)[0][0]

    def looks_bg(c):
        return sum(abs(a - b) for a, b in zip(c, bg)) < 40

    # OUTSIDE MEANS REACHABLE FROM THE EDGE, NOT MERELY THE RIGHT COLOUR. The
    # colour test alone called the vending machine's white "COLD DRINKS"
    # lettering background, because white sits within tolerance of the pale
    # sheet. fill_from_panel then skipped those pixels as "not part of the
    # prop", so the sign survived being painted out and tiled across the whole
    # widened cabinet as a ghost -- and the alpha cut would have punched the
    # letters clean through the face. Sheet is what the sheet is CONNECTED to;
    # anything enclosed by the prop is the prop, whatever colour it is.
    outside = [[False] * H for _ in range(W)]
    stack = []
    for x in range(W):
        for y in (0, H - 1):
            if looks_bg(px[x, y]) and not outside[x][y]:
                outside[x][y] = True
                stack.append((x, y))
    for y in range(H):
        for x in (0, W - 1):
            if looks_bg(px[x, y]) and not outside[x][y]:
                outside[x][y] = True
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < W and 0 <= ny < H and not outside[nx][ny] \
                    and looks_bg(px[nx, ny]):
                outside[nx][ny] = True
                stack.append((nx, ny))
    inside = [[not outside[x][y] for y in range(H)] for x in range(W)]
    for _ in range(erode):
        prev = [col[:] for col in inside]
        for x in range(W):
            for y in range(H):
                if not prev[x][y]:
                    continue
                if (x == 0 or y == 0 or x == W - 1 or y == H - 1
                        or not (prev[x - 1][y] and prev[x + 1][y]
                                and prev[x][y - 1] and prev[x][y + 1])):
                    inside[x][y] = False
    return inside


def fill_from_panel(ob, boxes, shaped=None):
    """Paint out the parts using panel taken from directly above or below.

    A cabinet panel is vertically streaked -- wear runs down it -- so a column
    of panel is the honest thing to continue a column of hole with. For each
    hole row, copy the nearest row at the same x that no part covers.
    """
    W, H = ob.size
    out = ob.copy()
    px = out.load()
    src = ob.load()
    covered = [[False] * H for _ in range(W)]
    if shaped:
        for (bx, m) in shaped:
            x0, y0, x1, y1 = bx
            mp = m.load() if m is not None else None
            for x in range(max(0, x0), min(W, x1)):
                for y in range(max(0, y0), min(H, y1)):
                    if mp is None or mp[x - x0, y - y0] > 128:
                        covered[x][y] = True
    else:
        for (x0, y0, x1, y1) in boxes:
            for x in range(max(0, x0), min(W, x1)):
                for y in range(max(0, y0), min(H, y1)):
                    covered[x][y] = True
    # SOURCE ROWS MUST BE PANEL, NOT MERELY UNCOVERED. Between two parts sits
    # dark trim, and it is uncovered -- so filling from "the nearest row no
    # part occupies" packed the holes with black. At scale 1 the parts sat on
    # top and hid it; the moment the background stretched, those fills came
    # out as black rectangles across the cabinet. Only rows that actually look
    # like the panel may be copied from.
    # AND THEY MUST BE INSIDE THE PROP. See silhouette(): the sheet showing
    # through a domed top is uncovered too, and on the jukebox it was the modal
    # colour, so "panel" resolved to white.
    inside = silhouette(ob)
    solid = silhouette(ob, erode=0)      # unroded: what to PAINT, vs what to copy FROM
    from collections import Counter as _C
    # PANEL IS NEITHER A VOID NOR A HIGHLIGHT. On a vending machine whose
    # frame and interior are near-black, the modal uncovered colour WAS black,
    # so "panel" resolved to the plinth shadow and every hole in the background
    # was filled with it -- the whole face came out a black rectangle, which
    # the judge reported for three rounds as "large black voids where the panel
    # should show cabinet metal". A painted panel has a mid tone; the darkest
    # and lightest few percent are shadow and specular, not material.
    def lum(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

    tally = _C()
    for x in range(0, W, 2):
        for y in range(0, H, 2):
            if not covered[x][y] and inside[x][y] and 28 < lum(src[x, y]) < 232:
                tally[src[x, y]] += 1
    base = tally.most_common(1)[0][0] if tally else (128, 128, 128)
    tol = 70

    def is_panel(c):
        return sum(abs(a - b) for a, b in zip(c, base)) < tol

    def usable(x, y):
        # PANEL IS PANEL WHETHER OR NOT A DECAL SITS ON IT. Requiring the patch
        # to be UNCOVERED made sense while a part was a rare large fitting; now
        # that every detail is lifted off, the boxes cover most of the face and
        # the largest "clean panel" left was a 20x11 sliver next to the trim.
        # Tiled, that read as corrugated slabs bolted to the flanks of every
        # widened prop. What the patch has to be is material, and a decal's box
        # is drawn over material like everything else.
        return (inside[x][y] and is_panel(src[x, y])
                and 28 < lum(src[x, y]) < 232)

    # FILL FROM A CLEAN PATCH, NOT FROM THE NEAREST ROW. Copying a hole's own
    # column meant the screen's coloured border was the nearest "panel" pixel
    # for the whole screen region, and the background came out with blue and
    # green streaks running down it plus a grey band where the coin door had
    # been. Invisible at scale 1 under the parts; the moment the background
    # repeated it was all the judge could see, four rounds running.
    #
    # Take one rectangle that is genuinely panel and tile it, mirrored, over
    # every hole. A patch of panel always looks like panel.
    #
    # SCORE BY SHAPE, NOT BY AREA ALONE. seamless_tile.py resamples whatever it
    # is given to a square, so the widest rectangle is not the best one: the
    # jukebox's 191x19 sliver became a 96x96 tile at a 10:1 stretch, which is a
    # smear before it is even repeated. Penalising elongation by the aspect
    # ratio makes a chunky patch beat a wide thin one of the same area.
    best, bw, bh, bscore = None, 0, 0, 0.0
    for y0 in range(0, H, 4):
        for x0 in range(0, W, 4):
            if not usable(x0, y0):
                continue
            x1 = x0
            while x1 + 1 < W and usable(x1 + 1, y0):
                x1 += 1
            y1 = y0
            while y1 + 1 < H and all(usable(x, y1 + 1)
                                     for x in range(x0, x1 + 1, 3)):
                y1 += 1
            w, h = x1 - x0 + 1, y1 - y0 + 1
            # a sliver is not a swatch: a 273x11 strip tiles as horizontal
            # banding whatever it contains, so it must lose to anything chunkier
            if min(w, h) < 8:
                continue
            score = w * h * (min(w, h) / max(w, h))
            if score > bscore:
                best, bw, bh, bscore = (x0, y0), w, h, score
    if best is None:
        return out
    ox, oy = best
    PANEL_PATCH["patch"] = [ox, oy, bw, bh]   # where the clean panel was found

    # FILL WITH A SEAMLESS TILE, NOT A MIRRORED ONE. Mirroring makes every join
    # a reflection, which removes the hard cut and replaces it with a butterfly:
    # each grime drip appears back to back with its own mirror image on a
    # regular grid, and once the background is stretched that pattern is the
    # most obvious thing on the prop. seamless_tile's overlap construction has
    # no join to hide, so the same patch can simply repeat.
    # damped for the same reason the renderer's tile is: one strong drip mark
    # repeated on a grid reads as wallpaper, and this fill covers whole panels
    # THE OVERLAP HAS TO FIT INSIDE THE PATCH. make_seamless_overlap reads
    # column x+W of its source, so the tile must be exactly the overlap
    # narrower than what it is given -- clamping the tile to a minimum instead
    # asked for pixels the patch did not have and took a whole prop down with
    # "IndexError: image index out of range".
    from seamless_tile import make_seamless_overlap, damp
    patch = damp(ob.crop((ox, oy, ox + bw, oy + bh)), 0.6)
    k = max(2, min(bw, bh) // 5)
    while k > 1 and min(bw - k, bh - k) < 6:
        k -= 1
    tw, th = bw - k, bh - k
    if tw < 4 or th < 4:            # too small to repair; repeat it as it is
        tile, tw, th = patch, bw, bh
    else:
        tile = make_seamless_overlap(patch, tw, th, k)
    tp = tile.load()
    for x in range(W):
        for y in range(H):
            if not covered[x][y] or not solid[x][y]:
                continue    # only holes, and only inside the prop -- a part box
                            # that overhangs the silhouette must not grow it
            px[x, y] = tp[x % tw, y % th]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir")
    ap.add_argument("--face", default="front")
    args = ap.parse_args()

    d = Path(args.sheet_dir)
    man = json.loads((d / f"parts_{args.face}.json").read_text())
    ob = object_crop(d / f"{args.face}.png")
    W, H = ob.size
    assert [W, H] == man["size"], f"size drift {W}x{H} vs {man['size']}"

    # A MASK IS THE SHAPE; A BOX WAS ONLY EVER ITS BOUNDING RECTANGLE. Where
    # segment_sheet has produced masks, the hole cut in the background is the
    # fitting's actual outline -- so a bezel and the screen inside it can abut
    # without either claiming the other's pixels, and the background is exactly
    # the body panel and nothing else.
    masks = {}
    for p in man["parts"]:
        if p.get("mask") and (d / p["mask"]).exists():
            masks[p["name"]] = Image.open(d / p["mask"]).convert("L")
    boxes = [p["px"] for p in man["parts"]]
    bg = fill_from_panel(ob, boxes, [(p["px"], masks.get(p["name"]))
                                     for p in man["parts"]])
    # CUT THE FACE TO THE PROP'S OUTLINE. A prop is not a rectangle and the
    # crop is, so a jukebox's domed top leaves sheet-white in the corners of
    # the background image. On a flat quad that read as a white fringe all the
    # way round the front face. Alpha there lets the renderer discard those
    # pixels, so the prop's outline is its own silhouette rather than its
    # bounding box -- and it costs nothing, because those pixels were never
    # part of the prop.
    bg = bg.convert("RGBA")
    mask = silhouette(ob, erode=0)
    ap_ = bg.load()
    cut = 0
    for x in range(W):
        for y in range(H):
            if not mask[x][y]:
                r, g, b, _ = ap_[x, y]
                ap_[x, y] = (r, g, b, 0)
                cut += 1
    print(f"  cut {100*cut/(W*H):.1f}% of the face outside the silhouette")
    bg.save(d / f"bg_{args.face}.png")
    if PANEL_PATCH.get("patch"):
        (d / f"panel_patch_{args.face}.json").write_text(json.dumps(PANEL_PATCH))
        print(f"  clean panel patch: {PANEL_PATCH['patch']}")

    kit = d / "parts"
    kit.mkdir(exist_ok=True)
    out = []
    # EVERY PART GETS ITS OWN NINE-SLICE. A part that spans the face was being
    # scaled as a plain quad, so a wider prop stretched its artwork -- the very
    # thing AdaptivePropBase calls a CRITICAL failure, applied to parts instead
    # of to the body. The bands are measured from the part's own crop by the
    # same scan that measures the background's, so the renderer can hold its
    # ends at real size and repeat only what is uniform.
    from nine_slice import bands as _bands
    for p in man["parts"]:
        x0, y0, x1, y1 = p["px"]
        crop = ob.crop((x0, y0, x1, y1))
        if p["name"] in masks:                 # cut to the fitting's real shape
            crop = crop.convert("RGBA")
            crop.putalpha(masks[p["name"]])
        crop.save(kit / f"{p['name']}.png")
        try:
            # STRICTER THAN THE BACKGROUND'S. The default scan calls the most
            # uniform third of an axis stretchable, which on a whole elevation
            # is panel but on a 220px marquee is the gap between two letters:
            # it returned h=[0.80,0.97], a band sitting ON the final E, and
            # stretching it smeared the letter across the sign. At quantile
            # 0.20 with a 15% minimum the marquee correctly reports NO band --
            # there is nowhere on it that can grow -- while the control deck,
            # the trim rails and the delivery flap keep theirs.
            b = _bands(kit / f"{p['name']}.png", quantile=0.20, min_frac=0.15)
        except Exception:
            b = None
        # A SPAN RULE THE MEASUREMENT CONTRADICTS IS NOT A RULE. The model
        # called a marquee TITLE occupying 29% of the width "spanx_center", and
        # a spanning part is drawn at the full width and centred -- so the title
        # was moved out of its own position and stretched across the face at
        # ORIGINAL SIZE, reading "ATE / KE". A part can only be told to run the
        # full width if it already nearly does; anything else is fixed.
        fw_, fh_ = (x1 - x0) / W, (y1 - y0) / H
        rule = p["resize"]
        # SPANNING AND PER-BAY ARE THE SAME QUESTION ANSWERED TWICE. Spanning
        # says "one of these, stretched across whatever width there is";
        # per-bay says "one of these in each bay, at its real size". Marked
        # both, the control deck was drawn once per bay AND stretched to the
        # full width each time, so it hung off both sides of the cabinet.
        # Per-bay is the more specific claim, so it wins and the part keeps its
        # real size.
        # PER-BAY IS FOR CONTROLS, AND A CONTROL IS SMALL. A bay is one
        # player's station, so what repeats in it is a joystick, a button
        # cluster, a coin slot. The rule was applied to a SCREEN, and a widened
        # cabinet came out with two screens side by side -- a two-player cabinet
        # has one wide screen and two sets of controls. Size settles it without
        # argument: nothing occupying a twelfth of the face is a control.
        if p.get("per_bay") and fw_ * fh_ > 0.08:
            print(f"  {p['name']}: {100*fw_*fh_:.0f}% of the face is too big "
                  f"to be per-bay -> once only")
            p["per_bay"] = False

        # THE PROP'S SCALE RULES ARE THE ONLY AUTHORITY ON RESIZING. Each part
        # is also given a resize rule when it is NAMED, and that is a guess made
        # while looking at one fitting in isolation -- the namer called a SCREEN
        # "spanx_repeat", so a widened cabinet showed three copies of the same
        # ship picture side by side. scale_rules decides afterwards, looking at
        # the whole prop and what a bigger one of it actually is, and names the
        # structure and the per-bay fittings explicitly. Anything it did not
        # name is fixed: one of them, at its real size, wherever it was.
        if not p.get("spans") and not p.get("per_bay") and rule != "fixed":
            print(f"  {p['name']}: not named as structure, {rule} -> fixed")
            rule = "fixed"

        # A FRAME IS STRUCTURE AND MUST WIDEN WITH THE PROP. The width guard
        # below exists to stop a 29%-wide TITLE being stretched across the
        # face, and it was doing its job -- but applied to everything it also
        # pinned the marquee housing, the screen bezel and the control deck, so
        # a widened cabinet was the same cabinet with panel either side of it
        # and nothing about it restructured. Which parts are frames is a
        # question about what the object IS, so scale_rules asks it, and an
        # explicit role beats a width heuristic.
        if p.get("spans"):
            if rule == "fixed":
                print(f"  {p['name']}: structure, fixed -> spanx_center")
                rule = "spanx_center"
            out_span = True
        else:
            out_span = False
        if p.get("per_bay") and rule != "fixed":
            print(f"  {p['name']}: per-bay, so {rule} -> fixed")
            rule = "fixed"
        if rule.startswith("spanx") and fw_ < 0.75 and not out_span:
            print(f"  {p['name']}: {rule} but only {100*fw_:.0f}% wide -> fixed")
            rule = "fixed"
        elif rule.startswith("spany") and fh_ < 0.75:
            print(f"  {p['name']}: {rule} but only {100*fh_:.0f}% tall -> fixed")
            rule = "fixed"
        # A FRAME OFTEN HAS NO UNIFORM BAND, AND STILL HAS TO WIDEN. Spanning
        # was gated on a measured repeat band, so a screen bezel marked as
        # structure kept its exact size and the widened cabinet was unchanged.
        # Give it the same growth the background uses: hold the artwork, insert
        # the extra just inside its own edge moulding. Frames and faces then
        # grow by one rule instead of two.
        hf = None
        if p.get("spans"):
            try:
                from strip_slice import col_diff, flank_window
                rgb = crop.convert("RGB")
                hf = list(flank_window(col_diff(rgb, 0, rgb.size[1]))[0])
            except Exception:
                hf = None
        out.append({
            "name": p["name"], "image": f"parts/{p['name']}.png",
            "hf": hf,
            "resize": rule, "anchor": p["anchor"],
            "depth": p.get("depth", "proud"), "motion": p.get("motion", "none"),
            "per_bay": bool(p.get("per_bay")),
            "scatter": bool(p.get("scatter")),
            # where THIS part may repeat, in its own 0..1 box
            "bands": {"h": (b or {}).get("h"), "v": (b or {}).get("v")},
            "px_size": [x1 - x0, y1 - y0],
            # fractions of the ORIGINAL face; the renderer turns these into
            # world units that do not change when the prop resizes
            "u": [round(x0 / W, 5), round(x1 / W, 5)],
            "v": [round(1 - y1 / H, 5), round(1 - y0 / H, 5)],
        })

    # LOSSLESS CHECK. Lay the parts back on the background at their own
    # coordinates; it must reproduce the reference. If the background fill or
    # a box is wrong this is where it shows, not three stages later.
    check = bg.copy()
    for p, o in zip(man["parts"], out):
        x0, y0, x1, y1 = p["px"]
        piece = Image.open(kit / f"{p['name']}.png")
        check.paste(piece, (x0, y0), piece if piece.mode == "RGBA" else None)
    a, b = ob.load(), check.load()
    diff = sum(1 for x in range(0, W, 2) for y in range(0, H, 2)
               if sum(abs(m - n) for m, n in zip(a[x, y], b[x, y])) > 12)
    tot = (W // 2) * (H // 2)
    check.save(d / f"_recomposed_{args.face}.png")

    # carry the background mode forward: the loop sets it between rebuilds and
    # regenerating this file would otherwise silently discard the judge's fix
    prev = d / f"layers_{args.face}.json"
    mode = "mirror"
    if prev.exists():
        try:
            mode = json.loads(prev.read_text()).get("background_mode", mode)
        except Exception:
            pass
    man2 = {"face": args.face, "size": [W, H], "aspect": round(W / H, 5),
            "background": f"bg_{args.face}.png", "background_mode": mode,
            "parts": out}
    (d / f"layers_{args.face}.json").write_text(json.dumps(man2, indent=1))
    print(f"{args.face}: {W}x{H}, {len(out)} parts, background written")
    print(f"  recomposition differs from the reference on "
          f"{100*diff/tot:.2f}% of sampled pixels")
    for o in out:
        print(f"  {o['name']:20} {o['resize']:6} {o['anchor']:7} "
              f"u {o['u'][0]:.3f}..{o['u'][1]:.3f}  v {o['v'][0]:.3f}..{o['v'][1]:.3f}")
    print(f"wrote {d / f'layers_{args.face}.json'}")


if __name__ == "__main__":
    main()
