"""Generate the production-test vaccine fridge on a strict 32 px/unit grid.

Geometry uses bmesh/data APIs. The glTF exporter is the sole bpy.ops exception.
Run: blender --background --python tools/authoring/vaccine_fridge_production.py
"""
from pathlib import Path
import bmesh
import bpy

PX = 32.0
U = lambda pixels: pixels / PX
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "models" / "vaccine-fridge.glb"
ATLAS_OUT = ROOT / "public" / "textures" / "vaccine-fridge-atlas.png"

# Deterministic scene: remove the factory cube/camera/light through the data API.
for existing in list(bpy.data.objects):
    bpy.data.objects.remove(existing, do_unlink=True)

SPEC = {
    "width": 40, "depth": 28, "height": 96,
    "base_h": 16, "crown_h": 8,
    "frame": 4, "door_w": 30, "door_h": 62,
    "glass_w": 26, "glass_h": 56,
}

def material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Base Color'].default_value = rgba
    principled.inputs['Roughness'].default_value = 0.9
    principled.inputs['Alpha'].default_value = rgba[3]
    if rgba[3] < 1:
        mat.surface_render_method = 'DITHERED'
    return mat

CREAM = material("cream_frame", (0.95, 0.88, 0.75, 1))
STEEL = material("steel_panel", (0.56, 0.62, 0.62, 1))
TEAL = material("teal_frame", (0.16, 0.37, 0.33, 1))
DARK = material("interior", (0.06, 0.18, 0.17, 1))
PLUM = material("fittings", (0.22, 0.16, 0.29, 1))
OAK = material("grille", (0.68, 0.43, 0.18, 1))
GLASS = material("glass", (0.35, 0.60, 0.58, 0.35))

def box(name, size_px, at_px, mat, parent=None):
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = map(U, size_px)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(sx, sy, sz))
    # Explicit per-face 0..1 UVs. Atlas transforms are applied in Three.js.
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        normal = face.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        axes = [i for i in range(3) if i != axis]
        mins = [min(v.co[a] for v in face.verts) for a in axes]
        spans = [max(v.co[a] for v in face.verts) - mins[j] for j, a in enumerate(axes)]
        for loop in face.loops:
            loop[uv_layer].uv = tuple(
                (loop.vert.co[a] - mins[j]) / (spans[j] or 1.0)
                for j, a in enumerate(axes)
            )
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = tuple(U(v) for v in at_px)
    obj.data.materials.append(mat)
    obj.parent = parent
    return obj

root = bpy.data.objects.new("vaccine_fridge_root", None)
bpy.context.scene.collection.objects.link(root)
root["pixelGrid"] = 32
root["sliceMarginsPx"] = [4, 4, 8]

# y is depth, z is vertical. Floor is z=0.
box("base", (40, 28, 14), (0, 0, 9), TEAL, root)
box("plinth", (38, 26, 4), (0, 1, 2), PLUM, root)
box("grille", (30, 1, 8), (0, -14.2, 10), OAK, root)
box("back", (32, 2, 66), (0, 12, 55), DARK, root)
box("side_L", (4, 26, 66), (-18, 0, 55), STEEL, root)
box("side_R", (4, 26, 66), (18, 0, 55), STEEL, root)
box("cavity_floor", (32, 24, 3), (0, 0, 23), DARK, root)

for z in (31, 43, 55, 67):
    box(f"shelf_{z}", (28, 21, 2), (0, 0, z), STEEL, root)

# Independent frame rails: fixed pixel widths, no stretched markings.
box("frame_top", (36, 3, 4), (0, -14, 83), CREAM, root)
box("frame_bottom", (36, 3, 4), (0, -14, 21), CREAM, root)
box("frame_left", (4, 3, 66), (-16, -14, 52), CREAM, root)
box("frame_right", (4, 3, 66), (16, -14, 52), CREAM, root)
box("door_top", (30, 2, 3), (0, -15.8, 80), TEAL, root)
box("door_bottom", (30, 2, 3), (0, -15.8, 24), TEAL, root)
box("door_left", (3, 2, 58), (-13.5, -15.8, 52), TEAL, root)
box("door_right", (3, 2, 58), (13.5, -15.8, 52), TEAL, root)
box("glass", (24, 1, 52), (0, -16.1, 52), GLASS, root)

box("crown_lower", (44, 30, 4), (0, 0, 89), CREAM, root)
box("crown_upper", (38, 26, 4), (0, 1, 93), CREAM, root)
box("handle", (3, 3, 18), (-18, -17, 52), PLUM, root)
box("display_housing", (11, 3, 5), (5, -16, 86), PLUM, root)

def socket(name, at_px):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.location = tuple(U(v) for v in at_px)
    obj.parent = root
    obj["restPositionPx"] = list(at_px)
    return obj

socket("socket_display", (5, -18, 86))
socket("socket_glass_decal", (0, -17, 63))
socket("socket_side_bolts", (19, 0, 55))
socket("socket_grille_repeat", (0, -15, 10))
for i, z in enumerate((31, 43, 55, 67)):
    socket(f"socket_item_{i}", (0, -4, z + 2))

# 256x256 nearest-neighbour atlas. Important marks stay inside 8 px margins.
def make_atlas():
    width = height = 256
    pixels = [(0.5, 0.5, 0.5, 1.0)] * (width * height)
    def put(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            pixels[y * width + x] = color
    def fill(x0, y0, w, h, color):
        for yy in range(y0, y0 + h):
            for xx in range(x0, x0 + w): put(xx, yy, color)
    def protected_panel(x0, y0, w, h, base, edge):
        fill(x0, y0, w, h, base)
        for i in range(w): put(x0+i, y0, edge); put(x0+i, y0+h-1, (1,.96,.84,1))
        for i in range(h): put(x0, y0+i, edge); put(x0+w-1, y0+i, (1,.96,.84,1))
        # Four 2 px bolts, strictly inside the fixed 8 px margin.
        for bx, by in ((6,6),(w-8,6),(6,h-8),(w-8,h-8)):
            for dy in range(2):
                for dx in range(2): put(x0+bx+dx, y0+by+dy, (.20,.15,.27,1))
            put(x0+bx, y0+by+1, (.72,.70,.72,1))
    protected_panel(0, 0, 64, 64, (.91,.84,.70,1), (.58,.52,.44,1))       # cream
    protected_panel(64, 0, 64, 128, (.56,.62,.62,1), (.35,.39,.40,1))     # steel
    protected_panel(128, 0, 64, 64, (.16,.37,.33,1), (.08,.22,.21,1))     # teal
    fill(192, 0, 64, 128, (.15,.35,.34,.30))                               # glass
    for yy in range(78, 116):
        xx = 199 + (115-yy)//3
        put(xx, yy, (.82,.92,.86,.42)); put(xx+1, yy, (.82,.92,.86,.42))
    fill(0, 128, 128, 32, (.68,.43,.18,1))                                 # grille tile
    for yy in (6,12,18,24): fill(4,128+yy,120,2,(.13,.12,.18,1))
    fill(128,128,64,32,(.06,.12,.14,1)); fill(144,141,30,5,(.31,.72,.58,1)) # display
    fill(192,128,32,64,(.22,.16,.29,1))                                    # handle
    # Unique fixed-size decal island.
    fill(224,128,32,32,(.07,.18,.17,1)); fill(233,139,14,4,(.96,.31,.18,1))
    image = bpy.data.images.new("vaccine_fridge_atlas", width=width, height=height, alpha=True)
    flat = []
    for color in pixels: flat.extend(color)
    image.pixels = flat
    image.filepath_raw = str(ATLAS_OUT)
    image.file_format = 'PNG'
    ATLAS_OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save()

make_atlas()

OUT.parent.mkdir(parents=True, exist_ok=True)
# Export is the intentional operator exception: Blender exposes glTF this way.
bpy.context.view_layer.objects.active = root
for obj in bpy.context.scene.objects: obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', use_selection=True,
                          export_yup=True, export_materials='EXPORT')
print(f"EXPORTED {OUT}")
