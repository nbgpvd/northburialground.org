#!/usr/bin/env python3
"""nara_cmsr.py -- find, index and fetch compiled military service records (CMSRs) in the
National Archives Catalog, one man at a time.

The Catalog holds a File Unit per soldier ("Howland, Zebedee - Age 35, Year: 1863 - 11th US
Colored Heavy Artillery", NAID 38587072) in the series "Carded Records Showing Military Service
of Soldiers Who Fought in Volunteer Organizations During the American Civil War" (RG 94), with
the page images attached. This script uses the Catalog API v2 (free read-only key from
Catalog_API@nara.gov). It is meant to run in Terminal on Bernard's Mac, where the internet is open.

  find  "Howland, Zebedee" [--unit "11th US Colored Heavy Artillery"] [--raw out.json]
        Search by exact name; print each hit with NAID, image count and URL.
  audit --register register.csv [--rows B,C | --grids G3,E9] [--status identified,draft] [--limit 60]
        For each named stone, search by exact name and record the best hits in refs/cmsr-index.csv.
        Skips men already in the index (--refresh to redo). One query per man, a pause between.
  fetch NAID --grid G3 [--out DIR] [--max 80] [--dry-run]
        Download the page images of ONE file into DIR (default ./cmsr/<GRID>/), named
        G3-cmsr-01.jpg ..., plus a captions stub (citation lines to complete by hand).

The key is read from the NARA_API_KEY environment variable, or the first line of
~/.config/nbg/nara_key. It is never printed and must never go into the repository.
A per-month query counter (~/.config/nbg/nara_usage.json) stops the script well short of
NARA's limit of 10,000 queries per key per month.

NARA's terms prohibit scraping or downloading the whole Catalog and ask for attribution; this
script is deliberately one-man-at-a-time. Read the terms at
https://www.archives.gov/research/catalog/help/api before relying on it, and check whether copies
of images may be stored.

NOT YET TESTED AGAINST THE LIVE API: the JSON is read defensively (any object with a naId), and
`find --raw` saves the exact response so the parser can be corrected on the first real run.
Standard library only; works on the Python 3 that ships with macOS.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("NARA_API_BASE", "https://catalog.archives.gov/api/v2/records/search")  # override: tests only
CONF = Path.home() / ".config" / "nbg"
KEYFILE = CONF / "nara_key"
USAGE = CONF / "nara_usage.json"
MONTHLY_CAP = 9000          # NARA's limit is 10,000 per key per month
PAUSE = 1.0                 # seconds between API calls
SERIES = ("Carded Records Showing Military Service of Soldiers Who Fought in Volunteer "
          "Organizations During the American Civil War")
INDEX_FIELDS = ["grid", "name_full", "query", "naid", "title", "images", "unit_match", "url", "checked"]


def get_key():
    k = os.environ.get("NARA_API_KEY", "").strip()
    if not k and KEYFILE.exists():
        k = KEYFILE.read_text().splitlines()[0].strip()
    if not k:
        sys.exit("No API key. Set NARA_API_KEY, or put the key on the first line of ~/.config/nbg/nara_key "
                 "(then: chmod 600 ~/.config/nbg/nara_key).")
    return k


def count_query():
    CONF.mkdir(parents=True, exist_ok=True)
    month = dt.date.today().strftime("%Y-%m")
    data = {}
    if USAGE.exists():
        try:
            data = json.loads(USAGE.read_text())
        except ValueError:
            data = {}
    n = data.get(month, 0)
    if n >= MONTHLY_CAP:
        sys.exit(f"Stopping: {n} queries counted this month (cap {MONTHLY_CAP}, NARA's limit is 10,000).")
    USAGE.write_text(json.dumps({month: n + 1}))


def api_get(params, key):
    count_query()
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-api-key": key, "Accept": "application/json",
                                               "User-Agent": "nbg-prescott-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        if e.code in (401, 403):
            sys.exit(f"The API refused the key (HTTP {e.code}). Check it, or write to Catalog_API@nara.gov. {body}")
        if e.code == 429:
            sys.exit("HTTP 429: rate limit reached. Stop and try later.")
        sys.exit(f"HTTP {e.code} from the API: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach the API: {e.reason}")


def walk(o):
    """Yield every dict that looks like a Catalog record (has a naId), wherever it sits in the JSON."""
    if isinstance(o, dict):
        if "naId" in o and ("title" in o or "digitalObjects" in o):
            yield o
        for v in o.values():
            for x in walk(v):
                yield x
    elif isinstance(o, list):
        for v in o:
            for x in walk(v):
                yield x


def records(data):
    seen, out = set(), []
    for d in walk(data):
        nid = str(d.get("naId"))
        if nid in seen:
            continue
        seen.add(nid)
        out.append(d)
    return out


def digital(d):
    objs = d.get("digitalObjects") or []
    return [o for o in objs if isinstance(o, dict) and o.get("objectUrl")]


def split_name(full):
    parts = (full or "").split()
    return (parts[-1], " ".join(parts[:-1])) if parts else ("", "")


def unit_number(unit):
    u = (unit or "").lower()
    if "14th rhode island heavy artillery" in u:
        return "11"                       # the 14th R.I. Heavy Artillery (Colored) became the 11th USCHA
    m = re.match(r"\s*(\d+)", u)
    return m.group(1) if m else ""


def unit_flag(title, unit):
    num = unit_number(unit)
    if not num:
        return "unknown"
    return "yes" if re.search(rf"\b{num}(st|nd|rd|th|d)?\b", (title or "").lower()) else "no"


def search_name(key, surname, given, extra=None):
    q = f'"{surname}, {given}"' if given else f'"{surname}"'
    params = {"q": q, "availableOnline": "true", "limit": 10}
    data = api_get(params, key)
    hits = [d for d in records(data) if str(d.get("title", "")).lower().startswith(surname.lower() + ",")]
    return q, hits, data


# ---------------------------------------------------------------- commands
def cmd_find(a):
    key = get_key()
    sur, given = (a.name.split(",", 1) + [""])[:2]
    sur, given = sur.strip(), given.strip()
    q, hits, data = search_name(key, sur, given)
    if a.raw:
        Path(a.raw).write_text(json.dumps(data, indent=1))
        print(f"raw response saved to {a.raw}")
    allrecs = records(data)
    print(f"{q}: {len(allrecs)} records returned, {len(hits)} with a title beginning '{sur},'")
    for d in hits:
        flag = unit_flag(d.get("title"), a.unit) if a.unit else ""
        print(f"  NAID {d['naId']}  {d.get('title')}  images={len(digital(d))} {('unit:' + flag) if flag else ''}")
        print(f"        https://catalog.archives.gov/id/{d['naId']}")
    if not allrecs:
        print("No records parsed. Re-run with --raw out.json and send me the file so I can fix the reader.")


def cmd_audit(a):
    key = get_key()
    reg = list(csv.DictReader(open(a.register, newline="")))
    want_status = set(s.strip() for s in a.status.split(","))
    rows = set(r.strip().upper() for r in a.rows.split(",")) if a.rows else None
    grids = set(g.strip().upper() for g in a.grids.split(",")) if a.grids else None
    todo = []
    for r in reg:
        if not (r.get("name_full") or "").strip():
            continue
        if grids and r["grid"] not in grids:
            continue
        if rows and r["grid"][0] not in rows:
            continue
        if not grids and (r.get("status") or "") not in want_status:
            continue
        todo.append(r)
    out = Path(a.index)
    have = set()
    if out.exists() and not a.refresh:
        have = set(row["grid"] for row in csv.DictReader(open(out, newline="")))
    todo = [r for r in todo if r["grid"] not in have][: a.limit]
    new = not out.exists()
    out.parent.mkdir(parents=True, exist_ok=True)
    found = none = 0
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        if new:
            w.writeheader()
        for i, r in enumerate(todo):
            sur, given = split_name(r["name_full"])
            q, hits, _ = search_name(key, sur, given)
            today = dt.date.today().isoformat()
            if hits:
                found += 1
                for d in hits[:3]:
                    w.writerow({"grid": r["grid"], "name_full": r["name_full"], "query": q, "naid": d["naId"],
                                "title": d.get("title", ""), "images": len(digital(d)),
                                "unit_match": unit_flag(d.get("title"), r.get("unit", "")),
                                "url": f"https://catalog.archives.gov/id/{d['naId']}", "checked": today})
            else:
                none += 1
                w.writerow({"grid": r["grid"], "name_full": r["name_full"], "query": q, "naid": "",
                            "title": "no file found by exact-name search", "images": 0,
                            "unit_match": "", "url": "", "checked": today})
            f.flush()
            print(f"  {r['grid']:>4} {r['name_full']}: {len(hits)} hit(s)")
            if i < len(todo) - 1:
                time.sleep(PAUSE)
    print(f"{len(todo)} men searched: {found} with at least one candidate file, {none} with none -> {out}")
    print("Candidates are leads: check the unit and company on the file before using it.")


def cmd_fetch(a):
    key = get_key()
    data = api_get({"naId": a.naid}, key)
    rec = next((d for d in records(data) if str(d.get("naId")) == str(a.naid)), None)
    if rec is None:
        sys.exit(f"NAID {a.naid} not found in the response. Try: find \"Surname, Given\" --raw out.json")
    objs = digital(rec)
    if not objs:
        sys.exit("That record has no downloadable images listed.")
    if len(objs) > a.max:
        sys.exit(f"{len(objs)} images exceeds --max {a.max}. Raise --max if you really want them all.")
    grid = a.grid.upper()
    out = Path(a.out) if a.out else Path("cmsr") / grid
    print(f"{rec.get('title')}: {len(objs)} images" + (" (dry run)" if a.dry_run else f" -> {out}"))
    if a.dry_run:
        return
    out.mkdir(parents=True, exist_ok=True)
    lines, srcs = [], []
    for i, o in enumerate(objs, 1):
        ext = (os.path.splitext(str(o.get("objectFilename") or o["objectUrl"].split("?")[0]))[1] or ".jpg").lower()
        name = f"{grid}-cmsr-{i:02d}{ext}"
        dest = out / name
        if not dest.exists():
            req = urllib.request.Request(o["objectUrl"], headers={"User-Agent": "nbg-prescott-research/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                f.write(r.read())
            time.sleep(0.3)
        srcs.append((name, o.get("objectFilename", "")))
        lines.append(f"- `records/{grid}/cmsr-{i:02d}{ext}` -- Compiled military service record, {rec.get('title')}, "
                     f"NARA RG 94, {SERIES}, NAID {a.naid}, image {i} of {len(objs)}. "
                     f"Image provided by Fold3 via the National Archives Catalog. [DESCRIBE: what this card shows]")
        print(f"  {name}")
    (out / f"{grid}-captions-stub.md").write_text("\n".join(lines) + "\n")
    with open(out / f"{grid}-sources.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "nara_objectFilename", "naid", "retrieved"])
        for n, fn in srcs:
            w.writerow([n, fn, a.naid, dt.date.today().isoformat()])
    print(f"Done. Captions stub and source list are in {out}. Nothing here is hosted until it is reviewed.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("name", help='"Surname, Given"')
    f.add_argument("--unit"); f.add_argument("--raw")
    f.set_defaults(fn=cmd_find)
    u = sub.add_parser("audit")
    u.add_argument("--register", required=True)
    u.add_argument("--index", default="refs/cmsr-index.csv")
    u.add_argument("--rows"); u.add_argument("--grids")
    u.add_argument("--status", default="identified,draft,complete")
    u.add_argument("--limit", type=int, default=60)
    u.add_argument("--refresh", action="store_true")
    u.set_defaults(fn=cmd_audit)
    g = sub.add_parser("fetch")
    g.add_argument("naid"); g.add_argument("--grid", required=True)
    g.add_argument("--out"); g.add_argument("--max", type=int, default=80)
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(fn=cmd_fetch)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
