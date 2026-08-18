#!/usr/bin/env python3
"""Tile the photos into labeled contact sheets for fast batch identification."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys

PHOTOS = Path(__file__).parent / "photos"
OUT = Path(__file__).parent / "sheets"
OUT.mkdir(exist_ok=True)

COLS, ROWS = 3, 2
CELL_W, CELL_H = 760, 900
LABEL_H = 46
PAD = 8

try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
except OSError:
    font = ImageFont.load_default()

files = sorted(PHOTOS.glob("C-*"))
per_sheet = COLS * ROWS

start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
end = int(sys.argv[2]) if len(sys.argv) > 2 else len(files)
files = [f for f in files if start <= int(f.stem.split("-")[1]) <= end]

for s in range(0, len(files), per_sheet):
    chunk = files[s:s + per_sheet]
    sheet = Image.new(
        "RGB",
        (COLS * (CELL_W + PAD) + PAD, ROWS * (CELL_H + LABEL_H + PAD) + PAD),
        "white",
    )
    draw = ImageDraw.Draw(sheet)

    for i, f in enumerate(chunk):
        c, r = i % COLS, i // COLS
        x = PAD + c * (CELL_W + PAD)
        y = PAD + r * (CELL_H + LABEL_H + PAD)

        im = Image.open(f)
        im = im.convert("RGB")
        im.thumbnail((CELL_W, CELL_H), Image.LANCZOS)
        ox = x + (CELL_W - im.width) // 2
        oy = y + LABEL_H + (CELL_H - im.height) // 2
        sheet.paste(im, (ox, oy))

        draw.rectangle([x, y, x + CELL_W, y + LABEL_H], fill="#111111")
        draw.text((x + 12, y + 6), f.stem, fill="white", font=font)

    first = chunk[0].stem
    last = chunk[-1].stem
    sheet.save(OUT / f"sheet_{first}_{last}.jpg", quality=88)

print(f"wrote {len(list(OUT.glob('sheet_*.jpg')))} sheets to {OUT}")
