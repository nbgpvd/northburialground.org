#!/usr/bin/env python3
"""
build.py — static site generator for the Prescott Post Digital Companion.

    python3 build.py                 # prototype build into _site/
    python3 build.py --release       # strict: fails on editor markers, uncaptioned records, broken links
    python3 build.py --out docs      # build somewhere else (e.g. GitHub Pages /docs)

Inputs (all in the repo, next to this file):
    register.csv              one row per stone; grid, name_carved, ..., status, researcher, notes
    site/plot.md              the plot page (front matter + markdown)  -> /map/
    veterans/<GRID>-<surname>.md  one dossier per man (front matter + markdown) -> /stone/<GRID>-<surname>/
    records/<GRID>/           hosted records (jpg/png/pdf) referenced from "## The records"

Standard library only. No database. Rebuild with one command.

Hosting (decided 1 Nov 2026): the canonical home is https://northburialground.org/prescott/
on GitHub Pages. northburialground.org is registered at Squarespace (juneteenthproj account,
10-year term, renews Oct 2036) and is to pass to the North Burial Ground Foundation once it
exists. The companion lives under /prescott/ so the foundation can use the root and other
paths later. Every published page carries a <link rel="canonical"> built from SITE_URL;
QR codes must be generated from SITE_URL, never from a github.io address.

Conventions the script enforces or reports:
  * [n] in body text becomes a link to source n in "## Sources" (li id="src-n").
  * ⟨ ... ⟩ is an editor's marker. Prototype builds render it highlighted; --release refuses to build.
  * <!-- ... --> HTML comments are editor's notes and are never published.
  * "## The records" bullets of the form `records/<GRID>/file` — caption [n] are matched
    against files on disk; hosted files render inline, missing ones are listed as "not yet hosted".
  * Every page carries the City of Providence credit and the researchers named in front matter.
"""

import argparse
import csv
import glob
import html
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_NAME = "Prescott Post Digital Companion"
SITE_URL = "https://northburialground.org/prescott/"   # canonical root; trailing slash required
CITY_CREDIT = ("Records courtesy of the City of Providence, Department of Parks, "
               "North Burial Ground.")
STATUS_ORDER = ["stone-only", "identified", "draft", "complete"]
STATUS_GLOSS = {
    "stone-only": "stone photographed and transcribed",
    "identified": "City record and service identity confirmed",
    "draft": "service record or pension located; life drafted",
    "complete": "civil life researched; second reader signed off",
}
MARKER_RE = re.compile(r"⟨([^⟩]*)⟩")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

PROBLEMS = []   # (severity, where, message); severity in {"error", "warn"}


def problem(sev, where, msg):
    PROBLEMS.append((sev, where, msg))


# ----------------------------------------------------------------------------
# Front matter (a deliberately small YAML subset: scalars, inline lists, block lists)
# ----------------------------------------------------------------------------

def _strip_yaml_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _yaml_scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_yaml_scalar(x) for x in _split_inline_list(inner)] if inner else []
    return s


def _split_inline_list(s):
    items, buf, quote = [], [], None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    return [x.strip() for x in items]


def parse_front_matter(text, where):
    """Return (dict, body). Front matter is the block between the first two '---' lines."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n")
    end = None
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            end = i
            break
    if end is None:
        problem("error", where, "front matter never closed with ---")
        return {}, text
    meta, key = {}, None
    for raw in parts[1:end]:
        line = _strip_yaml_comment(raw)
        if not line.strip():
            continue
        if re.match(r"^\s+-\s", line) and key is not None:
            if not isinstance(meta[key], list):
                meta[key] = []
            meta[key].append(_yaml_scalar(line.strip()[1:].strip()))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            problem("warn", where, f"front matter line not understood: {raw!r}")
            continue
        key, val = m.group(1), m.group(2)
        meta[key] = _yaml_scalar(val) if val.strip() else ""
    body = "\n".join(parts[end + 1:])
    return meta, body


# ----------------------------------------------------------------------------
# Markdown (the subset the dossier template uses)
# ----------------------------------------------------------------------------

def inline(text, prefix):
    """Escape, then apply inline markdown: code, bold, italic, links, [n] citations, ⟨markers⟩."""
    s = html.escape(text, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(((?:\.\./|/)[^)\s]+)\)", r'<a href="\2">\1</a>', s)   # relative links
    s = re.sub(r"\[(\d+)\](?!\()", r'<a class="cite" href="#src-\1">[\1]</a>', s)
    s = MARKER_RE.sub(lambda m: f'<mark class="todo">⟨{m.group(1)}⟩</mark>', s)
    return s


def render_markdown(body, prefix, where, records=None):
    """Render markdown body to HTML. Returns (html, sections) where sections maps
    heading text -> rendered html, so callers can place sections individually."""
    body = COMMENT_RE.sub("", body)
    lines = body.split("\n")
    out = []
    i = 0
    list_mode = None  # None | "ul" | "ol" | "sources" | "records"
    current_h2 = None

    def close_list():
        nonlocal list_mode
        if list_mode in ("ul", "records"):
            out.append("</ul>")
        elif list_mode in ("ol", "sources"):
            out.append("</ol>")
        list_mode = None

    para = []

    def flush_para():
        if para:
            out.append("<p>" + inline(" ".join(para), prefix) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_para()
            close_list()
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            close_list()
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1:
                # The H1 is the page title; the template renders it from front matter.
                i += 1
                continue
            current_h2 = text if level == 2 else current_h2
            slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            out.append(f'<h{level} id="{slug}">{inline(text, prefix)}</h{level}>')
            i += 1
            continue
        m = re.match(r"^!\[(.*)\]\(([^)\s]+)\)\s*$", stripped)
        if m:
            # A block-level image: ![caption](../records/...) -> figure with caption; the image links to itself.
            flush_para()
            close_list()
            alt, src = m.group(1), m.group(2)
            out.append(f'<figure><a href="{html.escape(src, quote=True)}"><img src="{html.escape(src, quote=True)}" loading="lazy" '
                       f'alt="{html.escape(re.sub(r"\[\d+\]", "", re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", alt)).strip(), quote=True)}"></a>'
                       + (f"<figcaption>{inline(alt, prefix)}</figcaption>" if alt else "") + "</figure>")
            i += 1
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            flush_para()
            n, text = m.group(1), m.group(2)
            if current_h2 and current_h2.lower() == "sources":
                if list_mode != "sources":
                    close_list()
                    out.append('<ol class="sources">')
                    list_mode = "sources"
                out.append(f'<li id="src-{n}" value="{n}">{inline(text, prefix)}</li>')
            else:
                if list_mode != "ol":
                    close_list()
                    out.append("<ol>")
                    list_mode = "ol"
                out.append(f"<li>{inline(text, prefix)}</li>")
            i += 1
            continue
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            flush_para()
            text = m.group(1)
            if current_h2 and current_h2.lower() == "the records" and records is not None:
                if list_mode != "records":
                    close_list()
                    out.append('<ul class="records">')
                    list_mode = "records"
                out.append(render_record_item(text, prefix, where, records))
            else:
                if list_mode != "ul":
                    close_list()
                    out.append("<ul>")
                    list_mode = "ul"
                out.append(f"<li>{inline(text, prefix)}</li>")
            i += 1
            continue
        # paragraph text (lines are joined until a blank line)
        if list_mode and line.startswith("  "):
            # continuation of a list item
            out[-1] = out[-1][:-5] + " " + inline(stripped, prefix) + "</li>"
            i += 1
            continue
        close_list()
        para.append(stripped)
        i += 1
    flush_para()
    close_list()
    return "\n".join(out)


RECORD_RE = re.compile(r"^`([^`]+)`\s*(?:—|-|–)\s*(.*)$")


def render_record_item(text, prefix, where, records):
    """A bullet under '## The records': `records/G3/file` — caption [n] ⟨note⟩."""
    m = RECORD_RE.match(text.strip())
    if not m:
        problem("warn", where, f"record line not in `path` — caption form: {text[:60]!r}")
        return f"<li>{inline(text, prefix)}</li>"
    pattern, caption = m.group(1).strip(), m.group(2).strip()
    matches = sorted(glob.glob(str(ROOT / pattern)))
    has_cite = re.search(r"\[\d+\]", caption) is not None
    caption_text = MARKER_RE.sub("", caption).strip()
    if not matches:
        return (f'<li class="record missing"><span class="path">{html.escape(pattern)}</span> — '
                f'{inline(caption, prefix)} <span class="note">(not yet hosted)</span></li>')
    parts = []
    for path in matches:
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        records.add(rel)
        if not caption_text or not has_cite:
            problem("error", where, f"hosted record {rel} lacks a caption or a [n] citation")
        src = prefix + rel
        if os.path.basename(rel).lower().startswith("stone") and rel.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            parts.append(f'<p class="doc"><a href="{src}">Headstone photograph</a> (shown above) — {inline(caption, prefix)}</p>')
        elif rel.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            parts.append(f'<figure><a href="{src}"><img src="{src}" loading="lazy" '
                         f'alt="{html.escape(caption_text, quote=True)}"></a>'
                         f"<figcaption>{inline(caption, prefix)}</figcaption></figure>")
        else:
            parts.append(f'<p class="doc"><a href="{src}">{html.escape(os.path.basename(rel))}</a> — '
                         f"{inline(caption, prefix)}</p>")
    return '<li class="record">' + "".join(parts) + "</li>"


# ----------------------------------------------------------------------------
# Page shell
# ----------------------------------------------------------------------------

def fmt_date(iso):
    """2026-10-31 -> October 31, 2026 (falls back to the input)."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso).strip())
    if not m:
        return str(iso)
    months = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
    return f"{months[int(m.group(2)) - 1]} {int(m.group(3))}, {m.group(1)}"


MAP_ICON = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linejoin="round" aria-hidden="true"><path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/>'
            '<path d="M9 3v15M15 6v15"/></svg>')


def page(title, body_html, prefix, researchers, revised, release, extra_head="", kind="page", path=""):
    """path is the page's location under SITE_URL, e.g. 'stone/G3-howland/' or 'map/'."""
    canonical = f'<link rel="canonical" href="{SITE_URL}{path}">'
    banner = "" if release else (
        '<div class="banner">Prototype build — not for public release. '
        'Yellow marks are editor\'s notes still to be resolved.</div>')
    credits = ""
    if researchers:
        credits = "Research by " + html.escape(", ".join(researchers)) + ". "
    revised_txt = f" Revised {html.escape(fmt_date(revised))}." if revised else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {SITE_NAME}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&amp;family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}assets/style.css">
{canonical}
{extra_head}
</head>
<body class="{kind}">
<div class="column">
{banner}
<header class="site">
  <a class="home" href="{prefix}map/index.html">Prescott Post lot</a>
  <a class="maplink" href="{prefix}map/index.html#rows">{MAP_ICON}<span>Map</span></a>
</header>
<main>
{body_html}
</main>
<footer class="site">
  <p>{credits}{CITY_CREDIT}{revised_txt}</p>
  <p><a href="{prefix}map/index.html#rows">Plot map</a> · <a href="{prefix}monument/index.html">The monument</a> · <a href="{prefix}help/index.html">How to help</a> · <a href="{prefix}standards/index.html">Standards</a> · <a href="{prefix}register.csv">Register (CSV)</a></p>
</footer>
</div>
</body>
</html>
"""


STYLE = """
/* Prescott Post Digital Companion — phone first, bright sun. Tokens from the design canvas. */
:root { --ink:#16181B; --muted:#4A4F55; --paper:#fff; --bg:#E9EBEE; --rule:#D8DBDF; --panel:#F2F3F5;
        --navy:#1E3A66; --navy-dark:#122744; --ident:#6F7F99; --stone:#C3C8CE; --dash:#7A8088;
        --monument:#E08A1E; --gold:#C9A227; --todo:#ffe66d;
        --sans:"Public Sans", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        --serif:"Source Serif 4", Georgia, "Times New Roman", serif; }
* { box-sizing:border-box; }
html { font-size:112.5%; -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans); line-height:1.5; }
.column { max-width:520px; margin:0 auto; background:var(--paper); min-height:100vh; box-shadow:0 0 0 1px var(--rule); }
a { color:var(--navy); }
a:hover { color:var(--navy-dark); }
main { padding:0 20px 2rem; }
header.site { display:flex; align-items:center; justify-content:space-between; padding:18px 20px 14px; border-bottom:1px solid var(--rule); }
header.site .home { font-weight:700; font-size:.82rem; letter-spacing:.09em; text-transform:uppercase; color:var(--ink); text-decoration:none; }
header.site .maplink { display:inline-flex; align-items:center; gap:6px; font-weight:700; font-size:1.05rem; text-decoration:none; }
footer.site { padding:1.2rem 20px 2rem; border-top:1px solid var(--rule); font-size:.85rem; color:var(--muted); }
footer.site a { color:var(--navy); }
.banner { background:var(--todo); color:var(--ink); font-size:.8rem; padding:.4rem 20px; }

h1 { font-family:var(--serif); font-weight:700; font-size:2.15rem; line-height:1.1; letter-spacing:.01em; margin:.5rem 0 .6rem; }
h2 { font-family:var(--serif); font-weight:700; font-size:1.5rem; line-height:1.2; margin:2rem 0 .6rem; padding-bottom:.3rem; border-bottom:2px solid var(--ink); }
h3 { font-family:var(--sans); font-weight:700; font-size:1.05rem; margin:1.4rem 0 .4rem; }
p { margin:.6rem 0; }
p.lede { font-size:1.15rem; line-height:1.4; margin:0 0 1rem; }
p.gridline { display:flex; align-items:center; gap:12px; margin:1.3rem 0 .2rem; color:var(--muted); font-size:1.05rem; }
.chip { display:inline-block; background:var(--ink); color:#fff; font-weight:800; font-size:1.05rem; padding:.35rem .9rem; border-radius:8px; letter-spacing:.02em; }
code { font-family:ui-monospace, Menlo, monospace; font-size:.9em; }
mark.todo { background:var(--todo); padding:0 .15em; }
img { max-width:100%; height:auto; }

/* research-status bar */
.progress { margin:1rem 0 1.2rem; }
.progress .segs { display:flex; gap:6px; }
.progress .seg { flex:1 1 0; height:9px; border-radius:5px; background:var(--rule); }
.progress .seg.on { background:var(--navy); }
.progress .labs { display:flex; gap:6px; margin-top:.35rem; font-size:.9rem; color:var(--muted); }
.progress .labs span { flex:1 1 0; }
.progress .labs span:nth-child(2) { text-align:left; }
.progress .labs .cur { color:var(--navy); font-weight:700; }
.progress .cap { margin:.5rem 0 0; color:var(--muted); font-size:.95rem; }

/* pill navigation */
nav.jump { display:flex; flex-wrap:wrap; gap:10px; margin:.2rem 0 1.4rem; }
nav.jump a { display:inline-block; background:var(--panel); color:var(--navy); font-weight:600; font-size:1.05rem;
             padding:.6rem 1.1rem; border-radius:999px; text-decoration:none; white-space:nowrap; }

/* the stone card */
section.stone { border:1px solid var(--rule); border-radius:14px; overflow:hidden; margin:0 0 1.6rem; background:var(--paper); }
section.stone .hero { display:block; width:100%; height:300px; object-fit:cover; object-position:center 45%; }
section.stone .nophoto { display:flex; align-items:center; justify-content:center; min-height:120px; background:var(--panel); color:var(--muted); font-style:italic; }
section.stone .stone-body { padding:14px 18px 12px; }
.eyebrow { font-size:.78rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin:0 0 .4rem; }
p.carved { font-family:var(--serif); font-weight:700; font-size:1.3rem; line-height:1.35; margin:0 0 .6rem; }
section.stone .stone-body p:last-child { margin-bottom:0; }
section.stone .stone-body p:not(.carved):not(.eyebrow) { font-size:.98rem; color:var(--ink); }

/* records */
ul.records { list-style:none; padding:0; }
ul.records li.record { margin:0 0 1.2rem; }
ul.records li.missing { margin:.4rem 0; }
ul.records .path { font-family:ui-monospace, Menlo, monospace; font-size:.85em; }
ul.records .note { font-style:italic; }
figure { margin:.6rem 0 1rem; }
figure img { width:100%; height:auto; border:1px solid var(--rule); border-radius:8px; display:block; }
figcaption { font-size:.9rem; margin-top:.35rem; color:var(--muted); }
p.doc { font-size:.95rem; }
ol.sources { padding-left:1.4rem; font-size:.95rem; }
ol.sources li { margin:.5rem 0; }
a.cite { text-decoration:none; font-weight:700; padding:0 1px; }
ul.cols { columns:2 14rem; padding-left:1.2rem; }
ul.cols li { break-inside:avoid; }
section.help { margin:1.6rem 0; padding:1rem 1.1rem; border:1px solid var(--rule); border-radius:14px; background:var(--panel); }
section.help h2 { margin-top:0; border:0; padding:0; font-size:1.35rem; }
a.button { display:inline-flex; align-items:center; justify-content:center; min-height:48px; padding:.6rem 1.1rem; border-radius:10px;
           background:var(--navy); color:#fff; text-decoration:none; font-weight:700; }
a.button:hover { background:var(--navy-dark); color:#fff; }

/* map page */
.lotmap { background:var(--panel); border-radius:14px; padding:14px 12px 10px; margin:1rem 0 .8rem; }
.lotmap .compass { display:flex; justify-content:space-between; font-size:.9rem; color:var(--muted); margin:0 2px 8px 24px; }
.lotmap .compass b { font-weight:600; color:var(--ink); }
.maprow { display:flex; align-items:center; gap:8px; padding:3px 2px; border-radius:6px; }
.maprow.on { background:#fff; box-shadow:inset 0 0 0 2px var(--navy); }
.maprow .maplabel { width:14px; text-align:center; font-size:.8rem; font-weight:600; color:var(--muted); }
.maprow.on .maplabel { color:var(--navy); font-weight:800; }
.maprow .cells { display:flex; gap:2px; align-items:flex-end; }
.cell { display:block; width:11px; height:17px; border-radius:5px 5px 2px 2px; background:var(--stone); }
.cell.i { background:var(--ident); } .cell.d { background:var(--navy); } .cell.c { background:var(--ink); box-shadow:0 0 0 2px var(--gold); }
.cell.e { background:transparent; border:1.5px dashed var(--dash); }
.cell.f { width:11px; height:11px; border-radius:50%; border:2px solid var(--ink); background:#fff; }
.cell.m { background:var(--monument); border-radius:2px; } .cell.gap { background:transparent; }
.lotmap .note { font-size:.9rem; color:var(--muted); margin:.6rem 2px 0; }
.legend { display:flex; flex-wrap:wrap; gap:.5rem 1.1rem; font-size:.95rem; margin:.6rem 0 1.4rem; }
.legend span { display:inline-flex; align-items:center; gap:6px; }
.chooser { margin:1.2rem 0 .4rem; }
.chooser .eyebrow { margin-bottom:.5rem; }
.chips { display:flex; flex-wrap:wrap; gap:8px; }
.chips button { height:44px; min-width:44px; padding:0 .8rem; border-radius:10px; font:700 1.05rem var(--sans); cursor:pointer;
                border:2px solid var(--stone); background:#fff; color:var(--ink); }
.chips button[aria-pressed="true"] { background:var(--navy); color:#fff; border-color:var(--navy); }
.rowlist .rowhead { display:flex; align-items:baseline; justify-content:space-between; padding:1.2rem 0 .5rem; border-bottom:2px solid var(--ink); }
.rowlist .rowhead h2 { margin:0; border:0; padding:0; font-size:1.5rem; }
.rowlist .rowhead span { font-size:.9rem; color:var(--muted); }
.place { display:flex; align-items:center; gap:14px; min-height:60px; padding:8px 0; border-bottom:1px solid var(--rule); color:var(--ink); text-decoration:none; }
.place .code { flex:0 0 44px; font-weight:700; color:var(--muted); }
.place.linked .code { color:var(--navy); }
.place .what { flex:1 1 auto; display:flex; flex-direction:column; gap:2px; }
.place .name { font-weight:600; }
.place .name.unnamed { font-weight:400; font-style:italic; color:var(--muted); }
.place .st { font-size:.85rem; color:var(--muted); }
.place svg { flex:0 0 auto; }
.essay h2 { margin-top:2rem; }
"""




# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------

def load_register():
    rows = []
    with open(ROOT / "register.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r = {k: (v or "").strip() for k, v in r.items()}
            if not r.get("grid"):
                continue
            m = re.match(r"^([A-Z])(\d+)$", r["grid"])
            if not m:
                problem("error", "register.csv", f"grid not of the form A1: {r['grid']!r}")
                continue
            r["_row"], r["_col"] = m.group(1), int(m.group(2))
            if r["status"] and r["status"] not in STATUS_ORDER:
                problem("error", "register.csv", f"{r['grid']}: status {r['status']!r} not in {STATUS_ORDER}")
            rows.append(r)
    seen = set()
    for r in rows:
        if r["grid"] in seen:
            problem("error", "register.csv", f"duplicate grid {r['grid']}")
        seen.add(r["grid"])
    return rows


def load_file_requests():
    """file-requests.csv: grid, upload_url, status (open|closed) ... -> {grid: url} for open requests."""
    path = ROOT / "file-requests.csv"
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            grid, url, status = (r.get("grid") or "").strip(), (r.get("upload_url") or "").strip(), (r.get("status") or "").strip()
            if grid and url and status == "open":
                if not url.startswith("https://www.dropbox.com/request/"):
                    problem("warn", "file-requests.csv", f"{grid}: upload_url is not a Dropbox file request: {url}")
                out[grid] = url
    return out


def load_dossiers():
    dossiers = []
    for path in sorted((ROOT / "veterans").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text, path.name)
        m = re.match(r"^([A-Z]\d+)-([a-z0-9-]+)\.md$", path.name)
        if not m:
            problem("error", path.name, "dossier filename must be <GRID>-<surname>.md (lowercase surname)")
            continue
        grid, surname = m.group(1), m.group(2)
        if meta.get("grid") != grid:
            problem("error", path.name, f"front matter grid {meta.get('grid')!r} != filename grid {grid}")
        if meta.get("status") not in STATUS_ORDER:
            problem("error", path.name, f"status {meta.get('status')!r} not in {STATUS_ORDER}")
        if not meta.get("name_carved"):
            problem("error", path.name, "name_carved is empty (it is the page title)")
        if meta.get("status") == "complete" and not meta.get("second_reader"):
            problem("error", path.name, "status complete requires second_reader")
        dossiers.append({"grid": grid, "surname": surname, "slug": f"{grid}-{surname}",
                         "meta": meta, "body": body, "file": path.name})
    return dossiers


# ----------------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------------

def help_block(name, url):
    name = html.escape(name)
    return (f'<section class="help" id="help"><h2>Help research this man</h2>'
            f'<p>Do you have a record of {name} — a census page, a pension card, a city-directory entry, '
            f'a newspaper item, a family story? You can upload it to the project without an account. '
            f'Please say what the record is, where you found it, and why you believe it is this man. '
            f'Every contributor is credited on this page.</p>'
            f'<p><a class="button" href="{html.escape(url)}" rel="noopener">Upload a record for {name}</a></p></section>')


STATUS_STEP = {"stone-only": 1, "identified": 2, "draft": 3, "complete": 4}
STATUS_CAPTION = {
    "stone-only": "Name read from the stone; the records not yet searched.",
    "identified": "Identified in the records; his life not yet written.",
    "draft": "Awaiting a second reader.",
    "complete": "Checked by a second reader.",
}
NAV_SHORT = {"Life": "Life", "The records": "Records", "What we don't know": "Unknowns", "Sources": "Sources",
             "A reading of the record": "Reading", "The stone": "Stone"}


def status_bar(status, revised):
    n = STATUS_STEP.get(status, 0)
    labels = ["Stone read", "Identified", "Life drafted", "Complete"]
    segs = "".join(f'<span class="seg{" on" if i < n else ""}"></span>' for i in range(4))
    labs = "".join(f'<span class="{"cur" if i == n - 1 else ""}">{l}</span>' for i, l in enumerate(labels))
    cap = STATUS_CAPTION.get(status, "")
    rev = f" Revised {html.escape(fmt_date(revised))}." if revised else ""
    return (f'<div class="progress" role="group" aria-label="Research status: {html.escape(status)}">'
            f'<div class="segs">{segs}</div><div class="labs">{labs}</div><p class="cap">{cap}{rev}</p></div>')


def stone_card(stone_md, grid, name, prefix, where):
    """'## The stone' section -> photo + 'The stone reads' + note. Returns html (or '')."""
    if not stone_md:
        return ""
    text = "\n".join(stone_md.split("\n")[1:]).strip()
    paras = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
    transcription, note_paras = "", paras
    if paras and " / " in paras[0] and not paras[0].lower().startswith("not yet"):
        transcription, note_paras = paras[0], paras[1:]
    photos = sorted(glob.glob(str(ROOT / "records" / grid / "stone*.jpg")))
    if photos:
        rel = os.path.relpath(photos[0], ROOT).replace(os.sep, "/")
        img = (f'<a href="{prefix}{rel}"><img class="hero" src="{prefix}{rel}" '
               f'alt="Headstone of {html.escape(name, quote=True)}, grave {grid}"></a>')
    else:
        img = '<div class="hero nophoto">No photograph of this stone yet</div>'
    carved = ""
    if transcription:
        carved = ('<p class="eyebrow">The stone reads</p><p class="carved">'
                  + "<br>".join(inline(x.strip(), prefix) for x in transcription.split(" / ")) + "</p>")
    note = render_markdown("\n\n".join(note_paras), prefix, where) if note_paras else ""
    return f'<section class="stone" id="the-stone">{img}<div class="stone-body">{carved}{note}</div></section>'


def render_stone(d, reg_by_grid, release, file_requests=None):
    meta, prefix, where = d["meta"], "../../", d["file"]
    records = set()
    raw = COMMENT_RE.sub("", d["body"])
    # Markers (editor's notes) in published text
    for m in MARKER_RE.finditer(raw):
        problem("error" if release else "warn", where, f"editor marker in text: ⟨{m.group(1)[:50]}⟩")
    for k, v in meta.items():
        if isinstance(v, str) and MARKER_RE.search(v):
            problem("error" if release else "warn", where, f"editor marker in front matter {k}")
    # Split the body: preamble (H1 + one-line subtitle), '## The stone', and the rest in order.
    parts = re.split(r"^(?=## )", raw, flags=re.M)
    pre, secs = parts[0], parts[1:]
    subtitle = " ".join(l.strip() for l in pre.split("\n") if l.strip() and not l.startswith("# "))
    stone_md, rest = None, []
    for s in secs:
        if s.lower().startswith("## the stone"):
            stone_md = s
        else:
            rest.append(s)
    body_html = render_markdown("".join(rest), prefix, where, records=records)
    # Register cross-check
    reg = reg_by_grid.get(d["grid"])
    if not reg:
        problem("error", where, f"{d['grid']} is not in register.csv")
    else:
        if reg["name_carved"].strip().upper() != str(meta.get("name_carved", "")).strip().upper():
            problem("warn", where, f"name_carved differs from register: {reg['name_carved']!r}")
        if reg["status"] != meta.get("status"):
            problem("warn", where, f"status {meta.get('status')!r} differs from register {reg['status']!r} "
                                   "(register should be updated to match the dossier)")
    name = str(meta.get("name_full") or meta.get("name_carved") or d["slug"]).strip()
    card = stone_card(stone_md, d["grid"], name, prefix, where)
    # Citations resolve?
    cited = set(re.findall(r"\[(\d+)\](?!\()", raw))
    defined = set(re.findall(r'id="src-(\d+)"', body_html))
    for n in sorted(cited - defined, key=int):
        problem("error", where, f"citation [{n}] has no Sources entry")

    title = html.escape(str(meta.get("name_carved", d["slug"])))
    status = meta.get("status", "")
    row, col = d["grid"][0], d["grid"][1:]
    head = [f'<p class="gridline"><span class="chip">{d["grid"]}</span> Row {row}, place {col}</p>',
            f"<h1>{title}</h1>",
            f'<p class="lede">{inline(subtitle, prefix)}</p>' if subtitle else "",
            status_bar(status, str(meta.get("last_revised", "")))]
    h2s = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body_html)
    nav_items = []
    for hid, t_ in h2s:
        if hid == "credits":
            continue
        label = html.unescape(re.sub("<[^>]+>", "", t_))
        nav_items.append(f'<a href="#{hid}">{html.escape(NAV_SHORT.get(label, label))}</a>')
    url = (file_requests or {}).get(d["grid"])
    if url:
        block = help_block(name, url)
        i = body_html.find('<h2 id="credits">')
        body_html = body_html[:i] + block + body_html[i:] if i >= 0 else body_html + block
        nav_items.append('<a href="#help">Help</a>')
    head.append('<nav class="jump">' + "".join(nav_items) + "</nav>")
    researchers = meta.get("researchers") or []
    if isinstance(researchers, str):
        researchers = [researchers]
    return page(str(meta.get("name_carved", d["slug"])), "\n".join(h for h in head if h) + "\n" + card + body_html, prefix,
                researchers, str(meta.get("last_revised", "")), release, kind="stone",
                path=f"stone/{d['slug']}/"), records


CHEVRON = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1E3A66" stroke-width="2.2" '
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>')
KIND_TEXT = {"s": "Stone read · not yet researched", "i": "Identified", "d": "Life drafted", "c": "Complete",
             "e": "No inscription recorded yet", "f": "Flagpole · not a grave"}
MONUMENT_AFTER = 10          # the monument stands in rows J and K, after place 10 (schematic)
MONUMENT_ROWS = ("J", "K")


def place_kind(r):
    notes = r["notes"].lower()
    if "flagpole" in notes:
        return "f"
    if not r["name_carved"] and not r["unit"]:
        return "e"
    return {"stone-only": "s", "identified": "i", "draft": "d", "complete": "c"}.get(r["status"], "s")


def render_map(rows, dossiers, release):
    prefix = "../"
    by_grid = {d["grid"]: d for d in dossiers}
    plot_path = ROOT / "site" / "plot.md"
    meta, body = parse_front_matter(plot_path.read_text(encoding="utf-8"), "site/plot.md")
    for m in MARKER_RE.finditer(COMMENT_RE.sub("", body)):
        problem("error" if release else "warn", "site/plot.md", f"editor marker in text: ⟨{m.group(1)[:50]}⟩")
    essay = render_markdown(body, prefix, "site/plot.md")

    letters = sorted({r["_row"] for r in rows}) or ["A"]
    ncol = max((r["_col"] for r in rows), default=1)
    by_rc = {(r["_row"], r["_col"]): r for r in rows}

    # --- schematic rows
    maprows = []
    for L in letters:
        cells = []
        if L == letters[-1]:                      # last row sits one place east of the others (survey sheet)
            cells.append('<span class="cell gap"></span>')
        cols = [c for (rr, c) in by_rc if rr == L]
        for n in range(1, max(cols) + 1 if cols else 1):
            if L in MONUMENT_ROWS and n == MONUMENT_AFTER + 1:
                cells += ['<span class="cell gap"></span>', '<span class="cell m"></span>',
                          '<span class="cell m"></span>', '<span class="cell gap"></span>']
            r = by_rc.get((L, n))
            k = place_kind(r) if r else "e"
            cells.append(f'<span class="cell {k}" title="{L}{n}"></span>')
        maprows.append(f'<div class="maprow" data-row="{L}"><span class="maplabel">{L}</span>'
                       f'<div class="cells">{"".join(cells)}</div></div>')

    # --- chips and per-row lists
    chips = "".join(f'<button type="button" class="rowchip" data-row="{L}" aria-pressed="false">{L}</button>' for L in letters)
    lists = []
    for L in letters:
        rr = sorted((r for r in rows if r["_row"] == L), key=lambda r: r["_col"])
        total = sum(1 for r in rr if place_kind(r) != "f")
        ident = sum(1 for r in rr if place_kind(r) in "idc")
        items = []
        for r in rr:
            k = place_kind(r)
            code = r["grid"]
            d = by_grid.get(code)
            if r["name_carved"]:
                nm, cls = html.escape(r["name_carved"]), "name"
            elif k == "f":
                nm, cls = "Flagpole", "name unnamed"
            elif r["unit"]:
                nm, cls = html.escape(r["unit"]) + " · name not yet read", "name unnamed"
            else:
                nm, cls = "Stone not yet read", "name unnamed"
            st = KIND_TEXT[k]
            inner = (f'<span class="code">{code}</span><span class="what"><span class="{cls}">{nm}</span>'
                     f'<span class="st">{st}</span></span>')
            if d:
                items.append(f'<a class="place linked" href="../stone/{d["slug"]}/index.html">{inner}{CHEVRON}</a>')
            else:
                items.append(f'<div class="place">{inner}</div>')
        lists.append(f'<div class="rowlist" data-row="{L}" hidden><div class="rowhead"><h2>Row {L}</h2>'
                     f'<span>{total} places · {ident} identified</span></div>{"".join(items)}</div>')

    n_named = sum(1 for r in rows if r["name_carved"])
    n_ident = sum(1 for r in rows if place_kind(r) in "idc")
    intro = f"""
<h1>{html.escape(str(meta.get("title", "The Prescott Post lot")))}</h1>
<div class="essay" id="about">
"""
    head = f"""
</div>
<h2 id="rows">The lot, row by row</h2>
<p class="lede">The lot is on a slope. Row A is at the top; the rows run downhill from there. Pick a row to see its stones.</p>
<div class="lotmap">
  <div class="compass"><span>West · 1</span><b>Uphill ↑</b><span>{ncol} · East</span></div>
  {"".join(maprows)}
  <p class="note">Schematic: places in order, not to scale. The monument stands in rows J and K; its exact place among their stones is still being fixed. {len(rows)} positions surveyed; {n_named} names read; {n_ident} men identified; {len(dossiers)} pages.</p>
</div>
<div class="legend"><span><i class="cell s"></i>Stone read</span><span><i class="cell i"></i>Identified</span><span><i class="cell d"></i>Life drafted</span><span><i class="cell c"></i>Complete</span><span><i class="cell e"></i>Not yet read</span><span><i class="cell m"></i>Monument</span><span><i class="cell f"></i>Flagpole</span></div>
<div class="chooser"><p class="eyebrow">Choose a row</p><div class="chips">{chips}</div></div>
{"".join(lists)}
"""
    script = """
<script>
(function(){
  function pick(L){
    document.querySelectorAll('.rowchip').forEach(function(b){ b.setAttribute('aria-pressed', b.dataset.row===L); });
    document.querySelectorAll('.rowlist').forEach(function(d){ d.hidden = d.dataset.row!==L; });
    document.querySelectorAll('.maprow').forEach(function(r){ r.classList.toggle('on', r.dataset.row===L); });
    try { history.replaceState(null, '', '#row-'+L); } catch(e){}
  }
  document.querySelectorAll('.rowchip').forEach(function(b){ b.addEventListener('click', function(){ pick(b.dataset.row); }); });
  document.querySelectorAll('.maprow').forEach(function(r){ r.addEventListener('click', function(){ pick(r.dataset.row); }); });
  var m = (location.hash||'').match(/^#row-([A-Z])$/);
  pick(m && document.querySelector('.rowlist[data-row="'+m[1]+'"]') ? m[1] : 'A');
})();
</script>"""
    researchers = meta.get("researchers") or []
    if isinstance(researchers, str):
        researchers = [researchers]
    # The essay's Sources belong after the map, so the map is not separated from the text by the notes.
    cut = essay.find('<h2 id="sources">')
    essay_text, essay_sources = (essay[:cut], essay[cut:]) if cut >= 0 else (essay, "")
    if essay_sources:
        essay_sources = '<div class="essay">' + essay_sources + "</div>"
    return page("Plot map", intro + essay_text + head + essay_sources + script, prefix, researchers,
                str(meta.get("last_revised", "")), release, kind="map", path="map/")




# ----------------------------------------------------------------------------
# How-to-help page
# ----------------------------------------------------------------------------


def photo_lists(rows, dossiers, redo_spec):
    """From the register (+ the help page's hand-kept redo list): (counts_html, wanted_html, redo_html)."""
    by_grid = {d["grid"]: d for d in dossiers}
    reg = {r["grid"]: r for r in rows}
    photographed = {r["grid"] for r in rows if "stone photographed" in r["notes"]}
    named = [r for r in rows if r["name_carved"]]
    unread = [r for r in rows if not r["name_carved"] and r["status"] == "stone-only"]
    sunk = [r for r in rows if not r["name_carved"] and "sunk" in r["notes"]]
    wanted = [r for r in named if r["grid"] not in photographed]

    def item(r, extra=""):
        label = html.escape(f'{r["grid"]} — {r["name_carved"]}')
        d = by_grid.get(r["grid"])
        link = f'<a href="../stone/{d["slug"]}/index.html">{label}</a>' if d else label
        return f"<li>{link}{(' <small>' + html.escape(extra) + '</small>') if extra else ''}</li>"

    redo_items = []
    for spec in redo_spec or []:
        grid, _, reason = str(spec).partition(" — ")
        grid = grid.strip()
        if grid not in reg:
            problem("warn", "site/help.md", f"redo: {grid} is not in the register")
            continue
        redo_items.append(item(reg[grid], reason.strip()))

    sunk_txt = ""
    if sunk:
        sunk_txt = (f" {len(sunk)} markers ({', '.join(r['grid'] for r in sunk)}) are sunk with no inscription read at all; "
                    f"photograph them as they are and tell us how far they are buried.")
    counts = (f"<p>The lot has {len(rows)} surveyed positions. We have read a name on {len(named)} stones and photographed "
              f"{len(photographed)} of them. <b>About {len(unread)} stones have not been read at all</b> — most were recorded "
              f"only by the state of service carved at the top. A clear photograph of any one of them, with its grid position, "
              f"is new knowledge.{sunk_txt}</p>")
    wanted_html = "<ul class=\"cols\">" + "".join(item(r) for r in wanted) + "</ul>" if wanted else "<p>None at present.</p>"
    redo_html = "<ul>" + "".join(redo_items) + "</ul>" if redo_items else "<p>None at present.</p>"
    return counts, wanted_html, redo_html


def render_help(rows, dossiers, file_requests, release):
    prefix = "../"
    path = ROOT / "site" / "help.md"
    if not path.exists():
        return None
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"), "site/help.md")
    for m in MARKER_RE.finditer(COMMENT_RE.sub("", body)):
        problem("error" if release else "warn", "site/help.md", f"editor marker in text: ⟨{m.group(1)[:50]}⟩")
    counts, wanted, redo = photo_lists(rows, dossiers, meta.get("redo"))
    url = str(meta.get("photo_request_url", "")).strip()
    button = (f'<p><a class="button" href="{html.escape(url)}" rel="noopener">Upload stone photographs</a></p>'
              if url else "")
    with_req = [d for d in dossiers if d["grid"] in file_requests]
    pages = ("<ul class=\"cols\">" + "".join(
        f'<li><a href="../stone/{d["slug"]}/index.html">{html.escape(d["grid"])} — {html.escape(str(d["meta"].get("name_carved", d["slug"])))}</a></li>'
        for d in sorted(with_req, key=lambda d: (d["grid"][0], int(d["grid"][1:])))) + "</ul>")
    fills = {"{{photo_counts}}": counts, "{{photo_wanted}}": wanted, "{{photo_redo}}": redo,
             "{{photo_button}}": button, "{{pages_with_requests}}": pages}
    html_body = f'<h1>{html.escape(str(meta.get("title", "How to help")))}</h1>' + render_markdown(body, prefix, "site/help.md")
    for k, v in fills.items():
        html_body = html_body.replace(f"<p>{k}</p>", v).replace(k, v)
    researchers = meta.get("researchers") or []
    if isinstance(researchers, str):
        researchers = [researchers]
    return page(str(meta.get("title", "How to help")), html_body, prefix, researchers,
                str(meta.get("last_revised", "")), release, kind="help", path="help/")

def render_site_pages(out, release):
    """Any site/*.md other than plot.md and help.md becomes a plain page at its front-matter slug."""
    for path in sorted((ROOT / "site").glob("*.md")):
        if path.name in ("plot.md", "help.md"):
            continue
        where = f"site/{path.name}"
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), where)
        for m in MARKER_RE.finditer(COMMENT_RE.sub("", body)):
            problem("error" if release else "warn", where, f"editor marker in text: ⟨{m.group(1)[:50]}⟩")
        slug = str(meta.get("slug", "/" + path.stem + "/")).strip("/")
        if not slug:
            problem("error", where, "slug is empty")
            continue
        prefix = "../" * (slug.count("/") + 1)
        html_body = f'<h1>{html.escape(str(meta.get("title", path.stem)))}</h1>' + render_markdown(body, prefix, where)
        researchers = meta.get("researchers") or []
        if isinstance(researchers, str):
            researchers = [researchers]
        dest = out / slug
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "index.html").write_text(
            page(str(meta.get("title", path.stem)), html_body, prefix, researchers,
                 str(meta.get("last_revised", "")), release, kind="help", path=slug + "/"), encoding="utf-8")


# ----------------------------------------------------------------------------
# Link check
# ----------------------------------------------------------------------------

def check_links(out):
    for p in out.rglob("*.html"):
        text = re.sub(r"<script>.*?</script>", "", p.read_text(encoding="utf-8"), flags=re.S)
        for m in re.finditer(r'(?:href|src)="([^"#]+)(#[^"]*)?"', text):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            target = (p.parent / href).resolve()
            if not target.exists():
                problem("error", str(p.relative_to(out)), f"broken link: {href}")
        for m in re.finditer(r'href="#([^"]+)"', text):
            if f'id="{m.group(1)}"' not in text:
                problem("error", str(p.relative_to(out)), f"anchor #{m.group(1)} not on page")


# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="_site", help="output directory (default _site)")
    ap.add_argument("--release", action="store_true", help="strict build: editor markers and warnings become errors")
    args = ap.parse_args()
    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    (out / "map").mkdir()
    (out / "assets" / "style.css").write_text(STYLE.strip() + "\n", encoding="utf-8")
    shutil.copy(ROOT / "register.csv", out / "register.csv")

    rows = load_register()
    reg_by_grid = {r["grid"]: r for r in rows}
    dossiers = load_dossiers()
    file_requests = load_file_requests()
    for grid in sorted(set(file_requests) - {d["grid"] for d in dossiers}):
        if not grid.startswith("_"):      # rows beginning "_" are general requests (e.g. _photos), not stones
            problem("warn", "file-requests.csv", f"{grid}: open request but no dossier page to show it on")

    hosted = set()
    for d in dossiers:
        html_text, records = render_stone(d, reg_by_grid, args.release, file_requests)
        dest = out / "stone" / d["slug"]
        dest.mkdir(parents=True)
        (dest / "index.html").write_text(html_text, encoding="utf-8")
        hosted |= records
    # Photographs of stones not yet matched to a grid position are shown on the help page.
    # ...and records that belong to site pages rather than stones live in records/_<name>/.
    for p in sorted((ROOT / "records").glob("_*/*")):
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".pdf"):
            hosted.add(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    for rel in sorted(hosted):
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dest)
    # Pages whose address changed (grid renumbering). Old address -> new slug. Keep these forever: QR codes may carry them.
    for old, new in {"E24-hammond": "E25-hammond"}.items():
        d = out / "stone" / old
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Moved</title>'
            f'<meta http-equiv="refresh" content="0; url=../{new}/"><link rel="canonical" href="../{new}/"></head>'
            f'<body><p>This page has moved to <a href="../{new}/">../{new}/</a>.</p></body></html>', encoding="utf-8")
    (out / "map" / "index.html").write_text(render_map(rows, dossiers, args.release), encoding="utf-8")
    render_site_pages(out, args.release)
    help_html = render_help(rows, dossiers, file_requests, args.release)
    if help_html:
        (out / "help").mkdir()
        (out / "help" / "index.html").write_text(help_html, encoding="utf-8")
    (out / "index.html").write_text(
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<title>{SITE_NAME}</title><meta http-equiv="refresh" content="0; url=map/index.html">'
        '</head><body><a href="map/index.html">Plot map</a></body></html>\n', encoding="utf-8")

    check_links(out)

    errors = [p for p in PROBLEMS if p[0] == "error"]
    warns = [p for p in PROBLEMS if p[0] == "warn"]
    print(f"built {len(dossiers)} stone page(s), 1 map, {len(hosted)} hosted record(s) -> {out}")
    for sev, where, msg in PROBLEMS:
        print(f"  {sev.upper():5} {where}: {msg}")
    print(f"{len(errors)} error(s), {len(warns)} warning(s)")
    if errors or (args.release and warns):
        sys.exit(1)


if __name__ == "__main__":
    main()
