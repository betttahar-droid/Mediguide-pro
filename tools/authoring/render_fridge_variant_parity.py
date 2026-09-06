"""Render source-true and generated one-door assets under an identical rig."""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "variants"
OUT.mkdir(parents=True, exist_ok=True)


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(collection):
            collection.remove(block)


def render(model_name: str, output_name: str):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(ROOT / "public" / "models" / model_name))
    scene = bpy.context.scene
    target = Vector((0, 0, 1.48))
    camera_data = bpy.data.cameras.new("parity_camera")
    camera = bpy.data.objects.new("parity_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = Vector((4.6, -6.2, 4.2))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3.85
    scene.camera = camera
    world = bpy.data.worlds.new("parity_world") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.055,.045,.065,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .22
    for name, energy, location, size in (
        ("Key",650,(-3.5,-4.5,6.0),4.5),
        ("Fill",280,(4.0,-2.0,3.5),5.0),
        ("Rim",420,(2.0,4.0,5.0),3.0),
    ):
        data = bpy.data.lights.new(name,"AREA")
        data.energy, data.size = energy, size
        light = bpy.data.objects.new(name,data)
        light.location = location
        light.rotation_euler = (target-light.location).to_track_quat("-Z","Y").to_euler()
        scene.collection.objects.link(light)
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / output_name)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)


render("vaccine-fridge-source-true.glb", "parity-source.png")
render("vaccine-fridge-voxel-1door.glb", "parity-generated-1door.png")
