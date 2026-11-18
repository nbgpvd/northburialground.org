# Emblems

One flag per stone page, faded in from the right behind the grid line and the name (the treatment of the
vfw4651.org home page). Read from the dossier's `unit` field (see `unit_states()` in `build.py`):

- **Sailors:** the First Navy Jack (`USN.svg`), the Naval jack of the United States as flown 2002–2019:
  thirteen stripes, the uncoiled rattlesnake, DONT TREAD ON ME. The editor's choice of emblem for the Navy men;
  it is not the jack of 1865 (the blue union with its stars). Source: U.S. Navy, Naval Historical Center;
  vectorization by User:Denelson83. Public domain. https://commons.wikimedia.org/w/index.php?curid=79399559
- **State regiments:** the current flag of the state. The 8th and 11th U.S. Colored Heavy Artillery are the
  14th Rhode Island Heavy Artillery (Colored) under later designations and get Rhode Island's.
- **Federal cavalry** (U.S. regular cavalry and U.S. Colored Cavalry, where no state flag applies): the
  company guidon of the U.S. cavalry (`USCAV.svg`). War Department General Orders No. 4, January 18, 1862,
  ordered that "guidons and camp colors will be made like the United States flag with stars and stripes"; the
  swallow-tailed form of the 1834 regulations was kept, 27 × 41 inches with a 15-inch swallowtail, and the stars
  were commonly gilt, in two concentric circles with one star in each corner of the canton. Drawn here with
  35 stars (21 and 10, plus the four corners) to match the national colors of April 1865; the star count and
  arrangement varied in practice. Drawn by `tools/emblems.py`. Source for the pattern: Flags of the World,
  "Army – Cavalry Guidons (U.S.)," https://www.crwflags.com/fotw/flags/us%5Ecav.html (accessed 17 Nov 2026).
  As of 17 Nov 2026: B3 Moseley (1st U.S. Cavalry), B12 Walker (2nd U.S. Cavalry). J15 Parker (5th U.S. Colored
  Cavalry) keeps Kentucky's flag and D14 White (2nd U.S. Colored Cavalry) Virginia's, by the editor's decisions below.
- **Any other unit** (U.S. regulars, U.S. Colored Troops, U.S. Volunteers): the national colors as of
  April 1865 (`US.svg`). Thirteen stripes and 35 stars: the 35-star flag was official from July 4, 1863
  (West Virginia) to July 4, 1865, when Nevada's star was added. No star pattern was fixed until 1912; five
  rows of seven is one common 35-star arrangement. Drawn by `tools/emblems.py`.

- **State origin of a USCT regiment, by the editor's decision:** where a U.S. Colored Troops regiment began
  under a state designation, or was raised by a state, the page carries that state's flag, set by `emblem:`
  in the dossier and explained in a cited sentence in the man's Life section. As of 11 Nov 2026:
  37th USCI (from the 3rd North Carolina Colored Infantry; C5), 54th USCI (from the 2nd Arkansas Infantry,
  African Descent; M11), 117th USCI (organized at Covington, Ky.; the stone carves "Ken."; M20), 28th USCI
  (raised by the State of Indiana; D15), 5th U.S. Colored Cavalry (organized at Camp Nelson, Ky.; J15).
  Extended 17 Nov 2026 to the state where the regiment was organized (Dyer):
  - Maryland: 9th USCI (Camp Stanton, Benedict; H15) and 39th USCI (Baltimore; M23), both raised as
    Maryland Volunteers (Wilmer et al., *History and Roster of Maryland Volunteers*, vol. 2, 1899).
  - New York: 20th and 26th USCI (Riker's Island; D9, M15) and 31st USCI (Hart's Island; K2). This reverses
    the 11 Nov hold. The 20th and 26th were raised by the Union League Club, not the state. K2 is to be
    revisited if his service record shows a 30th Connecticut enlistment.
  - Pennsylvania: 3rd USCI (Camp William Penn; N2, I2) and 45th USCI (Philadelphia; I9).
  - Virginia: 2nd USCI (Arlington; A19, C24), 23rd USCI (Camp Casey; D8, G2, J4) and 2nd U.S. Colored
    Cavalry (Fort Monroe; D14). The Virginia flag was adopted in 1861. Used by the editor's decision.
  - Kept national: 1st USCI (organized in the District of Columbia; C14, I21, K6, M10).
  - M11's page notes that the star above ARKANSAS on the 1924 flag commemorates the Confederacy, citing
    the state's flag law.
- **Native state, by the editor's decision:** where a man served in a federal unit and a record documents
  his birth in a Southern state, the page may carry that state's flag instead of the national colors, set by
  `emblem:` in the dossier with the record cited beside it. First case: A9 Isaac Grandy, 38th U.S. Colored
  Infantry, born Camden County, N.C. (CMSR descriptive book and later records), North Carolina; set with the
  knowledge and consent of living descendants personally known to the researcher.

Pages with no unit read yet carry no flag. A dossier can set `emblem: XX` or `emblem: none` in its front
matter to override what the unit field gives.

## State flags

These are the **current official state flags**, not the colors the regiments carried. Most were adopted after
the war (Rhode Island's, for example, in 1897). They mark the state the regiment belonged to and claim nothing more.

All are public domain. Source SVGs: Wikimedia Commons, via the curated set in
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
| NC | https://commons.wikimedia.org/wiki/File:Flag_of_North_Carolina.svg |
| MD | https://commons.wikimedia.org/wiki/File:Flag_of_Maryland.svg |
| DE | https://commons.wikimedia.org/wiki/File:Flag_of_Delaware.svg |
| AR | https://commons.wikimedia.org/wiki/File:Flag_of_Arkansas.svg |
| KY | https://commons.wikimedia.org/wiki/File:Flag_of_Kentucky.svg |
| IN | https://commons.wikimedia.org/wiki/File:Flag_of_Indiana.svg |
| VA | https://commons.wikimedia.org/wiki/File:Flag_of_Virginia.svg (rendered 17 Nov 2026 the same way, 14 KB) |

To add a state: render its flag the same way, add a row to `STATES` in `build.py`, and add it here.
