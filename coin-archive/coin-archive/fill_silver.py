#!/usr/bin/env python3
"""
fill_silver.py — derive asw_ozt for coins whose silver content is a constant.

A 90% silver US quarter contains 0.1808 troy ounces. That is not an estimate:
it follows from the coin's mass and fineness, both of which are fixed by the
mint. Where composition and denomination are recorded, the silver weight is
arithmetic, and leaving it blank makes the coin count as nothing.

Only exact, known combinations are filled. Anything whose weight depends on the
particular object — a hand-poured bar, rounds of unstated size, a bag weighed
whole — is left alone, because guessing there would be inventing data.
"""
import csv
from pathlib import Path

TROY = 31.1035  # grams per troy ounce

# (composition, denomination, country) -> (mass in grams, fineness)
COINS = {
    ("90% Ag", "Dime", "USA"):            (2.50, 0.900),
    ("90% Ag", "Quarter", "USA"):         (6.25, 0.900),
    ("90% Ag", "Half Dollar", "USA"):     (12.50, 0.900),
    ("90% Ag", "Dollar", "USA"):          (26.73, 0.900),
    ("40% Ag", "Half Dollar", "USA"):     (11.50, 0.400),
    ("90% Ag", "Half Dime", "USA"):       (1.24, 0.900),
    (".800 Ag", "5 Cents", "Canada"):     (1.1664, 0.800),
    (".800 Ag", "10 Cents", "Canada"):    (2.3328, 0.800),
    (".800 Ag", "25 Cents", "Canada"):    (5.8319, 0.800),
    (".800 Ag", "50 Cents", "Canada"):    (11.6638, 0.800),
}

NOTE = ("Silver weight derived from the coin's standard mass and fineness, "
        "not weighed individually.")


def main():
    path = Path(__file__).parent / "inventory.csv"
    rows = list(csv.DictReader(path.open()))
    cols = list(rows[0].keys())

    filled = 0
    for r in rows:
        if r["asw_ozt"].strip():
            continue
        key = (r["composition"].strip(), r["denomination"].strip(), r["country"].strip())
        spec = COINS.get(key)
        if not spec:
            continue
        mass, fine = spec
        r["asw_ozt"] = f"{mass * fine / TROY:.4f}"
        if not r["weight_g"].strip():
            r["weight_g"] = f"{mass:g}"
        if NOTE not in r["notes"]:
            r["notes"] = (r["notes"].strip() + " " + NOTE).strip()
        filled += 1
        print(f"  {r['id']} {key[1]:12} {key[0]:8} -> {r['asw_ozt']} ozt")

    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    print(f"\nfilled {filled} records")


if __name__ == "__main__":
    main()
