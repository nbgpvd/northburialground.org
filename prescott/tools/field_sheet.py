#!/usr/bin/env python3
"""field_sheet.py -- a pre-visit sheet for one row of the Prescott Post lot.

The point: arrive at the stones with every position's candidates already known,
so the visit is confirm-or-refute and the date lines get read on site.

  1. Parse the RI VETS PV001 list once (needs `pdftotext`, from poppler):

       python3 field_sheet.py pv001 ~/Downloads/providence-pv001.pdf refs/pv001-civilwar.csv

  2. Build a sheet for a row:

       python3 field_sheet.py sheet --register prescott/register.csv \\
           --pv001 refs/pv001-civilwar.csv --row C --out field/

     Writes field/field-sheet-C-<date>.html (phone-readable; open it from Files
     or Safari) and field/field-candidates-C-<date>.csv.

For each position it shows what the register already holds, the death-year window
implied by the neighbouring stones, and the PV001 Civil War men who fit that
window and the unit the register has for the stone (if any). Candidates are
LEADS, not identifications: standards.md says a name is not stated as fact until
a stone and a record agree. Use --pad to widen the window (default 1 year).

PV001 itself has known gaps and wrong years (B18 and B22 in row B), so a stone
that matches nothing is a finding, not a failure. Standard library only.
"""
import argparse
import csv
import datetime as dt
import html
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # explicit, so it also works under python3 -I
import nps_cache

DATE = r"\d{1,2}/\d{1,2}/\d{4}|\d{4}c?"

# ---------------------------------------------------------------- PV001
def parse_pv001(pdf, out):
    try:
        txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                             text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("pdftotext not found (install poppler, e.g. `brew install poppler`)")
    lines = txt.splitlines()
    rows = []
    for line in lines:
        # Column offsets drift from page to page, so split on runs of spaces instead.
        if not line.startswith("PV001"):
            continue
        m = re.search(r"Civil War", line, re.I)
        if not m:
            continue
        sm = re.match(r"PV001\s+(\S+(?: \S+)*?)(?:\s{2,}|\s*$)", line)
        if not sm:
            continue
        surname = sm.group(1).strip()
        seg = line[sm.end():m.start()]
        toks = re.findall(DATE, seg)
        given = re.split(DATE, seg)[0].strip() if toks else seg.strip()
        birth = death = ""
        if len(toks) >= 2:
            birth, death = toks[-2], toks[-1]
        elif len(toks) == 1:
            gap = len(seg) - len(seg.rstrip())
            if gap <= 2:
                death = toks[0]
            else:
                birth = toks[0]
        unit = re.split(r"\s{2,}", line[m.end():].strip())[0].strip()
        if unit.lower().startswith("north burial"):
            unit = ""
        y = re.search(r"(\d{4})", death)
        rows.append({"surname": surname, "given": given, "birth": birth, "death": death,
                     "death_year": y.group(1) if y else "", "unit": unit})
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["surname", "given", "birth", "death", "death_year", "unit"])
        w.writeheader()
        w.writerows(rows)
    withy = sum(1 for r in rows if r["death_year"])
    print(f"{len(rows)} Civil War entries ({withy} with a death year) -> {out}")


# ---------------------------------------------------------------- unit matching
STATES = {
    "maine": r"\bmaine\b|\bme\b", "vermont": r"\bvt\b|vermont",
    "connecticut": r"\bconn|\bct\b", "pennsylvania": r"\bpa\b|penn",
    "new york": r"\bn\.?\s?y\b|new york", "massachusetts": r"\bmass|\bma\b",
    "new hampshire": r"\bnh\b|new hamp", "rhode island": r"\bri\b|r\.i\.|rhode",
    "new jersey": r"\bnj\b|n\.j\.|new jersey", "delaware": r"\bdel\b|delaware",
    "maryland": r"\bmd\b|maryland", "michigan": r"\bmich", "illinois": r"\bill\b",
    "california": r"\bcal", "kentucky": r"\bken\b|\bky\b|kentucky",
}


def unit_patterns(unit):
    """Regexes a PV001 unit string must ALL match for this register unit; None = no filter."""
    u = (unit or "").lower().strip()
    if not u:
        return None
    pats = []
    m = re.match(r"(\d+)", u)
    if m:
        pats.append(rf"\b{m.group(1)}(st|nd|rd|th|d)?\b")
    if re.search(r"\busn\b|navy", u):
        pats.append(r"\busn\b|navy|u\.s\.n")
    state_hit = False
    for name, p in STATES.items():
        if re.search(p, u):
            pats.append(p)
            state_hit = True
            break
    if not state_hit and re.search(r"\bu\.?\s?s\.?\b|united states", u) and not re.search(r"usn", u):
        pats.append(r"\bu\.?\s?s\b|u\.s\.|\bus\b")
    if re.search(r"cav", u):
        pats.append(r"cav")
    elif re.search(r"artillery|\bh\.? ?a\b|\bart\b", u):
        pats.append(r"h\.? ?a\b|art")
    return pats or None


def unit_match(pats, pv_unit):
    if pats is None:
        return None
    pu = (pv_unit or "").lower()
    return all(re.search(p, pu) for p in pats)


# ---------------------------------------------------------------- sheet
def year_of(s):
    m = re.match(r"(\d{4})", (s or "").strip())
    return int(m.group(1)) if m else None


def col(grid):
    return int(re.sub(r"\D", "", grid))


def build_sheet(a):
    reg = list(csv.DictReader(open(a.register, newline="")))
    pv = list(csv.DictReader(open(a.pv001, newline="")))
    row = a.row.upper()
    stones = sorted([r for r in reg if re.fullmatch(rf"{row}\d+", r["grid"])], key=lambda r: col(r["grid"]))
    if not stones:
        sys.exit(f"no stones for row {row} in {a.register}")

    known = [(col(r["grid"]), year_of(r["died"])) for r in stones if year_of(r["died"])]
    others = {}
    for r in reg:
        y, nm = year_of(r["died"]), (r["name_full"] or "").strip()
        if y and nm:
            others[(nm.split()[-1].lower(), y)] = r["grid"]

    def window(c):
        if not known:
            return None
        left = [(abs(c - k), y) for k, y in known if k <= c]
        right = [(abs(k - c), y) for k, y in known if k >= c]
        ys = []
        if left:
            ys.append(min(left)[1])
        if right:
            ys.append(min(right)[1])
        lo, hi = min(ys), max(ys)
        pad = a.pad + (0 if len(ys) == 2 else 1)  # one-sided: widen a year
        return lo - pad, hi + pad

    for p in pv:
        p["_y"] = int(p["death_year"]) if p["death_year"].isdigit() else None
        p["_name"] = f"{p['given']} {p['surname']}".strip().title()

    cards, cand_rows = [], []
    pool_idx, claimed = set(), set()
    for r in stones:
        g, c = r["grid"], col(r["grid"])
        w = window(c)
        pats = unit_patterns(r["unit"])
        cands = []
        sur = (r["name_full"] or "").split()[-1].lower() if (r["name_full"] or "").strip() else ""
        if sur:
            mode = "check"          # a name is already in the register: show what PV001 says of it
            for i, p in enumerate(pv):
                if p["surname"].lower() == sur:
                    ok = year_of(r["died"]) is not None and p["_y"] == year_of(r["died"])
                    cands.append((0 if ok else 1, p["_y"] or 0, p["surname"], i, p))
        elif pats is None:
            mode = "pool"           # nothing to filter on: candidates go in one shared pool
        else:
            mode = "narrowed"
        if w and mode != "check":
            for i, p in enumerate(pv):
                if p["_y"] is None or not (w[0] <= p["_y"] <= w[1]):
                    continue
                m = unit_match(pats, p["unit"])
                if m is False:
                    continue
                placed = others.get((p["surname"].lower(), p["_y"]))
                if placed and placed != g:
                    continue
                cands.append((0 if m else 1, p["_y"], p["surname"], i, p))
        cands.sort(key=lambda t: t[:4])
        named = bool((r["name_carved"] or "").strip())
        todo = []
        if not named:
            todo.append("Read the name, unit, company and date line.")
        elif not year_of(r["died"]):
            todo.append("Read the date line (clear soil from the lower edge, with Annalisa's okay).")
        for sent in re.split(r"(?<=[.;])\s+", r["notes"] or ""):
            if re.search(r"\bcheck\b|conflict|illegible|re-?verify|sunk|buried", sent, re.I):
                todo.append(sent.strip()[:220])
        cards.append((r, w, pats, cands, todo, mode))
        for t in cands:
            p = t[4]
            if mode == "pool":
                pool_idx.add(t[3])
                continue
            claimed.add(t[3])
            tier = {"check": "PV001 agrees" if t[0] == 0 else "PV001 same surname",
                    "narrowed": "unit+year"}[mode]
            cand_rows.append({"grid": g, "tier": tier,
                              "name": p["_name"], "death": p["death"], "unit": p["unit"]})
    pool_idx -= claimed
    for i in sorted(pool_idx, key=lambda i: (pv[i]["_y"], pv[i]["surname"])):
        p = pv[i]
        cand_rows.append({"grid": "pool", "tier": "year-only", "name": p["_name"],
                          "death": p["death"], "unit": p["unit"]})

    today = dt.date.today().isoformat()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cpath = out / f"field-candidates-{row}-{today}.csv"
    with open(cpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["grid", "tier", "name", "death", "unit"])
        w.writeheader()
        w.writerows(cand_rows)

    e = html.escape
    parts = [f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Row {row} field sheet {today}</title>
<style>
body{{font:17px/1.4 -apple-system,system-ui,sans-serif;margin:0;padding:12px;background:#fafafa;color:#111}}
h1{{font-size:22px;margin:4px 0}} .sub{{color:#555;font-size:14px;margin-bottom:12px}}
.card{{background:#fff;border:1px solid #ddd;border-radius:10px;padding:10px 12px;margin:10px 0}}
.chip{{display:inline-block;background:#1f3a5f;color:#fff;border-radius:6px;padding:1px 9px;font-weight:700;margin-right:8px}}
.st{{font-size:13px;color:#555}} .win{{font-size:14px;color:#555}}
ul{{margin:4px 0 4px 18px;padding:0}} li{{margin:2px 0}} .t1{{font-weight:600}} .t2{{color:#555}}
.todo{{background:#fff6d6;border-radius:6px;padding:4px 8px;margin-top:6px;font-size:15px}}
.nps{{font-size:12px;border-radius:4px;padding:0 6px;white-space:nowrap}} .nps.ok{{background:#e1f0e1;color:#245c24}} .nps.no{{background:#eee;color:#555}}
.known{{margin:4px 0}} .none{{color:#888;font-style:italic}}
</style>
<h1>Row {e(row)} &mdash; field sheet</h1>
<div class="sub">Built {today} from register.csv and the RI VETS PV001 list. Candidates are leads, not identifications:
confirm against the stone and a record. Shoot oblique from downhill first, then close; view frames upright.</div>"""]
    nps_reg = nps_cache.load_register(a.register)
    nps_looks = nps_cache.load_lookups(a.lookups)
    NPS_TAG = {"found": ("NPS: card on file", "ok"), "none": ("NPS: searched, no card", "ok"),
               "unsearched": ("NPS: not yet searched", "no"), "not-searched": ("NPS: not yet searched", "no")}

    def li(t):
        p = t[4]
        state, _ = nps_cache.status_for(p["surname"], p["given"], nps_reg, nps_looks)
        label, cls = NPS_TAG[state]
        return (f'<li class="{"t1" if t[0]==0 else "t2"}">{e(p["_name"])} &mdash; d. {e(p["death"] or "no date")}'
                f'{" &mdash; " + e(p["unit"]) if p["unit"] else ""} <span class="nps {cls}">{label}</span></li>')

    for r, w, pats, cands, todo, mode in cards:
        known_bits = [x for x in (r["name_carved"], r["unit"], ("Co. " + r["company"]) if r["company"] else "",
                                  r["died"]) if x]
        parts.append(f'<div class="card"><span class="chip">{e(r["grid"])}</span>'
                     f'<span class="st">{e(r["status"] or "no record")}</span>')
        parts.append(f'<div class="known">{e(" · ".join(known_bits)) if known_bits else "<span class=none>nothing recorded</span>"}</div>')
        if mode == "check":
            if cands:
                parts.append('<div class="win">PV001 for this surname (bold = death year agrees):</div><ul>'
                             + "".join(li(t) for t in cands[: a.max]) + "</ul>")
            else:
                parts.append('<div class="none">Surname not found in PV001 Civil War list.</div>')
        elif mode == "narrowed":
            parts.append(f'<div class="win">Death {w[0]}–{w[1]} (neighbours); unit: {e(r["unit"])}</div>' if w
                         else f'<div class="win">Unit: {e(r["unit"])}</div>')
            if cands:
                parts.append("<ul>" + "".join(li(t) for t in cands[: a.max]) + "</ul>")
                if len(cands) > a.max:
                    parts.append(f'<div class="win">+ {len(cands)-a.max} more in the CSV</div>')
            else:
                parts.append('<div class="none">No PV001 man with that unit in that window: a finding.</div>')
        else:
            parts.append(f'<div class="win">Nothing to filter on. Death {w[0]}–{w[1]} (neighbours); see the pool below.</div>'
                         if w else '<div class="win">Nothing to filter on.</div>')
        for t in todo:
            parts.append(f'<div class="todo">&#9744; {e(t)}</div>')
        parts.append("</div>")
    pool = [pv[i] for i in sorted(pool_idx, key=lambda i: (pv[i]["_y"], pv[i]["surname"]))]
    if pool:
        parts.append(f'<details class="card"><summary><b>Unclaimed pool: {len(pool)} PV001 Civil War men</b> '
                     f'who died in a window above and are not yet placed or narrowed to a stone</summary><ul>'
                     + "".join(f'<li>{e(p["_name"])} &mdash; d. {e(p["death"])}'
                               f'{" &mdash; " + e(p["unit"]) if p["unit"] else ""}</li>' for p in pool)
                     + "</ul></details>")
    hpath = out / f"field-sheet-{row}-{today}.html"
    hpath.write_text("\n".join(parts), encoding="utf-8")
    nunit = sum(1 for r, w, pats, cands, todo, mode in cards if mode == 'narrowed' and cands)
    print(f"row {row}: {len(stones)} stones; {len(cand_rows)} candidate lines; "
          f"{nunit} stones narrowed by unit")
    print(f"  {hpath}\n  {cpath}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pv001", help="parse the PV001 PDF into a Civil War CSV")
    p.add_argument("pdf")
    p.add_argument("out")
    s = sub.add_parser("sheet", help="build the HTML field sheet for a row")
    s.add_argument("--register", required=True)
    s.add_argument("--pv001", required=True)
    s.add_argument("--row", required=True)
    s.add_argument("--out", default="field")
    s.add_argument("--lookups", default=None, help="refs/nps-lookups.csv (searches made for men not yet on a stone)")
    s.add_argument("--pad", type=int, default=1, help="years to widen the death-year window")
    s.add_argument("--max", type=int, default=12, help="candidates shown per stone")
    a = ap.parse_args()
    if a.cmd == "pv001":
        parse_pv001(a.pdf, a.out)
    else:
        build_sheet(a)


if __name__ == "__main__":
    main()
