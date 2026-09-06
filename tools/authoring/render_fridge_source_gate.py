"""Render the source-true candidate against the locked front view."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public'/'models'/'vaccine-fridge-source-true.glb'))
# The source skins are texture layers, not silhouette geometry.  Hide them for
# this gate so transparent atlas padding cannot inflate the measured hull.
for imported in list(bpy.context.scene.objects):
    if imported.name.startswith('source_skin_'):
        imported.hide_render=True
scene=bpy.context.scene; target=Vector((0.00776,0,1.5582))
cam_data=bpy.data.cameras.new('source_gate_front_camera')
cam=bpy.data.objects.new('source_gate_front_camera',cam_data); scene.collection.objects.link(cam)
cam.location=(target.x,-10,target.z); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.type='ORTHO'; cam_data.ortho_scale=3.213; scene.camera=cam
for name,energy,loc,size in (('Key',850,(-4,-5,7),5),('Fill',500,(4,-3,5),6)):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.size=size
    obj=bpy.data.objects.new(name,data); obj.location=loc
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler(); scene.collection.objects.link(obj)
scene.render.engine='BLENDER_WORKBENCH'; scene.render.resolution_x=358; scene.render.resolution_y=828
scene.display.shading.light='FLAT'; scene.display.shading.color_type='MATERIAL'
scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=True
scene.render.filepath=str(ROOT/'docs'/'reference-lock'/'vaccine-fridge-v1'/'candidate-front.png')
bpy.ops.render.render(write_still=True)
