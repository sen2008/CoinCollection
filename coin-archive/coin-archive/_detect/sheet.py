#!/usr/bin/env python3
"""Contact sheet of specific records, labelled, big enough to read a date."""
import csv
import sys
from PIL import Image, ImageDraw, ImageFont

# Not every photograph is a .jpg — the filename lives in the inventory.
PHOTO = {r["id"]: r["photo"] for r in csv.DictReader(open("inventory.csv"))}

ids = sys.argv[1:-1]
out = sys.argv[-1]
CELL, COLS = 360, 5
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
except OSError:
    font = ImageFont.load_default()

rows = (len(ids) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * CELL, rows * (CELL + 34)), "#101010")
for n, cid in enumerate(ids):
    im = Image.open("photos/" + PHOTO[cid])
    im.thumbnail((CELL - 8, CELL - 8))
    x, y = (n % COLS) * CELL, (n // COLS) * (CELL + 34)
    sheet.paste(im, (x + (CELL - im.width) // 2, y + 34 + (CELL - 8 - im.height) // 2))
    ImageDraw.Draw(sheet).text((x + 8, y + 4), cid, fill="#FFD34D", font=font)
sheet.save(out, quality=92)
print(f"{out}: {len(ids)} records")
