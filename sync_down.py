#!/usr/bin/env python3
"""
sync_down.py — pulls edits made on the website back into inventory.csv.

The site saves records to the Worker, so once anyone edits from a phone the
local CSV is behind. This brings it forward again, keeping inventory.csv the
archive of record rather than letting a Cloudflare key-value store become it.

    python3 sync_down.py            # write the site's records into inventory.csv
    python3 sync_down.py --check    # say whether they differ; change nothing

Needs worker.json (the Worker's address and token) and the passphrase, since the
records come back encrypted.
"""

import csv
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
from getpass import getpass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).parent
CSV_PATH = HERE / "coin-archive" / "coin-archive" / "inventory.csv"
STATE = HERE / "vault.json"
SYNC = HERE / "worker.json"


def fetch(cfg: dict) -> dict | None:
    req = urllib.request.Request(
        cfg["url"].rstrip("/") + "/records",
        headers={"Authorization": "Bearer " + cfg["token"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 401:
            sys.exit("sync_down.py: the Worker rejected the token in worker.json.")
        sys.exit(f"sync_down.py: the Worker returned {e.code}.")
    except urllib.error.URLError as e:
        sys.exit(f"sync_down.py: could not reach the Worker ({e.reason}).")


def open_records(stored: dict, passphrase: str) -> list[dict]:
    import base64
    state = json.loads(STATE.read_text())
    key = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode(), bytes.fromhex(state["salt"]),
        state["iterations"], 32)
    blob = base64.b64decode(stored["blob"])
    try:
        plain = AESGCM(key).decrypt(blob[:12], blob[12:], None)
    except Exception:
        sys.exit("sync_down.py: that passphrase does not open the saved records.")
    return json.loads(plain)


def as_csv(rows: list[dict], columns: list[str]) -> str:
    """Keeps inventory.csv's own CRLF line endings. Compared and written as bytes
    because text mode normalises CRLF, which would make the file differ from what
    we generate on every single run and never converge."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, columns, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in columns})
    return buf.getvalue()


def main():
    check_only = "--check" in sys.argv

    if not SYNC.exists():
        if check_only:
            return 0
        sys.exit("sync_down.py: worker.json is missing — nothing to pull from.")
    if not CSV_PATH.exists():
        sys.exit(f"sync_down.py: {CSV_PATH} is missing.")

    cfg = json.loads(SYNC.read_text())
    stored = fetch(cfg)
    if stored is None:
        print("nothing saved on the site yet")
        return 0

    passphrase = os.environ.get("ARCHIVE_PASSPHRASE") or (
        getpass("Passphrase: ") if sys.stdin.isatty()
        else sys.exit("sync_down.py: set ARCHIVE_PASSPHRASE, or run this from a terminal."))

    rows = open_records(stored, passphrase)
    columns = list(csv.DictReader(CSV_PATH.open()).fieldnames or [])
    text = as_csv(rows, columns)

    if text.encode() == CSV_PATH.read_bytes():
        print(f"inventory.csv already matches the site (version {stored['version']})")
        return 0

    if check_only:
        print(f"the site has edits not in inventory.csv (version {stored['version']}, "
              f"saved {stored['updated']})")
        return 1

    CSV_PATH.write_bytes(text.encode())
    print(f"inventory.csv updated from the site — {len(rows)} records, "
          f"version {stored['version']}, saved {stored['updated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
