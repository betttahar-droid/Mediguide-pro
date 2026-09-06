"""Create a red/reference green/candidate silhouette overlay and metrics."""
from pathlib import Path
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'docs'/'reference-lock'/'vaccine-fridge-v1'
reference=Image.open(folder/'front-mask-candidate.png').convert('L')
candidate_rgba=Image.open(folder/'candidate-front.png').convert('RGBA')
candidate=candidate_rgba.getchannel('A')

# Both images share the crop canvas; threshold anti-aliased alpha at 50%.
r=reference.load(); c=candidate.load(); overlay=Image.new('RGBA',reference.size,(0,0,0,0)); o=overlay.load()
intersection=union=ref_count=cand_count=0
for y in range(reference.height):
    for x in range(reference.width):
        rv=r[x,y]>=128; cv=c[x,y]>=128
        ref_count+=rv; cand_count+=cv; intersection+=rv and cv; union+=rv or cv
        if rv and cv: o[x,y]=(255,255,255,180)
        elif rv: o[x,y]=(255,40,40,220)
        elif cv: o[x,y]=(40,255,80,220)
overlay.save(folder/'front-silhouette-overlay.png')
metrics={'referencePixels':ref_count,'candidatePixels':cand_count,
         'intersectionOverUnion':intersection/union if union else 0,
         'differentPixels':union-intersection}
(folder/'front-gate-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
print(json.dumps(metrics,indent=2))
