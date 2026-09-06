from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
scene = bpy.context.scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'public' / 'models' / 'vaccine-fridge-exact.glb'))

camera_data = bpy.data.cameras.new("Exact preview camera")
camera = bpy.data.objects.new("Exact preview camera", camera_data)
scene.collection.objects.link(camera)
camera.location = (4.2, -5.8, 3.8)
target = Vector((0, 0, 1.5))
camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 3.8
scene.camera = camera

for name, energy, location, size in (
    ("Key", 900, (-3,-4,6), 4), ("Fill", 500, (4,-2,4), 5),
):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size = energy, 'DISK', size
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(obj)

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(ROOT / 'docs' / 'concept' / 'vaccine-fridge-exact-bmesh-preview.png')
scene.world.color = (.055, .065, .07)
bpy.ops.render.render(write_still=True)
