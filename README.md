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
sync_down.py             pulls edits made on the site back into inventory.csv
worker/archive-sync.js   optional Cloudflare Worker, so the site can save edits
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
identical bytes and git stays quiet. `vault.json` carries the salt; it is
committed, holds nothing secret, and catches a mistyped passphrase before it
republishes the site under a new one.

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

## Saving edits from the website

By default the site is read-only: edits live in the browser tab and leave only
through **Save CSV**. GitHub Pages is a static file host, so there is nothing to
save back to.

`worker/archive-sync.js` is a small Cloudflare Worker that fixes that. It holds
one blob of records, and the site pulls the latest on unlock and pushes edits
when you press **Save to archive**. The records are sealed in the browser under
the same passphrase, so the Worker, its KV store and Cloudflare hold nothing but
ciphertext.

Writes are compare-and-set: a tab that has not seen someone else's save is
refused with a 409 rather than quietly overwriting them.

### Setting it up

1. In the Cloudflare dashboard, create a **KV namespace** (any name).
2. Create a **Worker**, paste in `worker/archive-sync.js`, and deploy.
3. Bind the KV namespace to the Worker as `ARCHIVE`.
4. Add two variables: `TOKEN`, a long random string, as a **secret**; and
   `ORIGIN`, set to `https://coin.lucaswalker.net`.
5. Locally, write `worker.json` — it is gitignored, and the token is baked into
   the encrypted site rather than published:

```json
{
  "url": "https://your-worker.workers.dev",
  "token": "the same long random string"
}
```

6. Run `./publish.sh`.

Without `worker.json` the build simply omits all of this and the site stays
read-only, so nothing breaks if you never set it up or take it away later.

### The loop once it is running

Edit on the site from anywhere, press **Save to archive**, and any other device
with the passphrase sees it on next unlock. `inventory.csv` is still the archive
of record, so bring those edits home before republishing:

```bash
python3 sync_down.py      # pull the site's records into inventory.csv
./publish.sh
```

`publish.sh` checks this for you and refuses to publish over edits made on the
site, naming the command to pull them down. `SKIP_SYNC_CHECK=1` overrides it if
you really do mean to discard them.

### What the token means

Anyone who can unlock the site can also read the write token out of the
decrypted page, so everyone you share the passphrase with can save. That is the
intent for a family archive, but it is worth being clear that the passphrase now
grants writing as well as reading. The blast radius is one blob of records: the
token cannot touch the repository, the photographs, or anything else.

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
