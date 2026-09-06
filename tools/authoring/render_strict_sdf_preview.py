"""Render the exact strict-SDF JS box manifest with flat analytic-band twins."""
from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "strict-sdf-preview-manifest-v1.json"
OUTPUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "strict-sdf-fridge-render-v1.png"
DATA = json.loads(MANIFEST.read_text(encoding="utf-8"))
U = 1 / 32
PALETTE = DATA["style"]["palette"]
TINTS = DATA["style"]["tints"]


def hex_rgb(value: str, factor=1.0, alpha=1.0):
    value = value.lstrip("#")
    rgb = [int(value[index:index+2], 16) / 255 for index in (0, 2, 4)]
    return tuple(min(1, channel * factor) for channel in rgb) + (alpha,)


def material(role: str, variant: str, tint: float, opacity=1.0):
    name = f"strict_{role}_{variant}_{tint:.3f}_{opacity:.2f}"
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    index = {"base": 0, "shadow": 1, "highlight": 2, "outline": 3}[variant]
    rgba = hex_rgb(PALETTE[role][index], tint, opacity)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = rgba
    emission.inputs["Strength"].default_value = 1.0
    if opacity < 1:
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = opacity
        mat.node_tree.links.new(transparent.outputs["BSDF"], mix.inputs[1])
        mat.node_tree.links.new(emission.outputs["Emission"], mix.inputs[2])
        mat.node_tree.links.new(mix.outputs["Shader"], output.inputs["Surface"])
    else:
        mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    mat.diffuse_color = rgba
    if opacity < 1:
        mat.surface_render_method = "BLENDED"
    return mat


def quad(name, coordinates, mat):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(coordinates, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def strips_front(part, bounds):
    x0, y0, z0, x1, _, z1 = bounds
    role, rule = part["role"], part["rule"]
    width, height = x1-x0, z1-z0
    if rule == "flat" or min(width, height) <= U * 3:
        return
    y = y0 - U * .018
    dark = material(role, "outline", TINTS["front"], part["opacity"])
    light = material(role, "highlight", TINTS["front"], part["opacity"])
    shadow = material(role, "shadow", TINTS["front"], part["opacity"])
    # Outer one-unit rim, then the directional catch immediately inside it.
    for index, (coords, mat) in enumerate((
        ([(x0,y,z0),(x0+U,y,z0),(x0+U,y,z1),(x0,y,z1)], dark),
        ([(x1-U,y,z0),(x1,y,z0),(x1,y,z1),(x1-U,y,z1)], dark),
        ([(x0,y,z0),(x1,y,z0),(x1,y,z0+U),(x0,y,z0+U)], dark),
        ([(x0,y,z1-U),(x1,y,z1-U),(x1,y,z1),(x0,y,z1)], dark),
        ([(x0+U,y,z0+U),(x0+2*U,y,z0+U),(x0+2*U,y,z1-U),(x0+U,y,z1-U)], light),
        ([(x0+U,y,z1-2*U),(x1-U,y,z1-2*U),(x1-U,y,z1-U),(x0+U,y,z1-U)], light),
        ([(x1-2*U,y,z0+U),(x1-U,y,z0+U),(x1-U,y,z1-U),(x1-2*U,y,z1-U)], shadow),
        ([(x0+U,y,z0+U),(x1-U,y,z0+U),(x1-U,y,z0+2*U),(x0+U,y,z0+2*U)], shadow),
    )):
        quad(f"{part['name']}_front_band_{index}", coords, mat)
    if rule == "panel" and min(width, height) > U * 9:
        inset, line = U * 4, U * .75
        xi0, xi1, zi0, zi1 = x0+inset, x1-inset, z0+inset, z1-inset
        for index, coords in enumerate((
            [(xi0,y,zi0),(xi0+line,y,zi0),(xi0+line,y,zi1),(xi0,y,zi1)],
            [(xi1-line,y,zi0),(xi1,y,zi0),(xi1,y,zi1),(xi1-line,y,zi1)],
            [(xi0,y,zi0),(xi1,y,zi0),(xi1,y,zi0+line),(xi0,y,zi0+line)],
            [(xi0,y,zi1-line),(xi1,y,zi1-line),(xi1,y,zi1),(xi0,y,zi1)],
        )):
            quad(f"{part['name']}_front_inset_{index}", coords, shadow)


def add_box(part):
    sx, sy, sz = part["size"]
    px, py, pz = part["position"]
    x0, x1 = px-sx/2, px+sx/2
    y0, y1 = py-sy/2, py+sy/2
    z0, z1 = pz-sz/2, pz+sz/2
    vertices = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh = bpy.data.meshes.new(part["name"] + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(part["name"], mesh)
    bpy.context.scene.collection.objects.link(obj)
    role, opacity = part["role"], part["opacity"]
    for face_role, tint in (("bottom", TINTS["bottom"]), ("top", TINTS["top"]),
                            ("front", TINTS["front"]), ("side", TINTS["side"]),
                            ("back", TINTS["back"]), ("side", TINTS["side"])):
        obj.data.materials.append(material(role, "base", tint, opacity))
    for index, polygon in enumerate(obj.data.polygons):
        polygon.material_index = index
    strips_front(part, (x0,y0,z0,x1,y1,z1))


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for part in DATA["parts"]:
        add_box(part)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 840
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT)
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.006, 0.008, 0.011, 1.0)
    background.inputs["Strength"].default_value = 0.08
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (4.7, -6.7, 4.6)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 4.05
    look_at(camera, (0, 0, 1.52))
    scene.camera = camera
    bpy.ops.render.render(write_still=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
