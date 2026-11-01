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
REV = "2026-11-01"

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
 "A17": dict(carved="NATHANIEL MOS[E]LEY / Co. I. 1 U.S. Cav. / Died Dec. 3, 1919", photo="IMG_1745",
    nps="unsearched", chenery=None, pv001=None, died_text="December 3, 1919",
    notes=["His place in the row is inferred, not surveyed: the stone was photographed between A12 and A19, and a December 1919 death fits the one unrecorded place between A16 (August 1920) and A18 (December 1919). It should be confirmed on site.",
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
}

CHENERY = ("William H. Chenery, *The Fourteenth Regiment Rhode Island Heavy Artillery (Colored) in the War "
           "to Preserve the Union, 1861–1865* (Providence: Snow & Farnham, 1898)")
NPS_URL = "https://www.nps.gov/civilwar/soldiers-and-sailors-database.htm"


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
    sl = slug(full)
    srcs = []
    sheet_only = not s.get("photo")
    if sheet_only:
        srcs.append(f"Prescott Post plot survey sheet, grave {grid}, compiled by Bernard Brennan, 2026: name, unit and date of death as read on site. "
                    f"The stone has not yet been photographed.")
    else:
        srcs.append(f"Gravestone of {full}, grave {grid}, Prescott Post plot, North Burial Ground, Providence, Rhode Island. "
                    f"Photograph by Bernard Brennan ({s['photo']}), 2026; transcription as recorded in the plot register.")
    n_stone = 1
    n_nps = n_chen = n_pv = None
    if s.get("nps") != "unsearched":
        srcs.append(f"National Park Service, Civil War Soldiers and Sailors Database, search for \"{full}\" "
                    f"({unit.replace(' (USCT)', '')}); accessed October 31, 2026, {NPS_URL}.")
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
    first += f"Company {co} of the {unit_c}" if co else unit_c
    first += f", and gives his death as {s['died_text']}. [{n_stone}]"
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

    if sheet_only:
        sheet_bits = [carved] + ([f"Co. {co}" if co else ""]) + [unit_c] + ([rank] if rank else []) + ([f"died {s['died_text']}"] if s.get("died_text") else [])
        stone_section = ("Not yet photographed. The plot survey sheet records: " + ", ".join(b for b in sheet_bits if b) +
                         f". A photograph is wanted; see the help page. [{n_stone}]")
    else:
        stone_section = (f"{s['carved']}\n\nTranscription as recorded in the plot register from the photograph; square brackets mark "
                         f"letters not legible or below ground. Photograph {s['photo']} (B. Brennan). [{n_stone}]")
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

- `records/{grid}/stone-2026.jpg` — Headstone of {full}, grid {grid}, Prescott Post lot, 2026{(' (' + s['photo'] + ')') if s.get('photo') else ''}. [{n_stone}]

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
