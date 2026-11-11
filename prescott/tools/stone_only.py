#!/usr/bin/env python3
"""Generate stone-only dossiers (veterans/<GRID>-<surname>.md) for photographed,
transcribed stones that have no dossier yet.

    python3 tools/stone_only.py            # writes missing dossiers only; never overwrites
    python3 tools/stone_only.py --force G2 # regenerate one (you will lose hand edits)

Every fact comes from register.csv or from the STONES table below, which was
curated from the register notes on 1 Nov 2026. A page says only what the stone,
the NPS index, Chenery (1898) and the PV001 list say. Everything else goes under
"What we don't know". Standard library only.
"""
import csv, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REV = "2026-11-11"

# grid: dict(carved=transcription as recorded (lines separated by " / "),
#            photo="IMG_xxxx", nps=..., chenery=page or None, pv001=death year or None,
#            notes=[extra bullets for What we don't know], died_text=how the stone gives the death)
STONES = {
 "A6": dict(carved="J. EDWARD BROWN / Co. E. 29 Conn. Inf / Died May 8, 1924", photo="IMG_0859",
    nps=None, nps_note="The index has several John Browns in Company E of the 29th Connecticut and no J. Edward Brown.",
    chenery=None, pv001="1924", died_text="May 8, 1924"),
 "A12": dict(carved="JAMES CHERRY / U.S. NAVY / Died Dec. 6, 1921", photo="IMG_1746",
    nps="unsearched", chenery=None, pv001="1921", died_text="December 6, 1921",
    notes=["Which ship or ships did he serve on? The Navy's enlistment rendezvous records and the NPS sailors index have not yet been searched."]),
 "A19": dict(carved="ALEXANDER JONES / Pvt. Co. G. 2 U.S. Col. Inf. / Died Jan. 11, 1927", photo="IMG_1747",
    nps="Jones, Alexander, 2nd U.S. Colored Cavalry, Company G, private in and out, microfilm M589 roll 49",
    nps_note="The stone says infantry; the only Alexander Jones the index places in Company G of a 2nd U.S. Colored regiment is in the cavalry. No Alexander Jones was found in the 2nd U.S. Colored Infantry. Which regiment he served in is unresolved.",
    chenery=None, pv001=None, died_text="January 11, 1927"),
 "B7": dict(carved="CHARLES F. QUEEN / Co. B. 102 Michigan Vol / Died July 24 1918", photo="IMG_0858",
    nps="Queen, Charles H., 102nd U.S. Colored Infantry, Company B, private in and out, microfilm M589 roll 70",
    nps_note="The 102nd U.S. Colored Infantry was raised as the 1st Michigan Colored Infantry, which explains the stone's \"102 Michigan Vol.\" The index gives his middle initial as H; the stone and the PV001 list give F.",
    chenery=None, pv001="1918", died_text="July 24, 1918"),
 "E13": dict(carved="HENRY FRAWLEY / Co. ? 4?th & 58th Mass Vol. / Died Feb. 5, 1902", photo="IMG_2600",
    nps="Frawley, Henry, 47th Massachusetts Infantry (Militia), Company C, and 58th Massachusetts Infantry, Company C (filed as Frowly), private in and out, microfilm M544 roll 14",
    nps_note="The index files him under both regiments named on the stone.",
    chenery=None, pv001="1907", died_text="February 5, 1902",
    notes=["Did he serve in both regiments, and when? The 47th was a nine-month militia regiment of 1862–63 and the 58th was raised in 1864; his service record will show whether both enlistments are his.",
           "The survey sheet had the name as \"Henry Frank\"; the photograph reads FRAWLEY. The company letter and the first regiment's number are only partly legible.",
           "The PV001 list gives his death as 1907 and adds a 7th Massachusetts; the stone reads 1902. A death in 1902 fits the dates in row F better than row E, so his grid position should be re-verified on site."]),
 "F19": dict(carved="CHARLES SNYDER / Co. A. 14th R.I.H.Art. / Died Nov. 11, 1902", photo="IMG_1208",
    nps="Snyder, Charles, 11th U.S. Colored Heavy Artillery, Company A, private in, corporal out, microfilm M589 roll 81",
    chenery="158", pv001=None, died_text="November 11, 1902"),
 "G2": dict(carved="JAMES UPSHAW / Co. H. 23d U.S. Col. Tps. / Died April 9, 1886", photo="IMG_1210",
    nps="Upshaw, James, 23rd U.S. Colored Infantry, Company H, private in and out, microfilm M589 roll 89",
    chenery=None, pv001=None, died_text="April 9, 1886"),
 "I9": dict(carved="PHILIP HARRIS / Co. A. 45th U.S. Col. Tps. / Died May 23, 18[??]", photo="IMG_1218",
    nps="Harris, Philip, 45th U.S. Colored Infantry, Company A, private in and out, microfilm M589 roll 38",
    chenery=None, pv001="1891", died_text="May 23 of a year now illegible on the stone",
    notes=["The year of death is illegible on the stone; the PV001 list gives 1891."]),
 "I21": dict(carved="CHARLES H. SMITH / Co. K. 1st U.S. Col. Inf. / Died March 9, 188[?]", photo="IMG_1219",
    nps="Smith, Charles H., 1st U.S. Colored Infantry, Company K, corporal in, private out, microfilm M589 roll 80",
    nps_note="The index has him entering as a corporal and leaving as a private; the service record will say why.",
    chenery=None, pv001=None, died_text="March 9 of a year in the 1880s, the last digit illegible"),
 "I23": dict(carved="JOHN H. BARNETT / Co. C 14th R.I.H.Art. / Died Nov. 19, 1[???]", photo="IMG_1220",
    nps="Barnett, John, 11th U.S. Colored Heavy Artillery, Company E, private in and out, microfilm M589 roll 5",
    nps_note="The stone and the PV001 list put him in Company C; the index card says Company E. The service record will settle the company.",
    chenery="195", pv001=None, died_text="November 19 of a year now illegible on the stone"),
 "J1": dict(carved="HENRY B. WILLIAMS / Co. M. 14th R.I.H.Arty. / Died Jan. 27, 1895", photo="IMG_1221",
    nps="Williams, Henry B., 11th U.S. Colored Heavy Artillery, Company M, private in, corporal out, microfilm M589 roll 95",
    chenery="258", pv001=None, died_text="January 27, 1895"),
 "J2": dict(carved="ORRIN VROMAN / Co. G. 14th R.I.H.Arty. / Died April 1[4 or 5], 1895", photo="IMG_1222",
    nps="Vroman, Orin, 11th U.S. Colored Heavy Artillery, Company G, private in and out, microfilm M589 roll 89",
    chenery="218", pv001=None, died_text="April 1895; the day reads 15 in the photograph and 14 on the survey sheet",
    notes=["Was it April 14 or April 15, 1895? Re-read the stone on site."]),
 "J4": dict(carved="MARSHALL KING / Co. A. 23d U.S. Col. T. / Died Jan. 14, 1895", photo="IMG_1223",
    nps="King, Marshal, 23rd U.S. Colored Infantry, Company A, private in and out, microfilm M589 roll 51",
    chenery=None, pv001=None, died_text="January 14, 1895"),
 "J6": dict(carved="HENRY N. WELCH / Co. G. 1st Ill. Arty. / Died Sept. 19, 1894", photo="IMG_1224",
    nps="Welch, Henry (also filed as Welsh), 1st Illinois Light Artillery, Battery G, private in and out, microfilm M539 roll 96",
    chenery=None, pv001="1894", died_text="September 19, 1894"),
 "K4": dict(carved="JOSEPH HOVEY / Co. M. 14th R.I.H.Art. / Died July 12, 1897", photo="IMG_1228",
    nps="Hovey, Joseph, 11th U.S. Colored Heavy Artillery, Company M, private in and out, microfilm M589 roll 42",
    chenery="261", pv001=None, died_text="July 12, 1897"),
 "K6": dict(carved="ROBERT S. JOHNSON / Co. K. 1st U.S. Col. Tps. / Died March 16, 1897", photo="IMG_1229",
    nps="Johnson, Robert S., 1st U.S. Colored Infantry, Company K, private in and out, microfilm M589 roll 48",
    chenery=None, pv001=None, died_text="March 16, 1897"),
 "L20": dict(carved="JOHN GIBBS / Co. D. 14th R.I.H.A. / Died Nov. 2[?], 18[??]", photo="IMG_1230",
    nps="Gibbs, John, 11th U.S. Colored Heavy Artillery, Company D, private in and out, microfilm M589 roll 32",
    chenery="187", pv001="1889", died_text="November 1889 if the PV001 list is right; the day and year are illegible on the stone"),
 "L24": dict(carved="[AM]BROSE C[LARK] / Co. M. 14th [R.I.H.Art.] / [date line below ground]", photo="IMG_1231",
    nps="Clark, Ambrose, 11th U.S. Colored Heavy Artillery, Company M, private in and out, microfilm M589 roll 17",
    chenery="259", pv001="1897", died_text="1897 according to the PV001 list; no date is visible on the stone",
    notes=["The stone is partly buried. The name is read from its visible letters and from the PV001 list and Chenery; clear the turf to confirm it and read the date line.",
           "The 1890 veterans schedule for Providence lists an Ambrose Clark of Company M, 14th R.I. Heavy Artillery, at 35 Salem Street, on the same page as Israel Jackson (C14). See the Jackson page."]),
 "M4": dict(carved="THOMAS B. BAR[BER] / Co. [?]. 14th R.I.[H.Art.] / [date line below ground]", photo="IMG_1232",
    nps="Barber, Thomas, 11th U.S. Colored Heavy Artillery, Company G, private in and out, microfilm M589 roll 5",
    chenery="213", pv001=None, died_text="a date now below ground",
    notes=["The stone is half-buried; the name and \"14th R.I.\" are legible, the company letter and date are not."]),
 "M5": dict(carved="BENJ. G. GARDINER / Co. A. 14th R.I.H.Art. / [date line not read]", photo="IMG_1233",
    nps="Gardner, Benjamin G., 11th U.S. Colored Heavy Artillery, Company A, private in and out, microfilm M589 roll 31; a second card in the same company, Gardner, Benjamin C., corporal, may be the same man or another",
    nps_note="The stone and the PV001 list spell the name Gardiner, with a G; an earlier list had \"Benjamin C. Gardner,\" which the stone rules out.",
    chenery="160", pv001="1901", died_text="1901 according to the PV001 list; the stone's date line has not been read"),
 "M8": dict(carved="JOHN H. EASTON / Co. A. 14th R.I.H.A[rt.] / [lower line weathered]", photo="IMG_1234",
    nps="Easton, John, 11th U.S. Colored Heavy Artillery, Company A, two cards: one as musician in and out, the other (filed as John H.) as private; microfilm M589 roll 26",
    chenery="160", pv001="1901", died_text="1901 according to the PV001 list; the stone's lower line is weathered",
    notes=["Was he a musician? One of the two index cards says so; the service record will show whether both cards are his."]),
 "M10": dict(carved="EDW. CRUTCHFIELD / Co. K. 1st U.S.C.Tro[ops] / [no date line visible]", photo="IMG_1235",
    nps="Crutchfield, Edmond, 1st U.S. Colored Infantry, Company K, private in and out, microfilm M589 roll 20",
    nps_note="The stone abbreviates the given name EDW. and the PV001 list gives Edward; the index card gives Edmond. The service record will say which he answered to.",
    chenery=None, pv001="1901", died_text="1901 according to the PV001 list; no date line is visible on the stone"),
 "M11": dict(carved="WILLIAM W. WALLEY / Co. I. 54th U.S.C.Troops / [date line not read]", photo="IMG_1236",
    nps=None, nps_note="No William Walley or Whalley was found in the index for the 54th U.S. Colored Infantry; the spelling on his service record may differ.",
    chenery=None, pv001="1901", died_text="1901 according to the PV001 list; the stone's date line has not been read"),
 "M15": dict(carved="WILLIAM WALKER / Co. I. 26th U.S.C.[T.] / Died May 8, 190[?]", photo="IMG_1237",
    nps="Walker, William, 26th U.S. Colored Infantry, Company I, private in and out, microfilm M589 roll 90",
    chenery=None, pv001="1900", died_text="May 8 of a year in the 1900s, the last digit illegible; the PV001 list gives 1900"),
 "M20": dict(carved="DENNIS D. BURGESS / Co. I. 117th Ken. Col. T[ps]. / Died July 16 1899", photo="IMG_1238",
    nps=None, nps_note="The stone's \"117th Ken. Col. Tps.\" is the 117th U.S. Colored Infantry, raised in Kentucky. No Dennis Burgess was found in the index for that regiment; the spelling on his service record may differ.",
    chenery=None, pv001="1899", died_text="July 16, 1899"),
 "M23": dict(carved="JAMES B. BERRY / Co. A. 39th U.S.C.T. / Died April 2[?], 1[???]", photo="IMG_1239",
    nps=None, nps_note="No James B. Berry was found in the index for the 39th U.S. Colored Infantry. The index has a James B. Berry in the 128th U.S. Colored Infantry, not yet checked.",
    chenery=None, pv001=None, died_text="an April day of a year now illegible on the stone"),
 "N2": dict(carved="WILLIAM McCLOUD / Pvt. Co. H. 3 U.S. Col. Inf. / Died Mar. 16, 1928", photo="IMG_1240",
    nps=None, nps_note="No William McCloud or McLeod was found in the index for the 3rd U.S. Colored Infantry; the spelling on his service record may differ.",
    chenery=None, pv001="1928", died_text="March 16, 1928"),
 "B3": dict(carved="NATHANIEL MOS[E]LEY / Co. I. 1 U.S. Cav. / Died Dec. 3, 1918", photo="IMG_1745",
    nps="unsearched", chenery=None, pv001=None, died_text="December 3, 1918",
    notes=["His stone was first placed at A17 by inference from the date sequence. On site on November 2, 2026, it proved to be the third stone in row B, so his page moved from A17 to B3; the old address still leads here. The year was first read as 1919; two close photographs and a side view all read 1918.",
           "The 1st U.S. Cavalry was a regular-army regiment. Whether his service in it was in the Civil War or later is not yet established."]),
 "N9": dict(carved="CHARLES H. GARDNER / U.S. Hvy. Art. / Died March 7, 1932", photo="IMG_1748",
    nps="unsearched", chenery=None, pv001=None, died_text="March 7, 1932",
    notes=["His place in the row is inferred, not surveyed: the survey sheet read this stone only as \"U.S. H.A.\", and a death in 1932 falls where row N's dates put it, between N2 (1928) and N12 (1935). It should be confirmed on site.",
           "The stone names no regiment, only \"U.S. Hvy. Art.\" Which regiment, and whether his service was in the Civil War or later, is not yet established."]),
 "N12": dict(carved="ISAAC E. POTTER / Landsman U.S. Navy / Died Sept. 1, 1935", photo="IMG_1425 (detail)",
    nps="unsearched", chenery=None, pv001=None, died_text="September 1, 1935",
    notes=["The photograph is a detail from a view of the whole row; a close photograph of the stone is wanted.",
           "Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "N13": dict(carved="HENRY J. GEER / Cpl. Co. H. 1st N.H. Cav. / Died June 2, 1936", photo="IMG_1425 (detail)",
    nps="unsearched", chenery=None, pv001=None, died_text="June 2, 1936",
    notes=["The photograph is a detail from a view of the whole row; a close photograph of the stone is wanted."]),
 "N14": dict(carved="JEREMIAH DUPON[T] / Pvt. Co. E. 15th Reg. [Me.] / Died Aug. 14, 1937", photo="IMG_1425 (detail)",
    nps="unsearched", chenery=None, pv001=None, died_text="August 14, 1937",
    notes=["The last letter of the surname is at a broken edge of the stone and is read as T; the regiment's state is read as Maine from the letters \"ME\" and from the survey sheet. A close photograph is wanted.",
           "If this is the 15th Maine Infantry, he was among the last men buried in the lot, 62 years after it was dedicated."]),
 # ---- Row A, read from the survey sheet only (no photograph yet). photo=None.
 "A1": dict(carved=None, photo=None, nps=None,
    nps_note="The index has no Elijah E. Ferrin in the 28th Maine; the only Ferrin it lists in that regiment is an Eaton Ferrin. The identity behind the stone is not yet confirmed.",
    chenery=None, pv001="1928", died_text="January 18, 1928"),
 "A2": dict(carved=None, photo=None, nps="Woodbury, George C., 7th New Hampshire Infantry, Company B, private in and out, microfilm M549 roll 13",
    chenery=None, pv001=None, died_text="April 8, 1926"),
 "A3": dict(carved=None, photo=None, nps="Weston, James (no middle initial), 2nd California Cavalry, Company B, private in and out, microfilm M533 roll 7",
    nps_note="The index gives no middle initial; the sheet records James K. A California cavalryman buried in Providence is worth explaining.",
    chenery=None, pv001=None, died_text="January 2, 1926"),
 "A4": dict(carved=None, photo=None, nps="Latham, Charles F., 1st Rhode Island Cavalry, Company A, private in and out, microfilm M555 roll 4",
    chenery=None, pv001=None, died_text="March 25, 1925"),
 "A5": dict(carved=None, photo=None, nps=None,
    nps_note="No John H. Lemons (or Lemmons) was found in the index under the 11th U.S. Colored Heavy Artillery or Rhode Island; the spelling on his service record may differ.",
    chenery="262", pv001="1925", died_text="February 28, 1925"),
 "A7": dict(carved=None, photo=None, nps="unsearched", chenery=None, pv001="1923", died_text="January 23, 1923",
    notes=["Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "A10": dict(carved=None, photo=None, nps="unsearched", chenery=None, pv001="1922", died_text="April 7, 1922",
    notes=["Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "A11": dict(carved=None, photo=None, nps="Dean, Lewis O., 1st Connecticut Cavalry, Company A, private in and out, microfilm M535 roll 4",
    nps_note="The sheet records \"1st Connecticut Volunteers\"; the cavalry card fits. A Lewis Dean (or Deane) also appears in the 1st Connecticut Heavy Artillery, Companies H and A — the same man or another, unresolved.",
    chenery=None, pv001=None, died_text="January 15, 1922"),
 "A13": dict(carved=None, photo=None, nps=None,
    nps_note="No Edward S. Simpson was found in the index for the 55th Massachusetts; the spelling on his service record may differ.",
    chenery=None, pv001="1921", died_text="October 24, 1921"),
 "A14": dict(carved=None, photo=None, nps=None,
    nps_note="No William T. Fry was found in the index for the 5th Massachusetts Cavalry (it lists an Alfred Fry); the spelling on his service record may differ.",
    chenery=None, pv001=None, died_text="January 29, 1921"),
 "A15": dict(carved=None, photo=None, nps="Claus, Arthur (also filed as Clouse and Clause), 35th Massachusetts Infantry, Company G, private in and out, with a cross-reference to the 29th Massachusetts; microfilm M544 roll 7",
    nps_note="The sheet records \"25th & 29th Mass.\"; the index has him in the 35th and the 29th. Whether the sheet misread 35 as 25 is for the stone to settle.",
    chenery=None, pv001=None, died_text="December 10, 1920"),
 "A16": dict(carved=None, photo=None, nps="Crosby, Robert (also filed as Crosley), 2nd Rhode Island Infantry, Company A, private in and out, microfilm M555 roll 2 — a probable match",
    nps_note="A Robert Crossley (or Crosley) also appears in the 1st Rhode Island Light Artillery, Battery C, corporal to sergeant — the same man or another, unresolved.",
    chenery=None, pv001=None, died_text="August 30, 1920"),
 "A18": dict(carved=None, photo=None, nps="Dewey, Charles W., 10th Connecticut Infantry, Company F, private in and out, microfilm M535 roll 5 (a second card, Charles B., is filed with it)",
    chenery=None, pv001=None, died_text="December 27, 1919"),
 # ---- Rest of the lot, 1 Nov 2026. No photographs yet unless photo is set.
 "B1": dict(carved=None, photo=None, nps=None, nps_note="No Daniel W. Deane was found in the index for the 22nd Massachusetts; the spelling on his service record may differ.", chenery=None, pv001="1919", died_text="March 27, 1919"),
 "B17": dict(carved=None, photo=None, nps="Johnson, William L., 11th U.S. Colored Heavy Artillery, Company L, private in and out, microfilm M589 roll 48", chenery="252", pv001=None, died_text="August 11, 1916"),
 "B21": dict(carved=None, photo=None, nps="unsearched", chenery=None, pv001="1916", died_text="May 22, 1916",
    notes=["The 23rd U.S. Infantry was a regular-army regiment raised in 1866. His service may be after the Civil War; the records will say."]),
 "B25": dict(carved=None, photo=None, nps="Homan, John G., 15th New York Infantry (National Guard, thirty days' service, 1864), Company F, private in and out, microfilm M551 roll 66", chenery=None, pv001=None, died_text="November 28, 1915"),
 "C1": dict(carved=None, photo=None, nps="Jackson, Charles A., 11th U.S. Colored Heavy Artillery, Company B, private in, corporal out, microfilm M589 roll 44 — the card that fits the stone; a second Charles A. Jackson is in Company E of the same regiment",
    nps_note="The survey sheet names the unit as the 11th U.S. Heavy Artillery, which is the 14th Rhode Island under its later designation.", chenery=None, pv001="1905", died_text="November 11, 1915",
    notes=["The PV001 list gives his death as March 29, 1905; the survey sheet reads November 11, 1915 on the stone. One of them is wrong; the stone will settle it."]),
 "C23": dict(carved=None, photo=None, nps="Williams, Theodore, 11th U.S. Colored Heavy Artillery, Company L, private in and out, microfilm M589 roll 95", chenery="255", pv001=None, died_text="January 20, 1912"),
 "C24": dict(carved=None, photo=None, nps="Butler, Wm. H. (also filed as Henry W. and Henry J.), 2nd U.S. Colored Infantry, Company H, private in and out, microfilm M589 roll 14 — a probable match",
    nps_note="The stone and the PV001 list give the middle initial as I; the index card gives H. Unit and company agree.", chenery=None, pv001=None, died_text="January 15, 1912"),
 "D1": dict(carved=None, photo=None, nps="McGraw, Thomas H., 9th Maine Infantry, Company A, private in, corporal out, microfilm M543 roll 14", chenery=None, pv001=None, died_text=None),
 "D4": dict(carved=None, photo=None, nps="Parker, Joseph R., 11th U.S. Colored Heavy Artillery, Company M, private in, corporal out, microfilm M589 roll 66",
    nps_note="The survey sheet read the company as \"U\"; the index card settles it as M.", chenery="258", pv001=None, died_text=None),
 "D7": dict(carved=None, photo=None, nps="Lee, Adam, 11th U.S. Colored Heavy Artillery, Company L, private in, corporal out, microfilm M589 roll 53", chenery="248", pv001=None, died_text=None),
 "D8": dict(carved=None, photo=None, nps="Mackbee, Jeff, 23rd U.S. Colored Infantry, Company E, private in and out, microfilm M589 roll 56", chenery=None, pv001="1910", died_text=None),
 "D9": dict(carved=None, photo=None, nps=None, nps_note="No Joseph Devendor (or Devender, Devendore) was found in the index for the 20th U.S. Colored Infantry, which has a John and a Henry Devendorf; the spelling on his service record may differ.", chenery=None, pv001="1910", died_text=None),
 "D10": dict(carved=None, photo=None, nps="Stafford, Charles H., 11th U.S. Colored Heavy Artillery, Company B, private in and out, microfilm M589 roll 82",
    nps_note="The survey sheet read the name as Stratford; the index, the PV001 list and Chenery's errata have Stafford. The sheet and the PV001 list put him in Company D, the index card in Company B. Both questions are for the stone and the service record.", chenery="172 (errata)", pv001="1911", died_text=None),
 "D14": dict(carved=None, photo=None, nps="White, Jacob, 2nd U.S. Colored Cavalry, Company F, private in and out, microfilm M589 roll 93", chenery=None, pv001="1910", died_text=None),
 "D15": dict(carved=None, photo=None, nps="Johnson, James E., 28th U.S. Colored Infantry, two cards: Company D, private in and out, and one with no company (\"unassigned recruits\"); microfilm M589 roll 47", chenery=None, pv001="1910", died_text=None,
    notes=["Which company he served in, and whether both cards are his, is for the service record."]),
 "D16": dict(carved="POLK / [marker sunk; the rest below ground]", photo=None, nps=None,
    nps_note="The PV001 list has a James H. Polk of the 14th Rhode Island Heavy Artillery, died 1910, and the index has a James K. Polk in the 11th U.S. Colored Heavy Artillery. Until the stone is raised and read, he is a candidate, not an identification.", chenery=None, pv001="1910", died_text=None,
    notes=["Only the surname has been read. The marker is sunk; the City's staff would need to clear it before the rest can be read."]),
 "D20": dict(carved="TAFFT / [marker sunk; the rest below ground]", photo=None, nps=None,
    nps_note="The PV001 list has a Henry S. Tafft, U.S. Signal Corps, died 1909, and the index has a Henry S. Tafft in the Signal Corps, U.S. Volunteers. Until the stone is raised and read, he is a candidate, not an identification.", chenery=None, pv001="1909", died_text=None,
    notes=["Only the surname has been read. The marker is sunk; the City's staff would need to clear it before the rest can be read."]),
 "E1": dict(carved=None, photo=None, nps="Knight, Alonzo H., 2nd Rhode Island Infantry, Company D, private in and out, microfilm M555 roll 4",
    nps_note="The survey sheet read the given name as Lonzo; the index and the PV001 list have Alonzo.", chenery=None, pv001="1909", died_text=None),
 "E10": dict(carved="JEREMIAH / [marker sunk; the rest below ground]", photo=None, nps=None,
    nps_note="\"Jeremiah\" may be a given name rather than a surname: the PV001 list has no veteran surnamed Jeremiah, but it has a Jeremiah Lee, U.S. Navy, died 1907, and others. Until the stone is raised and read, no identification is made.", chenery=None, pv001=None, died_text=None,
    notes=["Only one word has been read. The marker is sunk; the City's staff would need to clear it before the rest can be read."]),
 "E12": dict(carved=None, photo=None, nps="Green, Sylvanus, 11th U.S. Colored Heavy Artillery, Company C, private in and out, microfilm M589 roll 34", chenery="178", pv001="1907", died_text=None),
 "E16": dict(carved="CARL / [rest not read]", photo=None, nps=None,
    nps_note="The PV001 list has a George C. Carl, died 1906, with no unit given. The index search for Rhode Island found no Carl. \"Carl\" could also be a given name. No identification is made.", chenery=None, pv001="1906", died_text=None,
    notes=["Only one word has been read from the stone."]),
 "E17": dict(carved="DEXTER / [rest not read]", photo=None, nps=None,
    nps_note="The PV001 list has two candidates: Charles A. Dexter, Rhode Island militia, Company B, died 1906, and James H. Dexter, U.S. Navy, died 1897. The index has a Charles A. Dexter in the 1st Rhode Island Light Artillery and the three-months' 1st Rhode Island Infantry. A death in 1906 fits this row's dates. No identification is made.", chenery=None, pv001=None, died_text=None,
    notes=["Only the surname has been read from the stone."]),
 "E18": dict(carved="CHAFEE / [rest not read]", photo=None, nps=None,
    nps_note="The PV001 list has a James H. Chafee, 12th Rhode Island Volunteers, Company B, died 1906, and the index has a James H. Chafee in the 12th Rhode Island Infantry. A death in 1906 fits this row's dates. He is a candidate, not an identification.", chenery=None, pv001="1906", died_text=None,
    notes=["Only the surname has been read from the stone."]),
 "E25": dict(carved=None, photo=None, nps="Hammond, Joshua F., 28th Independent Battery, New York Light Artillery, private in and out, microfilm M551 roll 58", chenery=None, pv001="1905", died_text=None),
 "F5": dict(carved=None, photo=None, nps="Williams, Benjamin (no middle initial), 11th U.S. Colored Heavy Artillery, Company I, private in and out, microfilm M589 roll 94", chenery="236", pv001="1904", died_text="November 2 of a year the survey could not read; the PV001 list gives 1904"),
 "F8": dict(carved=None, photo=None, nps="Silvey, Edward, 11th U.S. Colored Heavy Artillery, Company E, private in and out, microfilm M589 roll 79", chenery="199", pv001=None, died_text="August 3, 1904"),
 "F16": dict(carved=None, photo=None, nps="Burr, William, 11th U.S. Colored Heavy Artillery, Company C, private in and out, microfilm M589 roll 13", chenery="177", pv001="1903", died_text=None),
 "F22": dict(carved=None, photo=None, nps="Jenkins, John A., 11th U.S. Colored Heavy Artillery, Company A, sergeant in, private out, microfilm M589 roll 46",
    nps_note="He entered as a sergeant and left as a private; the service record will say why. Chenery lists him twice, in the Company A roster and at p. 20.", chenery="156 and 20", pv001=None, died_text="June 4, 1902"),
 "G11": dict(carved=None, photo=None, nps="Hunter, Henry, 11th U.S. Colored Heavy Artillery, Company B, private in and out, microfilm M589 roll 43", chenery="170", pv001=None, died_text="November 14, 1885"),
 "G14": dict(carved=None, photo=None, nps="Jackson, Theodore, 11th U.S. Colored Heavy Artillery, Company B, private in and out, microfilm M589 roll 45", chenery="170", pv001=None, died_text="April 9, 1876",
    notes=["His 1876 death is the earliest yet read in the lot, a year after it was dedicated. The register carries a note \"died in Louisiana?\" with no source; if he died where the regiment served, how he came to be buried here is a question. The PV001 list gives a birth about 1833."]),
 "H15": dict(carved=None, photo=None, nps="Chase, Joseph (no middle initial), 9th U.S. Colored Infantry, Company H, private in and out, microfilm M589 roll 16 — a probable match", chenery=None, pv001=None, died_text="June 1 of a year in the 1880s, the last digit not read",
    notes=["He is not on the PV001 list."]),
 "H20": dict(carved=None, photo=None, nps="Black, George H., 11th U.S. Colored Heavy Artillery, Company A, corporal in, sergeant out, microfilm M589 roll 7", chenery="156 and 10", pv001=None, died_text="May 14, 1887"),
 "I2": dict(carved="GIBBS / [marker sunk; the rest below ground]", photo=None, nps=None,
    nps_note="The survey recorded the unit as the 3rd U.S. Colored Infantry. The PV001 list has a Franklin A. Gibbs, 3rd U.S.C.T., Company A, not found in the index; the only Gibbs the index shows in the 3rd U.S. Colored Infantry is a Warren Gibbs, Company G. Unresolved.", chenery=None, pv001=None, died_text=None,
    notes=["Only the surname and unit have been read. The marker is sunk; the City's staff would need to clear it before the rest can be read."]),
 "I6": dict(carved="DIGGS / 14th R.I.H.A. / Died Sept. 30, 18[??]", photo=None, nps="two men named Diggs in the 11th U.S. Colored Heavy Artillery: John Diggs, Company M, private in, corporal out, and Henry C. Diggs, Company H, private in and out; both microfilm M589 roll 24",
    nps_note="The PV001 list has Henry C. Diggs, Company H, died 1891, which favors him; the stone's given name has not been read.", chenery=None, pv001="1891", died_text="September 30 of a year the survey could not read; the PV001 list gives 1891"),
 "J7": dict(carved=None, photo=None, nps="Lewis, Robert, 11th U.S. Colored Heavy Artillery, Company I, private in and out, microfilm M589 roll 54", chenery="234", pv001=None, died_text="July 27, 1894"),
 "J15": dict(carved=None, photo=None, nps=None, nps_note="No Emanuel Parker was found in the index for the 5th U.S. Colored Cavalry (it has a James and a Richard Parker); the spelling on his service record may differ.", chenery=None, pv001=None, died_text="April 8, 1898"),
 "K2": dict(carved=None, photo=None, nps=None, nps_note="No Thomas George was found in the index for the 31st U.S. Colored Infantry (there is one in the 110th); the spelling on his service record may differ.", chenery=None, pv001="1897", died_text="November 5, 1897"),
}

# ---- Photo dump of 1 Nov 2026 (Dropbox photo-dump, 115 frames, 2023-2026): photographs matched to grid
#      positions by what is carved and by their order in the shooting sequence. photo = date and time of the frame.
STONES["A1"].update(carved="ELIJAH E. FERRIN / Pvt. Co. C 28 Maine Inf. / Died Jan. 18, 1928", photo="2026-06-23 13:08")
STONES["A2"].update(carved="GEORGE C. WOODBURY / Co. B 7 N.H. Inf. / Died Apr. 8, 1926", photo="2026-10-30 13:38")
STONES["A3"].update(carved="JAMES K. WESTON / Co. B 2 Cal. Cav. / Died Jan. 2, 1926", photo="2026-10-30 13:38")
STONES["A4"].update(carved="CHARLES F. LATHAM / Co. A 1 R.I. Cav. / [date line under leaves]", photo="2026-10-30 13:38",
    stone_note="The date line was under fallen leaves when photographed; the survey sheet read it as March 25, 1925.")
STONES["A5"].update(carved="JOHN H. LEMONS / Co. M 14 R.I. Art. / [Died Feb.] 28, 1925", photo="2026-10-30 13:38")
STONES["A6"].update(photo="2026-10-30 13:38")
STONES["A7"].update(carved="HENRY C. CHILDS / U.S. Navy / Died Jan. 23, 192?", photo="2026-10-30 13:38")
STONES["A10"].update(carved="NEWTON H. BRIGGS / U.S. Navy / Died April 7, 1922", photo="2026-10-30 13:38")
STONES["A11"].update(carved="LEWIS O. DEAN / Co. A 1 Conn. Vol. / Died Jan. 15, 1922", photo="2026-10-30 13:38")
STONES["A12"].update(photo="2026-10-30 13:38")
STONES["A13"].update(carved="EDWARD S. SIMPSON / Co. F 55 Mass. Vol. / Died Oct. 24, 1921", photo="2026-10-30 13:39")
STONES["A14"].update(carved="WILLIAM T. FRY / Co. F 5 Mass. Cav. / Died Jan. 29, 1921", photo="2026-10-30 13:39")
STONES["A15"].update(carved="ARTHUR A. CLAUS / Co. [G] 25 Mass. & Co. G 29 Mass. / Died Dec. 10, 1920", photo="2026-10-30 13:39",
    stone_note="The stone reads 25 Mass., as the survey sheet did; the index card's 35th is therefore the index's reading, not the stone's.")
STONES["A16"].update(carved="ROBERT CROSSLEY / Co. A 2 R.I. Vol. / Died Aug. 30, 1920", photo="2026-10-30 13:39")
STONES["B3"].update(photo="2026-10-22 09:31")
STONES["A18"].update(carved="CHARLES W. DEWEY / Co. F 10 Conn. Vol. / Died Dec. 27, 1919", photo="2026-10-30 13:39")
STONES["A19"].update(photo="2026-10-22 09:32")
STONES["E1"].update(carved="LONZO H. KNIGHT / Co. D 2d R.I. Vol. / Died A[??]. 24, 1909", photo="2026-10-30 14:05",
    died_text="the 24th of a month in 1909 (the month is under earth; April or August)")
STONES["E12"].update(carved="SYLVANUS GREE[N] / Co. C 14th R.I. Art. / Died May [?], 19[0?]", photo="2026-10-30 14:07",
    died_text="a day in May of a year read only as 19--; the PV001 list gives 1907")
STONES["E13"].update(carved="HENRY FRAWLEY / 7th 4?th 58th Mass Vol. / Died Feb. 5, 1907", photo="2025-10-16 14:45", pv001="1907",
    died_text="February 5, 1907",
    notes=["Did he serve in all three regiments, and when? The 7th and the 47th (a nine-month militia regiment of 1862–63) and the 58th (raised in 1864) are all named on the stone; his service record will show which enlistments are his.",
           "The survey sheet had the name as \"Henry Frank\" and the year as 1902; the photographs read FRAWLEY and 1907. The middle regiment's number reads 42 or 47; the index has him in the 47th. A death in 1907 fits row E's dates, so the earlier doubt about his grid position is withdrawn."])
STONES["E16"].update(carved="GEO. C. CARL / [lower lines under earth]", photo="2026-10-30 14:07",
    nps_note="The stone's GEO. C. CARL matches the PV001 list's George C. Carl, died 1906, with no unit given. The index search for Rhode Island found no Carl. The unit and date lines are under earth.",
    notes=["Only the top line of the stone is exposed; the unit and date are under earth."])
STONES["E17"].update(carved="[CHA]RLES A. DEXT[ER] / [lower lines under earth]", photo="2026-10-30 14:07",
    nps_note="The stone's CHARLES A. DEXTER matches the PV001 list's Charles A. Dexter, Rhode Island militia, Company B, died 1906; the index has a Charles A. Dexter in the 1st Rhode Island Light Artillery and the three-months' 1st Rhode Island Infantry. The unit and date lines are under earth.",
    notes=["Only the top line of the stone is exposed; the unit and date are under earth."])
STONES["E18"].update(carved="JAMES H. CHAFEE / Priv. Co. B 12th R.I. Vol. / Died Aug. 25, 1906", photo="2026-10-30 14:07",
    nps="Chafee, James H., 12th Rhode Island Infantry, Company B — a candidate noted from an index search for Rhode Island, detail card not yet opened",
    nps_note="The stone confirms the PV001 list's James H. Chafee, 12th Rhode Island Volunteers, Company B, died 1906.", died_text="August 25, 1906", notes=[])
STONES["E25"].update(carved="JOSHUA F. HAMMOND / 28th Co. Indp. Battery N.Y. / Died [date under grass]", photo="2026-10-30 14:08",
    notes=["This stone was E24 until November 1, 2026. The photographs of October 30 show a stone the survey sheet missed, William A. Lewis, between Ira Smith (E23) and this one, so row E has twenty-five stones and this is E25."])
STONES["F5"].update(carved="BENJAMIN F. WILLIAMS / Co. I 14th R.I.H.Art. / Died Nov. 2, 190[?]", photo="2025-04-07 12:43")
STONES["F8"].update(carved="EDWARD SILVEY / Co. E 14th R.I.H.Art. / Died Aug. 3, 1904", photo="2025-04-07 12:43")
STONES["F16"].update(carved="WILLIAM BURR / Co. C 14th R.I.H.A. / [Died ???.] 14, 190[?]", photo="2025-04-07 12:44",
    died_text="the 14th of a month in the 1900s; the PV001 list gives 1903")
STONES["F22"].update(carved="JOHN A. JENKINS / Co. A 14th R.I.H.Art. / Died June 4, 1902", photo="2025-04-07 12:46")
STONES["G14"].update(carved="THEODORE H. JACKSON / Co. B 14th R.I.H.Art. / Died Apr. 9, 1876", photo="2025-04-07 12:49")
STONES["H15"].update(carved="[JOS]EPH N. CHAS[E] / [Co.] H 9th U.S.C.[T.] / [Die]d June 1, 188[?]", photo="2024-04-02 14:44")
STONES["H20"].update(carved="GEORGE H. BLACK / Co. A 14th R.I.H.Art. / Died May 14, 1887", photo="2025-04-07 12:52")
STONES["I2"].update(carved="[????] GIBBS / [Co. ?] U.S.C.[T.] / [worn]", photo="2025-04-07 12:53",
    notes=["The stone is badly worn and partly sunk; the given name has not been read."])
STONES["I6"].update(carved="[HENR]Y C. DIGGS / [Co. H] 14th R.I.H.A. / Died Sept. 30, 18[??]", photo="2025-06-20 15:01",
    nps_note="The photograph reads the given name's last letter as Y and the middle initial as C, which favors Henry C. Diggs, Company H; the PV001 list has him dying in 1891.")
STONES["J7"].update(carved="ROBERT LEWIS / Co. I 14th R.I.H.Art. / Died July 27, 1894", photo="2025-04-07 12:59")
STONES["J15"].update(carved="EMANUEL PARKER / [Co.] H 5th U.S.C. Cav. / Died April 8, 1898", photo="2024-04-02 14:43")
STONES["K2"].update(carved="THOMAS GEORGE / Co. G 31st U.S. Col. T[ps]. / Died Nov. 5, 189?", photo="2025-04-07 13:01")
STONES["N9"].update(photo="2026-10-22 09:33")
STONES["N12"].update(photo="2026-10-30 13:56", notes=["Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."])
STONES["N13"].update(photo="2026-10-30 13:57", notes=[])
STONES["N14"].update(carved="JEREMIAH DUPONT / Pvt. Co. E 15th Reg. (Me.) / Died Aug. 14, 1937", photo="2026-10-30 13:57",
    notes=["If this is the 15th Maine Infantry, he was among the last men buried in the lot, 62 years after it was dedicated."])
STONES["E10"].update(carved="JEREMIAH / [the rest under earth]", photo="2026-10-30 14:06",
    notes=["Only the first line has been read. Three-quarters of the stone is under earth; the City's staff would need to clear it before the rest can be read."])

# Newly read stones (first photographs, 30 Oct 2026). NPS not yet searched for any of them.
_unsearched = dict(nps="unsearched", chenery=None, pv001=None)
STONES.update({
 "E24": dict(carved="WILLIAM A. LEWIS / Co. C 2nd R.I. Vols. / [date under grass]", photo="2026-10-30 14:08", died_text=None, nps="unsearched", chenery=None, pv001=None,
    notes=["This stone is not on the plot survey sheet; it was found in the photographs of October 30, 2026, between Ira Smith (E23) and Joshua F. Hammond, who was renumbered from E24 to E25 to make room for it.", "The date line is under grass."]),
 "I1": dict(carved="JAMES M. CLARK / U.S. N[avy] / [worn]", photo="2025-06-20 15:02", died_text=None, nps="unsearched", chenery=None, pv001=None,
    notes=["His place at I1 rests on the order of the photographs of June 20, 2025 (Diggs at I6, Gibbs at I2, then this stone, then an uninscribed one) and on the survey sheet's reading of I1 as a Navy stone; confirmed by B. Brennan on November 1, 2026.", "Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "E2": dict(carved="BENJAMIN W. FOSTER / Priv. 1st R.I. Art. / Died Ma[?]. 18, 1909", photo="2026-10-30 14:06", died_text="the 18th of March or May 1909", **_unsearched),
 "E3": dict(carved="WILLIAM BURROUGHS / U.S. Navy / [lower half under earth]", photo="2026-10-30 14:06", died_text=None, **_unsearched,
    notes=["The lower half of the stone is under earth; no date has been read.", "Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "E4": dict(carved="[JOH]N LAMBERT / [Co. ?] 11th R.I. Vol. / [under earth]", photo="2026-10-30 14:06", died_text=None, **_unsearched,
    notes=["The left and lower parts of the stone are under earth; the given name is read as John from its last letter and the space before it, and no date has been read."]),
 "E5": dict(carved="THEODORE MACE / U.S. Navy / Died Jan. 10, 19[??]", photo="2026-10-30 14:06", died_text="January 10 of a year in the 1900s, the last digits worn", **_unsearched,
    notes=["The surname may continue past the worn edge (Mace or Macey). Which ship or ships did he serve on? The Navy's records have not yet been searched."]),
 "E6": dict(carved="BARTLETT B. MATTHEWS / [Co. ?] 43[d] U.S. V[ol.] / [under earth]", photo="2026-10-30 14:06", died_text=None, **_unsearched,
    notes=["The lower right of the stone is under earth. The unit line is read with the survey sheet's \"43rd US Vol\"; which regiment that is (a 43rd U.S. Colored Infantry existed; so did state 43rds) is for the records to settle."]),
 "E7": dict(carved="RICHARD PIERCE / Priv. Troop C 1st R.I. Cav. / [date line worn]", photo="2026-10-30 14:06", died_text=None, **_unsearched),
 "E8": dict(carved="[???]R M[c]KENNEY / Co. H 2[?]th Maine Inf. / Died [???] 1909", photo="2026-10-30 14:06", died_text="a day in 1909", slug="mckenney", **_unsearched,
    notes=["The stone was photographed in hard shadow and is mostly under earth; the surname is read as McKenney with reservation, the given name is not read, and the regiment's number reads 2-th. A photograph in flat light, with the earth cleared, is wanted."]),
 "E11": dict(carved="CHARLES H. SAN[D]ER[S] / [Co.] A [???] / [under earth]", photo="2026-10-30 14:07", died_text=None, slug="sanders", **_unsearched,
    notes=["The surname is read with reservation: the letters visible are SAN·ER·, consistent with Sanders (or Sanborn). The right half of the stone is under earth."]),
 "E14": dict(carved="EDWARD GERALD / Co. H 1st Conn. H. Arty / Died March 2, [under grass]", photo="2026-10-30 14:07", died_text="March 2 of a year not yet read", **_unsearched),
 "E15": dict(carved="JAMES A. L[?????] / [Co. ?] [???] / [under earth]", photo="2026-10-30 14:07", died_text=None, slug="james-a-l", **_unsearched,
    notes=["Only JAMES A. L and part of a unit line are exposed; the surname is under earth. A photograph with the earth cleared is wanted."]),
 "E19": dict(carved="WILLIAM W. [??????] / Co. D 11th R.I. Art. / Died May 5, 1906", photo="2026-10-30 14:07", died_text="May 5, 1906", slug="william-w", **_unsearched,
    notes=["A flag lay across the surname when the stone was photographed. The unit as carved, \"11th R.I. Art.\", is the 14th Rhode Island Heavy Artillery under its later federal designation, the 11th U.S. Colored Heavy Artillery; Chenery's Company D roster should give candidates for a William W.", "A photograph without the flag is wanted."]),
 "E20": dict(carved="JOHN VANYEA / Co. D 142d N.Y. Vol. / [date line under earth]", photo="2026-10-30 14:08", died_text=None, **_unsearched),
 "E21": dict(carved="CHARLES L. RUMENAPP / Co. F 2d Penn. Cav. / Died May 14, 1905", photo="2026-10-30 14:08", died_text="May 14, 1905", **_unsearched),
 "E22": dict(carved="[JOH]N H. SPENCER / [Co. ?] [??] Conn. Vols. / [under earth]", photo="2026-10-30 14:08", died_text=None, **_unsearched,
    notes=["Most of the stone is under earth; the given name is read as John from its last letter, and the regiment's number and the date are not exposed."]),
 "E23": dict(carved="IRA SMITH / [Co.] K 5th Mass. C[av.] / [under earth]", photo="2026-10-30 14:08", died_text=None, **_unsearched),
 "N1": dict(carved="ASA A. ANDREWS / Pvt. Co. H 5 U.S. Art. / Died Feb. 27, 1928", photo="2026-10-30 13:50", died_text="February 27, 1928", **_unsearched,
    notes=["The 5th U.S. Artillery was a regular-army regiment. Whether his service was in the Civil War or later is not yet established."]),
 "N3": dict(carved="PVT. JOEL HOLBROOK / Co. G 4 Mass. Art. / Died [???] 1928", photo="2026-10-30 13:50", died_text="a day in 1928, the month and day in shadow in the photograph", **_unsearched),
 "N4": dict(carved="OLIVER COGGESHALL / Pvt. Troop B 3 R.I. Cav. / Died Apr. 28, 1928", photo="2026-10-30 13:51", died_text="April 28, 1928", **_unsearched),
 "N5": dict(carved="WILLIAM G. BAKER / Pvt. Co. F 1 R.I. Inf. / Died Nov. 29, 1929", photo="2026-10-30 13:51", died_text="November 29, 1929", **_unsearched),
 "N6": dict(carved="GEORGE W. STODDARD / Co. A 3rd R.I. Art. / Died Apr. 5, 1930", photo="2026-10-30 13:55", died_text="April 5, 1930", **_unsearched),
 "N7": dict(carved="SAMUEL E. WHITE / Co. F 11th R.I. Inf. / Died Nov. 20, 1930", photo="2026-10-30 13:56", died_text="November 20, 1930", **_unsearched),
 "N8": dict(carved="JOHN S. BROWN / U.S. Navy / Died Dec. 30, 1930", photo="2026-10-30 13:56", died_text="December 30, 1930", **_unsearched,
    notes=["Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "N10": dict(carved="JOSEPH S. CASSEN / Pvt. Bat. B 1st R.I. Art. / Died April 19, 1933", photo="2026-10-30 13:56", died_text="April 19, 1933", **_unsearched),
 "N11": dict(carved="OTHELLO W. GODFREY / Pvt. Co. A 1st R.I. Cav. / Died Dec. 3, 1934", photo="2026-10-30 13:56", died_text="December 3, 1934", **_unsearched),
})


# Row B, read on site 2 Nov 2026 (close and oblique frames, contrast-enhanced where noted) and checked the same
# afternoon against the PV001 list and the NPS index (cards opened; URLs in register notes).
_rb = dict(chenery=None, nps_accessed="November 2, 2026")
_ph = "2026-11-02 12:45"
STONES.update({
 "B2": dict(carved="RICHARD NIGH[TINGALE] / Co. G 30 N.Y. Vol. / Died Mar. 24, 1919", photo=_ph, died_text="March 24, 1919", pv001="1919", **_rb,
    nps=None, nps_note="No Richard Nightingale was found in the index for the 30th New York Infantry; the index has men of that name only in other regiments.",
    notes=["Only RICHARD NIGH can be read on the stone; the rest of the surname is worn away. \"Nightingale\" comes from the PV001 list, which records a Richard Nightingale, about 1840–1919, of the 30th New York Volunteers. His service record will confirm it."]),
 "B4": dict(carved="ROBERT W. SMAL[L] / Co. I 2 R.I. Vol. / Died Nov. 4, 1918", photo=_ph, died_text="November 4, 1918", pv001="1918", **_rb,
    nps="Small, Robert W., 2nd Rhode Island Infantry, Company I, private in, first lieutenant and regimental quartermaster out, field and staff, microfilm M555 roll 6",
    nps_note="The stone gives no rank.",
    notes=["The index shows him leaving the regiment as its quartermaster, an officer. When was he promoted, and from what rank? His service record will say."]),
 "B5": dict(carved="ALEXANDER G. S[MITH] / Co. C 17 Mass. Vol. / Died Nov. 4, 1918", photo=_ph, died_text="November 4, 1918", pv001="1919", **_rb,
    nps="Smith, Alexander G., 2nd Massachusetts Heavy Artillery, Company E, private in and out, with the note \"See also 17 Mass. Inf.\", microfilm M544 roll 37",
    nps_note="The stone names the 17th Massachusetts; the index card for that regiment has not yet been opened.",
    notes=["Only ALEXANDER G. S can be read in the surname; \"Smith\" comes from the PV001 list, which records an Alexander G. Smith of the 17th Massachusetts.",
           "The stone gives 1918 and the PV001 list 1919. The stone is followed here; his death record will settle it."]),
 "B6": dict(carved="THOMAS A[RR] / U.S. Navy / Died Oct. 13, 1918", photo=_ph, died_text="October 13, 1918", pv001="1918", nps="unsearched", chenery=None,
    notes=["Only THOMAS A and a worn R can be read in the surname; \"Arr\" comes from the PV001 list, which records a Thomas Arr, U.S. Navy, died 1918.",
           "Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "B8": dict(carved="[MA]SON B. FRANKLIN / Co. H 2 R.I. Vol. / Died Jan. 30, 1918", photo=_ph, died_text="January 30, 1918", pv001="1918", **_rb,
    nps="Franklin, Mason B., 2nd Rhode Island Infantry, Company H, private in and out, microfilm M555 roll 3"),
 "B9": dict(carved="CHARLES H. KENDALL / Co. B 2 R.I. Vol. / Died Oct. 22, 1917", photo=_ph, died_text="October 22, 1917", pv001="1917", **_rb,
    nps="Kendall, Charles (also filed as Charles H. Kendall), 2nd Rhode Island Infantry, Companies E and B, private in and out, microfilm M555 roll 4"),
 "B10": dict(carved="[RI]CHARD H. [F]REEMA[N] / Co. K 29 Conn. Vol. / [Died] May 8, 1917", photo=_ph, died_text="May 8, 1917", pv001="1917", **_rb,
    nps=None, nps_note="No Richard Freeman was found in the index for the 29th Connecticut Infantry; the index has other men named Freeman in that regiment, and his record may be filed under another spelling.",
    notes=["The name was read from an enhanced photograph; the first letters of the given name and of the surname are worn. The PV001 list records a Richard H. Freeman, Company K, 29th Connecticut Volunteers, died 1917, which agrees with the stone.",
           "His service in the 29th rests on his stone and the PV001 list until his service record is found."]),
 "B11": dict(carved="JOHN S. GAY / Co. A 20 Mass. Vol. / Died Apr. 24, 1917", photo=_ph, died_text="April 24, 1917", pv001="1917", **_rb,
    nps="Gay, John S., 20th Massachusetts Infantry, Company A, private in and out, microfilm M544 roll 15"),
 "B12": dict(carved="JOHN T. WALKER / Co. C 2 U.S. Cav. / Died Jan. 30, 1917", photo=_ph, died_text="January 30, 1917", pv001="1917", **_rb,
    nps=None, nps_note="No John T. Walker was found in the index for the 2nd U.S. Cavalry, whose regular-army records the index covers only in part.",
    notes=["The 2nd U.S. Cavalry was a regular-army regiment. Whether his service in it was in the Civil War or later is not yet established."]),
 "B13": dict(carved="JOHN R. NORTHU[P] / Co. H 4 R.I. Vol. / [Died ???.] 21, 19[1?]", photo=_ph, died_text="the 21st of a month in the 1910s (the month is under earth); the PV001 list gives 1917", pv001="1917", **_rb,
    nps="Northup, John R., 4th Rhode Island Infantry, Company H, private in and out, microfilm M555 roll 5",
    nps_note="A second card under the same name has not yet been opened."),
 "B14": dict(carved="THEODORE KUH[N] / Co. D 2 N.J. Vol. / Died Jan. 2, 191[?]", photo=_ph, died_text="January 2 of a year in the 1910s, the last digit under earth; the PV001 list gives 1917", pv001="1917", **_rb,
    nps="Kuhn, Theodore, 2nd New Jersey Infantry (three months, 1861), Company D, private in and out, microfilm M550 roll 13"),
 "B15": dict(carved="THOMAS E. WEST / 7 N.Y. Cav. / [Died ???.] 1916", photo=_ph, died_text="a day in 1916", pv001="1916", **_rb,
    nps="West, Thomas, 7th New York Cavalry, Company A, private in and out, microfilm M551 roll 150",
    nps_note="The card has no middle initial, so the match is probable, not certain.",
    notes=["Half the stone is under earth; the month and day of death are not exposed."]),
 "B16": dict(carved="ALLEN P. PECK / Co. I 9 R.I. Vol. / [date line under earth]", photo=_ph, died_text=None, pv001="1916", **_rb,
    nps="Peck, Allen P., 9th Rhode Island Infantry, Company I, private in and out, microfilm M555 roll 6",
    notes=["The 9th Rhode Island was a three-month regiment of 1862.", "The date line is under earth."]),
 "B18": dict(carved="JOSEPH H. CORNELL / [Co.] C 11 R.I. Vol. / [date line under earth]", photo=_ph, died_text=None, pv001=None, **_rb,
    nps="Cornell, Joseph H., 11th Rhode Island Infantry, Company G, private in and out, with the note \"See also 3 R.I. Cavy.\", microfilm M555 roll 2",
    nps_note="The company letter on the stone was read as C; the index gives G.",
    notes=["The PV001 list has a Joseph H. Cornell, 11th Rhode Island, Company G, who died on March 30, 1905. That date does not fit this row, where the burials run from 1915 to 1919. Is this the same man? The stone's date line, now under earth, is the test.",
           "The 11th Rhode Island was a nine-month regiment of 1862–63; the index note points to later service in the 3rd Rhode Island Cavalry."]),
 "B19": dict(carved="JOHN HAWKESWORTH / Co. E 1 Mass. Vol. / [Died J]une 1[?], 19[1?]", photo=_ph, died_text="a day in June of a year in the 1910s; the PV001 list gives 1916", pv001="1916", **_rb,
    nps="Hawkesworth, John (filed under Hawksworth), 1st Massachusetts Heavy Artillery, Company E, private in and out, microfilm M544 roll 18",
    nps_note="The stone says 1st Massachusetts Volunteers; the card says heavy artillery. His service record will say which."),
 "B20": dict(carved="CHARLES D. KATES / Co. A [1?] Mass. [Vol.] / [Died ???] 1916", photo=_ph, died_text="a day in 1916", pv001="1916", **_rb,
    nps=None, nps_note="No Charles D. Kates was found in the index for a Massachusetts regiment.",
    notes=["The regiment's number is worn; the PV001 list gives the 1st Massachusetts Volunteers, Company A.", "Lichen covers the right half of the stone. It should not be scrubbed."]),
 "B22": dict(carved="CHARLES H. SMITH / Co. C 33 Reg. M[ass.] / [date line not read]", photo=_ph, died_text=None, pv001=None, **_rb,
    nps="Smith, Charles H., 33rd Massachusetts Infantry, Company F, private in and out, microfilm M544 roll 37",
    nps_note="The card gives Company F; the stone reads C. Which Charles H. Smith this is has not been established.",
    notes=["The PV001 list has a Charles H. Smith of the 33rd Massachusetts who died in 1890. That date does not fit this row, where the burials run from 1915 to 1919. The stone's date line has not been read.",
           "The surname was first read as Small; an enhanced photograph reads SMITH."]),
 "B23": dict(carved="[WI]LL[IAM] E. SMITH / Co. H 11 R.I. V[ol.] / [date line not read]", photo=_ph, died_text=None, pv001="1918", **_rb,
    nps="Smith, William E., 11th Rhode Island Infantry, Company H, private in and out, microfilm M555 roll 6",
    notes=["The stone is badly worn. Only LL, E. SMITH and the unit line can be read; \"William\" comes from the PV001 list and the index, both of which have a William E. Smith in Company H of the 11th Rhode Island. The identification is probable, not certain.",
           "The PV001 list gives his death as March 27, 1918, which is later than his neighbors' (1915–1916). The stone's date line has not been read."]),
 "B24": dict(carved="ISAIAH B. MONRO[E] / Co. G 2 R.I. Vol. / [Di]ed Jan. 8, 1916", photo=_ph, died_text="January 8, 1916", pv001="1916", **_rb,
    nps="Munroe, Isaiah B. (filed under Isaiah B. Monroe), 2nd Rhode Island Infantry, Company G, private in and out, microfilm M555 roll 5"),
})

# Row C, read on site 11 Nov 2026 (close frames, wet where noted; oblique and enhanced frames for C4) and checked
# the same afternoon against the PV001 list. The NPS index has not been searched for the new names.
_rc = dict(chenery=None, photo="2026-11-11 10:00")
_un = dict(nps="unsearched", **_rc)
STONES.update({
 "C2": dict(carved="CONSTANTINE G. W. BISCHOFF / Co. F. 5 R.I. H. Art. / Died Nov. 9, 1915", died_text="November 9, 1915", pv001="1915", **_un,
    notes=["The surname was read from the stone after it was wetted; the first initial reads G or C, and is given as G as read at the stone."]),
 "C3": dict(carved="CHARLES N. DOWNE[S] / Co. C. 16 Maine Vol. / Died Aug. 27, 1915", died_text="August 27, 1915", pv001="1915", **_un,
    notes=["The last letter of the surname runs off the worn edge; the PV001 list has a Charles N. Downes, Company C, 16th Maine, died 1915."]),
 "C4": dict(carved="[?????] [?]. CON[????] / Co. H. 4 R.I. Vol. / Died Apr. 12, 1915", died_text="April 12, 1915", pv001="1915", **_un,
    notes=["The top line is nearly worn away. Only CON can be read with confidence; the given name looks about five letters long, and there may be a middle initial. \"James Conley\" is a provisional reading made at the stone, and the PV001 list has a James Conley, Company H, 4th Rhode Island Volunteers, died 1915. The company roster of the 4th Rhode Island will confirm it or not.",
           "A photograph in low, raking light on an overcast day may recover more of the name."]),
 "C5": dict(carved="FREDERICK LEWI[S] / Co. H. 37 U.S. Inf. / Died May 16, 1915", died_text="May 16, 1915", pv001="1915", **_un,
    notes=["The 37th U.S. Infantry was a regular-army regiment that existed from 1866 to 1869. Whether he also served in the Civil War is not yet established."]),
 "C6": dict(carved="CHARLES H. SMITH / Co. H. 3 R.I. Cav. / [Died] Mar. 7, 1915", died_text="March 7, 1915", pv001="1916", **_un,
    notes=["The PV001 list has a Charles H. Smith of the 3rd Rhode Island Cavalry who died in 1916; the stone reads 1915. Is this the same man, and which year is right? His death record will settle it.",
           "The list has other Charles H. Smiths, one of whom also died in 1915 (1st Rhode Island Militia and 5th Rhode Island Battery). With so common a name, the unit on the stone is the best guide."]),
 "C7": dict(carved="JOSEPH E. BROOKS / Co. A. 1 R.I. Lt. Art. / Died Feb. 13, 1915", died_text="February 13, 1915", pv001="1915", **_un,
    notes=["The stone says Company A; the 1st Rhode Island Light Artillery was organized in batteries, so this is Battery A."]),
 "C8": dict(carved="JOHN SMITH / 68 N. York Vol. / Died Aug. 10, 1914", died_text="August 10, 1914", pv001="1914", **_un,
    notes=["The stone gives no company. With so common a name, the regiment is the only guide to his service record."]),
 "C9": dict(carved="ROBERT HOLLIDAY / Co. A. 168 N. York Vol. / Died July 24, 1914", died_text="July 24, 1914", pv001="1914", **_un),
 "C10": dict(carved="JAMES MULLE[N] / U.S. Navy / Feb. 8, 1914", died_text="February 8, 1914", pv001="1914", **_un,
    notes=["Which ship or ships did he serve on? The Navy's enlistment records and the NPS sailors index have not yet been searched."]),
 "C11": dict(carved="EUGENE K. ELLIS / Co. H. 12 Maine Inf. / Jan. 13, 1914", died_text="January 13, 1914", pv001="1914", **_un),
 "C12": dict(carved="JAMES M. PIERC[E] / Bat. F. 1 R.I. L.A. / Jan. 9, 191[4?]", died_text="January 9, 1914", pv001="1914", **_un,
    notes=["Soil covers the end of the surname and the last digit of the year; 1914 is read from the PV001 list and the order of the row."]),
 "C13": dict(carved="GEORGE W. HARVE[Y] / Co. D. 2 R.I. Vol. / Aug. 20, 1913", died_text="August 20, 1913", pv001="1913", **_un),
 "C15": dict(carved="PHILIP H. L. GILBERT / Co. G. 1 Mass. H. Art. / June 29, 1913", died_text="June 29, 1913", pv001="1913", **_un),
 "C16": dict(carved="LEO FRAZIER / Co. A. 17 Vt. Inf. / Apr. 18, 1913", died_text="April 18, 1913", pv001="1913", **_un,
    notes=["There is a wide gap after LEO, partly under grass. Was he Leo or Leon? The regiment's roster will say."]),
 "C17": dict(carved="DANIEL McCRILLIS / Co. B. 1 Mass. Cav. / Mar. 8, 1913", died_text="March 8, 1913", pv001="1913", **_un,
    notes=["The PV001 list gives him a middle initial I; the stone has none."]),
 "C18": dict(carved="[E]LIAS H. MATHEWSO[N] / Bat. E. 1 R.I. L. Art. / Died Oct. 12, 1912", died_text="October 12, 1912", pv001="1912", **_un,
    notes=["The stone gives his middle initial as H; the PV001 list gives Elias E. Mathewson. The stone is followed here; his service record will settle it."]),
 "C19": dict(carved="BENJAMIN BENSO[N] / Co. K. 13 Conn. Vol. / Died Nov. 7, 1912", died_text="November 7, 1912", pv001="1912", **_un),
 "C20": dict(carved="JOSEPH D. TAYLOR / Co. D. 4 R.I. Vol. / Died May 15, 1912", died_text="May 15, 1912", pv001="1912", **_un),
 "C21": dict(carved="WILLIAM H. SMITH / Co. H. 29. Conn. Vol. / Died Apr. 24, 1912", died_text="April 24, 1912", pv001="1912", **_un,
    notes=["With so common a name, the regiment and company on the stone are the guide to his service record."]),
 "C22": dict(carved="JOHN CRAWFORD / Co. B. 198 Penn. Vols. / Died Feb. 4, 1912", died_text="February 4, 1912", pv001="1912", **_un),
 "C25": dict(carved="[TH]OMAS HALL / Co. E. 1 Mass. Heavy Art. / Died Dec. 8, 1911", died_text="December 8, 1911", pv001="1911", **_un),
})
STONES["C1"].update(carved="[CH]ARLES A. JACKSO[N] / Co. B. 11 U.S. H. Art. / Died Nov. 11, 1915", photo="2026-11-11 10:00",
    nps_note="The stone names the unit as the 11th U.S. Heavy Artillery, which is the 14th Rhode Island under its later designation.",
    notes=["The PV001 list gives his death as March 29, 1905. The stone reads November 11, 1915, and the stone is followed here."])
STONES["C23"].update(carved="[THEO]DORE WILLIAM[S] / Co. L. 14 R.I. H. Art. / Died Jan. 20, 1912", photo="2026-11-11 10:00", pv001="1912")
STONES["C24"].update(carved="WILLIAM I. BUTLER / Co. H. 2 U.S. Inf. Col. / Died Jan. 15, 1912", photo="2026-11-11 10:00",
    nps_note="The stone gives the middle initial as I, a single narrow stroke with no room for an H; the index card gives H. Unit and company agree.")

CHENERY = ("William H. Chenery, *The Fourteenth Regiment Rhode Island Heavy Artillery (Colored) in the War "
           "to Preserve the Union, 1861–1865* (Providence: Snow & Farnham, 1898)")
NPS_URL = "https://www.nps.gov/civilwar/soldiers-and-sailors-database.htm"


MONTHS = "January February March April May June July August September October November December".split()


def photo_when(photo):
    """'IMG_1234' -> '2026 (IMG_1234)'; '2025-04-07 12:43' -> 'April 7, 2025'."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", photo or "")
    if m:
        return f"{MONTHS[int(m.group(2))-1]} {int(m.group(3))}, {m.group(1)}"
    return f"2026 ({photo})"


def slug(name_full):
    words = [re.sub(r"[^a-z]", "", w.lower()) for w in name_full.split()]
    words = [w for w in words if w]
    return words[-1]


def is14(unit):
    return "14th Rhode Island" in unit


def company_phrase(unit, company, rank):
    u = unit.replace(" (USCT)", "").replace("US Colored", "U.S. Colored")
    parts = []
    if rank:
        parts.append(rank)
    if company:
        parts.append(f"Co. {company}")
    parts.append(u)
    return ", ".join(parts)


def make(r, s):
    grid, carved, full = r["grid"], r["name_carved"], r["name_full"]
    unit, co, rank, status = r["unit"], r["company"], r["rank"], r["status"]
    sl = s.get("slug") or slug(full)
    srcs = []
    sheet_only = not s.get("photo")
    if sheet_only:
        srcs.append(f"Prescott Post plot survey sheet, grave {grid}, compiled by Bernard Brennan, 2026: name, unit and date of death as read on site. "
                    f"The stone has not yet been photographed.")
    else:
        srcs.append(f"Gravestone of {full}, grave {grid}, Prescott Post plot, North Burial Ground, Providence, Rhode Island. "
                    f"Photograph by Bernard Brennan, {photo_when(s['photo'])}; transcription as recorded in the plot register.")
    n_stone = 1
    n_nps = n_chen = n_pv = None
    if s.get("nps") != "unsearched":
        srcs.append(f"National Park Service, Civil War Soldiers and Sailors Database, search for \"{full}\" "
                    f"({unit.replace(' (USCT)', '')}); accessed {s.get('nps_accessed', 'October 31, 2026')}, {NPS_URL}.")
        n_nps = len(srcs)
    if s.get("chenery"):
        srcs.append(f"{CHENERY}, {s['chenery']}.")
        n_chen = len(srcs)
    if s.get("pv001"):
        srcs.append(f"James Bessel, list of Civil War veterans buried at North Burial Ground (PV001), 2022, entry for {full}.")
        n_pv = len(srcs)

    # ---- Life
    life = []
    unit_c = unit.replace(" (USCT)", "").replace("US Colored", "U.S. Colored")
    first = f"{full} lies in grave {grid} of the Prescott Post lot. " + ("The plot survey records his stone as naming his unit as " if sheet_only else "His stone names his unit as ")
    if unit_c:
        first += f"Company {co} of the {unit_c}" if co else unit_c
    else:
        first = f"The stone in grave {grid} of the Prescott Post lot has been read only as far as {carved.upper()}; the man it names is not yet identified"
    first += (f", and gives his death as {s['died_text']}. [{n_stone}]" if s.get("died_text") else f". No date of death has been read from it. [{n_stone}]")
    life.append(first)
    if s.get("nps") == "unsearched":
        life.append("The National Park Service's index of Civil War soldiers and sailors has not yet been searched for him.")
    elif s.get("nps"):
        lead = ("The National Park Service's index of Civil War soldiers, which files the 14th Rhode Island under its later "
                "name, the 11th U.S. Colored Heavy Artillery, lists " if is14(unit)
                else "The National Park Service's index of Civil War soldiers lists ")
        life.append(f"{lead}{s['nps']}. [{n_nps}]" + (f" {s['nps_note']}" if s.get("nps_note") else ""))
    else:
        life.append(f"{s.get('nps_note','')} [{n_nps}]".strip())
    if n_chen:
        life.append(f"He appears in the roster of the regiment's 1898 history, page {s['chenery']}. [{n_chen}]")
    if n_pv:
        life.append(f"A 2022 list of Civil War veterans buried at North Burial Ground gives his death as {s['pv001']}. [{n_pv}]")
    life.append("His service record, any pension file, and his life before and after the war have not yet been researched. "
                "This page will grow as the records are read.")

    # ---- What we don't know
    wdk = []
    for n in s.get("notes", []):
        wdk.append(n)
    if sheet_only:
        wdk.append("What exactly does the stone say? It has not yet been photographed; the name, unit and date here are from the survey sheet.")
    wdk += [
        "When and where did he enlist, and what did his company do? His compiled military service record (National Archives, RG 94) will say.",
        "Did he or his widow apply for a pension? The General Index to Pension Files (NARA T288/T289) has not yet been searched for him.",
        "Where was he born, and how did he come to Providence?",
        "Where did he live and work in Providence? The city directories and the censuses of 1870–1920 have not yet been read for him.",
        "Did he marry, and did he leave children?",
        "When was he buried here, and what does the City's interment record say? The City lot record has not yet been matched.",
    ]

    if sheet_only and s.get("carved"):
        stone_section = (f"{s['carved']}\n\nAs recorded on the plot survey sheet; the stone has not been photographed and the rest of the "
                         f"inscription has not been read. [{n_stone}]")
    elif sheet_only:
        sheet_bits = [carved] + ([f"Co. {co}" if co else ""]) + [unit_c] + ([rank] if rank else []) + ([f"died {s['died_text']}"] if s.get("died_text") else [])
        stone_section = ("Not yet photographed. The plot survey sheet records: " + ", ".join(b for b in sheet_bits if b) +
                         f". A photograph is wanted; see the help page. [{n_stone}]")
    else:
        stone_section = (f"{s['carved']}\n\nTranscription as recorded in the plot register from the photograph; square brackets mark "
                         f"letters not legible or below ground. Photograph by B. Brennan, {photo_when(s['photo'])}. [{n_stone}]"
                         + (f" {s['stone_note']}" if s.get("stone_note") else ""))
    rank_line = f'"{rank} [stone; NPS index]"' if rank else '""'
    variants = [f"{full} [stone]"]
    if s.get("nps") and s["nps"] not in ("unsearched",):
        nps_name = s["nps"].split(",")[0] + ", " + s["nps"].split(",")[1].strip()
        if nps_name.lower() != f"{full.split()[-1]}, {' '.join(full.split()[:-1])}".lower():
            variants.append(f"{nps_name} [NPS index]")
    var_yaml = "[" + ", ".join(f'"{v}"' for v in variants) + "]"
    died = r["died"]

    fm = f'''---
grid: "{grid}"
name_carved: "{carved}"
name_full: "{full}"
variants: {var_yaml}
unit: "{unit_c}"
company: "{co}"
rank_highest: {rank_line}
rank_at_discharge: ""
born: ""
birthplace: ""
died: "{died}"
death_place: ""
interred: ""
city_lot_ref: ""
status: "{status}"
researchers: ["Bernard Brennan"]
second_reader: ""
last_revised: "{REV}"
records_dir: records/{grid}/
---
'''
    sub = company_phrase(unit, co, rank)
    if died:
        sub += f" · died {died}" if not any(ch in died for ch in "X?") else ""
    body = f"""
# {carved}

{sub}

## Life

{(chr(10)*2).join(life)}

## The stone

{stone_section}

## The records

- `records/{grid}/stone-2026.jpg` — Headstone of {full}, grid {grid}, Prescott Post lot, photographed {photo_when(s['photo']) if s.get('photo') else '2026'}. [{n_stone}]

## What we don't know

{chr(10).join('- ' + w for w in wdk)}

## Sources

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(srcs))}

## Credits

Researched by Bernard Brennan. Records courtesy City of Providence, Department of Parks, North Burial Ground. Revised {REV}.

<!-- Editor's note (not for publication): stone-only page generated by tools/stone_only.py from the
     register, {REV}. Replace with a researched dossier in the template when the records are read. -->
"""
    return f"{grid}-{sl}.md", fm + body


def main():
    force = set(sys.argv[2:]) if len(sys.argv) > 1 and sys.argv[1] == "--force" else set()
    rows = {r["grid"]: r for r in csv.DictReader(open(ROOT / "register.csv", newline=""))}
    out = ROOT / "veterans"
    for grid, s in STONES.items():
        r = rows[grid]
        fname, text = make(r, s)
        path = out / fname
        if path.exists() and grid not in force:
            print("skip (exists)", fname)
            continue
        path.write_text(text, encoding="utf-8")
        print("wrote", fname)


if __name__ == "__main__":
    main()
