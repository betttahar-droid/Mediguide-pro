"""Render a CPU twin of the side-panel A/B for documentation and review."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
TILE = ROOT / "public" / "textures" / "vaccine-fridge-nano-steel-panel-microtile-v5.png"
OUT = ROOT / "docs" / "reference-lock" / "vaccine-fridge-v1" / "analytic-side-panel-ab-v1.png"
WIDTH, HEIGHT = 28, 66
SCALE = 7


def control_panel() -> Image.Image:
    tile = Image.open(TILE).convert("RGB")
    panel = Image.new("RGB", (WIDTH, HEIGHT))
    for y in range(0, HEIGHT, tile.height):
        for x in range(0, WIDTH, tile.width):
            panel.paste(tile, (x, y))
    return panel


def analytic_panel() -> Image.Image:
    base = (round(97 * .858), round(122 * .858), round(128 * .858))
    shadow = (round(74 * .858), round(93 * .858), round(98 * .858))
    highlight = (round(118 * .858), round(148 * .858), round(156 * .858))
    outline = (round(56 * .858), round(71 * .858), round(74 * .858))
    panel = Image.new("RGB", (WIDTH, HEIGHT), base)
    px = panel.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            distance = min(x, WIDTH - 1 - x, y, HEIGHT - 1 - y)
            if abs(distance - 4) < .5:
                px[x, y] = tuple(round(a * .28 + b * .72) for a, b in zip(base, shadow))
            if distance < 2:
                px[x, y] = highlight if min(x, HEIGHT - 1 - y) <= min(WIDTH - 1 - x, y) else shadow
            if distance < 1:
                px[x, y] = outline
    return panel


def add_shared_marks(panel: Image.Image) -> None:
    draw = ImageDraw.Draw(panel)
    dark, light = (57, 72, 76), (101, 127, 134)
    for color, box in (
        (dark, (19, 14, 25, 14)), (dark, (17, 17, 23, 17)), (light, (20, 18, 25, 18)),
        (dark, (18, 47, 25, 47)), (dark, (16, 50, 23, 50)), (light, (21, 51, 25, 51)),
    ):
        draw.rectangle(box, fill=color)


def main() -> None:
    panels = [("V5 CONTROL — TILED CENTER", control_panel()),
              ("HYBRID PILOT — UV-LESS BANDS", analytic_panel())]
    for _, panel in panels:
        add_shared_marks(panel)
    margin, header, gap = 18, 34, 24
    panel_width, panel_height = WIDTH * SCALE, HEIGHT * SCALE
    canvas = Image.new("RGB", (margin * 2 + panel_width * 2 + gap,
                                margin * 2 + header + panel_height), (15, 17, 21))
    draw = ImageDraw.Draw(canvas)
    for index, (label, panel) in enumerate(panels):
        x = margin + index * (panel_width + gap)
        draw.text((x, margin), label, fill=(232, 230, 220))
        canvas.paste(panel.resize((panel_width, panel_height), Image.Resampling.NEAREST),
                     (x, margin + header))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, optimize=False)
    print(OUT)


if __name__ == "__main__":
    main()
