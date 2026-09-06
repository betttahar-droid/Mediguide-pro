"""Build a non-destructive one-door GLB containing the Nano margin-decal experiment."""
from pathlib import Path

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_fridge_source_true as source


source.ENABLE_NANO_DECAL_EXPERIMENT = True
output = source.ROOT / "public" / "models" / "vaccine-fridge-nano-decals-v6.glb"
source.build(
    out_path=output,
    root_name="vaccine_fridge_nano_decals_v6_root",
    root_extras={
        "materialExperiment": "nano_banana_v6_fixed_decals_with_protected_margins",
        "acceptedBaseline": "vaccine-fridge-source-true.glb",
    },
)
