"""Render every authority variant alone at a comparable inspection scale."""
from pathlib import Path
import os

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "variants"
OUT.mkdir(parents=True, exist_ok=True)
SUFFIX = os.environ.get("FRIDGE_RENDER_SUFFIX", "")


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            datablocks.remove(block)


def world_bounds(objects):
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    return (Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
            Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))))


for door_count in (1, 2, 3):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(
        ROOT / "public" / "models" / f"vaccine-fridge-voxel-{door_count}door.glb"))
    imported = list(bpy.context.scene.objects)
    low, high = world_bounds(imported)
    target = (low + high) / 2

    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("authority_variant_camera")
    camera = bpy.data.objects.new("authority_variant_camera", camera_data)
    scene.collection.objects.link(camera)
    direction = Vector((4.6, -6.2, 4.2)).normalized()
    camera.location = target + direction * 8
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    width, height = high.x - low.x, high.z - low.z
    camera_data.ortho_scale = max(height * 1.12, width * 1.42)
    scene.camera = camera

    world = bpy.data.worlds.new("authority_variant_world") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.045, .052, .055, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .22
    for name, energy, offset, size in (
        ("Key", 650, Vector((-3.5,-4.5,6.0)), 4.5),
        ("Fill", 280, Vector((4.0,-2.0,3.5)), 5.0),
        ("Rim", 420, Vector((2.0,4.0,5.0)), 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size = energy, size
        light = bpy.data.objects.new(name, data)
        light.location = target + offset
        light.rotation_euler = (target-light.location).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(light)

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / f"authority-{door_count}door{SUFFIX}.png")
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)
    print(scene.render.filepath)
