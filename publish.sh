#!/usr/bin/env bash
#
# publish.sh — rebuild the catalogue from inventory.csv, encrypt it, and deploy.
#
# The whole update loop in one command:
#
#     ./publish.sh
#
# It asks for the passphrase rather than reading it from the environment, so it
# never lands in your shell history. Pass --no-push to build without deploying.

set -euo pipefail
cd "$(dirname "$0")"

ARCHIVE=coin-archive/coin-archive
PUSH=1
[ "${1:-}" = "--no-push" ] && PUSH=0

die() { printf '\npublish.sh: %s\n' "$1" >&2; exit 1; }

# --- the archive lives on this machine only, so check it is actually here ---
[ -f "$ARCHIVE/inventory.csv" ] || die "$ARCHIVE/inventory.csv is missing.
The collection is deliberately not in this repository. Restore your backup:
  tar -xzf 1-archive-data.tgz
  tar -xzf 2-photos-part1.tgz -C $ARCHIVE/photos
  tar -xzf 3-photos-part2.tgz -C $ARCHIVE/photos"

photos=$(ls "$ARCHIVE/photos" 2>/dev/null | wc -l)
[ "$photos" -gt 0 ] || die "$ARCHIVE/photos is empty. Restore the photo tarballs."

python3 -c 'import PIL' 2>/dev/null || die "Pillow is missing.  pip install Pillow"
python3 -c 'import cryptography' 2>/dev/null || die "cryptography is missing.  pip install cryptography"

echo "archive: $(wc -l < "$ARCHIVE/inventory.csv") CSV rows, $photos photographs"

# --- 1. inventory.csv -> catalog.html ---
echo
echo "[1/3] rebuilding the catalogue"
python3 "$ARCHIVE/build_catalog.py"

# --- 2. catalog.html + photos -> docs/ (encrypted) ---
echo
echo "[2/3] encrypting"
python3 build_site.py

# --- 3. publish ---
echo
echo "[3/3] publishing"
git add docs vault.json
if git diff --cached --quiet; then
  echo "nothing changed — the published site is already up to date"
  exit 0
fi

git diff --cached --stat | tail -1

if [ "$PUSH" = "0" ]; then
  echo "staged but not pushed (--no-push). Commit and push when ready."
  exit 0
fi

git commit -q -m "Update the published catalogue"
git push -q origin HEAD
echo
echo "pushed. GitHub Actions is deploying now — the site updates in a minute or two:"
echo "  https://coin.lucaswalker.net/"
