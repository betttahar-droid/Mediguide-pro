#!/usr/bin/env python3
"""
Authoring tool — NOT a build, CI, or runtime dependency (§11).

Run by hand; the PNGs it writes are committed to public/textures/ and the app
loads those. Delete this file and the game still runs.

    python3 tools/authoring/make_textures.py

Everything here is painted as LUMINANCE around mid-grey. palette.js supplies the
hue at sample time, which is what keeps a limited palette across the catalogue
(§4.4). The value range is deliberately wide — the reference boards' wood reads
because the groove is nearly black and the lit lip is nearly white, not because
of the hue.

Style rules taken off the reference sheet (hand-painted low-poly wood):
  * every groove gets a BRIGHT LIP on one side and a dark core
  * planks carry a soft vertical gradient, darker at the bottom
  * grain is few, long and confident — not noise
  * knots are drawn deliberately, as concentric rings
  * ends and edges are painted, not chamfered by the mesh alone
"""
import math
import random
from PIL import Image, ImageDraw, ImageFilter

OUT = "public/textures"
SHEET = 1024

# The brief's standard trim sheet layout, §4.1. Mirrored by src/art/trimLayout.js.
STRIPS = {
    "edge":       (0, 64),     # painted bevels, borders
    "detail":     (64, 128),   # screw heads, panel seams, label holders
    "surface":    (192, 512),  # painted wood, laminate, painted metal
    "transition": (704, 128),  # wear gradients, dirt masks
    "alpha":      (832, 192),  # cutouts — grilles, handles
}

V = lambda v: (v, v, v)


def normalise(img, target=132):
    """Shift a sheet so its mean value lands on mid-grey.

    The shader multiplies the palette tint by this luminance, so a sheet that
    averages dark makes its module read dark — and, worse, a trim sheet and an
    atlas with different means put a visible value step across the Tier A/B
    seam. Matching the means is what lets §4.2's blend read as a painted seam.
    """
    from PIL import ImageStat
    delta = target - ImageStat.Stat(img.convert("L")).mean[0]
    return img.point(lambda v: max(0, min(255, int(round(v + delta)))))


def wrapped(draw_fn, width=SHEET):
    """Run a drawing function three times so anything crossing the vertical
    seam appears on both sides. This is how the sheet tiles horizontally."""
    for dx in (-width, 0, width):
        draw_fn(dx)


def vgrad(img, box, top, bottom):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    h = max(1, y1 - y0)
    for i in range(h):
        t = i / (h - 1) if h > 1 else 0
        v = round(top + (bottom - top) * t)
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=V(v))


def grain_stroke(d, dx, x, y, length, amp, value, width, wobble):
    """One long tapered grain streak. Confident, not noisy."""
    pts = []
    steps = max(6, int(length / 24))
    for i in range(steps + 1):
        t = i / steps
        px = x + dx + t * length
        py = y + math.sin(t * math.pi * wobble + x * 0.01) * amp
        pts.append((px, py))
    for i in range(steps):
        # taper: thin at both ends, fat in the middle
        t = (i + 0.5) / steps
        w = max(1, width * (0.35 + 0.65 * math.sin(t * math.pi)))
        d.line([pts[i], pts[i + 1]], fill=V(value), width=int(round(w)))


def knot(d, dx, cx, cy, r, core, ring):
    """A wood knot: concentric rings with a dark core, squashed along the grain."""
    for i in range(6, 0, -1):
        t = i / 6
        rx, ry = r * t * 1.9, r * t
        v = round(ring + (core - ring) * (1 - t))
        d.ellipse([cx + dx - rx, cy - ry, cx + dx + rx, cy + ry], outline=V(v), width=2)
    d.ellipse([cx + dx - r * 0.45, cy - r * 0.28, cx + dx + r * 0.45, cy + r * 0.28],
              fill=V(core))


# ---------------------------------------------------------------- trim sheet
def make_trim():
    img = Image.new("RGB", (SHEET, SHEET), V(128))
    d = ImageDraw.Draw(img)
    rnd = random.Random(20260828)

    # --- surface strip: hand-painted planks, running along U ---------------
    sy, sh = STRIPS["surface"]
    PLANK = 86                      # plank height in px
    GROOVE = 7
    vgrad(img, (0, sy, SHEET, sy + sh), 122, 104)

    y = sy
    while y < sy + sh:
        top = y + GROOVE
        bot = min(sy + sh, y + PLANK)
        if bot - top < 12:
            break
        body = rnd.randint(112, 136)

        # plank body: darker at the bottom, so each plank reads as a round form
        vgrad(img, (0, top, SHEET, bot), body + 14, body - 26)

        # the lit lip directly under the groove — the single most important mark
        d.rectangle([0, top, SHEET, top + 3], fill=V(min(250, body + 96)))
        d.rectangle([0, top + 3, SHEET, top + 6], fill=V(min(240, body + 52)))
        # the shadow the plank above casts into the groove
        d.rectangle([0, y, SHEET, y + GROOVE], fill=V(46))
        d.rectangle([0, bot - 3, SHEET, bot], fill=V(66))

        # grain: several long confident streaks, high contrast
        for _ in range(rnd.randint(6, 9)):
            gy = rnd.uniform(top + 8, bot - 8)
            val = body + rnd.choice([-58, -44, -32, 46, 62, 74])
            wrapped(lambda dx, gy=gy, val=val: grain_stroke(
                d, dx, rnd.uniform(-300, 800), gy,
                rnd.uniform(460, 1200), rnd.uniform(2, 7),
                max(18, min(244, val)), rnd.uniform(2.0, 5.0), rnd.uniform(0.6, 1.8)))

        # knots, drawn deliberately
        for _ in range(rnd.randint(0, 2)):
            kx, ky = rnd.uniform(40, SHEET - 40), rnd.uniform(top + 20, bot - 20)
            r = rnd.uniform(13, 21)
            wrapped(lambda dx, kx=kx, ky=ky, r=r: knot(d, dx, kx, ky, r, 44, body - 34))

        # one staggered butt joint per board — dark core, lit lip on one side.
        # Staggered rather than aligned, so the sheet never reads as a grid.
        if rnd.random() < 0.7:
            jx = rnd.uniform(0, SHEET)
            def joint(dx, jx=jx, top=top, bot=bot):
                d.rectangle([jx + dx - 2, top + 2, jx + dx + 2, bot - 2], fill=V(48))
                d.rectangle([jx + dx + 2, top + 2, jx + dx + 5, bot - 2], fill=V(198))
            wrapped(joint)

        # paint chipped off the lit lip
        for _ in range(rnd.randint(2, 5)):
            cx, cw = rnd.uniform(0, SHEET), rnd.uniform(10, 40)
            wrapped(lambda dx, cx=cx, cw=cw, top=top: d.rectangle(
                [cx + dx, top, cx + dx + cw, top + 3], fill=V(96)))

        y += PLANK

    # --- edge trim: the painted bevel -------------------------------------
    ey, eh = STRIPS["edge"]
    vgrad(img, (0, ey, SHEET, ey + eh), 70, 96)
    d.rectangle([0, ey + int(eh * 0.34), SHEET, ey + int(eh * 0.52)], fill=V(228))
    d.rectangle([0, ey + int(eh * 0.52), SHEET, ey + int(eh * 0.62)], fill=V(158))
    d.rectangle([0, ey, SHEET, ey + 3], fill=V(48))
    d.rectangle([0, ey + eh - 4, SHEET, ey + eh], fill=V(58))
    # chips out of the painted lip, so the bevel is not a perfect extrusion
    for _ in range(46):
        x = rnd.uniform(0, SHEET)
        w = rnd.uniform(6, 26)
        wrapped(lambda dx, x=x, w=w: d.rectangle(
            [x + dx, ey + int(eh * 0.34), x + dx + w, ey + int(eh * 0.44)], fill=V(120)))

    # --- detail strip: bolts, a label rail, a seam ------------------------
    dy, dh = STRIPS["detail"]
    vgrad(img, (0, dy, SHEET, dy + dh), 132, 108)
    mid = dy + dh * 0.42
    for i in range(8):
        x = 64 + i * 128
        def bolt(dx, x=x):
            d.ellipse([x + dx - 11, mid - 11, x + dx + 11, mid + 11], fill=V(72))
            d.ellipse([x + dx - 9, mid - 10, x + dx + 8, mid + 7], fill=V(168))
            d.ellipse([x + dx - 7, mid - 8, x + dx + 6, mid + 5], fill=V(124))
            d.line([(x + dx - 5, mid - 3), (x + dx + 5, mid + 3)], fill=V(64), width=3)
        wrapped(bolt)
    # label holder rail along the bottom of the strip
    ry = dy + dh - 30
    d.rectangle([0, ry, SHEET, ry + 20], fill=V(92))
    d.rectangle([0, ry, SHEET, ry + 4], fill=V(206))
    d.rectangle([0, ry + 20, SHEET, ry + 24], fill=V(60))
    for i in range(16):
        x = 32 + i * 64
        wrapped(lambda dx, x=x: d.rectangle([x + dx, ry + 6, x + dx + 40, ry + 17], fill=V(150)))

    # --- transition: wear gradient ---------------------------------------
    ty, th = STRIPS["transition"]
    vgrad(img, (0, ty, SHEET, ty + th), 150, 74)
    for _ in range(160):
        x, yy = rnd.uniform(0, SHEET), rnd.uniform(ty, ty + th)
        r = rnd.uniform(6, 34)
        v = rnd.choice([58, 70, 176])
        wrapped(lambda dx, x=x, yy=yy, r=r, v=v: d.ellipse(
            [x + dx - r, yy - r * 0.4, x + dx + r, yy + r * 0.4], fill=V(v)))

    # --- alpha: grille ----------------------------------------------------
    ay, ah = STRIPS["alpha"]
    d.rectangle([0, ay, SHEET, ay + ah], fill=V(44))
    for i in range(21):
        x = i * 48
        wrapped(lambda dx, x=x: d.rectangle([x + dx + 8, ay + 22, x + dx + 34, ay + ah - 22],
                                           fill=V(196)))
        wrapped(lambda dx, x=x: d.rectangle([x + dx + 8, ay + 22, x + dx + 11, ay + ah - 22],
                                           fill=V(238)))

    # a whisper of blur so the paint reads as brush rather than pixels, then a
    # touch of contrast back
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return img


# --------------------------------------------------------------------- atlas
def painted_panel(img, box, seed, kind):
    """One 512² atlas cell: a framed, recessed panel with painted light."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    w, h = x1 - x0, y1 - y0

    vgrad(img, box, 146, 96)                      # the whole cell, lit from above

    # outer frame — bright on top and left, dark on bottom and right
    f = 26
    d.rectangle([x0, y0, x1, y0 + 6], fill=V(226))
    d.rectangle([x0, y0, x0 + 6, y1], fill=V(196))
    d.rectangle([x0, y1 - 8, x1, y1], fill=V(52))
    d.rectangle([x1 - 8, y0, x1, y1], fill=V(64))

    # recessed centre panel
    px0, py0, px1, py1 = x0 + f, y0 + f, x1 - f, y1 - f
    d.rectangle([px0 - 8, py0 - 8, px1 + 8, py1 + 8], fill=V(58))    # the recess shadow
    vgrad(img, (px0, py0, px1, py1), 132, 92)
    d.rectangle([px0, py0, px1, py0 + 4], fill=V(44))                # shadow inside the top
    d.rectangle([px0, py1 - 5, px1, py1], fill=V(214))               # bounce on the lower lip
    d.rectangle([px0, py0, px0 + 4, py1], fill=V(66))
    d.rectangle([px1 - 5, py0, px1, py1], fill=V(186))

    if kind == "wood":
        # boards across the panel, each with its own lit lip
        n = 3
        bh = (py1 - py0) / n
        for i in range(n):
            by = py0 + i * bh
            base = rnd.randint(118, 140)
            vgrad(img, (px0, int(by), px1, int(by + bh)), base + 18, base - 30)
            d.rectangle([px0, by, px1, by + 3], fill=V(46))
            d.rectangle([px0, by + 3, px1, by + 7], fill=V(min(250, base + 92)))
            for _ in range(7):
                gy = rnd.uniform(by + 10, by + bh - 10)
                grain_stroke(d, 0, px0 + rnd.uniform(-60, 40), gy,
                             rnd.uniform(240, 460), rnd.uniform(2, 7),
                             base + rnd.choice([-52, -38, 54, 70]), rnd.uniform(2, 5), 1.2)
            if rnd.random() < 0.7:
                knot(d, 0, rnd.uniform(px0 + 50, px1 - 50), by + bh * 0.5,
                     rnd.uniform(14, 20), 44, base - 34)
    elif kind == "laminate":
        for _ in range(120):
            cx, cy = rnd.uniform(px0, px1), rnd.uniform(py0, py1)
            r = rnd.uniform(8, 40)
            d.ellipse([cx - r, cy - r * 0.5, cx + r, cy + r * 0.5],
                      fill=V(int(rnd.gauss(118, 16))))
        d.rectangle([px0, py0, px1, py0 + 5], fill=V(44))
        d.rectangle([px0, py1 - 6, px1, py1], fill=V(212))
    elif kind == "metal":
        for _ in range(90):                     # brushed streaks
            gy = rnd.uniform(py0, py1)
            d.line([(px0, gy), (px1, gy + rnd.uniform(-3, 3))],
                   fill=V(int(rnd.gauss(126, 26))), width=rnd.randint(1, 3))
        d.polygon([(px0 + 46, py1 - 12), (px0 + 118, py0 + 12),
                   (px0 + 158, py0 + 12), (px0 + 86, py1 - 12)], fill=V(210))
        for cx in (px0 + 26, px1 - 26):
            for cy in (py0 + 26, py1 - 26):
                d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=V(56))
                d.ellipse([cx - 12, cy - 13, cx + 9, cy + 8], fill=V(196))
                d.ellipse([cx - 9, cy - 10, cx + 6, cy + 5], fill=V(120))
    elif kind == "glass":
        vgrad(img, (px0, py0, px1, py1), 186, 130)
        d.polygon([(px0 + 30, py1 - 16), (px0 + 120, py0 + 16),
                   (px0 + 168, py0 + 16), (px0 + 78, py1 - 16)], fill=V(240))
        d.polygon([(px0 + 190, py1 - 16), (px0 + 226, py0 + 16),
                   (px0 + 246, py0 + 16), (px0 + 210, py1 - 16)], fill=V(226))
        d.rectangle([px0, py1 - 26, px1, py1 - 18], fill=V(84))   # a shelf behind

    # corner wear, where hands and trolleys actually land
    for cx, cy in ((x0 + 18, y0 + 18), (x1 - 18, y1 - 18), (x1 - 22, y0 + 20)):
        for _ in range(46):
            r = rnd.uniform(1.5, 4.5)
            ox, oy = rnd.gauss(0, 22), rnd.gauss(0, 22)
            d.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r],
                      fill=V(int(rnd.choice([196, 210, 72]))))


def make_atlas():
    size = 1024
    cell = size // 2
    img = Image.new("RGB", (size, size), V(128))
    kinds = ["wood", "laminate", "metal", "glass"]
    for i, kind in enumerate(kinds):
        x, y = (i % 2) * cell, (i // 2) * cell
        painted_panel(img, (x, y, x + cell, y + cell), 11 + i * 7, kind)
    return img.filter(ImageFilter.GaussianBlur(0.5))


# ------------------------------------------------------------ tiling surface
def make_tiling():
    size = 512
    img = Image.new("RGB", (size, size), V(150))
    d = ImageDraw.Draw(img)
    rnd = random.Random(97)
    tile = size // 4

    for ty in range(4):
        for tx in range(4):
            x0, y0 = tx * tile, ty * tile
            base = rnd.randint(140, 164)
            vgrad(img, (x0, y0, x0 + tile, y0 + tile), base + 10, base - 12)
            for _ in range(240):                       # speckle, per tile
                px, py = rnd.uniform(x0, x0 + tile), rnd.uniform(y0, y0 + tile)
                v = base + rnd.choice([-26, -16, 18, 26])
                d.ellipse([px, py, px + rnd.uniform(1, 3), py + rnd.uniform(1, 3)], fill=V(v))
            if rnd.random() < 0.25:                    # a worn tile here and there
                for _ in range(3):
                    px, py = rnd.uniform(x0 + 10, x0 + tile - 10), rnd.uniform(y0 + 10, y0 + tile - 10)
                    r = rnd.uniform(10, 26)
                    d.ellipse([px - r, py - r * 0.6, px + r, py + r * 0.6], fill=V(base - 22))

    # grout: dark core with a lit lip on one side, so the floor reads as tiles
    for i in range(5):
        p = i * tile
        for a, b, v in ((-3, 3, 84), (3, 6, 186)):
            d.rectangle([p + a, 0, p + b, size], fill=V(v))
            d.rectangle([0, p + a, size, p + b], fill=V(v))
    return img.filter(ImageFilter.GaussianBlur(0.4))


# ---------------------------------------------------------------- hatch mask
def make_hatch():
    """Three densities in R/G/B; the shader picks a channel from the lighting
    term. White = no hatch."""
    size = 256

    def diagonals(spacing, width, cross=False):
        # spacing must divide `size` for a 45-degree line set to tile seamlessly
        layer = Image.new("L", (size, size), 255)
        d = ImageDraw.Draw(layer)
        for i in range(-size, size * 2, spacing):
            d.line([(i, 0), (i + size, size)], fill=0, width=width)
            if cross:
                d.line([(i, size), (i + size, 0)], fill=0, width=width)
        return layer

    return Image.merge("RGB", (
        diagonals(32, 3),                 # R — lightest shade
        diagonals(16, 3),                 # G — mid
        diagonals(16, 3, cross=True),     # B — densest, crossed
    ))


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    for name, img in (
        ("trim.png", normalise(make_trim())),
        ("atlas.png", normalise(make_atlas())),
        ("tiling.png", normalise(make_tiling())),
        ("hatch.png", make_hatch()),   # a mask, not paint — never normalised
    ):
        path = os.path.join(OUT, name)
        img.save(path, optimize=True)
        print(f"{path}  {img.size[0]}x{img.size[1]}  {os.path.getsize(path) // 1024} KB")
