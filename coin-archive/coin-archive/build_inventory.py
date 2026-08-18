#!/usr/bin/env python3
"""
build_inventory.py — assigns stable catalog IDs to every photograph,
copies the photos under their new names, and writes inventory.csv.

Run once. After that, inventory.csv is the source of truth and this
script should not be re-run (it would clobber hand-entered data).
Use --check to verify photos and CSV rows still line up.
"""

import csv
import os
import shutil
import sys
from pathlib import Path

SRC = Path("/mnt/project")
OUT = Path(__file__).parent
PHOTOS = OUT / "photos"
CSV_PATH = OUT / "inventory.csv"

# The schema. Order matters — this is the column order in the CSV.
COLUMNS = [
    "id",            # C-001 .. C-218. Stable forever. Never reused, never renumbered.
    "status",        # needs-id | identified | verified
    "category",      # Bulk Silver, Dollars, Half Dollars, Quarters, Dimes,
                     # Small Denominations, World Coins, Paper Currency,
                     # Bullion & Gold, Tokens & Novelty
    "qty",           # 1 for a single coin; N for a bag or a stack
    "country",
    "denomination",
    "year",
    "mint_mark",     # P D S O CC (blank = Philadelphia / none struck)
    "variety",       # "With Rays", "VDB", "Type 2", die variety, etc.
    "composition",   # 90% Ag | 40% Ag | .500 Ag | .900 Au | Cu | CuNi | ...
    "weight_g",
    "asw_ozt",       # actual silver weight, troy ounces
    "agw_ozt",       # actual gold weight, troy ounces
    "grade_noted",   # grade as written on the holder, in his hand
    "price_noted",   # price as written on the holder, in his hand
    "acquired",      # the red-ink date
    "bag",           # bag number where the item came out of a numbered bag
    "storage",       # flip | bag | envelope | sleeve | album | slab
    "key_date",      # Y when it's a recognised scarce date
    "authenticate",  # Y when it needs in-person verification before any sale
    "notes",
    "photo",         # current filename(s), semicolon-separated
    "orig_photo",    # original camera filename(s), semicolon-separated
]

BLANK = {c: "" for c in COLUMNS}


def natural_key(p: Path):
    """Sort by the numeric part of the camera filename, not lexically."""
    digits = "".join(ch for ch in p.stem if ch.isdigit())
    return int(digits) if digits else 0


def main():
    check_only = "--check" in sys.argv

    src_files = sorted(
        [p for p in SRC.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".webp", ".png")],
        key=natural_key,
    )
    if not src_files:
        sys.exit(f"No photographs found in {SRC}")

    width = max(3, len(str(len(src_files))))

    if check_only:
        rows = list(csv.DictReader(CSV_PATH.open()))
        print(f"{len(rows)} rows in inventory.csv, {len(src_files)} photos in source")
        missing = [r["id"] for r in rows if not (PHOTOS / r["photo"].split(";")[0]).exists()]
        print("missing photo files:", missing or "none")
        return

    PHOTOS.mkdir(exist_ok=True)
    rows = []

    for i, src in enumerate(src_files, start=1):
        cid = f"C-{i:0{width}d}"
        new_name = f"{cid}{src.suffix.lower()}"
        shutil.copy2(src, PHOTOS / new_name)

        row = dict(BLANK)
        row.update(
            id=cid,
            status="needs-id",
            qty="1",
            storage="flip",
            photo=new_name,
            orig_photo=src.name,
        )
        rows.append(row)

    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} items: {rows[0]['id']} through {rows[-1]['id']}")
    print(f"photos  -> {PHOTOS}")
    print(f"csv     -> {CSV_PATH}")


if __name__ == "__main__":
    main()
