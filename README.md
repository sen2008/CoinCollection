# Coin & Currency Archive — tooling

Build scripts for a private coin catalogue, and the machinery that publishes it
to GitHub Pages behind a passphrase.

**The collection is not in this repository.** This repo is public so that GitHub
Pages can serve the site for free, which means anything committed here is
readable by anyone. So the inventory, the photographs and the catalogue itself
stay on Lucas's machine; only the encrypted output in `docs/` is committed.
`.gitignore` enforces that. Keep your own backup of the archive — GitHub is not
holding a copy.

## What's here

```
publish.sh               rebuild, encrypt and deploy in one command
build_site.py            encrypts the catalogue into docs/
gate.html                markup for the unlock page (edit here, not in docs/)
docs/                    the encrypted site, committed and served by Pages

coin-archive/coin-archive/
├── template.html        markup for the catalogue (edit here, not in catalog.html)
├── build_inventory.py   one-time: assigns IDs and renames photos
├── build_catalog.py     regenerates catalog.html from inventory.csv
└── contact_sheets.py    regenerates the contact sheets
```

Alongside those, on your machine only, sit `inventory.csv`, `catalog.html`,
`photos/`, `sheets/` and the `seed_*.py` / `assign_*.py` identification scripts.
Git ignores all of them.

## The ID scheme

Every item has an ID of the form `C-001` onward, assigned in the order the
photographs were taken — which follows the order things were physically sorted,
so neighbouring IDs are usually related.

1. **IDs are permanent.** Never renumber, never reuse. If an item leaves the
   collection, set its status and leave the row in place.
2. **The ID is not a location.** Bag number, storage type and category are
   ordinary columns, free to be corrected as you learn more. The ID never moves.
3. **New items continue the sequence.** Don't backfill gaps.

Write the ID on the flip or on a slip in the bag. That's the whole point — it's
what connects the physical object to the record and the photograph.

## The CSV

`inventory.csv` is plain UTF-8, comma-separated, 25 columns. It's the thing to
back up and the thing every other file here is generated from. It will open in
Excel, Numbers, LibreOffice, pandas, sqlite, or a text editor in forty years.

Columns worth explaining:

| column | meaning |
|---|---|
| `status` | `needs-id` → `identified` → `verified`. Verified means checked in hand, not from a photo. |
| `asw_ozt` / `agw_ozt` | Actual silver / gold weight in troy ounces. Multiply by spot for melt. |
| `grade_noted` / `price_noted` | What's written on the holder in his hand. Not a current appraisal. |
| `acquired` | The date in red ink. |
| `key_date` | `Y` for recognised scarce dates. |
| `authenticate` | `Y` when it must be checked in person before any sale. |
| `bag_basis` | How the bag assignment was made. `owner` = confirmed from memory. `label` = the bag's own contents list matches one for one. `sequence` = the items sit between two bag photographs and are the right material. `unplaced` = no bag photograph brackets them. |
| `duplicate_of` | Set when a photograph is a second view of an object already catalogued. Those rows keep their record but are excluded from counts and weights. |

The last two columns, `photo` and `orig_photo`, keep the link back to the
original camera filenames so nothing is orphaned if the photos are re-imported.

## Using the catalogue

Open `catalog.html` in any browser. No server, no install, no internet.

- **Search** runs across every field — try a year, a serial number, `star`, `bag 3`.
- **Sort** reorders the grid. Bag, category and storage insert section headings,
  each showing that group's item count and its silver, gold and bulk weight.
- **All bags** narrows to one bag, or to everything not in a bag.
- **Needs ID / Key date / Authenticate** filter to the work that's left.
- **Click any flip** to open its record and edit it.
- **← →** or **J / K** move between records, **Esc** closes.
- **Save CSV** downloads the updated `inventory.csv`. **Load CSV** reads one back in.

Edits live in the browser tab until you press **Save CSV**. Nothing writes to
disk on its own, so save before closing — the tab will warn you.

## Regenerating

After editing `inventory.csv`:

```bash
python3 coin-archive/coin-archive/build_catalog.py
```

Thumbnails are embedded in `catalog.html`, so that file works alone if you email
it. Full-resolution photographs are referenced from `photos/`, so keep the folder
together and clicking a record shows the full plate.

Don't re-run `build_inventory.py` — it rebuilds the CSV from scratch and would
overwrite everything entered since.

## Publishing it behind a passphrase

`build_site.py` encrypts the catalogue into `docs/`, and the unlock page decrypts
it in the browser once the passphrase is entered. `publish.sh` runs the whole
loop — rebuild, encrypt, commit, push:

```bash
./publish.sh
```

It prompts for the passphrase rather than reading it from the environment, so it
stays out of your shell history. `--no-push` builds without deploying.

Pushing `docs/` is what publishes. `.github/workflows/pages.yml` uploads it to
Pages and refuses to deploy if anything in `docs/` turns out to be readable.

### Updating the catalogue

1. Open the site (or `catalog.html` locally), edit records, press **Save CSV**.
2. Put that downloaded file at `coin-archive/coin-archive/inventory.csv`.
3. Run `./publish.sh`.

The site updates a minute or two later. Editing a record rewrites only
`docs/app.bin`; the 218 encrypted plates are untouched unless a photograph
changes, because each file's nonce is derived from its own content.

### First-time setup on a new machine

The collection is not in the repository, so a fresh clone needs it restored
alongside the tooling:

```bash
git clone https://github.com/sen2008/CoinCollection.git
cd CoinCollection
pip install Pillow cryptography

tar -xzf 1-archive-data.tgz
tar -xzf 2-photos-part1.tgz -C coin-archive/coin-archive/photos
tar -xzf 3-photos-part2.tgz -C coin-archive/coin-archive/photos
tar -xzf 4-contact-sheets.tgz -C coin-archive/coin-archive
```

Everything lands in paths `.gitignore` already excludes, so none of it can be
committed by accident. `publish.sh` checks the archive is present and stops with
these instructions if it isn't.

That writes three things:

| file | what it is |
|---|---|
| `docs/index.html` | the unlock page — the only readable file on the site |
| `docs/app.bin` | `catalog.html`, encrypted |
| `docs/p/C-001.jpg.bin` … | each full-resolution plate, encrypted separately |

Everything is AES-256-GCM under a key derived from the passphrase with
PBKDF2-SHA256 at 600,000 iterations. The unlock page carries the salt and the
iteration count, which are not secrets. The passphrase is never stored anywhere
and cannot be reset — a forgotten one means rebuilding the site with a new one.

Plates are fetched and decrypted one at a time, only when a record is opened, so
unlocking downloads the catalogue and nothing else. The drawer shows the embedded
thumbnail immediately and swaps in the full plate as it arrives.

Nonces are derived from file content, so rebuilding unchanged files reproduces
identical bytes and git stays quiet. `vault.json` holds the salt locally and
catches a mistyped passphrase before it republishes the site under a new one.

### What this does and does not protect

The passphrase is the entire security boundary, so make it a long one. Anyone can
download `app.bin` and grind at it offline, and the 600,000 PBKDF2 iterations are
the only thing slowing them down — a real cost per guess, but no help at all
against a passphrase worth guessing. A short or reused one is the failure mode
here, not the cryptography.

The site is also a lock, not a log: everyone shares one passphrase, there is no
record of who opened it, and revoking access means rebuilding under a new one and
telling the people who should still have it.

For comparison, the usual "password page" for a static site just checks the typed
string in JavaScript and reveals content the browser already downloaded. That
protects nothing. Here the server never holds anything readable.
