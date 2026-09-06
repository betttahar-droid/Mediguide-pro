"""Manual Nano Banana authoring pass for handbook-compliant surface masks."""
from pathlib import Path

from PIL import Image, ImageDraw

from concept_sheet import generate_image, load_key


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "handbook-v12"
RESEARCH = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "style-research-v7"

REFS = (
    Path(r"C:\Users\mansour\Downloads\inspo 1.jpg"),
    Path(r"C:\Users\mansour\Downloads\inspo 4.jpg"),
    Path(r"C:\Users\mansour\Downloads\big inspo 3.jpg"),
    Path(r"C:\Users\mansour\Downloads\inspo 2.jpg"),
    RESEARCH / "inspo-3-gif-samples.png",
)

PROMPT = """Asset type: source sheet for UV-less nine-slice surface tone masks. The complete output canvas itself must be square. The final input image is a SPATIAL GUIDE ONLY: use its first five equal square safe zones and leave the sixth zone completely empty. Do not copy its grey outlines or white crosshairs.

Draw exactly FIVE separate SQUARE panels: three across the top row and two in the first two zones of the bottom row. Leave the bottom-right sixth zone empty magenta. All five panels must have exactly the same width and height and must fit inside the guide's equal safe zones. Leave wide clear pure-magenta #FF00FF channels between panels and around the outer canvas. Nothing may touch anything else. Each panel is straight-on and strictly orthographic: no perspective, no foreshortening, no vanishing point, no shadow, no ground plane, no reflection.

The five panels, left to right:
1. a plain pressed panel with a chunky border and one large square bolt just inside each corner;
2. the same pressed panel with one thick horizontal seam across its middle;
3. a bordered panel whose middle contains thick horizontal ventilation slots running edge to edge;
4. a plain bordered panel with nothing in its middle;
5. a bordered panel with one large shallow rectangular recess in its middle.

These are TONE MASKS, not coloured materials. Use NO COLOUR AT ALL and EXACTLY THREE flat neutral greys: #303030 for shade marks, #808080 for untouched base, and #E0E0E0 for highlight marks. The unused ground is exactly #FF00FF.

Each panel should look about twenty huge chunky square pixels across, like a rugged PlayStation 1 texture enlarged with nearest-neighbour scaling. Every mark is one or two of those huge pixels thick. No thin lines, fine detail, small dots, antialiasing, gradients, blur, texture noise, scratches, dirt, labels, text, annotations, cell borders, or watermark.

On every panel the authored border must sit exactly at that panel's outer edge with nothing outside it, and must be two chunky pixels thick. Bolts remain strictly inside the border. Keep the middle broad and quiet except where the requested seam, vent slots, or recess belongs."""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    guide = Image.new("RGB", (1024, 1024), "#ff00ff")
    draw = ImageDraw.Draw(guide)
    for row in range(2):
        for column in range(3):
            x0, y0 = 42 + column * 330, 190 + row * 390
            draw.rectangle((x0, y0, x0 + 280, y0 + 280), outline="#777777", width=3)
            draw.line((x0 + 132, y0 + 140, x0 + 148, y0 + 140), fill="#ffffff", width=2)
            draw.line((x0 + 140, y0 + 132, x0 + 140, y0 + 148), fill="#ffffff", width=2)
    guide_path = OUT / "surface-masks-v12-spatial-guide.png"
    guide.save(guide_path, optimize=False)
    prompt_path = OUT / "surface-masks-v12-prompt.txt"
    prompt_path.write_text(PROMPT, encoding="utf-8")
    output = generate_image(
        PROMPT,
        OUT / "surface-masks-v12-source-guided.png",
        load_key(),
        refs=(*REFS, guide_path),
        ref_instruction=(
            "Images 1-5 are the STYLE REFERENCE. Match their hard-edged blocky forms, "
            "large texel size and restrained surface vocabulary, but do not copy their subjects. "
            "Image 6 is an input-only SPATIAL GUIDE and is not a style reference."
        ),
    )
    print(f"PROMPT={prompt_path}")
    print(f"SAVED={output}")


if __name__ == "__main__":
    main()
