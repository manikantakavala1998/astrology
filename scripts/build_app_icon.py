"""Generate the desktop app icon (.ico) from the same artwork as star.svg.

Pillow cannot read SVG, so rather than pull in a native SVG rasteriser this
redraws the identical shape: the rounded dark square and the 4-point gold star
from web/static/star.svg, using that file's own viewBox coordinates and fill
colours so the window icon matches the favicon exactly.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Straight from star.svg: viewBox "0 0 40 40", rect rx=12, and the star path.
_VIEWBOX = 40
_CORNER_RADIUS = 12
_BACKGROUND = "#0c1528"
_STAR = "#f0ca83"
_STAR_POINTS = (
    (20, 5), (24, 16), (35, 20), (24, 24),
    (20, 35), (16, 24), (5, 20), (16, 16),
)

# Windows picks the best match per context (taskbar, title bar, alt-tab), so a
# single .ico carries every size it may ask for.
_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)

_OUTPUT = Path(__file__).resolve().parent.parent / "src" / "vedic_astro" / "web" / "static" / "app.ico"


def _render(size: int) -> Image.Image:
    """One square frame, drawn at 4x and downsampled for clean edges (Pillow
    has no anti-aliased polygon fill)."""
    scale = 4
    canvas = size * scale
    unit = canvas / _VIEWBOX

    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, canvas - 1, canvas - 1), radius=int(_CORNER_RADIUS * unit), fill=_BACKGROUND
    )
    draw.polygon([(x * unit, y * unit) for x, y in _STAR_POINTS], fill=_STAR)
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    frames = [_render(size) for size in _ICON_SIZES]
    frames[-1].save(_OUTPUT, format="ICO", sizes=[(s, s) for s in _ICON_SIZES])
    print(f"wrote {_OUTPUT} ({', '.join(f'{s}x{s}' for s in _ICON_SIZES)})")


if __name__ == "__main__":
    main()
