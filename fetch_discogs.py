#!/usr/bin/env python3
"""
fetch_discogs.py — populate data.json with Discogs metadata for the NJN checklist.

Runs locally, never on GitHub Pages. Your token stays on your machine.

Usage:
    export DISCOGS_TOKEN=xxxxxxxx        # never commit this
    python3 fetch_discogs.py             # fill in records that have no meta yet
    python3 fetch_discogs.py --force     # re-fetch everything
    python3 fetch_discogs.py --id 63     # (re-)fetch a single record by id
    python3 fetch_discogs.py --list-missing   # show records still lacking meta

Fixing bad matches:
    Edit overrides.json. Two forms, keyed by record id (as a string):
      "13": {"release_id": 1234567}          # pin an exact Discogs release
      "11": {"artist": "Jimmy Giuffre",      # correct the search terms
             "title": "Free Fall"}
    Then re-run with --force (or --id 11) to apply.

Discogs auth + limits: https://www.discogs.com/developers
Authenticated rate limit is ~60 requests/min; this script throttles itself.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.discogs.com"
UA = "NowJazzNow/1.0 +https://github.com/clwesterl/now-jazz-now"
DATA = "data.json"
OVERRIDES = "overrides.json"

# ~1.1s between calls keeps us comfortably under 60/min even with retries.
MIN_INTERVAL = 1.1
_last_call = [0.0]


def token():
    t = os.environ.get("DISCOGS_TOKEN", "").strip()
    if not t:
        sys.exit("Set DISCOGS_TOKEN in your environment first "
                 "(export DISCOGS_TOKEN=xxxx). It is never written to disk.")
    return t


def api_get(path, params=None):
    """GET against the Discogs API with throttling and one 429 backoff."""
    wait = MIN_INTERVAL - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Authorization": f"Discogs token={token()}",
        "Accept": "application/vnd.discogs.v2.discogs+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            _last_call[0] = time.time()
            return json.load(r)
    except urllib.error.HTTPError as e:
        _last_call[0] = time.time()
        if e.code == 429:
            print("    rate limited, waiting 60s…")
            time.sleep(60)
            return api_get(path, params)
        print(f"    HTTP {e.code} for {url}")
        return None
    except Exception as e:
        _last_call[0] = time.time()
        print(f"    error: {e}")
        return None


def release_to_meta(rel):
    """Flatten a Discogs release object into our compact meta dict."""
    if not rel:
        return None
    labels = rel.get("labels") or []
    label = labels[0].get("name", "") if labels else ""
    catno = labels[0].get("catno", "") if labels else ""
    fmts = rel.get("formats") or []
    fparts = []
    if fmts:
        f0 = fmts[0]
        if f0.get("name"):
            fparts.append(f0["name"])
        fparts += f0.get("descriptions") or []
    images = rel.get("images") or []
    cover = ""
    if images:
        cover = images[0].get("uri") or images[0].get("resource_url") or ""
    return {
        "year": str(rel.get("year") or "") if rel.get("year") else "",
        "label": label,
        "catno": catno,
        "format": ", ".join(fparts),
        "country": rel.get("country", ""),
        "cover": cover,
        "url": rel.get("uri", "") or (
            f"https://www.discogs.com/release/{rel.get('id')}" if rel.get("id") else ""),
        "source": "Discogs",
    }


def fetch_one(rec, override):
    """Resolve one record to meta. Returns (meta, note)."""
    # 1. Pinned release id wins.
    if override and override.get("release_id"):
        rid = override["release_id"]
        rel = api_get(f"/releases/{rid}")
        return release_to_meta(rel), f"pinned release {rid}"

    artist = (override or {}).get("artist", rec["artist"])
    title = (override or {}).get("title", rec["album"])

    # 2. Search, oldest pressing first (usually the original).
    res = api_get("/database/search", {
        "artist": artist,
        "release_title": title,
        "type": "release",
        "per_page": 10,
    })
    results = (res or {}).get("results") or []
    if not results:
        # looser fallback: single q string
        res = api_get("/database/search", {
            "q": f"{artist} {title}",
            "type": "release",
            "per_page": 10,
        })
        results = (res or {}).get("results") or []
    if not results:
        return None, "no match"

    def yr(x):
        try:
            return int(x.get("year") or 9999)
        except (ValueError, TypeError):
            return 9999
    results.sort(key=yr)
    best = results[0]

    # 3. Fetch the full release for label/catno/country/hi-res cover.
    rel = api_get(f"/releases/{best['id']}")
    meta = release_to_meta(rel)
    if meta and not meta.get("cover"):
        meta["cover"] = best.get("cover_image") or best.get("thumb") or ""
    return meta, f"matched release {best['id']} ({best.get('year','?')})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-fetch even if meta exists")
    ap.add_argument("--id", type=int, help="only this record id")
    ap.add_argument("--list-missing", action="store_true")
    args = ap.parse_args()

    data = json.load(open(DATA, encoding="utf-8"))
    overrides = {}
    if os.path.exists(OVERRIDES):
        overrides = json.load(open(OVERRIDES, encoding="utf-8"))

    if args.list_missing:
        miss = [r for r in data if not r.get("meta")]
        for r in miss:
            print(f"{r['id']:>3}  {r['artist']} — {r['album']}")
        print(f"\n{len(miss)} of {len(data)} still missing metadata.")
        return

    todo = []
    for r in data:
        if args.id and r["id"] != args.id:
            continue
        if r.get("meta") and not args.force and not args.id:
            continue
        todo.append(r)

    if not todo:
        print("Nothing to fetch. Use --force to re-fetch, or --id N for one record.")
        return

    print(f"Fetching {len(todo)} record(s) from Discogs…\n")
    for r in todo:
        ov = overrides.get(str(r["id"]))
        print(f"{r['id']:>3}  {r['artist']} — {r['album']}")
        meta, note = fetch_one(r, ov)
        r["meta"] = meta
        print(f"     -> {note}"
              + (f" · {meta['year']} · {meta['label']} {meta['catno']}".rstrip()
                 if meta else ""))
        # Save after every record so a crash never loses progress.
        json.dump(data, open(DATA, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    done = sum(1 for r in data if r.get("meta"))
    print(f"\nDone. {done}/{len(data)} records have metadata. "
          f"Commit data.json and push.")


if __name__ == "__main__":
    main()
