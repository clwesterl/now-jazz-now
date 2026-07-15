# CLAUDE.md — Now Jazz Now

Personal record checklist. 109 free-jazz / improvised-music LPs (roughly 1945–1980).
Tick what you own; each record shows Discogs metadata (cover, year, label, catalog
number, format, country). Deployed as a GitHub Pages site — just Chad, no sharing.

Repo: `clwesterl/now-jazz-now` · Live: `https://clwesterl.github.io/now-jazz-now/`

## Architecture (read this before changing anything)

Metadata is fetched **at build time, locally**, never in the browser. Two hard
reasons — don't undo them:

1. **Token secrecy.** GitHub Pages is public HTML. A Discogs token in the page is
   world-readable in view-source. It must stay on Chad's machine.
2. **CORS.** The Discogs API's browser CORS is broken for `/releases/{id}` (the
   calls needed for label/catno/format), plus intermittent Cloudflare 429s.
   Server-side/local calls avoid all of it.

So: `fetch_discogs.py` (local, token from env) → writes `data.json` (committed) →
`index.html` (static) loads it. Owned marks live in `localStorage`.

This mirrors the Zwift climbs tracker pattern (`update_climbs.py` sync + single-file
HTML reading committed JSON). Keep that shape.

## Files

| File | Role | Committed? |
|---|---|---|
| `index.html` | The app. Static, no secrets. Loads `data.json`. | yes |
| `data.json` | Record list + cached Discogs metadata. Build artifact. | yes |
| `fetch_discogs.py` | Local sync script. Fills metadata from Discogs. | yes |
| `overrides.json` | Per-record fixes for bad matches / source typos. | yes |
| `README.md` | Human setup notes. | yes |
| `.gitignore` | Ignores `.DS_Store`, `.env`, `token.txt`, `__pycache__`. | yes |

The **source of truth** for the tracklist is `data.json` itself (each entry is
`{id, artist, album, meta}`). `id` is stable and 1-based; the app pads it to 3
digits for display. Never renumber ids — `overrides.json` and any exported owned
marks key off them.

## Common tasks

Fetch / refresh metadata (needs a token in the environment):
```bash
export DISCOGS_TOKEN=xxxx          # never commit; .gitignore covers .env/token.txt
python3 fetch_discogs.py           # fill records lacking meta (~4 min, throttled)
python3 fetch_discogs.py --force   # re-fetch everything
python3 fetch_discogs.py --id 63   # one record
python3 fetch_discogs.py --list-missing
```

Fix a wrong match — edit `overrides.json`, keyed by id as a string, then re-run
(`--id N` or `--force`):
```json
"13": {"release_id": 1234567},                          // pin exact release
"11": {"artist": "Jimmy Giuffre", "title": "Free Fall"} // correct search terms
```
Release id = the number in a discogs.com release URL. `fetch_discogs.py` picks the
oldest-year search hit by default (usually the original pressing), so pin an id
whenever you want a specific pressing.

Add a record — append `{"id": <next>, "artist": "...", "album": "...", "meta": null}`
to `data.json`, then `python3 fetch_discogs.py --id <next>`.

Local preview (`file://` blocks `fetch()`):
```bash
python3 -m http.server 8000        # http://localhost:8000
```

Deploy — commit `data.json` and push; Pages serves from `main`/root.

## Rate limits & etiquette

Discogs authenticated limit is ~60 req/min. The script throttles to ~1.1s/call and
backs off 60s on a 429. Each record costs up to 2 calls (search + release fetch), so
a full `--force` is ~200 calls / ~4 min. Don't parallelize it. The `User-Agent`
string is required by Discogs — keep it set.

## Conventions

- Single-file app, no build step, no framework, no bundler. Keep it that way.
- No secrets in any committed file, ever. Token only via env var.
- Vanilla JS + `localStorage`; memory fallback is already wired for sandboxed
  previews that block storage.
- Design: warm paper (`--paper`), oxblood accent (`--stamp`), Archivo Black display
  over IBM Plex Mono. The "OWNED" rubber-stamp on ticked rows is the signature
  element — don't dilute it.

## Known rough edges

Discogs coverage on this list is deep but not total. Expect to hand-fix via
`overrides.json`: Japanese-language titles (Takayanagi/Abe, Togashi), and the truly
obscure private/rare pressings (Bengt Nordström, Abdul Hannan, Cairo Free Jazz
Ensemble, Percussive Unity). Source doc had typos already seeded as overrides
(`Giufffre`, the `Le Sun-Ra`/`Saturn` entry).

## Ideas parked for later

- Cross-device sync of owned marks via the GitHub Contents API + a fine-grained PAT
  (the Two Spins pattern), if `localStorage` + Export/Import stops being enough.
- Sort/group by year or label once metadata is populated.
- Pull Chad's actual Discogs *collection* to auto-tick owned records instead of
  manual marking (`/users/{user}/collection` endpoint, same local-fetch approach).
