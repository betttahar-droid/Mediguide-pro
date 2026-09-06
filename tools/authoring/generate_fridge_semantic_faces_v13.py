"""Generate face-role texture masks through the project's single Nano caller."""
from pathlib import Path

from PIL import Image, ImageDraw

from concept_sheet import generate_image, load_key


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "semantic-v13"
DIAGNOSTICS = LOCK / "diagnostics"
VARIANTS = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "variants"
STYLE = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "style-research-v7"

PROMPT = """Use case: stylized-concept
Asset type: source sheet for a deterministic UV-less per-face material compiler
Primary request: author exactly eight separate square FACE-ROLE TONE MASKS for the supplied vaccine-fridge geometry.

Input roles:
- Images 1 and 2 are immutable raw front and isometric geometry renders. Preserve their part boundaries.
- Images 3 and 4 are diagnostic part-ID and face-orientation passes for understanding only; do not copy their colors.
- Image 5 is the target vaccine-fridge visual authority.
- Images 6 through 10 are style references. Learn their hard rectangular pixel clusters, quiet broad faces, short directional catches and construction-readable marks; do not copy their subjects.
- Image 11 is the spatial guide. Fill its eight equal square safe zones in reading order. Do not copy the guide outlines.

The eight masks in reading order are:
1 ROOF_TOP: quiet inset roof plate, two short top/left catches, two tiny corner notches.
2 CROWN_FRONT: layered horizontal fascia bands, short left/right edge catches, quiet center reserved for controls.
3 CABINET_SIDE: quiet sheet metal, one construction seam, two short right-edge service marks and tiny corner fasteners.
4 DOOR_FRAME: enamel frame perimeter with sparse square hinge/socket notches, empty center.
5 SHELF_TOP: metal shelf field with a quiet middle, one short directional highlight cluster and a few long shallow horizontal seams.
6 SHELF_LIP: narrow horizontal lip vocabulary, bright upper catch, dark lower band, one square fastener at each end.
7 BASE_FRONT: recessed service-panel perimeter, two short corner catches, quiet center reserved for ventilation.
8 VENT_FIELD: repeated thick horizontal dark slots separated by base bands, with a bright upper rim and dark lower rim.

Output composition: pure flat magenta #FF00FF background. Exactly eight disconnected equal-size square panels in a 4-column by 2-row layout matching the guide. Wide magenta gutters. Nothing may touch another panel.

Tone language: these are semantic masks, never colored textures. Use only five flat neutral values: near-black #202020 for deepest construction/shadow marks, dark #606060 for secondary shade, base #808080 for untouched material, light #C0C0C0 for highlights, and near-white #F0F0F0 for strongest catches. The cutter will quantize them exactly.

Style and density: each panel looks 32 huge logical texels across, nearest-neighbor, hard square edges. Use deliberate 1-logical-texel lines and 2-to-8-texel clusters. Keep 75-to-85 percent of each broad field at the base value, but make the requested marks clearly readable. Directional catches favor top/left; dark construction bands favor bottom/right.

Constraints: no perspective, no object render, no shadows outside panels, no gradients, blur, antialiasing, texture noise, random dirt, scratches, text, letters, numbers, legends, labels, arrows, watermark, color, tiny speckle, or extra panels. Do not move or reinterpret the supplied fridge geometry."""


def make_guide(path: Path):
    guide = Image.new("RGB", (1024, 1024), "#ff00ff")
    draw = ImageDraw.Draw(guide)
    for row in range(2):
        for column in range(4):
            x0 = 37 + column * 245
            y0 = 175 + row * 360
            draw.rectangle((x0, y0, x0 + 210, y0 + 210), outline="#777777", width=3)
            draw.line((x0 + 97, y0 + 105, x0 + 113, y0 + 105), fill="#ffffff", width=2)
            draw.line((x0 + 105, y0 + 97, x0 + 105, y0 + 113), fill="#ffffff", width=2)
    guide.save(path, optimize=False)


def main():
    LOCK.mkdir(parents=True, exist_ok=True)
    guide = LOCK / "semantic-faces-v13-spatial-guide.png"
    make_guide(guide)
    prompt_path = LOCK / "semantic-faces-v13-prompt.txt"
    prompt_path.write_text(PROMPT, encoding="utf-8")
    refs = (
        DIAGNOSTICS / "view-front-surfaces-0-decals-0.png",
        DIAGNOSTICS / "view-iso-surfaces-0-decals-0.png",
        DIAGNOSTICS / "view-iso-diagnostic-parts.png",
        DIAGNOSTICS / "view-iso-diagnostic-faces.png",
        VARIANTS / "authority-1door.png",
        Path(r"C:\Users\mansour\Downloads\inspo 1.jpg"),
        Path(r"C:\Users\mansour\Downloads\inspo 4.jpg"),
        Path(r"C:\Users\mansour\Downloads\big inspo 3.jpg"),
        STYLE / "inspo-3-gif-samples.png",
        Path(r"C:\Users\mansour\Downloads\inspo 2.jpg"),
        guide,
    )
    output = generate_image(
        PROMPT,
        LOCK / "semantic-faces-v13-source.png",
        load_key(),
        refs=refs,
        ref_instruction=(
            "Respect the numbered input roles in the prompt. The final image is a source-mask sheet, "
            "not a presentation render. Geometry images are invariants, reference images are style only, "
            "and the final image is the layout guide only."
        ),
    )
    print(f"PROMPT={prompt_path}")
    print(f"SAVED={output}")


if __name__ == "__main__":
    main()
