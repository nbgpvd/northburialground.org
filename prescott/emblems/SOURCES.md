# Emblems

Small flags shown under the grid chip on a stone page (see `unit_states()` in `build.py`), read from the
dossier's `unit` field:

- **National colors, April 1865** (`US.svg`) on every page that names a unit. Thirteen stripes and 35 stars:
  the 35-star flag was official from July 4, 1863 (West Virginia) to July 4, 1865, when Nevada's star was added,
  so it was the lawful flag at Appomattox. No star pattern was fixed until 1912; five rows of seven is one
  common 35-star arrangement. Drawn for this project by `tools/emblems.py`.
- **U.S. Navy union jack, 1865** (`USN.svg`) added for sailors: the blue union alone, the same 35 stars.
  Same script.
- **State flag** where the unit names a state regiment. The 8th and 11th U.S. Colored Heavy Artillery are the
  14th Rhode Island Heavy Artillery (Colored) under later designations and carry Rhode Island's.

Pages with no unit read yet carry nothing. A dossier can set `emblem: US, RI` (codes in display order) or
`emblem: none` in its front matter to override what the unit field gives.

## State flags

These are the **current official state flags**, not the colors the regiments carried. Most were adopted after
the war (Rhode Island's, for example, in 1897). They mark the state the regiment belonged to and claim nothing more.

All twelve are public domain. Source SVGs: Wikimedia Commons, via the curated set in
github.com/Mo-Ibra/us-state-flag-icons (`flags/`, with per-file license metadata in `flags/credits.json`).
Rendered to PNG at 72 px tall on 11 Nov. 2026 with `rsvg-convert -h 72 <XX>.svg -o <XX>.png`, so the page
loads about 60 KB of flags in all rather than several megabytes of SVG.

| Code | Commons file |
|---|---|
| CA | https://commons.wikimedia.org/wiki/File:Flag_of_California.svg |
| CT | https://commons.wikimedia.org/wiki/File:Flag_of_Connecticut.svg |
| IL | https://commons.wikimedia.org/wiki/File:Flag_of_Illinois.svg |
| MA | https://commons.wikimedia.org/wiki/File:Flag_of_Massachusetts.svg |
| ME | https://commons.wikimedia.org/wiki/File:Flag_of_Maine.svg |
| MI | https://commons.wikimedia.org/wiki/File:Flag_of_Michigan.svg |
| NH | https://commons.wikimedia.org/wiki/File:Flag_of_New_Hampshire.svg |
| NJ | https://commons.wikimedia.org/wiki/File:Flag_of_New_Jersey.svg |
| NY | https://commons.wikimedia.org/wiki/File:Flag_of_New_York.svg |
| PA | https://commons.wikimedia.org/wiki/File:Flag_of_Pennsylvania.svg |
| RI | https://commons.wikimedia.org/wiki/File:Flag_of_Rhode_Island.svg |
| VT | https://commons.wikimedia.org/wiki/File:Flag_of_Vermont.svg |

To add a state: render its flag the same way, add a row to `STATES` in `build.py`, and add it here.
