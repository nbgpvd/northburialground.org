#!/usr/bin/env python3
"""nps_cache.py -- remember every NPS Soldiers and Sailors lookup so no man is searched twice.

Two sources are read together:
  * register.csv notes -- every segment starting "NPS:" (found, "no X found", or "not searched").
    The register is the source of truth, so nothing is copied out of it.
  * a lookups file (refs/nps-lookups.csv) -- searches made for men who are not on a stone yet,
    for example candidates from a field sheet. Columns:
    surname, given, unit_query, result (found|none), detail, url, grid, checked

Commands (all take --register prescott/register.csv and --lookups refs/nps-lookups.csv):

  status                         how many NPS findings the cache holds
  lookup SURNAME [GIVEN]         what we already know about a name, if anything
  todo --candidates FILE [--out FILE]
                                 for a field-candidates CSV, list the men NOT yet searched
                                 (the list to work through in the NPS search page)
  add SURNAME GIVEN --result found|none --detail TEXT [--unit U] [--url URL] [--grid G]
                                 record a lookup you have just made

The NPS search itself is not automated: direct queries to its index are refused, so each
search is made in the public search page by a person or by Claude in the browser.
Standard library only.
"""
import argparse
import csv
import datetime as dt
import difflib
import re
import sys
from pathlib import Path

FIELDS = ["surname", "given", "unit_query", "result", "detail", "url", "grid", "checked"]


def norm(s):
    return re.sub(r"[^a-z']", "", (s or "").lower())


def load_register(path):
    """-> list of dicts: grid, name, kind (found|none|unsearched), text."""
    out = []
    if not path or not Path(path).exists():
        return out
    for r in csv.DictReader(open(path, newline="")):
        for m in re.finditer(r"NPS[^;]*", r.get("notes") or ""):
            seg = re.split(r"\.\s+(?=PV001|Chenery|City lot|Stone|Born|Died)", m.group(0))[0].strip()
            low = seg.lower()
            if re.match(r"nps: no \S", low):
                kind = "none"
            elif "not searched" in low:
                kind = "unsearched"
            else:
                kind = "found"
            out.append({"grid": r["grid"], "name": (r.get("name_full") or "").strip(),
                        "kind": kind, "text": seg})
        if re.search(r"not found in nps", r.get("notes") or "", re.I):
            out.append({"grid": r["grid"], "name": (r.get("name_full") or "").strip(),
                        "kind": "none", "text": "NPS: not found (register note)"})
    return out


def load_lookups(path):
    if not path or not Path(path).exists():
        return []
    return list(csv.DictReader(open(path, newline="")))


def same_name(sur, given, text, name=""):
    """Does a register note or stone name refer to this surname (and, if given, first initial)?"""
    sur = norm(sur)
    if not sur:
        return False
    head = (name + " " + text[:70])
    words = [norm(w) for w in re.findall(r"[A-Za-z']+", head)]
    hit = sur in words or bool(difflib.get_close_matches(sur, [w for w in words if len(w) > 2], n=1, cutoff=0.86))
    if not hit:
        return False
    gi = norm(given)[:1]
    if gi and name:
        ni = norm(name.split()[0])[:1]
        if ni and ni != gi and not re.search(rf"\b{re.escape(given.split()[0])}", head, re.I):
            return False
    return True


def status_for(sur, given, reg, looks):
    """-> (state, text): state in found | none | unsearched | not-searched."""
    rank = {"found": 0, "none": 1, "unsearched": 2}
    hits = sorted((r for r in reg if same_name(sur, given, r["text"], r["name"])), key=lambda r: rank[r["kind"]])
    if hits:
        r = hits[0]
        return r["kind"], f'{r["grid"]}: {r["text"][:160]}'
    for l in looks:
        if norm(l["surname"]) == norm(sur) or difflib.SequenceMatcher(None, norm(l["surname"]), norm(sur)).ratio() >= 0.86:
            gi = norm(given)[:1]
            if not gi or not norm(l["given"]) or norm(l["given"])[:1] == gi:
                return ("found" if l["result"] == "found" else "none"), \
                       f'{l["checked"]}: {l["unit_query"]} {l["detail"]}'[:160]
    return "not-searched", ""


def cmd_status(a):
    reg, looks = load_register(a.register), load_lookups(a.lookups)
    c = {k: sum(1 for r in reg if r["kind"] == k) for k in ("found", "none", "unsearched")}
    print(f"register notes: {c['found']} found, {c['none']} searched with no card, {c['unsearched']} marked not searched")
    print(f"lookups file:   {len(looks)} rows")


def cmd_lookup(a):
    reg, looks = load_register(a.register), load_lookups(a.lookups)
    n = 0
    for r in reg:
        if same_name(a.surname, a.given or "", r["text"], r["name"]):
            n += 1
            print(f'[register {r["grid"]}] {r["kind"]}: {r["text"][:220]}')
    for l in looks:
        if norm(l["surname"]) == norm(a.surname):
            n += 1
            print(f'[lookups] {l["result"]}: {l["given"]} {l["surname"]} {l["unit_query"]} {l["detail"]} {l["url"]} ({l["checked"]})')
    if not n:
        print("not searched yet")


def cmd_todo(a):
    reg, looks = load_register(a.register), load_lookups(a.lookups)
    seen, todo, have = set(), [], 0
    for c in csv.DictReader(open(a.candidates, newline="")):
        if c["grid"] == "pool" and not a.include_pool:
            continue
        if c["tier"] == "PV001 same surname":
            continue
        parts = c["name"].split()
        sur, given = (parts[-1], " ".join(parts[:-1])) if parts else ("", "")
        key = (norm(sur), norm(given))
        if key in seen:
            continue
        seen.add(key)
        state, _ = status_for(sur, given, reg, looks)
        if state == "not-searched" or state == "unsearched":
            todo.append({"grid": c["grid"], "name": c["name"], "unit": c["unit"], "death": c["death"]})
        else:
            have += 1
    out = Path(a.out) if a.out else None
    if out:
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["grid", "name", "unit", "death"])
            w.writeheader()
            w.writerows(todo)
    print(f"{len(seen)} distinct candidates: {have} already in the cache, {len(todo)} to search"
          + (f" -> {out}" if out else ""))
    if not out:
        for t in todo:
            print(f'  {t["grid"]:>5}  {t["name"]} -- {t["unit"]} (d. {t["death"]})')


def cmd_add(a):
    p = Path(a.lookups)
    new = not p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"surname": a.surname, "given": a.given, "unit_query": a.unit or "", "result": a.result,
                    "detail": a.detail, "url": a.url or "", "grid": a.grid or "",
                    "checked": dt.date.today().isoformat()})
    print(f"recorded: {a.given} {a.surname} -> {a.result}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--register", default="prescott/register.csv")
    ap.add_argument("--lookups", default="refs/nps-lookups.csv")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("lookup")
    s.add_argument("surname"); s.add_argument("given", nargs="?")
    s.set_defaults(fn=cmd_lookup)
    t = sub.add_parser("todo")
    t.add_argument("--candidates", required=True); t.add_argument("--out")
    t.add_argument("--include-pool", action="store_true", help="also list the unclaimed pool (long)")
    t.set_defaults(fn=cmd_todo)
    d = sub.add_parser("add")
    d.add_argument("surname"); d.add_argument("given")
    d.add_argument("--result", required=True, choices=["found", "none"])
    d.add_argument("--detail", required=True); d.add_argument("--unit"); d.add_argument("--url"); d.add_argument("--grid")
    d.set_defaults(fn=cmd_add)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
