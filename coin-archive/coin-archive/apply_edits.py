#!/usr/bin/env python3
"""
apply_edits.py — apply reviewed per-record corrections to inventory.csv.

Reads edits.csv: id, then any inventory columns to set. Blank cells are left
alone, so a row can correct one field without disturbing the rest. Every change
is printed, and a value is only overwritten when it actually differs.

A blank cell means "leave this alone", which leaves no way to say "empty this".
A lone "-" does that: it clears the field. Needed when a record turns out to
hold less than was thought — a dollar that is really a clad half carrying no
silver at all has to lose its asw_ozt, not keep a stale one.

Used to resolve records inherited from group photographs, where a single coin
was left carrying "Mixed" for its denomination or composition.
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).parent
INV = HERE / "inventory.csv"
EDITS = HERE / Path(sys.argv[1] if len(sys.argv) > 1 else "edits.csv")

CLEAR = "-"   # in a cell, means empty the field rather than leave it alone


def main():
    rows = list(csv.DictReader(INV.open()))
    cols = list(rows[0].keys())
    by_id = {r["id"]: r for r in rows}

    edits = list(csv.DictReader(EDITS.open()))
    changed = touched = 0
    for e in edits:
        row = by_id.get(e["id"])
        if row is None:
            sys.exit(f"apply_edits.py: no record {e['id']}")
        hit = False
        for col, val in e.items():
            if col == "id" or not val.strip():
                continue
            if col not in cols:
                sys.exit(f"apply_edits.py: {col!r} is not a column")
            if val.strip() == CLEAR:
                val = ""
            if row[col] != val:
                print(f"  {e['id']} {col:12} {row[col]!r} -> {val!r}")
                row[col] = val
                changed += 1
                hit = True
        touched += hit

    with INV.open("w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{changed} field(s) changed across {touched} record(s)")


if __name__ == "__main__":
    main()
