"""Generate semantic face and fixed-fitting source sheets with Nano Banana 2."""
from pathlib import Path

from PIL import Image, ImageDraw

from concept_sheet import generate_image, load_key


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs" / "reference-lock" / "semantic-freezer-v1"
DIAGNOSTICS = LOCK / "diagnostics"
AUTHORITY = Path(r"C:\Users\mansour\Documents\Modular builder\Gemini version builder\img_gen")

FACE_PROMPT = """Use case: stylized-concept
Asset type: source sheet for a deterministic UV-less per-face material compiler.
Primary request: author exactly eight separate square FACE-ROLE TONE MASKS for the supplied tall medical freezer geometry.

Input roles:
- Images 1, 2 and 3 are the immutable visual authority: front/open-isometric, right-side, and rear views of the same appliance. Copy their purposeful surface vocabulary but never redraw the appliance.
- Images 4, 5 and 6 are raw geometry renders. Their silhouettes, part boundaries and mounting planes are immutable.
- Images 7 and 8 are diagnostic part-ID and face-orientation passes for spatial understanding only. Never copy their colors.
- Image 9 is the spatial guide. Fill its eight equal square safe zones in reading order and do not copy its outlines.

The eight masks in reading order are:
1 ROOF_TOP: pale enamel top, inset perimeter, short top/left catches, two small corner scuffs.
2 CROWN_FRONT: wide medical-freezer fascia with layered horizontal bands, a quiet left logo socket, center status-light sockets and a right digital-display socket.
3 CABINET_SIDE: purple-grey sheet metal with large rectangular service-panel divisions, one long vertical seam, short edge catches and sparse corner fasteners.
4 DOOR_FRAME: pale enamel frame strip with dark inner edge, bright outer catch, sparse hinge/socket notches and worn lower corner.
5 SHELF_TOP: cold metal shelf field, quiet center, long shallow horizontal seams, sparse blocky reflection patches.
6 SHELF_LIP: narrow metal lip vocabulary, bright upper catch, dark lower band and square end fasteners.
7 BASE_FRONT: lower service plinth with a recessed panel perimeter, controlled corner wear and quiet center reserved for fittings.
8 VENT_FIELD: repeated thick horizontal dark louvres separated by base bands, with a fixed pale rim.

Output composition: pure flat magenta #FF00FF background. Exactly eight disconnected equal-size square panels in a strict 4-column by 2-row layout matching the guide. Wide magenta gutters. Nothing may touch another panel.

Tone language: these are semantic masks, not colored textures. Use only five flat neutral values: #202020 deepest marks, #606060 secondary shade, #808080 untouched material, #C0C0C0 highlight, #F0F0F0 strongest catches. The deterministic compiler will quantize them.

Style: coarse retro PS1-era pixel art, each panel reading as 32 large logical texels across; nearest-neighbor square edges; deliberate one-texel lines and two-to-eight-texel clusters. Keep broad fields calm and make every mark explain construction. Directional catches favor top/left; dark construction bands favor bottom/right.

Hard constraints: no perspective, object render, text, letters, numbers, logos, shadows outside panels, gradients, blur, antialiasing, noise, random dirt, tiny speckle, watermark, color, extra panels, or geometry changes."""

FITTING_PROMPT = """Use case: stylized-concept
Asset type: fixed-size semantic decal source sheet for the supplied tall medical freezer.
Create exactly eight disconnected rectangular pixel-art fitting panels in a strict 4-column by 2-row layout on pure flat magenta #FF00FF.

Input roles are identical to the face-mask request: the first three images are the front/right/rear authority; the next three are immutable raw geometry; the next two are diagnostics; the final image is the layout guide.

Panels in reading order:
1 MEDICAL_BADGE: abstract snowflake/cross-like cold-storage emblem, no letters.
2 DIGITAL_STATUS: dark rectangular temperature display with two blocky numeral-like glyph groups and tiny status lamps; no readable text.
3 STATUS_STRIP: short dark control strip with four colored square lamps and two pale buttons.
4 SIDE_RATING: pale service/rating plate with dark barcode-like horizontal rows; no readable letters.
5 REAR_WARNING: pale warning plate with one ochre caution block and dark line rows; no readable letters.
6 CARTON_LABEL: medicine-package label with blue header, dark line rows and one colored corner tab.
7 VIAL_LABEL: compact pale wrap-label motif with dark line rows and one blue square.
8 FAN_GRILLE: bold circular-ish octagonal fan grille built from square pixel rings and four straight supports.

Match the authority's restrained cool-grey, pale enamel, medical blue, amber, muted red and charcoal palette. Coarse PS1-era pixel clusters, 20-to-32 logical texels per fitting, hard nearest-neighbor edges, no gradients, no antialiasing, no random dirt. Preserve wide magenta gutters. Do not draw the appliance, add shadows, change geometry, or include any extra objects, captions, legends, watermark or readable text."""


def guide(path: Path, rectangles: bool = False):
    image = Image.new("RGB", (1024, 1024), "#ff00ff")
    draw = ImageDraw.Draw(image)
    width, height = ((210, 130) if rectangles else (210, 210))
    y_step = 350
    for row in range(2):
        for column in range(4):
            x0 = 37 + column * 245
            y0 = 225 + row * y_step
            draw.rectangle((x0, y0, x0 + width, y0 + height), outline="#777777", width=3)
            draw.line((x0 + width // 2 - 8, y0 + height // 2, x0 + width // 2 + 8, y0 + height // 2), fill="#ffffff", width=2)
            draw.line((x0 + width // 2, y0 + height // 2 - 8, x0 + width // 2, y0 + height // 2 + 8), fill="#ffffff", width=2)
    image.save(path, optimize=False)


def main():
    LOCK.mkdir(parents=True, exist_ok=True)
    face_guide = LOCK / "face-spatial-guide.png"
    fitting_guide = LOCK / "fitting-spatial-guide.png"
    guide(face_guide)
    guide(fitting_guide, rectangles=True)
    (LOCK / "semantic-faces-prompt.txt").write_text(FACE_PROMPT, encoding="utf-8")
    (LOCK / "semantic-fittings-prompt.txt").write_text(FITTING_PROMPT, encoding="utf-8")

    shared = (
        AUTHORITY / "ref_front_view.png",
        AUTHORITY / "ref_right_side_view.png",
        AUTHORITY / "ref_back_view.png",
        DIAGNOSTICS / "view-front-surfaces-0.png",
        DIAGNOSTICS / "view-side-surfaces-0.png",
        DIAGNOSTICS / "view-backIso-surfaces-0.png",
        DIAGNOSTICS / "view-iso-diagnostic-parts.png",
        DIAGNOSTICS / "view-iso-diagnostic-faces.png",
    )
    key = load_key()
    face = generate_image(
        FACE_PROMPT,
        LOCK / "semantic-freezer-faces-source.png",
        key,
        refs=shared + (face_guide,),
        ref_instruction="Respect the numbered roles. Output only the requested source-mask sheet on exact magenta.",
    )
    print(f"FACES={face}")
    fitting = generate_image(
        FITTING_PROMPT,
        LOCK / "semantic-freezer-fittings-source.png",
        key,
        refs=shared + (fitting_guide,),
        ref_instruction="Respect the numbered roles. Output only the requested fixed-fitting sheet on exact magenta.",
    )
    print(f"FITTINGS={fitting}")


if __name__ == "__main__":
    main()
