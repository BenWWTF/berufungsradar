# Auftrag: Berufungen der MedUni Wien 2015–2024 erfassen

Kurzbriefing für einen zweiten Agenten. Alles, was hier steht, ist an den anderen
acht Wiener Universitäten schon erledigt; für die MedUni fehlt der Bestand.

## Was gebraucht wird

Alle Berufungen von Universitätsprofessor:innen an der **Medizinischen Universität
Wien** in den Jahren **2015 bis 2024**, geschätzt 100 bis 120 Personen (10 bis 12
pro Jahr). 2025 ist bereits erfasst (10 Einträge), 2026 fehlt ebenfalls.

Ergebnis ist **eine JSON-Datei** nach dem unten beschriebenen Schema, abgelegt als
`scripts/backfill/kuratiert_meduni.json`. Nicht die Hauptdatei bearbeiten.

## Was schon geprüft wurde und nicht funktioniert

Bitte nicht wiederholen, das ist alles belegt:

* **Mitteilungsblatt der MedUni**: 745 Blätter von 2003/04 bis 2025/26 unter
  `meduniwien.ac.at/web/rechtliches/mitteilungsblaetter/`. Enthält Bevollmächtigungen,
  Curricula, Wahlergebnisse, Satzungsänderungen. Genau eine Datei nennt ein
  Berufungsverfahren, und zwar die Satzungsänderung zu §99 Abs. 4. Keine Berufungen
  mit Namen. Stichproben aus 2015/16, 2019/20 und 2023/24 im Volltext bestätigt.
  Dasselbe gilt für Uni Wien, WU, BOKU, Akademie und Vetmeduni: österreichische
  Mitteilungsblätter verlautbaren Verfahren, nicht Ergebnisse.
* **unidata.gv.at, Wissensbilanz, Universitätsbericht**: nur Bestandszahlen
  (Kennzahl 1.A.1, Köpfe je Personalkategorie und Geschlecht), keine Kennzahl
  „Berufungen", keine Namen.
* **Eine Übersichtsseite „Neue Professuren"** wie bei TU Wien oder mdw existiert
  bei der MedUni nicht.

## Wo es aussichtsreich ist

* **Presseinformationen der MedUni**, einzeln pro Berufung. Beispiel für den Ton:
  „Neue Professoren für Kardiologie und Pulmologie an der MedUni Wien". Diese
  Meldungen werden teils von Dritten gespiegelt (LISAvienna, APA-Science, OTS).
* **Antrittsvorlesungen**: `meduniwien.ac.at/web/ueber-uns/events/jaehrliche-events/antrittsvorlesungen/`
  Jede neu berufene Person hält eine. Die Seite zeigt nur aktuelle Termine, aber
  Ankündigungen und Rückblicke liegen als PDF unter
  `meduniwien.ac.at/web/fileadmin/content/kommunikation/events/<jahr>/…` und im
  Webarchiv. Beispiel gefunden: Wulf Haubensak, Professor für Neuronale
  Zellbiologie, Antrittsvorlesung 23.09.2022.
* **Webarchiv** (`web.archive.org/cdx/search/cdx?url=meduniwien.ac.at&matchType=domain&...`).
  Bei Uni Wien und Vetmeduni war das der Schlüssel, weil die heutigen Seiten ihre
  Inhalte per JavaScript nachladen. Nützlicher Trick: der Brotkrumenpfad
  archivierter Seiten nennt oft den Jahresordner der Meldung und korrigiert damit
  falsche Jahresschätzungen aus dem Snapshot-Datum.
* **Kliniks- und Institutsseiten** der MedUni nennen Leitungswechsel mit Datum.
* **Wikipedia/Wikidata** für prominente Fälle, aber nur als Bestätigung, nie als
  einzige Quelle.

## Datenschema

Eine Liste von Objekten. Pflichtfelder sind `name`, `universitat`, `monat`, `year`,
`quelle`. Alles andere weglassen, wenn die Quelle es nicht hergibt.

```json
[
 {
  "name": "Kathryn Hoffmann",
  "universitat": "MedUni Wien",
  "monat": "FEBRUAR",
  "year": 2023,
  "art_berufung": "§98",
  "forschungsbereich": "Primary Care Medicine",
  "fakultat": "Zentrum für Public Health",
  "geschlecht": "W",
  "herkunft": "intern",
  "herkunft_institution": "Medizinische Universität Wien",
  "herkunft_land": "Österreich",
  "quelle": "https://www.meduniwien.ac.at/web/…",
  "_kuratiert": "Handrecherche 2026-08-22 aus Presseinformation vom 01.02.2023",
  "stufe": 1
 }
]
```

Feldregeln:

| Feld | Regel |
|---|---|
| `universitat` | immer genau `"MedUni Wien"` |
| `monat` | Großbuchstaben, deutsch: `JÄNNER FEBRUAR MÄRZ APRIL MAI JUNI JULI AUGUST SEPTEMBER OKTOBER NOVEMBER DEZEMBER` |
| `year` | Jahr des Dienstbeginns, nicht das Jahr der Meldung |
| `art_berufung` | `§98`, `§99(1)`, `§99(4)`, `§99(5)` — nur wenn die Quelle den Paragrafen nennt, sonst weglassen |
| `geschlecht` | `W` oder `M`, **nur** wenn die Quelle es sagt („neue Professorin", „er"). Nicht aus dem Vornamen raten, das macht die Pipeline dokumentiert selbst |
| `herkunft` | `intern` wenn die vorige Stelle an der MedUni Wien war, sonst `extern`. Nur wenn die Quelle die Vorstation nennt |
| `herkunft_land` | ausgeschriebener deutscher Ländername (`Deutschland`, `Großbritannien`, `USA`, `Schweiz` …) |
| `quelle` | direkter Link auf die Meldung, pro Person |
| `_kuratiert` | Datum der Recherche plus Herkunft der Angabe; **jede Unsicherheit hier vermerken**, z. B. „Monat nicht genannt, Monat der Meldung übernommen" |
| `stufe` | immer `1` |

## Harte Regeln aus den bisherigen Durchgängen

1. **Nicht raten.** Eine Lücke ist besser als ein falscher Wert. Wenn Monat oder
   Jahr unklar sind, den Eintrag entweder weglassen oder die Unsicherheit in
   `_kuratiert` schreiben. Drei Fälle bei der Vetmeduni wurden aus diesem Grund
   verworfen.
2. **Keine Regex-Ernte aus Fließtext.** Ein Versuch, Pressemeldungen automatisch zu
   parsen, hat falsche Monate produziert (Beginn Jänner 2026 wurde zu Oktober 2025).
   Bei überschaubaren Mengen ist Lesen genauer.
3. **Verfahren ist nicht Berufung.** Ausschreibungen, Hearings, Berufungskommissionen
   und Bewerber:innenlisten gehören nicht in die Daten. Es zählt der Dienstbeginn.
4. **Keine Gastprofessuren, keine Titularprofessuren, keine Verlängerungen**, keine
   Assistenzprofessuren (Tenure-Track-Einstieg) — nur Professuren nach §98 oder §99.
   Assoziierte Professuren nach §99 Abs. 4 gehören dazu und werden so markiert.
5. **Ordinalpunkte im Datum** („mit 1. Oktober") haben in drei Parsern Sätze
   zerschnitten. Falls doch automatisiert wird: vorher den Punkt vor Monatsnamen
   entfernen.

## Einpflegen

```bash
cd ~/Desktop/berufungsradar
python3 scripts/merge_backfill.py --dry     # zeigt, was neu wäre
python3 scripts/merge_backfill.py           # führt ein, überschreibt nie Kuratiertes
python3 scripts/classify_ofos.py            # ÖFOS-Zuordnung, meldet offene Fälle
bash scripts/update.sh                      # OpenAlex, Anreicherung, Herkunft, Build
```

`merge_backfill.py` gleicht Namen mit ausgeschriebenen Umlauten ab (Steinböck =
Steinboeck) und vergleicht zusätzlich nur Vor- und Nachnamen, Mittelnamen fallen
weg. Bestehende Datensätze werden nie überschrieben, leere Felder dürfen gefüllt
werden.

Fehlt für ein Fach eine ÖFOS-Regel, meldet `classify_ofos.py` das namentlich; die
Regel gehört dann in die Liste `STICHWORT` in derselben Datei. Für Medizin sind 301
(Grundlagenmedizin), 302 (Klinische Medizin), 303 (Gesundheitswissenschaften), 304
(Medizinische Biotechnologie) und 206 (Medizintechnik) vorbereitet.

Zum Schluss `datenabdeckung.json` aktualisieren: je Universität die Jahre, die
`vollstaendig` oder `teilweise` erfasst sind, plus eine Quellenangabe. Die Matrix
auf der Übersichtsseite liest daraus und macht Lücken sichtbar, statt sie als
„keine Berufungen" erscheinen zu lassen.

## Kontext

* Repository: `~/Desktop/berufungsradar`, GitHub `BenWWTF/berufungsradar`
* Dashboard: https://benwwtf.github.io/berufungsradar
* Methodenbericht mit allen Quellenbefunden: `SPEC.md`, Abschnitt 2a
* Aktueller Bestand: 565 Datensätze, 2014 bis 2026, neun Universitäten

---

## Ergebnis der ersten Runde (22.08.2026)

Geliefert wurden 55 Einträge. Nach Prüfung gegen die Quellen sind **48 übernommen**,
**7 verworfen** (`scripts/pruefung/meduni_verworfen.json`), **6 Daten korrigiert**.

Was die Prüfung ergab, als Muster für die nächste Runde:

* 54 der 55 Quellen-Links waren erreichbar und enthielten den Namen. Das ist gut,
  die Quellenarbeit stimmt.
* Bei **6 Einträgen nannte die Quelle ein anderes Antrittsdatum** als der Datensatz:
  Berger Oktober 2014 statt Februar 2015, Aufricht August 2015 statt Mai 2015,
  Podesser und Georg jeweils Oktober 2014 statt 2016, Strobel Jänner statt Oktober
  2021, Fischer Mai statt Juli 2023. Alle sechs sind korrigiert.
* **3 Einträge stützten sich auf Meldungen von 2011**, lagen also außerhalb des
  Zeitraums (Breiteneder, Bohle) oder betrafen ein anderes Ereignis
  (Jensen-Jarolim: eine Professur am Messerli-Institut der **Vetmeduni**).
* **1 Eintrag** beruhte auf einer Meldung über eine Berufung in das *Danish Research
  Council* (Barta), das ist keine Professur.
* **3 Einträge** waren nicht prüfbar: kein Antrittsdatum auf der Seite (Hoffmann,
  Zaitsev) oder 404 (Beisteiner).
* Bei **15 Einträgen** nennt die Quelle nur das Jahr. Der Monat stammt aus dem
  Meldedatum; das steht jetzt so in `_kuratiert` und ist damit zulässig.
* **Geschlecht war bei keinem der 55 Einträge gesetzt.** Bei MedUni-Meldungen steht
  es fast immer im Text („neue Professorin", „er übernimmt"). Bitte nachziehen, das
  ist eine der Kernauswertungen des Dashboards.
* Ein Feldfehler: bei Alwin Köhler nennt die Quelle „Mechanistische Zellbiologie",
  im Datensatz stand „Medizinische Biochemie". Solche Denominationen bitte wörtlich
  aus der Quelle übernehmen.

Offen bleiben 2016 (kein belegter Fall) sowie die Frage, ob 2019 mit drei und 2022
mit zwei Berufungen vollständig sind. MedUni beruft im Schnitt 10 bis 12 pro Jahr,
die Jahre 2015 bis 2019 und 2022 sind also sicher noch lückenhaft.
