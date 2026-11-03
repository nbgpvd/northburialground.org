#!/usr/bin/env python3
"""ingest_photos.py -- turn a dump of headstone photos into labelled, readable files.

Two steps, so the one judgment (which frame is which stone) stays with a person
or with Claude reading the contact sheets, and everything mechanical is scripted.

  1. scan   <src_dir> --batch NAME [--out DIR]
       Reads every JPG/PNG in src_dir (originals are never modified), turns each
       upright using its EXIF orientation, sorts by time taken, and writes into
       <out>/ :
         work/S001.jpg ...     upright working copies (long edge 2000 px)
         sheets/sheet-01.jpg   contact sheets, 6 frames each, labelled S001 + time
         map.csv               one row per frame: seq, source, taken, grid, view, notes
       Fill in `grid` and `view` in map.csv (by hand or by reading the sheets).
       Leave rows blank to skip them.  Views: close, oblique, wide, orient.
       A frame showing several stones takes a range, e.g. B02-B05.
       Optional `rotate` (90, 180, 270 = degrees clockwise) turns a frame so the
       lettering runs level; worn lettering reads best that way.

  2. apply  <out>
       For each filled-in row of map.csv, writes into <out>/named/ :
         B07-close.jpg         upright, named by grid and view
         B07-close-enh.jpg     grayscale, contrast-stretched, sharpened
                               (for shallow or worn lettering)
       and appends a row to photo-log.csv beside the batch folder.
       Re-running is safe: files that already exist are skipped (use --force).

Plain Python 3 + Pillow.  Default output goes to <src_dir>/../_derived/<batch>.
"""
import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

EXTS = {".jpg", ".jpeg", ".png"}
VIEWS = {"close", "oblique", "wide", "orient"}
LONG_EDGE = 2000
SHEET_COLS, SHEET_ROWS = 3, 2
CELL_W, CELL_H = 520, 700
MAP_FIELDS = ["seq", "source", "taken", "grid", "view", "rotate", "notes"]
LOG_FIELDS = ["batch", "file", "grid", "view", "taken", "source", "enhanced", "logged"]


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def open_upright(path):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def taken_time(path):
    try:
        ex = Image.open(path).getexif()
        s = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        if s:
            return dt.datetime.strptime(str(s)[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return dt.datetime.fromtimestamp(path.stat().st_mtime)


def fit(im, long_edge):
    im = im.copy()
    im.thumbnail((long_edge, long_edge), Image.LANCZOS)
    return im


def enhance(im):
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    return g.filter(ImageFilter.UnsharpMask(radius=3, percent=200, threshold=2))


# ---------------------------------------------------------------- scan
def scan(args):
    src = Path(args.src).expanduser().resolve()
    if not src.is_dir():
        sys.exit(f"not a folder: {src}")
    out = Path(args.out).expanduser().resolve() if args.out else src.parent / "_derived" / args.batch
    map_path = out / "map.csv"
    if map_path.exists() and not args.force:
        sys.exit(f"{map_path} exists; it may hold hand-entered labels. Use --force to rebuild.")
    (out / "work").mkdir(parents=True, exist_ok=True)
    (out / "sheets").mkdir(exist_ok=True)

    found, skipped = [], []
    for p in sorted(src.iterdir()):
        if p.name.startswith("."):
            continue
        if p.suffix.lower() in EXTS:
            found.append((taken_time(p), p))
        elif p.is_file():
            skipped.append(p.name)
    found.sort(key=lambda t: (t[0], t[1].name))
    if not found:
        sys.exit("no JPG/PNG files found")

    rows, cells = [], []
    for i, (t, p) in enumerate(found, 1):
        seq = f"S{i:03d}"
        try:
            im = open_upright(p)
        except Exception as e:
            print(f"  unreadable, skipped: {p.name} ({e})")
            continue
        fit(im, LONG_EDGE).save(out / "work" / f"{seq}.jpg", quality=90)
        cells.append((seq, t, fit(im, CELL_W)))
        rows.append({"seq": seq, "source": str(p), "taken": t.isoformat(timespec="seconds"),
                     "grid": "", "view": "", "notes": ""})

    with open(map_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAP_FIELDS)
        w.writeheader()
        w.writerows(rows)

    per = SHEET_COLS * SHEET_ROWS
    lab = font(34)
    for n in range(0, len(cells), per):
        sheet = Image.new("RGB", (SHEET_COLS * CELL_W, SHEET_ROWS * CELL_H), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for k, (seq, t, th) in enumerate(cells[n:n + per]):
            cx, cy = (k % SHEET_COLS) * CELL_W, (k // SHEET_COLS) * CELL_H
            th = fit(th, CELL_H - 8)
            th.thumbnail((CELL_W - 8, CELL_H - 8))
            sheet.paste(th, (cx + (CELL_W - th.width) // 2, cy + (CELL_H - th.height) // 2))
            tag = f"{seq}  {t:%H:%M:%S}"
            d.rectangle([cx, cy, cx + 330, cy + 44], fill=(0, 0, 0))
            d.text((cx + 8, cy + 4), tag, fill=(255, 220, 80), font=lab)
        sheet.save(out / "sheets" / f"sheet-{n // per + 1:02d}.jpg", quality=85)

    print(f"{len(rows)} frames -> {out}")
    print(f"  {(len(cells) + per - 1) // per} contact sheet(s) in {out/'sheets'}")
    print(f"  fill in grid/view in {map_path}, then:  ingest_photos.py apply \"{out}\"")
    if skipped:
        print(f"  ignored non-JPG/PNG files ({len(skipped)}): {', '.join(skipped[:5])}"
              + (" ..." if len(skipped) > 5 else ""))


# ---------------------------------------------------------------- apply
def safe(s):
    return "".join(c for c in s.strip() if c.isalnum() or c in "-_").strip("-_")


def apply(args):
    out = Path(args.batch_dir).expanduser().resolve()
    map_path = out / "map.csv"
    if not map_path.exists():
        sys.exit(f"no map.csv in {out}; run scan first")
    named = out / "named"
    named.mkdir(exist_ok=True)
    log_path = out.parent / "photo-log.csv"
    new_log = not log_path.exists()

    with open(map_path, newline="") as f:
        rows = list(csv.DictReader(f))

    used, done, skipped_existing, problems = {}, [], 0, []
    log_rows = []
    for r in rows:
        grid, view = (r.get("grid") or "").strip().upper(), (r.get("view") or "").strip().lower()
        if not grid and not view:
            continue
        if view not in VIEWS or not safe(grid):
            problems.append(f"{r['seq']}: needs a grid and a view in {sorted(VIEWS)} (got '{grid}', '{view}')")
            continue
        g = safe(grid)
        base = f"{g}-{view}" if "-" not in g else f"{view}-{g}"
        used[base] = used.get(base, 0) + 1
        if used[base] > 1:
            base = f"{base}-{used[base]}"
        plain, enh = named / f"{base}.jpg", named / f"{base}-enh.jpg"
        if plain.exists() and enh.exists() and not args.force:
            skipped_existing += 1
            continue
        src = Path(r["source"])
        if not src.exists():
            problems.append(f"{r['seq']}: source missing: {src}")
            continue
        im = open_upright(src)
        try:
            rot = int((r.get("rotate") or "0").strip() or 0) % 360
            if rot not in (0, 90, 180, 270):
                raise ValueError(rot)
        except ValueError:
            problems.append(f"{r['seq']}: rotate must be 0, 90, 180 or 270 (got '{r.get('rotate')}')")
            continue
        if rot:
            im = im.rotate(-rot, expand=True)  # clockwise, so the lettering runs level
        fit(im, LONG_EDGE).save(plain, quality=90)
        fit(enhance(im), LONG_EDGE).save(enh, quality=90)
        done.append(base)
        log_rows.append({"batch": out.name, "file": f"{base}.jpg", "grid": grid, "view": view,
                         "taken": r["taken"], "source": src.name, "enhanced": f"{base}-enh.jpg",
                         "logged": dt.date.today().isoformat()})

    if log_rows:
        with open(log_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
            if new_log:
                w.writeheader()
            w.writerows(log_rows)

    print(f"wrote {len(done)} named frame(s) (+ enhanced copies) to {named}")
    if skipped_existing:
        print(f"  {skipped_existing} already existed, skipped (use --force to redo)")
    if log_rows:
        print(f"  logged in {log_path}")
    unlabelled = sum(1 for r in rows if not (r.get('grid') or '').strip() and not (r.get('view') or '').strip())
    if unlabelled:
        print(f"  {unlabelled} frame(s) left unlabelled in map.csv (skipped)")
    for p in problems:
        print("  PROBLEM:", p)
    if problems:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="make working copies, contact sheets and a blank map.csv")
    s.add_argument("src")
    s.add_argument("--batch", required=True, help="batch name, e.g. 2026-11-02-row-B")
    s.add_argument("--out", help="output folder (default <src>/../_derived/<batch>)")
    s.add_argument("--force", action="store_true", help="rebuild even if map.csv exists")
    s.set_defaults(fn=scan)
    a = sub.add_parser("apply", help="name and enhance the frames labelled in map.csv")
    a.add_argument("batch_dir")
    a.add_argument("--force", action="store_true", help="redo files that already exist")
    a.set_defaults(fn=apply)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
