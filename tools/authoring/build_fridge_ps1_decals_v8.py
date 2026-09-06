"""Build a coarse, faceted fridge whose sub-4px details are Nano decals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_fridge_source_true as source


# Keep only silhouette-changing profile breaks and snap them to a half-pixel
# grid. This removes small transitional rings that made the hull feel smooth.
source.SOURCE_RINGS = [
    [3.5, 38.5, -15.0, 17.0],
    [4.5, 37.5, -15.0, 17.0],
    [15.5, 38.0, -15.0, 17.0],
    [18.5, 35.5, -15.0, 17.0],
    [20.6, 36.5, -15.0, 17.0],
    [86.45, 37.0, -15.0, 15.0],
    [87.5, 38.5, -16.0, 16.0],
    [92.5, 38.5, -16.0, 16.0],
    [94.5, 34.0, -13.0, 14.5],
    [96.0, 31.5, -13.0, 14.5],
]
source.ENABLE_PS1_DECAL_STYLE_V8 = True
output = source.ROOT / "public" / "models" / "vaccine-fridge-ps1-decals-v8.glb"
source.build(
    out_path=output,
    root_name="vaccine_fridge_ps1_decals_v8_root",
    root_extras={
        "styleFitVersion": 8,
        "styleAuthorities": 5,
        "acceptedBaseline": "vaccine-fridge-source-true.glb",
        "geometryPolicy": "coarse_half_pixel_faceted_macro_forms_only",
        "macroProfileRings": len(source.SOURCE_RINGS),
        "geometryDetailThresholdPx": 4,
        "smallDetailPolicy": "nano_fixed_decals_not_geometry",
    },
)
