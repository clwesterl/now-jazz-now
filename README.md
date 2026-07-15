# Now Jazz Now — record checklist

A personal checklist of 109 records. Tick what you own; each record shows Discogs
artwork, year, label, catalog number, format and country.

## How it's built

- **`index.html`** — the app. Static, no secrets. Loads `data.json`, keeps your
  owned marks in the browser's `localStorage`.
- **`data.json`** — the record list plus cached Discogs metadata. Committed, so
  GitHub Pages serves it with no API calls and no token in the browser.
- **`fetch_discogs.py`** — local sync script. Reads `data.json`, fills in metadata
  from Discogs using your token, writes `data.json` back.
- **`overrides.json`** — per-record fixes for bad matches / source typos.

Metadata is fetched **at build time on your machine**, never in the browser. That
keeps your Discogs token off the public page and sidesteps the API's browser CORS
limits.

## First run

```bash
export DISCOGS_TOKEN=your_token_here     # stays in your shell; never committed
python3 fetch_discogs.py                 # fills in all 109 records (~4 min, throttled)
```

Watch the log for `no match` or obviously wrong years — those are the ones to fix.

## Fixing a wrong match

Edit `overrides.json`, keyed by record id (the 3-digit number in the app):

```json
"13": {"release_id": 1234567},                    // pin an exact Discogs release
"11": {"artist": "Jimmy Giuffre", "title": "Free Fall"}   // correct the search
```

To find a release id, open the record on discogs.com — it's the number in the URL.
Then:

```bash
python3 fetch_discogs.py --id 13    # re-fetch one record
python3 fetch_discogs.py --force    # re-fetch everything
python3 fetch_discogs.py --list-missing
```

## Deploy to GitHub Pages

```bash
git add index.html data.json fetch_discogs.py overrides.json .gitignore README.md
git commit -m "Now Jazz Now checklist"
git push
```

Then on GitHub: **Settings → Pages → Source: Deploy from a branch → `main` / `root`**.
Live at `https://clwesterl.github.io/now-jazz-now/` within a minute or two.

Your owned marks are stored per-browser. Use **Export** in the app to back them up
or carry them to another device (paste into **Import**).

## Local preview

`file://` blocks `fetch()`, so use a server:

```bash
python3 -m http.server 8000    # then open http://localhost:8000
```
