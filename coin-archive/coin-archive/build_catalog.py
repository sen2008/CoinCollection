#!/usr/bin/env python3
"""
build_catalog.py — reads inventory.csv + photos/, writes catalog.html.

Thumbnails are embedded in the file so the catalog works on its own,
emailed or copied anywhere. Full-resolution plates are referenced
relatively from photos/, so keep the folder together and you get both.

Re-run this any time inventory.csv changes.
"""

import base64
import csv
import io
import json
from pathlib import Path
from PIL import Image, ImageOps

HERE = Path(__file__).parent
PHOTOS = HERE / "photos"
CSV_PATH = HERE / "inventory.csv"
TEMPLATE = HERE / "template.html"
OUT = HERE / "catalog.html"

THUMB_W = 340
QUALITY = 68


def thumb(path: Path) -> str:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    im = im.resize((THUMB_W, round(h * THUMB_W / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    rows = list(csv.DictReader(CSV_PATH.open()))
    columns = list(rows[0].keys())

    thumbs = {}
    for r in rows:
        p = PHOTOS / r["photo"]
        if p.exists():
            thumbs[r["id"]] = thumb(p)

    html = TEMPLATE.read_text()
    html = html.replace("/*__ITEMS__*/[]", json.dumps(rows, ensure_ascii=False))
    html = html.replace("/*__THUMBS__*/{}", json.dumps(thumbs))
    html = html.replace("/*__COLUMNS__*/[]", json.dumps(columns))
    OUT.write_text(html)

    done = sum(1 for r in rows if r["status"] != "needs-id")
    print(f"catalog.html  {OUT.stat().st_size/1e6:.1f} MB")
    print(f"{len(rows)} items, {len(thumbs)} thumbnails, {done} identified")


if __name__ == "__main__":
    main()
