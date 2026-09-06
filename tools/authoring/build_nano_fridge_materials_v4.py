"""Compile the stronger retro Nano Banana v4 board without mutating v3."""
from __future__ import annotations

import build_nano_fridge_materials as compiler


compiler.NANO = compiler.LOCK / "nano-banana-v4"
compiler.SOURCE_BASENAME = "nano-retro-microtexture-kit-v4"
compiler.OUTPUT_VERSION = "v4"
compiler.SOURCE_CANDIDATES = tuple(
    compiler.NANO / f"{compiler.SOURCE_BASENAME}{extension}"
    for extension in (".png", ".jpg", ".webp")
)
compiler.AUDIT = compiler.NANO / f"{compiler.SOURCE_BASENAME}.audit.json"
compiler.MATERIALS = {
    "cream": {"column": 0, "dark": 4, "bright": 2},
    "steel": {"column": 1, "dark": 4, "bright": 2},
    "teal": {"column": 2, "dark": 4, "bright": 2},
    "glass": {"column": 3, "dark": 2, "bright": 2},
}
compiler.FACE_FACTORS = {
    "cream": {"top": 1.10, "side": 0.80},
    "steel": {"top": 1.14, "side": 0.70},
    "teal": {"top": 1.12, "side": 0.70},
    "glass": {"top": 1.08, "side": 0.74},
}


if __name__ == "__main__":
    compiler.main()
