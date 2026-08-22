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
├── contact_sheets.py    regenerates the contact sheets
├── split_records.py     one-time: cut multi-coin photographs into one record each
├── apply_edits.py       apply a reviewed sheet of per-record corrections
├── relabel_split.py     replace a split record's inherited group note
├── fill_silver.py       derive asw_ozt from standard mass and fineness
└── _detect/             coin-finding and contact sheets, used by the two above
```

Alongside those, on your machine only, sit `inventory.csv`, `catalog.html`,
`photos/`, `sheets/` and the `seed_*.py` / `assign_*.py` identification scripts.
Git ignores all of them.

## The ID scheme

Every item has an ID of the form `C-001` onward, assigned in the order the
photographs were taken — which follows the order things were physically sorted,
so neighbouring IDs are usually related.

1. **IDs are permanent.** Never renumber, never reuse. If an item leaves the
   collection, set its status and leave the row in place. The catalogue was
   renumbered once, when multi-coin photographs were split into one record each,
   and that was only safe because no coin carried a written ID yet. Once a flip
   is labelled, that door is closed — `split_records.py` must not be re-run.
2. **The ID is not a location.** Bag number, storage type and category are
   ordinary columns, free to be corrected as you learn more. The ID never moves.
3. **New items continue the sequence.** Don't backfill gaps.

Write the ID on the flip or on a slip in the bag. That's the whole point — it's
what connects the physical object to the record and the photograph.

## One coin, one record

Some photographs held several coins and were catalogued as a single row with a
`qty`. `split_records.py` cut those into one image per coin and rewrote the
inventory so every row is a single object, taking 218 records to 390.

Coins are found by circle detection and then checked: the right count, radii that
agree with each other, and a colour that could be metal. Photographs failing any
of those are left whole rather than cut wrongly. Eight remain, and they are not
fixable by better code — five are sealed bags whose coins the camera never saw
individually, one a bagged pile and one a tube on the scale. The last, C-204,
shows six cents where only five can be resolved.

`id-map.csv` records what became what, keyed to the camera filenames, and stays
out of the repository along with everything else describing the collection.

Splitting left each new record carrying the note written for the whole group —
"Four Indian Head cents: 1895, 1893, 1903, 1893" sitting on four separate coins
and describing none of them. `relabel_split.py` replaces that opening sentence
per coin while keeping the provenance that follows it, which is still true of
the single coin: which bag, how the boundary was decided, which camera file it
came from.

Reading the coins one at a time also caught what the group notes had guessed at.
Several were the wrong denomination — a Barber quarter catalogued as a dollar, a
clad Kennedy half catalogued as a Peace dollar — and three records turned out to
be one two-ounce round the detector had cut into three. Where a photograph shows
a coin the totals had wrong, the coin wins.

## The CSV

`inventory.csv` is plain UTF-8, comma-separated, 25 columns. It's the thing to
back up and the thing every other file here is generated from. It will open in
Excel, Numbers, LibreOffice, pandas, sqlite, or a text editor in forty years.

Columns worth explaining:

Correcting a sheet: `apply_edits.py` takes `edits.csv` with an `id` and any
columns to set, leaving blank cells alone so a row can fix one field without
disturbing the rest. A lone `-` empties a field instead, for when a record turns
out to hold less than was thought and a stale silver weight has to go.

| column | meaning |
|---|---|
| `status` | `needs-id` → `identified` → `verified`. Verified means checked in hand, not from a photo. |
| `asw_ozt` / `agw_ozt` | Actual silver / gold weight in troy ounces, **for one coin** — the catalogue multiplies by `qty`. Multiply by spot for melt. Putting a whole group's weight here double-counts it, a mistake that overstated the silver total by 30 ozt until it was found. `fill_silver.py` derives the value where mass and fineness are fixed by the mint, and refuses to guess for hand-poured bars, rounds of unstated size, or bags weighed whole. |
| `grade_noted` / `price_noted` | What's written on the holder in his hand. Not a current appraisal. |
| `acquired` | The date in red ink. |
| `key_date` | `Y` for recognised scarce dates. |
| `authenticate` | `Y` when it must be checked in person before any sale. |
| `bag_basis` | How the bag assignment was made. `owner` = confirmed from memory. `label` = the bag's own contents list matches one for one. `sequence` = the items sit between two bag photographs and are the right material. `unplaced` = no bag photograph brackets them. |
| `duplicate_of` | Set when a photograph is a second view of an object already catalogued. Those rows keep their record but are excluded from counts and weights. |
| `qty` | Coins in this record — 1 for everything except the eight group photographs that could not be split. `asw_ozt`, `agw_ozt` and `weight_g` are all **per coin**, and the catalogue multiplies each by `qty`. |

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
- **← →** or **J / K** move between records, **Esc** closes. On a phone,
  swipe the record left or right instead — the arrows are a small target.
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
`docs/app.bin`; the 390 encrypted plates are untouched unless a photograph
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
the everyday passphrase, so the Worker, its KV store and Cloudflare hold nothing
but ciphertext. Saving needs a second passphrase — see below.

Writes are compare-and-set: a tab that has not seen someone else's save is
refused with a 409 rather than quietly overwriting them.

### Setting it up

1. In the Cloudflare dashboard, create a **KV namespace** (any name).
2. Create a **Worker**, paste in `worker/archive-sync.js`, and deploy.
3. Bind the KV namespace to the Worker as `ARCHIVE`.
4. Add two **secrets**: `READ_TOKEN` and `WRITE_TOKEN`, each a long random
   string. `ORIGIN` is set from `wrangler.toml`, not the dashboard.
5. Locally, write `worker.json` — gitignored, and never published in the clear:

```json
{
  "url": "https://your-worker.workers.dev",
  "read_token": "the first random string",
  "write_token": "the second random string"
}
```

6. Run `./publish.sh`. It generates a **write passphrase** on first run, prints
   it once, and stores it in `worker.json`. Save it somewhere safe — it is not
   recoverable from the published site.

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

### Two passphrases

Reading and writing are separate privileges, so sharing the archive does not
hand out the ability to change it.

| | passphrase | what it opens |
|---|---|---|
| **Read** | the one you chose | the catalogue, the plates, and other people's saved edits |
| **Write** | randomly generated, 100 bits | saving edits back to the archive |

The site carries a read token, which is enough to fetch saved records. The write
token is sealed *again* under the write passphrase, so someone who decrypts the
entire page still cannot recover it — and the Worker refuses a write from the
read token with a 403 regardless.

The write passphrase is asked for the first time you press **Save to archive**
in a tab, then held in memory for that tab. Give it only to whoever should be
editing; everyone else gets the everyday passphrase and a read-only archive.

Its blast radius is one blob of records either way: neither token can touch the
repository, the photographs, or anything else.

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
