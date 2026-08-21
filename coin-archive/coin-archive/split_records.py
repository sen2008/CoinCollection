#!/usr/bin/env python3
"""
split_records.py — one coin, one record.

Photographs holding several coins were catalogued as a single row with a qty.
This cuts each of those photographs into one image per coin (see the companion
detector) and rewrites the inventory so every row is a single object, then
renumbers the whole catalogue C-001 upward in photograph order.

Renumbering is only safe while no coin carries a written ID. Once flips are
labelled, IDs are permanent — see the README — and this must not be re-run.

Writes everything into rebuilt/ first so the result can be inspected before it
replaces anything. Nothing in photos/ or inventory.csv is touched.
"""

import csv
import os
import re
import shutil
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_detect"))
from find_coins import load, detect, reading_order   # noqa: E402
from PIL import Image                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(HERE, "photos")
OUT = os.path.join(HERE, "rebuilt")
OUT_PHOTOS = os.path.join(OUT, "photos")
PAD = 0.28


def coin_boxes(path, expected):
    """Circles for a photograph, or None when the result should not be trusted."""
    rgb = load(path)
    circles = reading_order(detect(rgb, expected))
    if len(circles) != expected:
        return rgb, None
    radii = [c[2] for c in circles]
    med = statistics.median(radii)
    if any(r > med * 1.5 or r < med * 0.55 for r in radii):
        return rgb, None          # something round that is not a coin
    return rgb, circles


def crop(rgb, circle):
    x, y, r = circle
    h, w = rgb.shape[:2]
    half = int(r * (1 + PAD))
    return Image.fromarray(rgb).crop((max(0, x - half), max(0, y - half),
                                      min(w, x + half), min(h, y + half)))


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "inventory.csv"))))
    columns = list(rows[0].keys())

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT_PHOTOS)

    out_rows, mapping, split_count, kept_group = [], [], 0, []

    for row in rows:
        qty = (row["qty"] or "").strip()
        src = os.path.join(PHOTOS, row["photo"])
        want = int(qty) if qty.isdigit() else 0

        circles = None
        if want >= 2 and os.path.exists(src):
            rgb, circles = coin_boxes(src, want)

        if not circles:
            # Left whole: either a single coin already, or a group the detector
            # could not separate honestly. Its qty is preserved as-is.
            new = dict(row)
            out_rows.append((new, row["photo"], None))
            if want >= 2 or want == 0:
                kept_group.append((row["id"], qty))
            continue

        split_count += 1
        for i, c in enumerate(circles, 1):
            new = dict(row)
            new["qty"] = "1"
            note = row["notes"].strip()
            provenance = (f"Coin {i} of {len(circles)} from camera file "
                          f"{row['orig_photo'] or row['photo']}, which was catalogued as one "
                          f"record before the coins were separated.")
            new["notes"] = (note + " " + provenance).strip()
            out_rows.append((new, None, (rgb, c, i, row)))

    # Renumber in photograph order, and name each image after its record.
    width = max(3, len(str(len(out_rows))))
    for n, (row, keep_photo, made) in enumerate(out_rows, 1):
        new_id = f"C-{n:0{width}d}"
        old_id = row["id"]
        row["id"] = new_id
        if keep_photo:
            ext = os.path.splitext(keep_photo)[1]
            row["photo"] = new_id + ext
            shutil.copy2(os.path.join(PHOTOS, keep_photo),
                         os.path.join(OUT_PHOTOS, row["photo"]))
            mapping.append((old_id, "", new_id, row["orig_photo"]))
        else:
            rgb, circle, i, parent = made
            row["photo"] = new_id + ".jpg"
            crop(rgb, circle).save(os.path.join(OUT_PHOTOS, row["photo"]),
                                   quality=92, optimize=True)
            mapping.append((old_id, str(i), new_id, row["orig_photo"]))

    # Notes cross-reference other records — "bracketed by the bag 6 photograph at
    # C-052" — and renumbering would silently point every one of those at the
    # wrong coin. Rewrite them against the new numbering. Where a referenced
    # photograph was split, the reference means the photograph, so it goes to the
    # first coin taken from it.
    first_new = {}
    for old_id, idx, new_id, _ in mapping:
        first_new.setdefault(old_id, new_id)

    unresolved = set()

    def renumber(match):
        ref = match.group(0)
        if ref in first_new:
            return first_new[ref]
        unresolved.add(ref)
        return ref

    pattern = re.compile(r"\bC-\d{3}\b")
    rewritten = 0
    for row, _, _ in out_rows:
        before = row["notes"]
        after = pattern.sub(renumber, before)
        if after != before:
            row["notes"] = after
            rewritten += 1

    # duplicate_of holds an id too, and it is easy to miss because it does not
    # look like prose. Left alone it keeps an old number that now belongs to an
    # unrelated coin, so the row would claim to duplicate something it has never
    # seen. Where the referenced photograph was split, the duplicate is of the
    # photograph, so it points at the first coin taken from it.
    redirected = 0
    for row, _, _ in out_rows:
        ref = row["duplicate_of"].strip()
        if ref and ref in first_new and first_new[ref] != ref:
            row["duplicate_of"] = first_new[ref]
            redirected += 1
        elif ref and ref not in first_new:
            unresolved.add(ref)
    print(f"  duplicate_of fixed: {redirected} rows")

    print(f"  notes renumbered  : {rewritten} rows")
    if unresolved:
        print(f"  WARNING unresolved references: {sorted(unresolved)}")

    with open(os.path.join(OUT, "inventory.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, columns)
        w.writeheader()
        w.writerows(r for r, _, _ in out_rows)

    with open(os.path.join(OUT, "id-map.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["old_id", "coin_index", "new_id", "orig_photo"])
        w.writerows(mapping)

    print(f"{len(rows)} records in  ->  {len(out_rows)} records out")
    print(f"  photographs split : {split_count}")
    print(f"  left as groups    : {len(kept_group)}")
    for i, q in kept_group:
        print(f"      {i} (qty {q})")
    print(f"\nwrote {OUT}/inventory.csv, {OUT}/id-map.csv and "
          f"{len(os.listdir(OUT_PHOTOS))} photographs")


if __name__ == "__main__":
    main()
