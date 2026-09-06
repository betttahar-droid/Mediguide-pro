"""Compatibility entry point for the authority-driven variant builder.

The former hard-coded voxel approximation was retired.  Keeping this filename
as a redirect prevents old documentation or local commands from regenerating
the rejected 40x28px geometry and legacy v7 atlas.
"""
from build_fridge_authority_variants import build_variant


if __name__ == "__main__":
    for door_count in (1, 2, 3):
        build_variant(door_count)
