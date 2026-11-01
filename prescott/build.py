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
        if rel.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
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

def page(title, body_html, prefix, researchers, revised, release, extra_head="", kind="page", path=""):
    """path is the page's location under SITE_URL, e.g. 'stone/G3-howland/' or 'map/'."""
    canonical = f'<link rel="canonical" href="{SITE_URL}{path}">'
    banner = "" if release else (
        '<div class="banner">Prototype build — not for public release. '
        'Yellow marks are editor\'s notes still to be resolved.</div>')
    credits = ""
    if researchers:
        credits = "Research by " + html.escape(", ".join(researchers)) + ". "
    revised_txt = f" Revised {html.escape(revised)}." if revised else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {SITE_NAME}</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
{canonical}
{extra_head}
</head>
<body class="{kind}">
{banner}
<header class="site">
  <a class="home" href="{prefix}map/index.html">{SITE_NAME}</a>
  <span class="place">North Burial Ground, Providence</span>
</header>
<main>
{body_html}
</main>
<footer class="site">
  <p>{credits}{CITY_CREDIT}{revised_txt}</p>
  <p><a href="{prefix}map/index.html">Plot map</a> · <a href="{prefix}register.csv">Register (CSV)</a></p>
</footer>
</body>
</html>
"""


STYLE = """
/* Phone first, bright sun: black on white, large type, no light grey text. */
:root { --ink:#111; --paper:#fff; --rule:#444; --link:#0a3d7a; --accent:#1f3a5f;
        --stone:#e9e6df; --stone2:#cfcac0; --ident:#8aa6c9; --page:#1f3a5f; --todo:#ffe66d; }
* { box-sizing:border-box; }
html { font-size:112.5%; }
body { margin:0; background:var(--paper); color:var(--ink);
       font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height:1.5; }
main { max-width:40rem; margin:0 auto; padding:0 1rem 2rem; }
h1, h2, h3 { font-family: Georgia, "Times New Roman", serif; line-height:1.15; color:var(--ink); }
h1 { font-size:1.9rem; margin:.6rem 0 .2rem; letter-spacing:.01em; }
h2 { font-size:1.3rem; margin:1.8rem 0 .5rem; border-bottom:2px solid var(--rule); padding-bottom:.2rem; }
p { margin:.6rem 0; }
a { color:var(--link); }
a.cite { text-decoration:none; font-size:.8em; vertical-align:super; line-height:0; padding:0 .05em; }
mark.todo { background:var(--todo); color:var(--ink); padding:0 .15em; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size:.9em; }
header.site { display:flex; flex-wrap:wrap; gap:.25rem 1rem; align-items:baseline; justify-content:space-between;
              max-width:40rem; margin:0 auto; padding:.7rem 1rem; border-bottom:3px solid var(--ink); }
header.site .home { font-family:Georgia, serif; font-weight:bold; text-decoration:none; color:var(--ink); }
header.site .place { font-size:.9rem; }
footer.site { max-width:40rem; margin:2rem auto 0; padding:1rem; border-top:3px solid var(--ink); font-size:.9rem; }
.banner { background:var(--todo); color:var(--ink); text-align:center; padding:.4rem 1rem; font-size:.9rem; }
.lede { font-size:1.05rem; margin:.2rem 0 .8rem; }
.grid-ref { display:inline-block; font-family:ui-monospace, Menlo, monospace; background:var(--ink); color:#fff;
            padding:.1rem .45rem; border-radius:.2rem; font-size:.95rem; }
.status { font-size:.9rem; border-left:4px solid var(--rule); padding:.3rem .6rem; margin:.8rem 0; background:#f3f1ec; }
.status b { text-transform:capitalize; }
section.help { margin:1.6rem 0; padding:.9rem 1rem; border:1px solid var(--rule); background:#f3f1ec; }
section.help h2 { margin-top:0; }
a.button { display:inline-block; padding:.6rem 1rem; border:1px solid currentColor; border-radius:4px; text-decoration:none; font-weight:600; }
nav.jump { display:flex; flex-wrap:wrap; gap:.3rem .9rem; font-size:.95rem; margin:.4rem 0 1rem; }
nav.jump a { white-space:nowrap; }
ul.records { list-style:none; padding:0; }
ul.records li.record { margin:0 0 1.2rem; }
ul.records li.missing { margin:.4rem 0; }
ul.records .path { font-family:ui-monospace, Menlo, monospace; font-size:.85em; }
ul.records .note { font-style:italic; }
figure { margin:0; }
figure img { width:100%; height:auto; border:1px solid var(--rule); display:block; }
figcaption { font-size:.9rem; margin-top:.3rem; }
ol.sources { padding-left:1.6rem; font-size:.95rem; }
ol.sources li { margin:.4rem 0; }
ol.sources li:target { background:var(--todo); }
/* map */
.mapwrap { overflow-x:auto; -webkit-overflow-scrolling:touch; border:1px solid var(--rule); margin:.6rem 0; }
svg.plot { display:block; min-width:640px; width:100%; height:auto; font-family:ui-monospace, Menlo, monospace; }
svg.plot .cell { stroke:var(--rule); stroke-width:1; }
svg.plot .blank { fill:#fff; stroke:#999; }
svg.plot .stone-only { fill:var(--stone); }
svg.plot .named { fill:var(--stone2); }
svg.plot .identified { fill:var(--ident); }
svg.plot .page { fill:var(--page); }
svg.plot a .page { cursor:pointer; }
svg.plot .flagpole { fill:var(--ink); }
svg.plot .lbl { font-size:11px; fill:var(--ink); }
svg.plot .here { stroke:#c00; stroke-width:3; fill:none; }
.legend { display:flex; flex-wrap:wrap; gap:.4rem 1rem; font-size:.9rem; margin:.3rem 0 .6rem; }
.legend span::before { content:""; display:inline-block; width:.9em; height:.9em; border:1px solid var(--rule);
                       margin-right:.35em; vertical-align:-.1em; }
.legend .l-page::before { background:var(--page); } .legend .l-ident::before { background:var(--ident); }
.legend .l-named::before { background:var(--stone2); } .legend .l-stone::before { background:var(--stone); }
.legend .l-blank::before { background:#fff; }
#picked { min-height:3.2rem; border:1px solid var(--rule); padding:.5rem .7rem; margin:.4rem 0 1rem; background:#f3f1ec; }
#picked b { font-family:Georgia, serif; }
ul.pages { padding-left:1.2rem; }
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


def render_stone(d, reg_by_grid, release, file_requests=None):
    meta, prefix, where = d["meta"], "../../", d["file"]
    records = set()
    body_html = render_markdown(d["body"], prefix, where, records=records)
    # Markers (editor's notes) in published text
    for m in MARKER_RE.finditer(COMMENT_RE.sub("", d["body"])):
        problem("error" if release else "warn", where, f"editor marker in text: ⟨{m.group(1)[:50]}⟩")
    for k, v in meta.items():
        if isinstance(v, str) and MARKER_RE.search(v):
            problem("error" if release else "warn", where, f"editor marker in front matter {k}")
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
    # Citations resolve?
    cited = set(re.findall(r"\[(\d+)\](?!\()", COMMENT_RE.sub("", d["body"])))
    defined = set(re.findall(r'id="src-(\d+)"', body_html))
    for n in sorted(cited - defined, key=int):
        problem("error", where, f"citation [{n}] has no Sources entry")

    title = html.escape(str(meta.get("name_carved", d["slug"])))
    status = meta.get("status", "")
    gloss = STATUS_GLOSS.get(status, "")
    head = [f'<p class="lede"><span class="grid-ref">{d["grid"]}</span></p>',
            f"<h1>{title}</h1>"]
    # First paragraph of the body is the one-line subtitle; render_markdown already emitted it.
    head.append(f'<div class="status">Research status: <b>{html.escape(status)}</b> — {html.escape(gloss)}.</div>')
    short = {"The records": "Records", "What we don't know": "Not known", "A reading of the record": "Reading"}
    h2s = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body_html)
    head.append('<nav class="jump">' + "".join(
        f'<a href="#{hid}">{html.escape(short.get(html.unescape(re.sub("<[^>]+>", "", t)), html.unescape(re.sub("<[^>]+>", "", t))))}</a>'
        for hid, t in h2s if hid != "credits") + "</nav>")
    researchers = meta.get("researchers") or []
    if isinstance(researchers, str):
        researchers = [researchers]
    url = (file_requests or {}).get(d["grid"])
    if url:
        # Insert before the Credits heading so the ask sits with the open questions, not after the footer line.
        name = str(meta.get("name_full") or meta.get("name_carved") or d["slug"]).strip()
        block = help_block(name, url)
        i = body_html.find('<h2 id="credits">')
        body_html = body_html[:i] + block + body_html[i:] if i >= 0 else body_html + block
        head[-1] = head[-1].replace("</nav>", '<a href="#help">Help</a></nav>')
    return page(str(meta.get("name_carved", d["slug"])), "\n".join(head) + "\n" + body_html, prefix,
                researchers, str(meta.get("last_revised", "")), release, kind="stone",
                path=f"stone/{d['slug']}/"), records


def render_map(rows, dossiers, release):
    prefix = "../"
    by_slug = {d["grid"]: d for d in dossiers}
    plot_path = ROOT / "site" / "plot.md"
    meta, body = parse_front_matter(plot_path.read_text(encoding="utf-8"), "site/plot.md")
    for m in MARKER_RE.finditer(COMMENT_RE.sub("", body)):
        problem("error" if release else "warn", "site/plot.md", f"editor marker in text: ⟨{m.group(1)[:50]}⟩")
    essay = render_markdown(body, prefix, "site/plot.md")

    # --- SVG grid. A1 top-left; letters are rows, numbers are columns.
    letters = sorted({r["_row"] for r in rows}) or ["A"]   # an empty register still builds
    ncol = max((r["_col"] for r in rows), default=1)
    cw, ch, left, top = 24, 28, 28, 22
    W, H = left + ncol * cw + 6, top + len(letters) * ch + 6
    svg = [f'<svg class="plot" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="Plan of the Prescott Post lot, rows A to {letters[-1]}, columns 1 to {ncol}">']
    for c in range(1, ncol + 1):
        svg.append(f'<text class="lbl" x="{left + (c - 1) * cw + cw / 2:.0f}" y="14" text-anchor="middle">{c}</text>')
    for ri, L in enumerate(letters):
        svg.append(f'<text class="lbl" x="10" y="{top + ri * ch + ch / 2 + 4:.0f}" text-anchor="middle">{L}</text>')
    for r in rows:
        ri = letters.index(r["_row"])
        x, y = left + (r["_col"] - 1) * cw + 2, top + ri * ch + 2
        w, h = cw - 4, ch - 4
        note = r["notes"].lower()
        d = by_slug.get(r["grid"])
        if "flagpole" in note:
            svg.append(f'<circle class="flagpole" cx="{x + w / 2}" cy="{y + h / 2}" r="5"><title>{r["grid"]}: flagpole</title></circle>')
            continue
        if d:
            cls = "page"
        elif r["status"] == "identified":
            cls = "identified"
        elif r["name_carved"]:
            cls = "named"
        elif r["status"] == "stone-only":
            cls = "stone-only"
        else:
            cls = "blank"
        label = r["name_carved"] or (r["unit"] and f"stone reads: {r['unit']}") or "not yet transcribed"
        detail = " · ".join(x for x in [r["unit"] if r["name_carved"] else "", f"Co. {r['company']}" if r["company"] else "",
                                        r["rank"], f"d. {r['died']}" if r["died"] else ""] if x)
        data = (f'data-grid="{r["grid"]}" data-name="{html.escape(label, quote=True)}" '
                f'data-detail="{html.escape(detail, quote=True)}" data-status="{r["status"]}"')
        rect = (f'<rect class="cell {cls}" {data} x="{x}" y="{y}" width="{w}" height="{h}" rx="2">'
                f'<title>{r["grid"]}: {html.escape(label)}</title></rect>')
        if d:
            svg.append(f'<a href="{prefix}stone/{d["slug"]}/index.html">{rect}</a>')
        else:
            svg.append(rect)
    svg.append("</svg>")

    pages_list = "".join(
        f'<li><a href="{prefix}stone/{d["slug"]}/index.html">{html.escape(str(d["meta"].get("name_carved", d["slug"])))}</a> '
        f'<span class="grid-ref">{d["grid"]}</span> — {html.escape(str(d["meta"].get("unit", "")).split(";")[0])}</li>'
        for d in sorted(dossiers, key=lambda d: (d["grid"][0], int(d["grid"][1:]))))
    n_named = sum(1 for r in rows if r["name_carved"])
    n_ident = sum(1 for r in rows if r["status"] == "identified") + len(dossiers)

    head = f"""
<h1>{html.escape(str(meta.get("title", "The Prescott Post lot")))}</h1>
<p class="lede">Find your row (letter) and column (number) on the plan. A1 is the top-left stone as you face the rows from the road. Tap a stone to see what the register has; dark stones have a page.</p>
<div class="mapwrap">{"".join(svg)}</div>
<div class="legend"><span class="l-page">has a page</span><span class="l-ident">identified</span><span class="l-named">name read</span><span class="l-stone">stone read in part</span><span class="l-blank">not yet read</span></div>
<div id="picked" aria-live="polite"><b>Tap a stone.</b> {len(rows)} positions surveyed; {n_named} names read; {n_ident} men identified; {len(dossiers)} page{"s" if len(dossiers) != 1 else ""} written.</div>
<h2 id="pages">Stones with a page</h2>
<ul class="pages">{pages_list}</ul>
"""
    script = """
<script>
(function(){
  var box=document.getElementById('picked'); if(!box) return;
  document.querySelectorAll('svg.plot rect.cell').forEach(function(r){
    r.addEventListener('click',function(ev){
      var d=r.dataset, link=r.closest('a');
      box.innerHTML='<b>'+d.grid+' — '+d.name+'</b>'+(d.detail?'<br>'+d.detail:'')+
        '<br><small>status: '+(d.status||'unsurveyed')+(link?' · <a href="'+link.getAttribute('href')+'">open page</a>':'')+'</small>';
      document.querySelectorAll('svg.plot .here').forEach(function(h){h.remove();});
      var h=document.createElementNS('http://www.w3.org/2000/svg','rect');
      ['x','y','width','height','rx'].forEach(function(a){h.setAttribute(a,r.getAttribute(a));});
      h.setAttribute('class','here'); r.parentNode.insertBefore(h, r.nextSibling);
      if(link){ ev.preventDefault(); }
    });
  });
})();
</script>"""
    researchers = meta.get("researchers") or []
    if isinstance(researchers, str):
        researchers = [researchers]
    return page(str(meta.get("title", "Plot map")), head + essay + script, prefix, researchers,
                str(meta.get("last_revised", "")), release, kind="map", path="map/")


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
        problem("warn", "file-requests.csv", f"{grid}: open request but no dossier page to show it on")

    hosted = set()
    for d in dossiers:
        html_text, records = render_stone(d, reg_by_grid, args.release, file_requests)
        dest = out / "stone" / d["slug"]
        dest.mkdir(parents=True)
        (dest / "index.html").write_text(html_text, encoding="utf-8")
        hosted |= records
    for rel in sorted(hosted):
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dest)
    (out / "map" / "index.html").write_text(render_map(rows, dossiers, args.release), encoding="utf-8")
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
