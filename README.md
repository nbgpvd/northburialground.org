# northburialground.org

Source for **northburialground.org**, the website of the North Burial Ground Foundation
(in formation), Providence, Rhode Island, and home of the **Prescott Post Digital Companion**
at `/prescott/`.

## Layout

| Path | What it is |
|---|---|
| `root/` | The foundation's landing page(s), copied verbatim to the site root |
| `prescott/` | The Prescott Post Digital Companion: `build.py`, `register.csv`, `veterans/`, `records/`, `site/` |
| `CNAME` | The custom domain for GitHub Pages — do not remove |
| `.github/workflows/pages.yml` | Builds the site and deploys it to GitHub Pages on every push to `main` |

## Build locally

    python3 prescott/build.py              # prototype build into prescott/_site/
    python3 prescott/build.py --release    # strict build; fails on editor markers, uncaptioned records, broken links

Standard library only. No database. Anyone with this repo can rebuild the site with one command.

## URLs are permanent

QR codes at the plot point to `https://northburialground.org/prescott/stone/<GRID>-<surname>/`.
Do not rename a published stone page or change the grid scheme without a redirect.

## Ownership

The domain is registered at Squarespace (10-year term, renews October 2036) and this
organization (`nbgpvd`) holds the code. Both are to pass to the North Burial Ground Foundation
once it is incorporated. Research and editorial decisions: Bernard Brennan, investigator and
editor of record. Records courtesy of the City of Providence, Department of Parks, North Burial Ground.
