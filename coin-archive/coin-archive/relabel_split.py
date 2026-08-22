#!/usr/bin/env python3
"""
relabel_split.py — rewrite the opening of a split record's note.

When multi-coin photographs were cut into one record each, every new record
inherited the note written for the whole group: "Four Indian Head cents: 1895,
1893, 1903, 1893" now sits on four separate coins, describing none of them. The
rest of that note is still true and worth keeping — which bag the coin came
from, how the boundary was decided, which camera file it was cut out of.

So this splits each note at the first provenance sentence, replaces only the
part before it, and leaves the rest alone.

    edits-heads.csv     id, head, and any inventory columns to set
    edits.csv           written out, ready for apply_edits.py

    python3 relabel_split.py && python3 apply_edits.py

Both CSVs are gitignored: they name coins, so they belong with the collection.
"""

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
INVENTORY = HERE / "inventory.csv"
HEADS = HERE / "edits-heads.csv"
EDITS = HERE / "edits.csv"

# Where the group description ends and what is still true of the single coin
# begins. Every split note reaches one of these.
PROVENANCE = re.compile(
    r"(Loose copper cents, bracketed"
    r"|Tubes and loose silver running"
    r"|Bag \d+ —"
    r"|Boundary note:"
    r"|Silver weight derived"
    r"|Coin \d+ of)"
)


def tail_of(note: str) -> str:
    """Everything from the first provenance sentence onward."""
    found = PROVENANCE.search(note)
    if not found:
        return ""
    return note[found.start():].strip()


def main():
    if not HEADS.exists():
        sys.exit(f"relabel_split.py: {HEADS.name} is missing.")

    notes = {r["id"]: r["notes"] for r in csv.DictReader(
        INVENTORY.open(newline="", encoding="utf-8"))}

    heads = list(csv.DictReader(HEADS.open(newline="", encoding="utf-8")))
    if not heads:
        sys.exit("relabel_split.py: nothing to do.")

    columns = [c for c in heads[0] if c != "head"]
    if "notes" not in columns:
        columns.append("notes")

    unknown = [r["id"] for r in heads if r["id"] not in notes]
    if unknown:
        sys.exit("relabel_split.py: not in the inventory — " + ", ".join(unknown))

    orphaned = 0
    with EDITS.open("w", newline="", encoding="utf-8") as fh:
        out = csv.DictWriter(fh, fieldnames=columns)
        out.writeheader()
        for row in heads:
            head = (row.pop("head", "") or "").strip()
            if head:
                tail = tail_of(notes[row["id"]])
                if not tail:
                    orphaned += 1
                row["notes"] = (head + " " + tail).strip()
            out.writerow(row)

    print(f"{EDITS.name}: {len(heads)} record(s), columns {', '.join(columns)}")
    if orphaned:
        print(f"  {orphaned} had no provenance sentence to keep — note replaced whole")
    print("now: python3 apply_edits.py")


if __name__ == "__main__":
    main()
