"""Exact pixel-plotted vaccine fridge master.

No primitive or UV operators are used. Every vertex is authored in blueprint
pixels and divided by PIXELS_PER_UNIT. Every loop receives atlas coordinates
from an explicit top-left-origin pixel rectangle. glTF export is the only
operator call because Blender exposes the exporter as an operator.
"""
from pathlib import Path
import bmesh
import bpy

PIXELS_PER_UNIT = 32.0
ATLAS_W = ATLAS_H = 1024
ROOT = Path(__file__).resolve().parents[2]
ATLAS_PATH = ROOT / "public" / "textures" / "vaccine-fridge-atlas-v5.png"
GLB_PATH = ROOT / "public" / "models" / "vaccine-fridge-exact.glb"

# Authoritative construction table, in reference pixels. Main body W = 40 px
# = 1.25 Blender units. Overall crown is 44 px wide and total height is 96 px.
P = {
    "body_w": 40, "body_d": 28, "overall_h": 96,
    "plinth_h": 4, "base_h": 18, "body_top": 84,
    "crown_0": 84, "crown_1": 88, "crown_2": 92, "crown_3": 96,
    "outer_frame_x": 18, "outer_frame_z0": 18, "outer_frame_z1": 84,
    "door_x": 15, "door_z0": 22, "door_z1": 81,
    "glass_x": 12, "glass_z0": 25, "glass_z1": 78,
    "protected_edge": 4,
}

# Top-left atlas rectangles: x, y, width, height. These are the only atlas
# coordinates used by geometry; changing artwork never changes UV math.
R = {
    "cream": (0,0,256,256), "steel": (256,0,256,256),
    "teal": (512,0,256,256), "glass": (768,0,256,256),
    "cream_edge": (0,256,256,256), "steel_edge": (256,256,256,256),
    "teal_edge": (512,256,256,256), "screen": (818,348,156,74),
    "grille": (0,512,256,256), "grille_ends": (256,512,256,256),
    "handle": (602,536,79,203), "bolts": (768,512,256,256),
    "cream_decal": (0,768,256,256), "steel_decal": (256,768,256,256),
    "teal_decal": (512,768,256,256), "empty": (768,768,256,256),
}

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

atlas = bpy.data.images.load(str(ATLAS_PATH), check_existing=True)
atlas.colorspace_settings.name = "sRGB"
mat = bpy.data.materials.new("vaccine_fridge_exact_atlas")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = atlas
tex.interpolation = "Closest"
mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = .9

decal_mat = mat.copy(); decal_mat.name = "vaccine_fridge_fixed_islands"
decal_tex = next(n for n in decal_mat.node_tree.nodes if n.type == 'TEX_IMAGE')
decal_bsdf = decal_mat.node_tree.nodes.get("Principled BSDF")
decal_mat.node_tree.links.new(decal_tex.outputs["Alpha"], decal_bsdf.inputs["Alpha"])
decal_mat.surface_render_method = 'DITHERED'

glass_mat = mat.copy(); glass_mat.name = "vaccine_fridge_glass"
glass_bsdf = glass_mat.node_tree.nodes.get("Principled BSDF")
glass_bsdf.inputs["Alpha"].default_value = .38
glass_mat.surface_render_method = 'DITHERED'

plum_mat = bpy.data.materials.new("vaccine_fridge_plum_fittings")
plum_mat.use_nodes = True
plum_bsdf = plum_mat.node_tree.nodes.get("Principled BSDF")
plum_bsdf.inputs["Base Color"].default_value = (.07, .025, .11, 1)
plum_bsdf.inputs["Roughness"].default_value = .88

root = bpy.data.objects.new("vaccine_fridge_exact_root", None)
bpy.context.scene.collection.objects.link(root)
root["pixelsPerUnit"] = 32
root["blueprintSizePx"] = [44, 30, 96]
root["protectedMarginPx"] = P["protected_edge"]

def uv(x, y):
    """Exact atlas pixel corner -> Blender UV (top-left input origin)."""
    return (x / ATLAS_W, 1.0 - (y / ATLAS_H))

def rect_uvs(rect):
    x, y, w, h = rect
    return (uv(x, y + h), uv(x + w, y + h), uv(x + w, y), uv(x, y))

def plotted_box(name, bounds_px, region, policy="structural"):
    """Create an axis-aligned cuboid from eight explicitly plotted vertices."""
    x0, y0, z0, x1, y1, z1 = bounds_px
    coords_px = (
        (x0,y0,z0), (x1,y0,z0), (x1,y0,z1), (x0,y0,z1),
        (x0,y1,z0), (x1,y1,z0), (x1,y1,z1), (x0,y1,z1),
    )
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    verts = [bm.verts.new(tuple(c / PIXELS_PER_UNIT for c in p)) for p in coords_px]
    bm.verts.ensure_lookup_table()
    face_indices = (
        (0,1,2,3), (5,4,7,6), (4,0,3,7),
        (1,5,6,2), (4,5,1,0), (3,2,6,7),
    )
    uv_layer = bm.loops.layers.uv.verify()
    face_uv = rect_uvs(R[region])
    for indices in face_indices:
        face = bm.faces.new(tuple(verts[i] for i in indices))
        for loop, exact_uv in zip(face.loops, face_uv):
            loop[uv_layer].uv = exact_uv
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(glass_mat if region == "glass" else mat)
    obj.parent = root
    obj["texturePolicy"] = policy
    obj["atlasRectPx"] = list(R[region])
    obj["blueprintBoundsPx"] = list(bounds_px)
    return obj

def plotted_front_decal(name, bounds_px, region):
    """A fixed, non-stretching atlas island slightly in front of a panel."""
    x0, y, z0, x1, z1 = bounds_px
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    verts = [bm.verts.new((x/PIXELS_PER_UNIT, y/PIXELS_PER_UNIT, z/PIXELS_PER_UNIT))
             for x, z in ((x0,z0),(x1,z0),(x1,z1),(x0,z1))]
    uv_layer = bm.loops.layers.uv.verify()
    face = bm.faces.new(verts)
    for loop, exact_uv in zip(face.loops, rect_uvs(R[region])):
        loop[uv_layer].uv = exact_uv
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(decal_mat); obj.parent = root
    obj["texturePolicy"] = "fixed_1to1"
    obj["atlasRectPx"] = list(R[region])
    return obj

# Condenser/plinth, hollow carcass, rear and shelves.
plinth_obj = plotted_box("plinth", (-20,-13,0, 20,13,4), "teal", "protected_edge")
plinth_obj.data.materials.clear(); plinth_obj.data.materials.append(plum_mat)
left_foot = plotted_box("left_foot", (-20,-14,0, -12,-8,3), "teal", "fixed_1to1")
left_foot.data.materials.clear(); left_foot.data.materials.append(plum_mat)
right_foot = plotted_box("right_foot", (12,-14,0, 20,-8,3), "teal", "fixed_1to1")
right_foot.data.materials.clear(); right_foot.data.materials.append(plum_mat)
plotted_box("condenser_base", (-20,-14,4, 20,14,18), "teal", "tile_center")
plotted_box("rear_wall", (-16,11,18, 16,13,84), "teal", "tile_center")
plotted_box("left_cheek", (-20,-13,18, -16,13,84), "steel", "tile_center")
plotted_box("right_cheek", (16,-13,18, 20,13,84), "steel", "tile_center")
plotted_box("cavity_floor", (-16,-11,18, 16,11,21), "teal", "tile_center")
for index, z in enumerate((29,41,53,65)):
    plotted_box(f"shelf_{index}", (-14,-10,z, 14,10,z+2), "steel", "repeat_per_bay")

# Cream outer frame and teal door frame are independent strips. The center of
# each strip may tile, while fixed details live on separate socket/decal nodes.
plotted_box("outer_left", (-18,-15,18, -14,-12,84), "cream", "protected_edge")
plotted_box("outer_right", (14,-15,18, 18,-12,84), "cream", "protected_edge")
plotted_box("outer_bottom", (-14,-15,18, 14,-12,23), "cream", "protected_edge")
plotted_box("outer_top", (-14,-15,79, 14,-12,84), "cream", "protected_edge")
plotted_box("door_left", (-15,-17,22, -12,-15,81), "teal", "protected_edge")
plotted_box("door_right", (12,-17,22, 15,-15,81), "teal", "protected_edge")
plotted_box("door_bottom", (-12,-17,22, 12,-15,25), "teal", "protected_edge")
plotted_box("door_top", (-12,-17,78, 12,-15,81), "teal", "protected_edge")
plotted_box("glass", (-12,-17.25,25, 12,-17,78), "glass", "tile_center")

# Three exact stepped crown layers reproduce the reference silhouette.
plotted_box("crown_lower", (-22,-15,84, 22,15,88), "cream", "protected_edge")
plotted_box("crown_middle", (-20,-13,88, 20,13,92), "cream", "protected_edge")
plotted_box("crown_top", (-18,-11,92, 18,11,96), "cream", "tile_center")

# Fixed 1:1 recognizable islands.
handle_obj = plotted_box("handle", (-20,-18,43, -17,-15,61), "teal", "fixed_1to1")
handle_obj.data.materials.clear(); handle_obj.data.materials.append(plum_mat)
for mount_name, z0, z1 in (("handle_mount_low",43,46), ("handle_mount_high",58,61)):
    mount = plotted_box(mount_name, (-19,-16,z0, -16,-13,z1), "teal", "fixed_1to1")
    mount.data.materials.clear(); mount.data.materials.append(plum_mat)
display_obj = plotted_box("display", (0,-18,83, 11,-15,88), "teal", "fixed_1to1")
display_obj.data.materials.clear(); display_obj.data.materials.append(plum_mat)
plotted_box("grille", (-15,-15,8, 15,-14,15), "grille", "fixed_ends_repeat_x")
plotted_front_decal("display_detail", (1,-18.2,84,10,87), "screen")

def socket(name, p):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = root
    obj.location = tuple(c / PIXELS_PER_UNIT for c in p)
    obj["restPositionPx"] = list(p)
    obj["texturePolicy"] = "fixed_1to1"
    return obj

socket("socket_display", (5.5,-18,85.5))
socket("socket_handle", (-18.5,-18,52))
socket("socket_glass_streak", (-5,-17.5,66))
socket("socket_grille_left", (-14,-15.5,11.5))
socket("socket_grille_right", (14,-15.5,11.5))
socket("socket_side_bolts", (19,0,55))

GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
# Intentional sole operator exception: Blender's built-in glTF exporter.
for obj in bpy.context.scene.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.gltf(
    filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
    export_yup=True, export_materials="EXPORT", export_extras=True,
)
print("EXACT_BMESH", GLB_PATH)
