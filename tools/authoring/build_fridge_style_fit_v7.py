"""Build the reference-researched v7 style-fit fridge without replacing v5."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_fridge_source_true as source


source.ENABLE_STYLE_FIT_V7 = True
output = source.ROOT / "public" / "models" / "vaccine-fridge-style-fit-v7.glb"
source.build(
    out_path=output,
    root_name="vaccine_fridge_style_fit_v7_root",
    root_extras={
        "styleFitVersion": 7,
        "styleAuthorities": 5,
        "acceptedBaseline": "vaccine-fridge-source-true.glb",
        "geometryPolicy": "chunky_nested_relief_fixed_hardware",
        "texturePolicy": "nano_semantic_clusters_fixed_sockets_with_gutters",
    },
)
