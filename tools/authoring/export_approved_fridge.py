"""Export the approved textured fridge .blend as the production GLB.

Run Blender with docs/vaccine-fridge-remodel.blend before this script. Existing
mesh/material/image data is preserved; only studio objects are excluded and
adaptive sockets are added. glTF export is the sole operator exception.
"""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "models" / "vaccine-fridge.glb"

exclude = {"Floor", "Camera", "Key", "Fill", "Rim", "Warm key", "Cool fill"}
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in exclude]

root = bpy.data.objects.get("vaccine_fridge_root")
if not root:
    root = bpy.data.objects.new("vaccine_fridge_root", None)
    bpy.context.scene.collection.objects.link(root)
root["pixelGrid"] = 32
root["sliceMarginsPx"] = [4, 4, 8]

for obj in meshes:
    if obj.parent is None:
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world

def socket(name, location, rest_px):
    obj = bpy.data.objects.get(name)
    if not obj:
        obj = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.location = location
    obj.parent = root
    obj["restPositionPx"] = rest_px
    return obj

socket("socket_display", (.17, -.60, 2.585), [5, -18, 86])
socket("socket_glass_decal", (0, -.57, 1.92), [0, -17, 63])
socket("socket_side_bolts", (.64, 0, 1.60), [19, 0, 55])
socket("socket_grille_repeat", (0, -.47, .35), [0, -15, 10])
for i, z in enumerate((.84, 1.23, 1.62, 2.01)):
    socket(f"socket_item_{i}", (0, -.12, z + .06), [0, -4, 31 + i * 12])

for obj in bpy.context.scene.objects:
    obj.select_set(False)
for obj in [root, *meshes, *[o for o in bpy.data.objects if o.name.startswith('socket_')]]:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT), export_format='GLB', use_selection=True,
    export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
    export_extras=True,
)
print(f"EXPORTED_APPROVED {OUT} meshes={len(meshes)}")
