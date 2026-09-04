#!/usr/bin/env python3
"""Cut the generated fittings sheet into a decal atlas with alpha.

    python3 tools/authoring/cut_fittings.py

Authoring tool. NOT a build, CI or runtime dependency.

WHY DECALS AND NOT MORE PROCEDURAL TEXTURE. The style bible's character-ab
sheet draws the same cabinet plain and finished, and the difference is not
noise — it is FITTINGS. A vent where air moves, a rating plate where you would
read one, screws at the corners of each panel, a label in a holder. Both halves
of that sheet have perfectly flat fields; the finished one simply has things ON
it, each placed where it belongs. No hash function produces that, because the
placement is the meaning.

So the fittings become a small atlas, and the renderer places them
deliberately. Each is drawn at a FIXED WORLD SIZE anchored to a face's corner
or centre, which keeps the resize property: a cabinet twice as wide has the
same rating plate in the same place relative to its corner, not a plate
stretched to twice the width.

The sheet is generated on magenta so the cutter can find each fitting as an
island and key the background out to alpha. Nothing here guesses a grid: the
tiles are found, not assumed, because a generator lays them out however it
likes and a hard-coded 4x4 would silently mis-slice the moment it did not.
"""
import json
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "style-bible" / "fittings.png"
OUT_PNG = ROOT / "tools" / "voxel-fridge" / "fittings.png"
OUT_JSON = ROOT / "tools" / "voxel-fridge" / "fittings.json"

# Row-major, matching the order the sheet was asked for. Checked against the
# image rather than trusted: cut_fittings prints a grid map so a mismatch is
# visible immediately instead of showing up as a hinge where a dial should be.
NAMES = [
    "hinge", "latch", "vent",
    "ratingPlate", "biohazard", "biohazard2", "labelHolder",
    "rocker", "dialA", "dialB", "readout",
    "screwSlot", "screwCross", "foot", "hazardStripe",
]


def is_bg(c, tol=150):
    return abs(c[0] - 255) + abs(c[1] - 0) + abs(c[2] - 255) < tol


def islands(im, min_px=400):
    """Connected non-magenta regions. Flood fill on a coarse stride, then take
    the true bounds of each island at full resolution."""
    px = im.load()
    w, h = im.size
    seen = [[False] * h for _ in range(w)]
    out = []
    for sx in range(0, w, 3):
        for sy in range(0, h, 3):
            if seen[sx][sy] or is_bg(px[sx, sy]):
                continue
            stack, pts = [(sx, sy)], []
            while stack:
                x, y = stack.pop()
                if not (0 <= x < w and 0 <= y < h) or seen[x][y] or is_bg(px[x, y]):
                    continue
                seen[x][y] = True
                pts.append((x, y))
                # Step by ONE. Stepping by two preserves parity, so a solid
                # shape splits into four independent even/odd lattices and each
                # fitting came back as four islands — fifteen tiles counted as
                # sixty-eight.
                stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            if len(pts) * 4 < min_px:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            out.append([min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2])
    return out


def merge_close(boxes, gap=26):
    """Fuse islands that are near each other into one fitting.

    A fitting is not always one connected shape: the vent is three separate
    horizontal bars with clear space between them, so a pure island count
    reported seventeen tiles for fifteen fittings and shifted every name after
    it. Anything within `gap` of another box is part of the same fitting — the
    sheet leaves far more space than that between fittings.
    """
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if (a[0] - gap < b[2] and b[0] - gap < a[2]
                        and a[1] - gap < b[3] and b[1] - gap < a[3]):
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]),
                                max(a[2], b[2]), max(a[3], b[3])]
                    boxes.pop(j)
                    changed = True
                    break
            if changed:
                break
    return boxes


def rows(boxes, tol=60):
    """Group islands into rows by vertical overlap, then sort each row by x, so
    the naming order is reading order whatever the generator's spacing."""
    boxes = sorted(boxes, key=lambda b: b[1])
    out, cur = [], [boxes[0]]
    for b in boxes[1:]:
        if b[1] - cur[-1][1] < tol:
            cur.append(b)
        else:
            out.append(sorted(cur, key=lambda q: q[0]))
            cur = [b]
    out.append(sorted(cur, key=lambda q: q[0]))
    return out


def main():
    im = Image.open(SRC).convert("RGB")
    boxes = merge_close(islands(im))
    grid = rows(boxes)
    flat = [b for row in grid for b in row]
    print(f"found {len(flat)} fittings in {len(grid)} rows: "
          f"{[len(r) for r in grid]}")
    if len(flat) != len(NAMES):
        print(f"  WARNING: {len(flat)} islands but {len(NAMES)} names — the "
              f"names below will be wrong. Check {SRC.name} and adjust NAMES.")

    # Pack into one strip with 2px gutters. A strip rather than a square: there
    # are fifteen small tiles and nothing gains from a clever packer.
    tiles = []
    for i, (x0, y0, x1, y1) in enumerate(flat):
        name = NAMES[i] if i < len(NAMES) else f"tile{i}"
        tiles.append((name, im.crop((max(0, x0), max(0, y0), x1, y1))))

    W = sum(t.width + 2 for _, t in tiles) + 2
    H = max(t.height for _, t in tiles) + 4
    atlas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    man = {}
    x = 2
    for name, t in tiles:
        rgba = t.convert("RGBA")
        px = rgba.load()
        # Key out the magenta ground. Anything close to it goes fully
        # transparent; the generator's anti-aliased fringe would otherwise leave
        # a pink halo around every decal at nearest filtering.
        for yy in range(rgba.height):
            for xx in range(rgba.width):
                r, g, b, _ = px[xx, yy]
                # Key on HUE, not distance from pure magenta. A distance test
                # leaves the generator's anti-aliased fringe behind — every
                # decal kept a thin pink outline at nearest filtering, which is
                # exactly where it is most visible. Anything whose red and blue
                # both clearly beat its green is ground, at any brightness.
                if r > 90 and b > 90 and g < min(r, b) - 45:
                    px[xx, yy] = (0, 0, 0, 0)
        # Then ERODE THE FRINGE. The hue test above cannot catch a fitting's own
        # black outline blended halfway into magenta — that lands near #3a1a3a,
        # too dark to trip it, and leaves a purple rim exactly where nearest
        # filtering shows it most. So: any purple-tinted pixel TOUCHING
        # transparency is fringe and goes too. Anchoring on adjacency is what
        # makes this safe — it cannot eat a fitting's interior, only its border.
        for _ in range(2):
            doomed = []
            for yy in range(rgba.height):
                for xx in range(rgba.width):
                    r, g, b, aa = px[xx, yy]
                    if aa == 0 or g >= min(r, b) - 12:
                        continue
                    if any(px[nx, ny][3] == 0
                           for nx, ny in ((xx+1,yy),(xx-1,yy),(xx,yy+1),(xx,yy-1))
                           if 0 <= nx < rgba.width and 0 <= ny < rgba.height):
                        doomed.append((xx, yy))
            for q in doomed:
                px[q] = (0, 0, 0, 0)
        atlas.paste(rgba, (x, 2))
        man[name] = {"rect": [x, 2, rgba.width, rgba.height],
                     "aspect": round(rgba.width / rgba.height, 4)}
        print(f"  {name:14s} {rgba.width:3d}x{rgba.height:3d}")
        x += rgba.width + 2

    # The atlas's OWN colours, exported so the renderer can widen its palette.
    # The post pass snaps every frame to a locked palette; without these the
    # hazard yellow and the plate's warm grey would snap to whatever cabinet
    # colour happened to be nearest, and the decals would come out as smears.
    seen = Counter(c[:3] for c in atlas.getdata() if c[3] > 128)
    keep = []
    for c, n in seen.most_common():
        if n < 30:
            break
        if all(sum(abs(a - b) for a, b in zip(c, k)) > 44 for k in keep):
            keep.append(c)
    print(f"  atlas palette: {len(keep)} colours")

    atlas.save(OUT_PNG)
    OUT_JSON.write_text(json.dumps(
        {"size": [W, H], "tiles": man,
         "palette": ["#%02x%02x%02x" % c for c in keep[:24]]}, indent=1) + "\n")
    print(f"wrote {OUT_PNG.relative_to(ROOT)} ({W}x{H}) and "
          f"{OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
