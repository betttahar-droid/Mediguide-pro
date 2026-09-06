"""Cut the guided Nano sheet into measured three-level nine-slice masks."""
from collections import deque
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "handbook-v12"
SOURCE = LOCK / "surface-masks-v12-source-guided.png"
OUTPUT = ROOT / "public" / "textures" / "vaccine-fridge-surfaces-v12.png"
MANIFEST = ROOT / "public" / "textures" / "vaccine-fridge-surfaces-v12.json"
PREVIEW = LOCK / "surface-masks-v12-compiled-preview.png"
AUDIT = LOCK / "surface-masks-v12.audit.json"
NAMES = ("plate", "plateSeam", "vent", "trim", "recess")
TEXELS = 20


def magenta(rgb):
    p = rgb.astype(np.int16)
    return ((p[..., 0] > 180) & (p[..., 2] > 160) & (p[..., 1] < 135)
            & (np.abs(p[..., 0] - p[..., 2]) < 125))


def components(mask):
    seen = np.zeros(mask.shape, bool)
    groups = []
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            queue, group = deque(((x, y),)), []
            seen[y, x] = True
            while queue:
                px, py = queue.popleft(); group.append((px, py))
                for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
                    nx, ny = px+dx, py+dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = True; queue.append((nx,ny))
            if len(group) > 1000: groups.append(group)
    return groups


def sort_reading_order(boxes):
    centers = [(box, (box[1]+box[3])*.5, (box[0]+box[2])*.5) for box in boxes]
    split = (min(item[1] for item in centers) + max(item[1] for item in centers)) * .5
    top = sorted((item for item in centers if item[1] < split), key=lambda item: item[2])
    bottom = sorted((item for item in centers if item[1] >= split), key=lambda item: item[2])
    return [item[0] for item in (*top, *bottom)]


def quantize(crop):
    small = np.asarray(crop.resize((TEXELS,TEXELS), Image.Resampling.BOX), np.uint8)
    luma = small[...,0]*.2126 + small[...,1]*.7152 + small[...,2]*.0722
    p10, median, p90 = np.percentile(luma, (10,50,90))
    slack = max(5.0, (p90-p10)*.16)
    result = np.full((TEXELS,TEXELS), 128, np.uint8)
    result[luma < median-slack] = 0
    result[luma > median+slack] = 255
    return result, {"p10":round(float(p10),2), "median":round(float(median),2),
                    "p90":round(float(p90),2), "slack":round(float(slack),2)}


def center_border(mask):
    def run(values):
        count = 0
        for value in values:
            if value == 128: break
            count += 1
        return count
    mid = TEXELS//2
    return {"left":run(mask[mid,:]), "right":run(mask[mid,::-1]),
            "top":run(mask[:,mid]), "bottom":run(mask[::-1,mid])}


def measured_margin(mask, border):
    # Corner content must remain in the fixed cap. Inspect only the outer 40%
    # so a deliberate middle seam cannot inflate the cap.
    cap = max(2, round(TEXELS*.40))
    extent = max(border.values())
    fixed_border = extent
    for y_slice, x_slice, flip_y, flip_x in (
        (slice(0,cap),slice(0,cap),False,False),
        (slice(0,cap),slice(TEXELS-cap,TEXELS),False,True),
        (slice(TEXELS-cap,TEXELS),slice(0,cap),True,False),
        (slice(TEXELS-cap,TEXELS),slice(TEXELS-cap,TEXELS),True,True),
    ):
        corner = mask[y_slice,x_slice]
        if flip_y: corner = corner[::-1]
        if flip_x: corner = corner[:,::-1]
        # Ignore the perpendicular outer border. It crosses the whole corner
        # and would falsely force every margin to the scan limit. Only content
        # strictly inside the measured centre-line border may enlarge the cap.
        inner = corner[fixed_border:, fixed_border:]
        ys, xs = np.where(inner != 128)
        occupied = len(xs) / max(1, inner.size)
        if len(xs) and occupied >= .25:
            extent = max(extent, fixed_border + int(max(xs.max(),ys.max())) + 1)
    return min(extent, TEXELS//2-1)


def main():
    source = Image.open(SOURCE).convert("RGB")
    data = np.asarray(source)
    groups = components(~magenta(data))
    boxes = []
    for group in groups:
        xs, ys = zip(*group)
        boxes.append((min(xs),min(ys),max(xs)+1,max(ys)+1))
    boxes = sort_reading_order(boxes)
    if len(boxes) != 5:
        raise ValueError(f"Expected 5 disconnected panels; found {len(boxes)}: {boxes}")

    atlas = Image.new("L", (TEXELS*5,TEXELS), 128)
    entries = []
    print("GRID MAP (connected islands, reading order)")
    for index, (name, box) in enumerate(zip(NAMES, boxes)):
        x0,y0,x1,y1 = box
        ratio = (x1-x0)/(y1-y0)
        mask, levels = quantize(source.crop(box))
        border = center_border(mask)
        margin = measured_margin(mask, border)
        middle = mask[margin:TEXELS-margin, margin:TEXELS-margin]
        content_share = float(np.mean(middle != 128)) if middle.size else 0
        repeat = content_share >= .25
        counts = {str(value):int(np.sum(mask == value)) for value in (0,128,255)}
        if any(counts[str(value)] == 0 for value in (0,128,255)):
            raise ValueError(f"{name}: missing one of the three tone levels: {counts}")
        atlas.paste(Image.fromarray(mask, "L"), (index*TEXELS,0))
        entry = {"name":name, "sourceBoundsPx":list(box), "sourceRatio":round(ratio,4),
                 "atlasRectPx":[index*TEXELS,0,TEXELS,TEXELS], "marginPx":margin,
                 "centerBorderPx":border, "middleContentShare":round(content_share,4),
                 "middleMode":"repeat" if repeat else "stretch", "toneCounts":counts,
                 "cutLevels":levels}
        entries.append(entry)
        print(f"{index+1} {name:10s} box={box} ratio={ratio:.3f} border={border} "
              f"margin={margin} middle={content_share:.3f}->{entry['middleMode']} tones={counts}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    atlas.convert("RGB").save(OUTPUT, optimize=False)
    atlas.resize((1000,200), Image.Resampling.NEAREST).save(PREVIEW, optimize=False)
    payload = {"schemaVersion":12, "source":SOURCE.relative_to(ROOT).as_posix(),
               "sourceSha256":sha256(SOURCE.read_bytes()).hexdigest(),
               "atlas":OUTPUT.relative_to(ROOT).as_posix(), "atlasSizePx":[100,20],
               "toneLevels":[0,128,255], "tiles":entries,
               "checks":{"islandCount":len(boxes)==5,
                         "sourceRatiosConsistent":max(item['sourceRatio'] for item in entries)-min(item['sourceRatio'] for item in entries)<.02,
                         "normalizedLogicalSize":[TEXELS,TEXELS],
                         "allThreeTone":all(all(item['toneCounts'][str(v)]>0 for v in (0,128,255)) for item in entries)}}
    MANIFEST.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    AUDIT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(f"PASS surface atlas -> {OUTPUT}")


if __name__ == '__main__': main()
