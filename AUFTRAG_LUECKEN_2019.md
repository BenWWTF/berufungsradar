# Aufträge: Lücken 2019 bis 2026 schließen

Der Auswertungszeitraum des Berufungsradars ist auf **2019 bis 2026** festgelegt
(Begründung in `SPEC.md`, Abschnitt 2b). Bestand: 537 Datensätze. Geschätzt fehlen
noch **311 Berufungen**. Diese Datei beschreibt vier Aufträge, nach Wert sortiert.

Gemeinsame Grundlagen für alle vier: Datenschema und Feldregeln stehen in
`AUFTRAG_MEDUNI.md`, Abschnitt „Datenschema". Bereits geprüfte Sackgassen stehen in
`SPEC.md`, Abschnitt 2a.

## Fehlende Berufungen je Uni und Jahr

```
                  2019  2020  2021  2022  2023  2024  2025  2026  fehlt
TU Wien             ok    ok    ok    ok    ok    ok    ok    ok      0
mdw                 ok    ok    ok    ok    ok    ok    ok    ok      0
Uni Wien            11     7    25    30    30    30    ok    30    163
WU Wien              7     0     0     7     7     7    ok     7     35
BOKU                ok    ok     4     5     8     7    ok     8     32
MedUni Wien          6    ok     5     9    ok    ok    ok     9     29
Angewandte           4     4     1     6     0     6    ok    ok     21
Vetmeduni Wien       3     3     3     1     2     1    ok     3     16
Akademie             5     5     0     0     0     2    ok     3     15
```

„ok" heißt: für dieses Jahr ist eine Quelle ausgewertet, die alle Berufungen nennt.
Die Zahlen sind Schätzungen aus dem erwarteten Jahresvolumen minus dem Erfassten.

---

## Auftrag 1: Uni Wien 2021 bis 2024 und 2026 — 163 Berufungen

Der mit Abstand größte Posten, mehr als die Hälfte aller Lücken.

**Was vorliegt:** 139 Datensätze, davon 2019 mit 19 und 2020 mit 23 aus dem
Webarchiv, 2025 vollständig kuratiert. Ab 2021 bricht es ab, weil das Webarchiv
dort endet.

**Was geprüft und tot ist:**
* Die heutige Seite `univie.ac.at/aktuelles/neue-professuren` lädt ihre Inhalte per
  JavaScript, im HTML steht kein einziger Name.
* Das Mitteilungsblatt `mtbl.univie.ac.at` führt 5213 Artikel von 2002 bis 2026.
  Davon nennen 355 eine Berufungs**kommission**, aber nur ein einziger überhaupt
  das Wort „Professur", „berufen" oder „Ruf" — und der ist auch nur eine
  Kommissionswahl. Verlautbart wird das Verfahren, nicht das Ergebnis.
* Die CV-Seiten im Webarchiv (`medienportal.univie.ac.at/uniview/professuren/cv/`)
  sind ausgewertet, 379 Stück, davon 116 verwertbar. Sie enden 2021.

**Was noch offen ist, in dieser Reihenfolge:**
1. **Wissensbilanz der Uni Wien.** Bei der BOKU war genau das der Durchbruch: ihre
   Wissensbilanz listet ab 2017 alle Berufungen namentlich mit Fach und Paragraf.
   Die Uni-Wien-Wissensbilanzen liegen unter
   `public.univie.ac.at/fileadmin/user_upload/d_oeffentlichkeitsarbeit/Dokumente/`
   (Beispiel: `LB_2019_webinteraktiv.pdf`). Ich habe darin nur die Kennzahlen
   geprüft, nicht den qualitativen Teil. Prüf zuerst, ob dort eine namentliche
   Berufungsliste steht. Wenn ja, sind 2021 bis 2024 in einem Zug erledigt.
2. **Rudolphina und uni:view.** Das Wissenschaftsmagazin der Uni Wien porträtiert
   neu Berufene. `rudolphina.univie.ac.at`, Rubriken zu Personen und Professuren.
3. **Fakultätsseiten und Institutsnachrichten.** Die 20 Fakultäten melden
   Neuberufungen einzeln, oft mit Datum.
4. **OTS und APA-Science**, gefiltert auf „Universität Wien Professur".
5. **Webarchiv der neuen Seite** `univie.ac.at/aktuelles/neue-professuren`. Auch
   wenn die Live-Seite JavaScript nutzt, könnten ältere Snapshots gerenderte
   Fassungen enthalten.

**Ziel:** `scripts/backfill/kuratiert_univie2.json`

---

## Auftrag 2: WU Wien 2019, 2022 bis 2024, 2026 — 35 Berufungen

**Was vorliegt:** 38 Datensätze. 2016 bis 2021 sind aus den Presseaussendungen
kuratiert, 2025 vollständig.

**Das Problem:** Die Jahresarchive `wu.ac.at/presse/presseaussendungen/archiv/presseaussendungen-<jahr>`
liefern für 2019 und ab 2022 keine Meldungen im HTML, sie laden dynamisch nach.
Für 2016 bis 2021 funktionieren sie.

**Wege:** Webarchiv der Jahresarchive; die englische Fassung `wu.ac.at/en/press/`;
OTS; die Rubrik „News und Events" unter `wu.ac.at/universitaet/news-und-events/news`;
die WU-Wissensbilanz (siehe Auftrag 1, gleicher Ansatz).

**Ziel:** `scripts/backfill/kuratiert_wu2.json`

---

## Auftrag 3: BOKU 2021 bis 2024 und 2026 — 32 Berufungen

**Was vorliegt:** 48 Datensätze. 2017 bis 2020 sind über die Wissensbilanz
vollständig, 2025 kuratiert.

**Die Quelle ist bekannt und funktioniert:** Die BOKU-Wissensbilanz nennt ab 2017
alle Berufungen namentlich mit Fach, Paragraf und Vorinstitution. Beispiel aus
WB2017: „1. Astrid Gühnemann (University of Leeds), Verkehrswesen für eine
nachhaltige Entwicklung (§ 98)". Die Wissensbilanzen erscheinen als Beilage zum
Mitteilungsblatt, Pfadmuster:
`boku.ac.at/fileadmin/data/H01000/mitteilungsblatt/MB_<jjjj>_<jj>/MB<nn>/BOKU_Wissensbilanz<jahr>.pdf`

**Aufgabe:** Die Wissensbilanzen 2021, 2022, 2023 und 2024 finden und auslesen. Das
ist reine Fleißarbeit an einer bewährten Quelle, kein Suchproblem.

**Wichtig:** Die Wissensbilanz nennt nur das Kalenderjahr, keinen Monat. Setz
`"monat_unsicher": true` und lass den Monat weg oder trag ihn nur ein, wenn eine
zweite Quelle den Dienstbeginn nennt. Eine Antrittsvorlesung ist **nicht** der
Dienstbeginn, sie liegt oft ein bis zwei Jahre danach.

**Ziel:** `scripts/backfill/kuratiert_boku2.json`

---

## Auftrag 4: die drei kleinen Häuser — 52 Berufungen

Angewandte (21), Vetmeduni (16), Akademie (15). Kleine Fallzahlen, verstreute
Quellen, deshalb zusammen in einem Auftrag.

**Angewandte**, fehlen 2019 bis 2022 und 2024. Quelle ist das Pressearchiv
`dieangewandte.at/presse`, dort stehen Sammelmeldungen pro Studienjahr („startet
mit acht neuen Professuren"). Acht Meldungen sind ausgewertet, das Archiv hat 135.
Auch die News unter `dieangewandte.at/aktuell/news/news_archiv` prüfen.

**Vetmeduni**, fehlen 2019 bis 2024 durchgehend. Presseinformationen je Berufung,
im Webarchiv, weil die heutige Seite JavaScript nutzt. Pfadmuster der Ordner:
`vetmeduni.ac.at/…/presseinformationen/presseinformationen-<jahr>/<slug>`. Der
Brotkrumenpfad archivierter Seiten nennt den Jahresordner, das korrigiert falsche
Jahresschätzungen aus dem Snapshot-Datum.

**Akademie**, fehlen 2019, 2020, 2024 und 2026. News-Meldungen unter
`akbild.ac.at/de/news/<jahr>/<slug>`. Zwei Eigenheiten: die Namen stehen nur im
`og:description`-Tag, nicht im gerenderten Text, und die Seiten tragen kein
Veröffentlichungsdatum. Das Jahr ermittelst du, indem du den Slug unter mehreren
Jahrespfaden abfragst, bis einer mit HTTP 200 antwortet.

**Ziel:** `scripts/backfill/kuratiert_klein2.json` (alle drei Häuser in einer Datei,
das Feld `universitat` trennt sie)

---

## Fehler aus den bisherigen Runden, die nicht wiederkommen dürfen

Vier Runden mit zwei Agenten, hier die Bilanz der Ablehnungen:

1. **Antrittsdatum aus der Quelle, nicht aus dem Meldedatum.** Häufigster Fehler.
   In der MedUni-Runde 1 waren sechs Daten falsch, zwei davon um zwei Jahre.
2. **Die Quelle muss die Person nennen.** Fünf Einträge der MedUni-Runde 2 verwiesen
   auf Seiten, auf denen der Name nicht vorkommt. Vier weitere stützten sich auf
   eine Seite, deren einziges Datum aus dem Jahr 2004 stammte.
3. **Bestehende Datensätze prüfen, bevor du lieferst.** Neun Dubletten in einer
   einzigen Runde, obwohl das Briefing die erfassten Namen aufgelistet hatte. Lies
   `dashboard_data_2025.json` und filtere auf die Universität, an der du arbeitest.
4. **Antrittsvorlesung ist nicht Dienstbeginn.** In der BOKU-Runde waren dadurch
   fast alle Monate falsch und Josef Eitzinger zweimal erfasst.
5. **`art_berufung` nimmt nur `§98`, `§99(1)`, `§99(3)`, `§99(4)`, `§99(5)`.**
   Freitext wie „§99(5) Stiftungsprofessur (BMK)" fällt aus Filter und Badge heraus.
   Zusätzliche Angaben gehören in `_kuratiert`.
6. **Verfahren ist nicht Berufung.** Ausschreibungen, Hearings,
   Berufungskommissionen und Bewerberlisten gehören nicht in die Daten.
7. **Nichts vor 2019.** Der Merge übergeht solche Sätze und meldet die Zahl.

## Einpflegen

```bash
cd ~/Desktop/berufungsradar
python3 scripts/merge_backfill.py --dry
python3 scripts/merge_backfill.py
python3 scripts/classify_ofos.py     # meldet Fächer ohne ÖFOS-Regel namentlich
bash scripts/update.sh
```

Danach `datenabdeckung.json` für die bearbeitete Universität aktualisieren und den
Bericht als Datei unter `scripts/pruefung/` ablegen, nicht über einen
Nachrichtenkanal verschicken.
