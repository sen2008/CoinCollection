#!/usr/bin/env python3
"""
sync_down.py — pulls edits made on the website back into inventory.csv.

The site saves records to the Worker, so once anyone edits from a phone the
local CSV is behind. This brings it forward again, keeping inventory.csv the
archive of record rather than letting a Cloudflare key-value store become it.

    python3 sync_down.py            # write the site's records into inventory.csv
    python3 sync_down.py --check    # say whether they differ; change nothing
    python3 sync_down.py --push     # send inventory.csv up, making local authoritative

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
# Cloudflare's browser-integrity check answers the default Python-urllib
# signature with a 403 and error code 1010, which looks exactly like the Worker
# rejecting the token. Anything that is not the stock agent string gets through.
USER_AGENT = "coin-archive-sync/1.0"
CSV_PATH = HERE / "coin-archive" / "coin-archive" / "inventory.csv"
STATE = HERE / "vault.json"
SYNC = HERE / "worker.json"


def fetch(cfg: dict) -> dict | None:
    req = urllib.request.Request(
        cfg["url"].rstrip("/") + "/records",
        headers={"Authorization": "Bearer " + cfg["read_token"],
                 "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 401:
            sys.exit("sync_down.py: the Worker rejected read_token in worker.json.")
        if e.code == 403:
            sys.exit("sync_down.py: Cloudflare refused the request (403). If the body "
                     "mentions error 1010 this is its bot check, not the Worker.")
        sys.exit(f"sync_down.py: the Worker returned {e.code}.")
    except urllib.error.URLError as e:
        sys.exit(f"sync_down.py: could not reach the Worker ({e.reason}).")


def read_key(passphrase: str) -> bytes:
    state = json.loads(STATE.read_text())
    return hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode(), bytes.fromhex(state["salt"]),
        state["iterations"], 32)


def push(cfg: dict, passphrase: str) -> int:
    """
    Sends inventory.csv up as the archive's records. Publishing from a computer
    ends with this, so the site does not keep serving an older set that would
    then override the freshly published catalogue on every unlock.
    """
    import base64
    stored = fetch(cfg)
    version = stored["version"] if stored else 0

    rows = list(csv.DictReader(CSV_PATH.open()))
    nonce = os.urandom(12)
    sealed = nonce + AESGCM(read_key(passphrase)).encrypt(
        nonce, json.dumps(rows).encode(), None)

    body = json.dumps({"version": version,
                       "blob": base64.b64encode(sealed).decode()}).encode()
    req = urllib.request.Request(
        cfg["url"].rstrip("/") + "/records", data=body, method="PUT",
        headers={"Authorization": "Bearer " + cfg["write_token"],
                 "Content-Type": "application/json",
                 "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            out = json.loads(res.read())
    except urllib.error.HTTPError as e:
        if e.code == 409:
            sys.exit("sync_down.py: the site was saved to while this was running. "
                     "Run it again.")
        if e.code == 403:
            sys.exit("sync_down.py: write_token in worker.json is not the Worker's "
                     "write token.")
        sys.exit(f"sync_down.py: the Worker returned {e.code} on push.")
    print(f"pushed {len(rows)} records to the site — version {out['version']}")
    return 0


def open_records(stored: dict, passphrase: str) -> list[dict]:
    import base64
    key = read_key(passphrase)
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


def ask(check_only: bool) -> str:
    passphrase = os.environ.get("ARCHIVE_PASSPHRASE")
    if passphrase:
        return passphrase
    if not sys.stdin.isatty():
        sys.exit("sync_down.py: set ARCHIVE_PASSPHRASE, or run this from a terminal.")
    return getpass("Passphrase: ")


def main():
    check_only = "--check" in sys.argv
    pushing = "--push" in sys.argv

    if not SYNC.exists():
        if check_only:
            return 0
        sys.exit("sync_down.py: worker.json is missing — nothing to pull from.")
    if pushing:
        if not CSV_PATH.exists():
            sys.exit(f"sync_down.py: {CSV_PATH} is missing.")
        cfg = json.loads(SYNC.read_text())
        for field in ("url", "write_token"):
            if not cfg.get(field):
                sys.exit(f"sync_down.py: worker.json is missing {field!r}.")
        return push(cfg, ask(False))
    if not CSV_PATH.exists():
        sys.exit(f"sync_down.py: {CSV_PATH} is missing.")

    cfg = json.loads(SYNC.read_text())
    stored = fetch(cfg)
    if stored is None:
        print("nothing saved on the site yet")
        return 0

    rows = open_records(stored, ask(check_only))
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
