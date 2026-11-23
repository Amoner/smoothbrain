"""Draws arrow.tga, the nearest-vendor arrow: gold, pointing up, with a dark rim.

    python SmoothBrain/dev/make-arrow.py

The game turns it to point at the vendor, so it must point straight up here.
Drawn four times larger and shrunk, for smooth edges. Uncompressed 32-bit
TGA, like auction.tga and lock.tga.
"""
import os
from PIL import Image, ImageDraw

SIZE, SCALE = 64, 4
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "arrow.tga")


def arrow(scale):
    """The arrow's outline, in a SIZE x SIZE square, times `scale`."""
    points = [(32, 4), (58, 34), (42, 34), (42, 60), (22, 60), (22, 34), (6, 34)]
    return [(x * scale, y * scale) for x, y in points]


big = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
draw = ImageDraw.Draw(big)
# Gold, like the game's own text, with an even dark rim.
draw.polygon(arrow(SCALE), fill=(255, 210, 0, 255), outline=(20, 12, 0, 255), width=3 * SCALE)
small = big.resize((SIZE, SIZE), Image.LANCZOS)
small.save(OUT, compression=None)
print("wrote", os.path.normpath(OUT))
