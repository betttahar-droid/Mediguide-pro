"""Compile Nano motif proposals through the measured reference-style contract."""
from __future__ import annotations

import json

import build_nano_fridge_materials as compiler


PROFILE_PATH = compiler.LOCK / "style-references" / "texture-style-profile-v1.json"
AUTHORITY_PATH = compiler.LOCK / "geometry-authority.json"
profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
ratios = profile["materialRules"]["paletteSteps"]
SHADOW, HIGHLIGHT = ratios[1], ratios[4]


def ramp(role: str) -> list[list[int]]:
    if role == "glass":
        base = [11, 48, 45]
    else:
        base = [round(channel * 255) for channel in authority["materials"][role][:3]]
    dark = [max(0, min(255, round(channel * SHADOW))) for channel in base]
    bright = [max(0, min(255, round(channel * HIGHLIGHT))) for channel in base]
    return [base, dark, bright]


compiler.NANO = compiler.LOCK / "nano-banana-v5"
compiler.SOURCE_BASENAME = "nano-reference-material-primitives-v5"
compiler.OUTPUT_VERSION = "v5"
compiler.SOURCE_CANDIDATES = tuple(
    compiler.NANO / f"{compiler.SOURCE_BASENAME}{extension}"
    for extension in (".png", ".jpg", ".webp")
)
compiler.AUDIT = compiler.NANO / f"{compiler.SOURCE_BASENAME}.audit.json"
compiler.MATERIALS = {
    # Three accents per 16x16 exactly match the measured 1.17% local-detail
    # occupancy of the primary refrigerator reference.
    "cream": {"column": 0, "dark": 2, "bright": 1},
    "steel": {"column": 1, "dark": 2, "bright": 1},
    "teal": {"column": 2, "dark": 2, "bright": 1},
    "glass": {"column": 3, "dark": 1, "bright": 1},
}
compiler.PALETTE_OVERRIDES = {role: ramp(role) for role in compiler.MATERIALS}
compiler.FACE_FACTORS = {
    role: {"top": HIGHLIGHT, "side": SHADOW}
    for role in compiler.MATERIALS
}
compiler.CLEAN_FACE_VARIANTS = {"cream": {"top"}}


def main() -> None:
    compiler.main()
    audit = json.loads(compiler.AUDIT.read_text(encoding="utf-8"))
    audit["schemaVersion"] = 5
    audit["styleProfile"] = PROFILE_PATH.relative_to(compiler.ROOT).as_posix()
    audit["compilerPolicy"] = (
        "Nano ranks motif locations; reference profile owns value ratios and "
        "1.17% center-field occupancy; authority owns material hues; semantic "
        "edge/corner/panel details are fixed-size adaptive layers"
    )
    audit["measuredStyleContract"] = profile["materialRules"]
    compiler.AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
