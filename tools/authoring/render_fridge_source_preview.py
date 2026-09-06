"""Render the source-true fridge from an isometric inspection camera."""
from pathlib import Path
import os
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get(
    "FRIDGE_RENDER_PATH",
    ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "source-true-preview.png",
))
MODEL = Path(os.environ.get(
    "FRIDGE_MODEL_PATH",
    ROOT / "public" / "models" / "vaccine-fridge-source-true.glb",
))

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(MODEL))

scene = bpy.context.scene
target = Vector((0, 0, 1.48))
camera_data = bpy.data.cameras.new("source_true_preview_camera")
camera = bpy.data.objects.new("source_true_preview_camera", camera_data)
scene.collection.objects.link(camera)
camera.location = Vector((4.6, -6.2, 4.2))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 3.85
scene.camera = camera

world = bpy.data.worlds.new("source_true_world") if not scene.world else scene.world
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.045, 0.065, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

for name, energy, location, size in (
    ("Key", 650, (-3.5, -4.5, 6.0), 4.5),
    ("Fill", 280, (4.0, -2.0, 3.5), 5.0),
    ("Rim", 420, (2.0, 4.0, 5.0), 3.0),
):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    light.location = location
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(light)

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    # Blender 5.2 folded the Eevee Next identifier back into BLENDER_EEVEE.
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.filepath = str(OUT)
scene.view_settings.look = "AgX - Medium High Contrast"
bpy.ops.render.render(write_still=True)
print(OUT)
