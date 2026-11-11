# State emblems

Small flags shown on a stone page when the man's unit names a state regiment (see `unit_states()` in `build.py`).
Federal units (U.S. regulars, U.S. Colored Troops, U.S. Navy) carry none. A dossier can set `emblem: RI` (or
`emblem: none`) in its front matter to override what the unit field gives.

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
