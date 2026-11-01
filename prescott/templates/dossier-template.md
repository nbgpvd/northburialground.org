---
# Dossier template — Prescott Post Digital Companion
# One file per stone: veterans/<GRID>-<surname>.md
# Front matter is read by build.py; everything below the second --- is the page body.
# Never fill a field to fill it. Blank means blank; explain under "What we don't know."
grid: ""                 # e.g. G3
name_carved: ""          # exactly as cut, caps as cut; this is the page title
name_full: ""            # best-documented full name; used in the text
variants: []             # every spelling met in any record, with the record in brackets
unit: ""                 # as documented, not as carved, if they differ (say so in notes)
company: ""
rank_highest: ""         # highest rank held, with the record that shows it
rank_at_discharge: ""
born: ""                 # ISO date or year; "" if unknown
birthplace: ""
died: ""                 # ISO
death_place: ""
interred: ""             # ISO date of interment in THIS plot (not death, not first burial)
city_lot_ref: ""         # City's lot/grave reference, only as approved for publication
status: ""               # stone-only | identified | draft | complete  (highest step FINISHED)
researchers: []          # people, in order of contribution
second_reader: ""        # required for status: complete
last_revised: ""         # ISO
records_dir: records/<GRID>/
---

# {{name_carved}}

<!-- Plain, one line under the title: unit and dates as documented. -->

## Life
<!-- 150–300 words for a phone in bright sun. Declarative sentences. His actions first.
     No adjectives doing the work of evidence. Every sentence traceable to a numbered
     entry in Sources, cited inline as [n]. -->

## The stone
<!-- Transcription line by line as carved, with / between lines. Condition. Photo ref.
     What the stone says that the record contradicts, and what it omits. -->

## The records
<!-- One line per hosted record in records/<GRID>/: filename — caption — citation [n].
     Only NARA (public domain), City records Annalisa has approved, and our own photos.
     Everything else is a link in Sources, not an image. -->

## What we don't know
<!-- Bullets. Silences in the record and open questions, stated as questions.
     This section is published. -->

## Sources
<!-- Chicago notes-bibliography, numbered. NARA: record group, series/entry, file.
     Pensions: certificate or application number. Newspapers: title, date, page.
     Links out (Find a Grave, NPS Soldiers and Sailors, FamilySearch, NARA catalog) go here. -->

## Credits
<!-- Researched by … . Records courtesy City of Providence, Department of Parks,
     North Burial Ground. Revised {{last_revised}}. -->
