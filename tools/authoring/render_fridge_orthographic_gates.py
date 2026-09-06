"""Render clean geometry silhouettes for all locked orthographic panels."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "public" / "models" / "vaccine-fridge-source-true.glb"))
for obj in bpy.context.scene.objects:
    if obj.name.startswith("source_skin_"):
        obj.hide_render = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_y = 828
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True

camera_data = bpy.data.cameras.new("orthographic_gate_camera")
camera = bpy.data.objects.new("orthographic_gate_camera", camera_data)
scene.collection.objects.link(camera)
camera_data.type = "ORTHO"
scene.camera = camera

views = {
    "front": {"resolution_x": 358, "ortho": 3.213, "target": (0.00776, 0, 1.5621), "location": (0.00776, -10, 1.5621)},
    "side": {"resolution_x": 327, "ortho": 3.222, "target": (0, 0.375 / 32.0, 1.5642), "location": (-10, 0.375 / 32.0, 1.5642)},
    "back": {"resolution_x": 347, "ortho": 3.222, "target": (0, 0, 1.5642), "location": (0, 10, 1.5642)},
}
for name, settings in views.items():
    target = Vector(settings["target"])
    camera.location = Vector(settings["location"])
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.ortho_scale = settings["ortho"]
    scene.render.resolution_x = settings["resolution_x"]
    scene.render.filepath = str(OUT / f"candidate-{name}.png")
    bpy.ops.render.render(write_still=True)
