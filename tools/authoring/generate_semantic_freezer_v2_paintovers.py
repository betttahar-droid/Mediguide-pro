"""Generate geometry-locked, view-aligned texture paintovers with Nano Banana 2."""
from pathlib import Path
import sys

from concept_sheet import generate_image, load_key


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v2"
INPUTS = LOCK / "paintover-inputs"
OUTPUTS = LOCK / "paintovers"
AUTHORITY = Path(r"C:\Users\mansour\Documents\Modular builder\Gemini version builder\img_gen")

COMMON = """Use case: precise-object-edit
Asset type: view-aligned material and texture paintover for extraction into an adaptive 3D face shader.

Input roles:
- Image 1 is the EDIT TARGET and immutable geometry raster. Preserve its exact camera, silhouette, object scale, positions, openings, shelves, contents, handle and machinery. Do not add, remove, resize or move geometry.
- Image 2 is the matching VISUAL AUTHORITY. Transfer its material colors, pixel density, construction markings, edge wear, labels and localized shading onto Image 1.
- Image 3 is supporting cross-view authority for consistent material identity only. Never copy its camera or silhouette.

Background: preserve pure flat #FF00FF everywhere outside the edit target. No shadow and no background texture.
Style: match the authority's dense retro PS1-era pixel-textured 3D rendering: small crisp square texels, cool grey-green enamel, blue-grey service panels, dark construction seams, controlled dither, clustered edge wear, and localized one-to-four-pixel highlights. Preserve large forms but do not leave large faces uniformly flat.
Material rule: variation must describe construction and material response. Concentrate wear at exposed corners, lower edges, fasteners and service openings. Use quieter but still subtly dithered centers. No soft gradients, blur, antialiasing, painterly strokes or photographic noise.
Identity details: retain the authority's medical cold-storage vocabulary. Where visible, render the exact strings "MED-FREEZE", "TEMP OK", "4.2°C" and "VACSAFE 5000" in a tiny deterministic-looking pixel font. Medicine cartons and bottles should carry concise readable label blocks such as "COVID-19", "MMR", "FLU VAX", "POLIO", "HEP B" and "BOOSTER" when space permits. Never create extra products.
Invariants: Image 1 geometry wins over Image 2. Repaint surfaces only. Keep every object boundary aligned to Image 1 within one pixel. Output one view only, filling the same frame, with no caption, border, legend, watermark or extra object."""

PROMPTS = {
    "iso": COMMON + """
View-specific request: texture the front/isometric edit target. Keep the open cavity readable. Place the medical emblem and MED-FREEZE identity on the left of the fascia, TEMP OK near center, and the 4.2°C display on the right. Apply distinct fixed labels to existing cartons and vials without changing their box silhouettes. The visible service side must contain authority-matched large panel seams, a small upper rating plate, and a lower louvred vent.""",
    "side": COMMON + """
View-specific request: texture the exact orthographic service-side edit target. Preserve the handle at the front edge and rear machinery projection. Match the authority's segmented access panels, narrow dark seams, upper-front rating plate, wide lower-rear louvred vent, sparse edge catches, and denser wear along the lower/front edges. Do not draw front-face contents onto this side.""",
    "back": COMMON + """
View-specific request: texture the rear/isometric edit target. Preserve every existing condenser bar, rail, fan housing, compressor and pipe. Match the authority's high-frequency condenser rhythm, warning plates, dark mechanical bay, cool metal panels, copper accents and localized lower machinery shading. Never replace the real coil geometry with a painted rectangle.""",
}


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    key = load_key()
    jobs = (
        (
            "iso",
            INPUTS / "view-iso-surfaces-0-fittings-0-bg-magenta.png",
            AUTHORITY / "ref_front_view.png",
            AUTHORITY / "ref_right_side_view.png",
        ),
        (
            "side",
            INPUTS / "view-side-surfaces-0-fittings-0-bg-magenta.png",
            AUTHORITY / "ref_right_side_view.png",
            AUTHORITY / "ref_front_view.png",
        ),
        (
            "back",
            INPUTS / "view-backIso-surfaces-0-fittings-0-bg-magenta.png",
            AUTHORITY / "ref_back_view.png",
            AUTHORITY / "ref_right_side_view.png",
        ),
    )
    selected = set(sys.argv[1:])
    for name, target, authority, support in jobs:
        if selected and name not in selected:
            continue
        prompt_path = OUTPUTS / f"{name}-prompt.txt"
        prompt_path.write_text(PROMPTS[name], encoding="utf-8")
        output = generate_image(
            PROMPTS[name], OUTPUTS / f"{name}-paintover.png", key,
            refs=(target, authority, support),
            ref_instruction=(
                "Treat Image 1 as the only edit target. Treat Images 2 and 3 as visual evidence. "
                "Preserve the target geometry and exact magenta background."
            ),
        )
        print(f"{name.upper()}={output}")


if __name__ == "__main__":
    main()
