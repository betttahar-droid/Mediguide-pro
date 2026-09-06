"""Freeze the turnaround and derive auditable orthographic crops/masks."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'docs'/'concept'/'vaccine-fridge-turnaround-v1.png'
OUT=ROOT/'docs'/'reference-lock'/'vaccine-fridge-v1'
OUT.mkdir(parents=True,exist_ok=True)
image=Image.open(SOURCE).convert('RGB')

# Rectangles isolate the four panels before their captions. Coordinates are
# source-image pixels and are kept in the manifest, never hidden in Blender.
CROPS={
    'front':(32,58,390,886),
    'side':(408,58,735,886),
    'back':(765,58,1112,886),
    'iso':(1125,45,1536,906),
}

def distance(a,b): return max(abs(a[i]-b[i]) for i in range(3))

manifest={
    'authority':'docs/concept/vaccine-fridge-turnaround-v1.png',
    'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'sourceSizePx':list(image.size),
    'pixelsPerUnit':32,
    'views':{},
    'status':'candidate masks; geometry is not approved until overlays pass',
}

for name,rect in CROPS.items():
    crop=image.crop(rect); crop.save(OUT/f'{name}.png')
    # Estimate the local paper color from the four corners. Foreground includes
    # the cream silhouette, so the threshold is intentionally conservative.
    corners=[crop.getpixel((x,y)) for x,y in ((2,2),(crop.width-3,2),(2,crop.height-3),(crop.width-3,crop.height-3))]
    bg=tuple(sum(p[i] for p in corners)//4 for i in range(3))
    raw=Image.new('L',crop.size,0); px=raw.load()
    for y in range(crop.height):
        for x in range(crop.width):
            p=crop.getpixel((x,y)); sat=max(p)-min(p)
            # Either chroma or a visible value delta from the surrounding paper.
            if distance(p,bg)>=13 or sat>=16: px[x,y]=255
    # Remove isolated specks and fill one-pixel holes with a 3x3 majority pass.
    for _ in range(2):
        src=raw.copy(); sp=src.load(); dp=raw.load()
        for y in range(1,crop.height-1):
            for x in range(1,crop.width-1):
                count=sum(sp[x+dx,y+dy]>0 for dy in (-1,0,1) for dx in (-1,0,1))
                dp[x,y]=255 if count>=4 else 0
    bbox=raw.getbbox()
    raw.save(OUT/f'{name}-mask-candidate.png')
    manifest['views'][name]={
        'sourceCropPx':list(rect), 'localBackgroundRgb':list(bg),
        'candidateObjectBoundsPx':list(bbox) if bbox else None,
    }

(OUT/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
