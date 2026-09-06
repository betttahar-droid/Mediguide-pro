"""Add reference-matched chipped paint, undercoat and restrained rust to v6."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
im=Image.open(ROOT/'public'/'textures'/'vaccine-fridge-atlas-v6.png').convert('RGBA')
d=ImageDraw.Draw(im); CLEAR=(0,0,0,0)

def damage_cell(x0, paint, undercoat, rust):
    # Runtime crops the lower-left 80x76 portion of each cell.
    d.rectangle((x0,948,x0+79,1023),fill=CLEAR)
    # stepped missing-paint silhouette, deliberately asymmetric
    for box,color in (
        ((2,54,30,74),paint),((10,42,44,65),paint),((25,31,57,54),paint),
        ((4,62,18,74),undercoat),((20,49,37,65),undercoat),((42,38,57,52),undercoat),
        ((8,46,14,52),rust),((31,56,38,63),rust),((49,42,55,49),rust),
        ((62,67,76,74),paint),((68,58,76,67),undercoat),
    ):
        a,b,c,e=box; d.rectangle((x0+a,948+b,x0+c,948+e),fill=color)
    # isolated square chips/scratches, all hard pixels
    for x,y,color in ((5,28,undercoat),(18,22,paint),(35,18,rust),(54,27,undercoat),(65,35,paint)):
        d.rectangle((x0+x,948+y,x0+x+5,948+y+5),fill=color)

damage_cell(0,(239,229,204,255),(102,95,81,255),(155,91,43,255))
damage_cell(256,(220,229,222,255),(69,86,89,255),(147,82,41,255))
damage_cell(512,(104,151,135,255),(27,63,59,255),(139,76,38,255))

out=ROOT/'public'/'textures'/'vaccine-fridge-atlas-v7.png'; im.save(out)
print(f'REFINED {out}')
