from pathlib import Path
import os
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj,do_unlink=True)

for filename,offset in (
    ("vaccine-fridge-voxel-1door.glb", -2.8),
    ("vaccine-fridge-voxel-2door.glb", 0.0),
    ("vaccine-fridge-voxel-3door.glb", 3.4),
):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/"public"/"models"/filename))
    imported=set(bpy.data.objects)-before
    roots=[o for o in imported if o.parent is None]
    for root in roots: root.location.x += offset

scene=bpy.context.scene
target=Vector((0.8,0,1.45))
cam_data=bpy.data.cameras.new("Voxel comparison camera")
cam=bpy.data.objects.new("Voxel comparison camera",cam_data); scene.collection.objects.link(cam)
cam.location=(5.2,-8.5,4.5); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.type='ORTHO'; cam_data.ortho_scale=8.1; scene.camera=cam
for name,energy,loc,size in (("Key",1000,(-4,-5,7),5),("Fill",600,(5,-3,5),6)):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.size=size
    obj=bpy.data.objects.new(name,data); obj.location=loc
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler(); scene.collection.objects.link(obj)
scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=1024; scene.render.resolution_y=768
scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
suffix=os.environ.get("FRIDGE_RENDER_SUFFIX", "")
scene.render.filepath=str(ROOT/"docs"/"concept"/f"vaccine-fridge-voxel-variants{suffix}.png")
scene.world.color=(.045,.052,.055)
bpy.ops.render.render(write_still=True)
