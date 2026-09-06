"""Fit the approved textured fridge to the measured turnaround grid.

Input: docs/vaccine-fridge-remodel.blend
Output: docs/vaccine-fridge-turnaround-v11.blend and a comparison render.

The model sheet is authored at 32 px per Blender unit. Structural fields are
allowed to tile; recognizable marks are tagged fixed and retain their authored
world dimensions while the carcass is fitted to 44 x 30 x 96 pixels.
"""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT_BLEND = ROOT / "docs" / "vaccine-fridge-turnaround-v11.blend"
OUT_RENDER = ROOT / "docs" / "concept" / "vaccine-fridge-turnaround-v11.png"
PPU = 32.0

STUDIO = {"Floor", "Camera", "Key", "Fill", "Rim"}
parts = [o for o in bpy.data.objects if o.type == "MESH" and o.name not in STUDIO]

fixed_names = {
    "Continuous handle", "Handle mount", "Handle mount.001",
    "Readout housing", "Readout texture", "Right side unique texture layer",
}
repeat_names = {
    "Left side panel", "Right side panel", "Rear wall", "Condenser base",
    "Crown top", "Crown upper", "Crown lower", "Glass door",
}
edge_names = {
    "Outer frame bottom", "Outer frame top", "Outer frame stile",
    "Outer frame stile.001", "Inner door bottom", "Inner door top",
    "Inner door stile", "Inner door stile.001", "Plinth shadow",
    "Plum foot", "Plum foot.001", "Crown shadow",
}

def bounds(objects):
    pts = [o.matrix_world @ Vector(corner) for o in objects for corner in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi

lo, hi = bounds(parts)
size = hi - lo
target = Vector((44 / PPU, 30 / PPU, 96 / PPU))
factor = Vector((target.x / size.x, target.y / size.y, target.z / size.z))
pivot = Vector(((lo.x + hi.x) * .5, (lo.y + hi.y) * .5, lo.z))

# Cache invariant world dimensions before fitting the structural shell.
fixed_dims = {o.name: o.dimensions.copy() for o in parts if o.name in fixed_names}
for obj in parts:
    delta = obj.location - pivot
    obj.location = pivot + Vector((delta.x * factor.x, delta.y * factor.y, delta.z * factor.z))
    obj.scale.x *= factor.x
    obj.scale.y *= factor.y
    obj.scale.z *= factor.z

# Fixed islands slide with the fitted carcass but never change world size.
for obj in parts:
    if obj.name in fixed_dims:
        obj.dimensions = fixed_dims[obj.name]

# Quantize transforms to the 32 px/unit construction grid. Sub-pixel bevel
# vertices remain legal, but every modular resting point and part extent is an
# integer authored pixel.
for obj in parts:
    obj.location = Vector(tuple(round(v * PPU) / PPU for v in obj.location))
    if obj.name not in fixed_names:
        obj.dimensions = Vector(tuple(max(1, round(v * PPU)) / PPU for v in obj.dimensions))
    if obj.name in fixed_names:
        policy = "fixed_1to1"
    elif obj.name == "Recessed grille":
        policy = "fixed_ends_repeat_x"
    elif obj.name in edge_names:
        policy = "protected_edge"
    elif obj.name.startswith("Empty shelf") or obj.name.startswith("Shelf lip"):
        policy = "repeat_per_bay"
    elif obj.name in repeat_names:
        policy = "tile_center"
    else:
        policy = "structural"
    obj["texturePolicy"] = policy
    obj["pixelsPerUnit"] = 32

def place_part(name, size_px, center_px):
    """Set exact world-space pixel bounds even when a mesh has an offset origin."""
    obj = bpy.data.objects[name]
    obj.dimensions = Vector(tuple(v / PPU for v in size_px))
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    current_center = Vector(tuple((min(p[i] for p in corners) + max(p[i] for p in corners)) * .5 for i in range(3)))
    wanted_center = Vector(tuple(v / PPU for v in center_px))
    obj.location += wanted_center - current_center
    obj.location = Vector(tuple(round(v * PPU) / PPU for v in obj.location))

# Sheet-critical silhouette modules use absolute integer-pixel bounds. This
# also prevents the old off-centre mesh origins from opening gaps after fitting.
place_part("Crown lower", (44, 30, 4), (0, 0, 86))
place_part("Crown upper", (40, 26, 4), (0, 1, 90))
place_part("Crown top", (36, 22, 4), (0, 2, 94))
place_part("Condenser base", (40, 28, 14), (0, 1, 11))
place_part("Recessed grille", (28, 1, 7), (0, -14, 11))
place_part("Plum foot", (8, 20, 4), (-15, 1, 2))
place_part("Plum foot.001", (8, 20, 4), (15, 1, 2))

# Explicit independent anchors for details that cannot be baked into a tiled
# or stretched center field.
socket_specs = {
    "socket_display": (5, -18, 84),
    "socket_handle": (-19, -18, 52),
    "socket_glass_streak": (-5, -17, 66),
    "socket_grille_left": (-14, -15, 11),
    "socket_grille_right": (14, -15, 11),
    "socket_side_bolts": (20, 0, 56),
}
for name, px in socket_specs.items():
    obj = bpy.data.objects.get(name) or bpy.data.objects.new(name, None)
    if obj.name not in bpy.context.scene.objects:
        bpy.context.scene.collection.objects.link(obj)
    obj.location = tuple(v / PPU for v in px)
    obj["restPositionPx"] = list(px)
    obj["texturePolicy"] = "fixed_1to1"

scene = bpy.context.scene
scene["pixelsPerUnit"] = 32
scene["referenceSizePx"] = [44, 30, 96]
scene["textureArchitecture"] = "tile_center+protected_edge+fixed_1to1"

# Preserve the established studio but frame the taller corrected silhouette.
scene.render.resolution_x = 768
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT_RENDER)
OUT_RENDER.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
bpy.ops.render.render(write_still=True)

lo2, hi2 = bounds(parts)
print("TURNAROUND_FIT", [round(v * PPU, 2) for v in (hi2 - lo2)])
print("SAVED", OUT_BLEND)
print("RENDERED", OUT_RENDER)
