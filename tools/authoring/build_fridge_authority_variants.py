"""Build scalable fridge variants from the locked measurement authority.

One door is emitted by the exact source-true builder.  Wider models translate
fixed end caps and insert complete measured door bays.  No dimension in this
file replaces or guesses a coordinate owned by geometry-authority.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_fridge_source_true as source


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1"
AUTHORITY = json.loads((LOCK / "geometry-authority.json").read_text(encoding="utf-8"))
OUT_DIR = ROOT / "public" / "models"
ADAPTIVE_ATLAS = ROOT / "public" / "textures" / "vaccine-fridge-adaptive-source-atlas.png"
DISPLAY_TEXTURE = ROOT / "public" / "textures" / "vaccine-fridge-display.png"
PPU = float(AUTHORITY["pixelsPerUnit"])
BAY_WIDTH = float(AUTHORITY["adaptive"]["doorBayWidthPx"])


def bay_centers(door_count: int) -> list[float]:
    return [(index - (door_count - 1) / 2.0) * BAY_WIDTH for index in range(door_count)]


def shift_bounds(bounds, x_offset: float):
    result = list(bounds)
    result[0] += x_offset
    result[3] += x_offset
    return result


def expand_bounds(bounds, delta: float):
    result = list(bounds)
    result[0] -= delta / 2.0
    result[3] += delta / 2.0
    return result


def shift_points(points, x_offset: float):
    return [[point[0] + x_offset, point[1], point[2]] for point in points]


def add_textured_face(name, material, points_px, uv, parent, extras=None):
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.verify()
    verts = [bm.verts.new(tuple(value / PPU for value in point)) for point in points_px]
    face = bm.faces.new(verts)
    for loop, coordinate in zip(face.loops, uv):
        loop[uv_layer].uv = coordinate
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    if extras:
        for key, value in extras.items():
            obj[key] = value
    return obj


def add_adaptive_front_skin(rings, door_count, material, parent):
    """Repeat the exact 32px front bay; preserve crown ends and centre-fill it."""
    delta = (door_count - 1) * BAY_WIDTH
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.verify()

    def add_face(lower, upper, lx0, lx1, ux0, ux1, lu0, lu1, uu0, uu1):
        lower_z, _, lower_front, _ = lower
        upper_z, _, upper_front, _ = upper
        verts = (
            bm.verts.new((lx0 / PPU, (lower_front - .60) / PPU, lower_z / PPU)),
            bm.verts.new((lx1 / PPU, (lower_front - .60) / PPU, lower_z / PPU)),
            bm.verts.new((ux1 / PPU, (upper_front - .60) / PPU, upper_z / PPU)),
            bm.verts.new((ux0 / PPU, (upper_front - .60) / PPU, upper_z / PPU)),
        )
        face = bm.faces.new(verts)
        lower_v, upper_v = 96 - lower_z, 96 - upper_z
        for loop, (u, v) in zip(face.loops, (
            (lu0, lower_v), (lu1, lower_v), (uu1, upper_v), (uu0, upper_v),
        )):
            loop[uv_layer].uv = (u / source.ATLAS_SIZE, 1 - v / source.ATLAS_SIZE)

    for lower, upper in zip(rings, rings[1:]):
        lower_z, lower_width, _, _ = lower
        upper_z, upper_width, _, _ = upper
        lower_half, upper_half = lower_width / 2, upper_width / 2
        # The body and base both own a complete 32px semantic bay.  Repeating
        # this interval duplicates doors/shelves/grilles without scaling pixels.
        if lower_width >= BAY_WIDTH and upper_width >= BAY_WIDTH and upper_z <= 87.70:
            left_edge = -door_count * BAY_WIDTH / 2
            add_face(lower, upper,
                     -lower_half - delta / 2, left_edge,
                     -upper_half - delta / 2, left_edge,
                     19.5 - lower_half, 19.5 - BAY_WIDTH / 2,
                     19.5 - upper_half, 19.5 - BAY_WIDTH / 2)
            for center in bay_centers(door_count):
                add_face(lower, upper,
                         center - BAY_WIDTH / 2, center + BAY_WIDTH / 2,
                         center - BAY_WIDTH / 2, center + BAY_WIDTH / 2,
                         19.5 - BAY_WIDTH / 2, 19.5 + BAY_WIDTH / 2,
                         19.5 - BAY_WIDTH / 2, 19.5 + BAY_WIDTH / 2)
            right_edge = door_count * BAY_WIDTH / 2
            add_face(lower, upper,
                     right_edge, lower_half + delta / 2,
                     right_edge, upper_half + delta / 2,
                     19.5 + BAY_WIDTH / 2, 19.5 + lower_half,
                     19.5 + BAY_WIDTH / 2, 19.5 + upper_half)
        else:
            # The tapered roof is narrower than a door bay.  Keep its original
            # left/right halves 1:1 and fill only the newly inserted centre.
            add_face(lower, upper,
                     -lower_half - delta / 2, -delta / 2,
                     -upper_half - delta / 2, -delta / 2,
                     19.5 - lower_half, 19.5,
                     19.5 - upper_half, 19.5)
            if delta:
                for column in range(int(delta)):
                    x0 = -delta / 2 + column
                    x1 = min(x0 + 1, delta / 2)
                    add_face(lower, upper, x0, x1, x0, x1, 13, 14, 13, 14)
            add_face(lower, upper,
                     delta / 2, lower_half + delta / 2,
                     delta / 2, upper_half + delta / 2,
                     19.5, 19.5 + lower_half,
                     19.5, 19.5 + upper_half)

    mesh = bpy.data.meshes.new("adaptive_source_skin_front_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("adaptive_source_skin_front", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    obj["texturePolicy"] = "repeat_complete_source_bay_keep_endcaps_1to1"


def add_adaptive_back_skin(rings, door_count, material, parent):
    """Preserve back end strips and repeat its neutral measured centre."""
    delta = (door_count - 1) * BAY_WIDTH
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.verify()
    center_u = 96.5
    for lower, upper in zip(rings, rings[1:]):
        lz, lw, _, lback = lower
        uz, uw, _, uback = upper
        lh, uh = lw / 2, uw / 2
        segments = [
            (-lh - delta / 2, -delta / 2, -uh - delta / 2, -delta / 2,
             center_u + lh, center_u, center_u + uh, center_u),
            (delta / 2, lh + delta / 2, delta / 2, uh + delta / 2,
             center_u, center_u - lh, center_u, center_u - uh),
        ]
        if delta:
            for column in range(int(delta)):
                x0 = -delta / 2 + column
                x1 = min(x0 + 1, delta / 2)
                segments.append((x0, x1, x0, x1, center_u, center_u - 1, center_u, center_u - 1))
        for lx0, lx1, ux0, ux1, lu0, lu1, uu0, uu1 in segments:
            verts = (
                bm.verts.new((lx1 / PPU, (lback + .08) / PPU, lz / PPU)),
                bm.verts.new((lx0 / PPU, (lback + .08) / PPU, lz / PPU)),
                bm.verts.new((ux0 / PPU, (uback + .08) / PPU, uz / PPU)),
                bm.verts.new((ux1 / PPU, (uback + .08) / PPU, uz / PPU)),
            )
            face = bm.faces.new(verts)
            lv, uv = 96 - lz, 96 - uz
            for loop, coordinate in zip(face.loops, (
                (lu1, lv), (lu0, lv), (uu0, uv), (uu1, uv),
            )):
                loop[uv_layer].uv = (coordinate[0] / source.ATLAS_SIZE,
                                     1 - coordinate[1] / source.ATLAS_SIZE)
    mesh = bpy.data.meshes.new("adaptive_source_skin_back_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("adaptive_source_skin_back", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    obj["texturePolicy"] = "fixed_back_ends_repeat_neutral_center"


def add_right_side_skin(rings, material, parent):
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.verify()
    rows = []
    for z, width, front_y, back_y in rings:
        if not 20.6 <= z <= 86.45:
            continue
        x = width / 2 + .08
        rows.append((
            bm.verts.new((x / PPU, (front_y + 2.2) / PPU, z / PPU)),
            bm.verts.new((x / PPU, back_y / PPU, z / PPU)), 96 - z,
        ))
    for lower, upper in zip(rows, rows[1:]):
        face = bm.faces.new((lower[0], lower[1], upper[1], upper[0]))
        for loop, coordinate in zip(face.loops, (
            (74, lower[2]), (40, lower[2]), (40, upper[2]), (74, upper[2]),
        )):
            loop[uv_layer].uv = (coordinate[0] / source.ATLAS_SIZE,
                                 1 - coordinate[1] / source.ATLAS_SIZE)
    mesh = bpy.data.meshes.new("adaptive_source_skin_side_right_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("adaptive_source_skin_side_right", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = parent
    obj["texturePolicy"] = "fixed_side_translate_only"


def add_adaptive_top(surface, door_count, material, parent):
    points = surface["pointsPx"]
    delta = (door_count - 1) * BAY_WIDTH
    left, right = points[0][0], points[1][0]
    front_y, back_y, z = points[0][1], points[2][1], points[0][2]
    add_textured_face("source_top_left", material,
                      [[left - delta / 2, front_y, z], [-delta / 2, front_y, z],
                       [-delta / 2, back_y, z], [left - delta / 2, back_y, z]],
                      [(0, 0), (.5, 0), (.5, 1), (0, 1)], parent,
                      {"texturePolicy": "FIXED_CORNER"})
    for column in range(int(delta)):
        x0 = -delta / 2 + column
        x1 = min(x0 + 1, delta / 2)
        u0 = 15 / 32
        u1 = 16 / 32
        add_textured_face(f"source_top_repeat_{column}", material,
                          [[x0, front_y, z], [x1, front_y, z],
                           [x1, back_y, z], [x0, back_y, z]],
                          [(u0, 0), (u1, 0), (u1, 1), (u0, 1)], parent,
                          {"texturePolicy": "REPEATABLE_CENTER"})
    add_textured_face("source_top_right", material,
                      [[delta / 2, front_y, z], [right + delta / 2, front_y, z],
                       [right + delta / 2, back_y, z], [delta / 2, back_y, z]],
                      [(.5, 0), (1, 0), (1, 1), (.5, 1)], parent,
                      {"texturePolicy": "FIXED_CORNER"})


def export_glb(root, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(out_path), export_format="GLB",
                              use_selection=True, export_yup=True,
                              export_materials="EXPORT", export_extras=True)
    data = out_path.read_bytes().replace(b'"minFilter":9984', b'"minFilter":9728')
    out_path.write_bytes(data)


def build_wide_variant(door_count: int, out_path: Path):
    source.clear_scene()
    delta = (door_count - 1) * BAY_WIDTH
    rings = [[z, width + delta, front_y, back_y]
             for z, width, front_y, back_y in AUTHORITY["sourceRingsPx"]]
    root = bpy.data.objects.new(f"vaccine_fridge_authority_{door_count}door_root", None)
    bpy.context.scene.collection.objects.link(root)
    metadata = {
        "pixelsPerUnit": AUTHORITY["pixelsPerUnit"],
        "authoritySha256": AUTHORITY["authoritySha256"],
        "sourceTruthVersion": AUTHORITY["schemaVersion"],
        "variantGeneratorVersion": 2,
        "gridDerived": True,
        "doorCount": door_count,
        "doorBayWidthPx": BAY_WIDTH,
        "bodyWidthPx": AUTHORITY["modelGridPx"]["frontOverallWidth"] + delta,
        "bodyDepthPx": AUTHORITY["modelGridPx"]["sideOverallDepth"],
        "bodyHeightPx": AUTHORITY["modelGridPx"]["totalHeight"],
        "adaptivePolicy": AUTHORITY["adaptive"]["policy"],
        "textureMode": "reference_measured_v5_microfields+semantic_bay_repeat+anchored_material_details+locked_identity_decals",
    }
    for key, value in metadata.items():
        root[key] = value

    materials = {key: source.solid_material(f"structure_{key}", tuple(rgba))
                 for key, rgba in AUTHORITY["materials"].items()}
    cream_tile = source.tiled_material_set("nano_cream_microfield", source.NANO_CREAM_TILE)
    steel_tile = source.tiled_material_set("nano_steel_microfield", source.NANO_STEEL_TILE)
    steel_panel_tile = source.tiled_material("nano_steel_panel_microfield", source.NANO_STEEL_PANEL_TILE)
    teal_tile = source.tiled_material_set("nano_teal_microfield", source.NANO_TEAL_TILE)
    materials.update({"cream": cream_tile, "steel": steel_tile, "teal": teal_tile})
    reflection = source.image_decal_material("source_glass_reflection", source.GLASS_OVERLAY)
    display_pixels = source.image_surface_material("source_display_pixels", DISPLAY_TEXTURE)
    grille_pixels = source.image_surface_material("source_grille_pixels", source.GRILLE_TEXTURE)

    source.add_loft("source_hull", rings, materials["steel"], root)
    rules = AUTHORITY["adaptive"]["partRules"]
    classified = set().union(*map(set, rules.values()))
    names = {part["name"] for part in AUTHORITY["parts"]}
    if classified != names:
        raise ValueError(f"Adaptive part rules do not partition authority parts: {classified ^ names}")
    centers = bay_centers(door_count)
    for part in AUTHORITY["parts"]:
        name = part["name"]
        if name in rules["perBay"]:
            for bay_index, center in enumerate(centers):
                source.add_box(f"{name}_bay{bay_index}", shift_bounds(part["boundsPx"], center),
                               materials[part["material"]], root, part["role"])
        elif name in rules["anchorLeft"]:
            source.add_box(name, shift_bounds(part["boundsPx"], -delta / 2),
                           materials[part["material"]], root, part["role"])
        elif name in rules["anchorRight"]:
            source.add_box(name, shift_bounds(part["boundsPx"], delta / 2),
                           materials[part["material"]], root, part["role"])
        else:
            source.add_box(name, expand_bounds(part["boundsPx"], delta),
                           materials[part["material"]], root, part["role"])

    shelf_spec = AUTHORITY["shelfTemplate"]
    for bay_index, center in enumerate(centers):
        for shelf_z in shelf_spec["elevationsPx"]:
            body = shift_bounds(shelf_spec["bodyBoundsPx"], center)
            lip = shift_bounds(shelf_spec["lipBoundsPx"], center)
            body[2] += shelf_z; body[5] += shelf_z
            lip[2] += shelf_z; lip[5] += shelf_z
            source.add_box(f"shelf_bay{bay_index}_{shelf_z}", body,
                           materials[shelf_spec["bodyMaterial"]], root, "shelf")
            source.add_box(f"shelf_lip_bay{bay_index}_{shelf_z}", lip,
                           materials[shelf_spec["lipMaterial"]], root, "shelf_front_lip")

    surface_by_name = {item["name"]: item for item in AUTHORITY["imageSurfaces"]}
    for bay_index, center in enumerate(centers):
        for surface_name, material in (("glass_reflection", reflection),):
            surface = surface_by_name[surface_name]
            source.add_image_quad(f"{surface_name}_bay{bay_index}", material,
                                  shift_points(surface["pointsPx"], center), root,
                                  {"texturePolicy": surface["texturePolicy"]})
    top_points = []
    for point in surface_by_name["source_top_surface"]["pointsPx"]:
        x_offset = -delta / 2 if point[0] < 0 else delta / 2
        top_points.append([point[0] + x_offset, point[1], point[2]])
    source.add_tiled_image_quad(
        "nano_tile_top_surface", cream_tile[2], top_points, ("x", "y"), root,
        {"texturePolicy": "TILE_WORLD_SCALE_16PX", "generatedSource": "nano-banana-2"},
    )

    source.add_conformal_side_panel(rings, steel_panel_tile, root)
    source.add_conformal_back_panel(rings, steel_panel_tile, root)
    source.add_panel_detail_decals(rings, root)
    source.add_front_style_details(centers, shelf_spec["elevationsPx"], root)
    source.add_top_style_details(root, half_width=15.7 + delta / 2)

    # The locked source builder models the plinth below the first profile ring
    # as a separate skin; apply the same bay-repeat policy here.
    x0, x1, z0, z1 = AUTHORITY["frontFeaturesPx"]["display"]
    source.add_image_quad("fixed_display", display_pixels,
                          [[x0,-16.5,z0],[x1,-16.5,z0],[x1,-16.5,z1],[x0,-16.5,z1]],
                          root, {"texturePolicy": "FIXED_CENTER_1TO1"})
    x0, x1, z0, z1 = AUTHORITY["frontFeaturesPx"]["grille"]
    for bay_index, center in enumerate(centers):
        source.add_image_quad(f"fixed_grille_bay{bay_index}", grille_pixels,
                              [[x0+center,-15.68,z0],[x1+center,-15.68,z0],
                               [x1+center,-15.68,z1],[x0+center,-15.68,z1]],
                              root, {"texturePolicy": "FIXED_PER_BAY_1TO1"})

    for name, position in AUTHORITY["socketsPx"].items():
        socket = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(socket)
        socket.parent = root
        socket.location = tuple(value / PPU for value in position)
        socket["restPositionPx"] = list(position)
        socket["adaptivePolicy"] = "fixed_center" if name == "socket_display" else "per_bay_or_edge"

    export_glb(root, out_path)
    print(json.dumps({"model": str(out_path), **metadata}, indent=2))


def build_variant(door_count: int):
    if door_count < 1:
        raise ValueError("door_count must be >= 1")
    out_path = OUT_DIR / f"vaccine-fridge-voxel-{door_count}door.glb"
    if door_count == 1:
        source.build(out_path=out_path,
                     root_name="vaccine_fridge_authority_1door_root",
                     root_extras={
                         "variantGeneratorVersion": 2,
                         "gridDerived": True,
                         "doorCount": 1,
                         "bodyWidthPx": AUTHORITY["modelGridPx"]["frontOverallWidth"],
                         "bodyDepthPx": AUTHORITY["modelGridPx"]["sideOverallDepth"],
                         "bodyHeightPx": AUTHORITY["modelGridPx"]["totalHeight"],
                         "textureMode": "reference_measured_v5_microfields+anchored_material_details+locked_identity_decals",
                     })
    else:
        build_wide_variant(door_count, out_path)


if __name__ == "__main__":
    for count in (1, 2, 3):
        build_variant(count)
