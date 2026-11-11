# Emblems

One flag per stone page, faded in from the right behind the grid line and the name (the treatment of the
vfw4651.org home page). Read from the dossier's `unit` field (see `unit_states()` in `build.py`):

- **Sailors:** the First Navy Jack (`USN.svg`): thirteen red and white stripes, an uncoiled rattlesnake,
  DONT TREAD ON ME. The editor's choice of emblem for the Navy men. It is not the jack the Navy flew in 1865
  (the blue union with its stars); it is the 1776 design as revived by the Navy in 2002. Drawn for this
  project by `tools/emblems.py`.
- **State regiments:** the current flag of the state. The 8th and 11th U.S. Colored Heavy Artillery are the
  14th Rhode Island Heavy Artillery (Colored) under later designations and get Rhode Island's.
- **Any other unit** (U.S. regulars, U.S. Colored Troops, U.S. Volunteers): the national colors as of
  April 1865 (`US.svg`). Thirteen stripes and 35 stars: the 35-star flag was official from July 4, 1863
  (West Virginia) to July 4, 1865, when Nevada's star was added. No star pattern was fixed until 1912; five
  rows of seven is one common 35-star arrangement. Drawn by `tools/emblems.py`.

Pages with no unit read yet carry no flag. A dossier can set `emblem: XX` or `emblem: none` in its front
matter to override what the unit field gives.

## State flags

These are the **current official state flags**, not the colors the regiments carried. Most were adopted after
the war (Rhode Island's, for example, in 1897). They mark the state the regiment belonged to and claim nothing more.

All twelve are public domain. Source SVGs: Wikimedia Commons, via the curated set in
github.com/Mo-Ibra/us-state-flag-icons (`flags/`, with per-file license metadata in `flags/credits.json`).
Rendered on 11 Nov. 2026 to 320 px tall with `rsvg-convert -h 320 <XX>.svg`, then saved as WebP at quality 72
(5–17 KB each, against up to 600 KB for the source SVG).

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
