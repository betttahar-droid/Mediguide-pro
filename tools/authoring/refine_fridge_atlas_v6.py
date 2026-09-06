"""Refine Nano's atlas with deterministic reference-matched fixed details."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
src=ROOT/'public'/'textures'/'vaccine-fridge-atlas-v5.png'
dst=ROOT/'public'/'textures'/'vaccine-fridge-atlas-v6.png'
im=Image.open(src).convert('RGBA'); d=ImageDraw.Draw(im)

PLUM=(43,24,58,255); PLUM_HI=(82,54,99,255); DARK=(24,30,34,255)
GOLD=(180,116,43,255); GOLD_HI=(220,157,69,255); GREEN=(77,150,116,255)
ORANGE=(232,105,45,255); CLEAR=(0,0,0,0)

# Fixed display cell: exact readable 4C and orange status lamp.
d.rectangle((768,256,1023,511),fill=CLEAR)
d.rectangle((806,345,985,424),fill=PLUM)
d.rectangle((814,353,977,416),fill=PLUM_HI)
d.rectangle((824,360,967,408),fill=DARK)
d.rectangle((835,373,851,392),fill=ORANGE)
def seg4(x,y,s=5):
    for box in ((x+15,y,x+20,y+15),(x,y+15,x+20,y+20),(x+15,y+20,x+20,y+40)):
        d.rectangle(tuple(v*s//5 if False else v for v in box),fill=GREEN)
def digit4(x,y):
    d.rectangle((x+16,y,x+21,y+17),fill=GREEN); d.rectangle((x,y+13,x+21,y+18),fill=GREEN)
    d.rectangle((x+16,y+13,x+21,y+38),fill=GREEN); d.rectangle((x,y,x+5,y+18),fill=GREEN)
def glyph_c(x,y):
    d.rectangle((x,y,x+5,y+38),fill=GREEN); d.rectangle((x,y,x+21,y+5),fill=GREEN)
    d.rectangle((x,y+33,x+21,y+38),fill=GREEN)
digit4(876,365); glyph_c(908,365)

# Grille: four bold rows and three bays, matching the turnaround.
d.rectangle((0,512,255,767),fill=(20,44,43,255))
d.rectangle((18,548,237,724),fill=GOLD)
d.rectangle((27,557,228,715),fill=GOLD_HI)
for yy in (568,600,632,664):
    for x0,x1 in ((34,91),(101,158),(168,221)):
        d.rectangle((x0,yy,x1,yy+13),fill=PLUM)

# Fixed handle sprite with mounts and a one-pixel-style highlight.
d.rectangle((512,512,767,767),fill=CLEAR)
d.rectangle((602,544,681,735),fill=PLUM)
d.rectangle((616,560,663,719),fill=(54,31,72,255))
d.rectangle((616,560,630,704),fill=PLUM_HI)
d.rectangle((584,558,616,596),fill=PLUM); d.rectangle((584,684,616,722),fill=PLUM)

# One clean bolt sprite and one hinge sprite in a transparent fixed cell.
d.rectangle((768,512,1023,767),fill=CLEAR)
d.rectangle((786,536,831,581),fill=(75,88,92,255)); d.rectangle((794,544,823,573),fill=(151,166,166,255))
d.rectangle((802,552,815,565),fill=(43,53,57,255)); d.rectangle((795,545,802,552),fill=(218,224,211,255))
d.rectangle((900,540,970,616),fill=(63,72,79,255)); d.rectangle((912,550,958,606),fill=(126,139,143,255))
d.rectangle((932,550,939,606),fill=PLUM)

# Transparent asymmetric wear islands. Detail is concentrated at exposed
# lower corners exactly as the turnaround, leaving the centers quiet.
for x0,color in ((0,(231,220,194,255)),(256,(182,199,198,255)),(512,(63,113,104,255))):
    d.rectangle((x0,768,x0+255,1023),fill=CLEAR)
    for bx,by,bw,bh in ((8,214,34,18),(18,194,18,12),(40,226,20,10),(220,220,25,16),(230,200,12,12)):
        d.rectangle((x0+bx,768+by,x0+bx+bw,768+by+bh),fill=color)
    # sparse square paint chips/bolts near fixed corners only
    d.rectangle((x0+14,782,x0+25,793),fill=color); d.rectangle((x0+230,782,x0+241,793),fill=color)

im.save(dst)
print(f'REFINED {dst}')
