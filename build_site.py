#!/usr/bin/env python3
"""
build_site.py — packs the archive into docs/ as an encrypted, passphrase-gated
site that GitHub Pages can serve as-is.

Nothing readable is published. catalog.html and every full-resolution plate are
encrypted with AES-256-GCM under a key derived from the passphrase, and the only
plaintext file on the site is docs/index.html — the unlock page, which carries
the salt and the iteration count but no secret. A visitor without the passphrase
can download every byte of the site and still has nothing.

    ARCHIVE_PASSPHRASE='…' python3 build_site.py     # or it will prompt

The passphrase is the whole security boundary: it is never stored, and it cannot
be recovered or reset without rebuilding. Use a long one.

Re-run this after build_catalog.py, then commit docs/.
"""

import hashlib
import hmac
import json
import os
import sys
from getpass import getpass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).parent
ARCHIVE = HERE / "coin-archive" / "coin-archive"
CATALOG = ARCHIVE / "catalog.html"
PHOTOS = ARCHIVE / "photos"
GATE = HERE / "gate.html"
STATE = HERE / "vault.json"
DOCS = HERE / "docs"

ITERATIONS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
CHECK_LABEL = b"coin-archive/vault-check"
PLATE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".heic"}


# ---------- keys ----------

def derive(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, ITERATIONS, 32)


def checksum(key: bytes) -> str:
    """Lets a rebuild notice a mistyped passphrase before it republishes."""
    return hmac.new(key, CHECK_LABEL, hashlib.sha256).hexdigest()


def nonce_for(key: bytes, name: str, plaintext: bytes) -> bytes:
    """
    A nonce fixed by the content, so rebuilding unchanged files reproduces the
    same bytes and git stays quiet. Distinct plaintexts still get distinct
    nonces, which is what GCM actually requires.
    """
    tag = hashlib.sha256(plaintext).digest()
    return hmac.new(key, name.encode() + b"\0" + tag, hashlib.sha256).digest()[:NONCE_BYTES]


def seal(key: bytes, name: str, plaintext: bytes) -> bytes:
    nonce = nonce_for(key, name, plaintext)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


# ---------- catalogue ----------

# The catalogue loads plates straight from photos/. On the published site those
# files are ciphertext, so the drawer is rewired to show the embedded thumbnail
# at once and let the unlock page decrypt the plate over the top of it. The
# local copy in coin-archive/ is left exactly as it is.
PATCHES = [
    (
        '  const full = "photos/"+(it.photo||"");\n',
        "",
    ),
    (
        '    `<img class="plate" src="${full}" alt="${it.id}"\n'
        '      onerror="this.onerror=null;this.src=\'${THUMBS[it.id]||""}\'">\n',
        '    `<img class="plate" src="${THUMBS[it.id]||""}"'
        ' data-plate="${esc(it.photo||"")}" alt="${it.id}">\n',
    ),
    (
        '  $("#dBody").scrollTop = 0;\n',
        '  $("#dBody").scrollTop = 0;\n'
        '  window.VAULT && VAULT.plate($("#dBody").querySelector(".plate"));\n',
    ),
]


def patch_catalog(html: str) -> str:
    for old, new in PATCHES:
        found = html.count(old)
        if found != 1:
            sys.exit(
                f"build_site.py: expected exactly one match for a catalogue patch, "
                f"found {found}. catalog.html has changed shape — update PATCHES.\n"
                f"  looking for: {old.strip()[:70]}…"
            )
        html = html.replace(old, new)
    return html


# ---------- output ----------

def write(path: Path, data: bytes) -> bool:
    """Writes only on change, so untouched files keep their place in git."""
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def load_state(passphrase: str) -> bytes:
    """Reuses the stored salt so an unchanged file re-encrypts to identical bytes."""
    changing = "--change-passphrase" in sys.argv

    if STATE.exists() and not changing:
        state = json.loads(STATE.read_text())
        salt = bytes.fromhex(state["salt"])
        key = derive(passphrase, salt)
        if not hmac.compare_digest(checksum(key), state["check"]):
            sys.exit(
                "build_site.py: that is not the passphrase the site was last built with.\n"
                "Re-run with --change-passphrase to re-encrypt everything under a new one."
            )
        return key

    salt = os.urandom(SALT_BYTES)
    key = derive(passphrase, salt)
    STATE.write_text(json.dumps(
        {"salt": salt.hex(), "iterations": ITERATIONS, "check": checksum(key)}, indent=2) + "\n")
    print("passphrase set" if changing else "new vault created")
    return key


def read_passphrase() -> str:
    passphrase = os.environ.get("ARCHIVE_PASSPHRASE")
    if passphrase:
        return passphrase
    if not sys.stdin.isatty():
        sys.exit("build_site.py: set ARCHIVE_PASSPHRASE, or run this from a terminal.")
    passphrase = getpass("Passphrase: ")
    if not passphrase:
        sys.exit("build_site.py: empty passphrase.")
    if not STATE.exists() or "--change-passphrase" in sys.argv:
        if passphrase != getpass("Again: "):
            sys.exit("build_site.py: the two passphrases differ.")
    return passphrase


def main():
    for required in (CATALOG, GATE):
        if not required.exists():
            sys.exit(f"build_site.py: {required} is missing.")

    key = load_state(read_passphrase())
    salt = json.loads(STATE.read_text())["salt"]

    # The catalogue, patched and sealed.
    app = patch_catalog(CATALOG.read_text()).encode()
    changed = write(DOCS / "app.bin", seal(key, "app.bin", app))

    # The plates, one file each, fetched and decrypted only when a record is opened.
    photo_dir = DOCS / "p"
    photos = sorted(p for p in PHOTOS.glob("C-*") if p.suffix.lower() in PLATE_TYPES)
    published = set()
    for photo in photos:
        name = photo.name + ".bin"
        published.add(name)
        changed += write(photo_dir / name, seal(key, name, photo.read_bytes()))

    # Drop plates that have left the archive.
    stale = 0
    if photo_dir.exists():
        for old in photo_dir.iterdir():
            if old.name not in published:
                old.unlink()
                stale += 1

    # The unlock page: the one file on the site that is not ciphertext.
    gate = GATE.read_text()
    gate = gate.replace('/*__SALT__*/""', json.dumps(salt))
    gate = gate.replace("/*__ITERATIONS__*/0", str(ITERATIONS))
    if "__SALT__" in gate or "__ITERATIONS__" in gate:
        sys.exit("build_site.py: gate.html placeholders did not substitute.")
    changed += write(DOCS / "index.html", gate.encode())

    # Publish the tree verbatim — no Jekyll pass.
    changed += write(DOCS / ".nojekyll", b"")

    total = sum(f.stat().st_size for f in DOCS.rglob("*") if f.is_file())
    print(f"docs/  {len(photos)} plates + catalogue, {total/1e6:.1f} MB")
    print(f"{changed} file(s) written, {stale} removed")
    print(f"AES-256-GCM, PBKDF2-SHA256 x {ITERATIONS:,}")


if __name__ == "__main__":
    main()
