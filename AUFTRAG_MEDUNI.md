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

---

## Runde 2: was noch fehlt

Nachtrag vom 22.08.2026, nach dem Einpflegen der ersten Lieferung. Stand MedUni
Wien im Datensatz:

| Jahr | erfasst | Einschätzung |
|---|---|---|
| 2014 | 3 | außerhalb des Auftrags, aus Runde 1 mitgekommen |
| 2015 | 3 | lückenhaft |
| 2016 | **0** | vollständig offen |
| 2017 | 4 | lückenhaft |
| 2018 | 5 | plausibel, aber prüfen |
| 2019 | **3** | lückenhaft |
| 2020 | 11 | wirkt vollständig |
| 2021 | 6 | lückenhaft |
| 2022 | **2** | vollständig offen |
| 2023 | 5 | lückenhaft |
| 2024 | 6 | lückenhaft |
| 2025 | 10 | erfasst |
| 2026 | **0** | vollständig offen |

Die MedUni beruft im Schnitt 10 bis 12 Professuren im Jahr. Fehlen also rund 40 bis
50 Personen, der Schwerpunkt liegt auf 2016, 2019, 2022 und 2026.

### Aufträge, nach Wert sortiert

1. **2016, 2022 und 2026** von vorne aufarbeiten. Für diese drei Jahre gibt es fast
   nichts, dort ist der Ertrag pro Suchstunde am höchsten.
2. **2015, 2017, 2019, 2021, 2023, 2024** auffüllen. Die vorhandenen Einträge sind
   belegt, es fehlt der Rest des Jahrgangs.
3. **Drei ungeklärte Fälle aus Runde 1 nachliefern**, sie liegen mit Begründung in
   `scripts/pruefung/meduni_verworfen.json`: Kathryn Hoffmann (Primary Care Medicine,
   Quelle nennt kein Antrittsdatum), Maxim Zaitsev (dito), Roland Beisteiner
   (Quellenlink liefert 404, bitte durch eine erreichbare Quelle ersetzen).
4. **Zehn fehlende Geschlechtsangaben** ergänzen, aber nur aus der Quelle:
   Giulio Superti-Furga, Alwin Köhler, Edda Tschernko, Herwig Czech,
   Mariann Pavone-Gyöngyösi, Xiaohui Rausch-Fan, Gerhard Prager, Kaan Boztug,
   Tilman Kühn, Stanisa Raspopovic.
5. **Denominationen stichprobenartig gegen die Quelle prüfen.** Bei Alwin Köhler
   stand „Medizinische Biochemie" im Datensatz, die Quelle sagt „Mechanistische
   Zellbiologie".

### Quellenwege, die in Runde 1 offen geblieben sind

* **News-Rubrik „Menschen der MedUni Wien"** — eigene Kategorie für Personalien,
  aufgetaucht im Seitenkopf der Köhler-Meldung. Dort systematisch durchgehen.
* **OTS-Archiv pro Jahr** (`ots.at`, Suche nach „MedUni Wien Professur"). Mehrere
  der belegten Einträge stammen von dort, das Archiv ist vollständiger als die
  Uni-eigene News-Liste, besonders für 2016 bis 2019.
* **Antrittsvorlesungs-Ankündigungen** als PDF unter
  `meduniwien.ac.at/web/fileadmin/content/kommunikation/events/<jahr>/…`.
  Jede berufene Person hält eine, der Ankündigungstext nennt Denomination und oft
  den Dienstbeginn.
* **Webarchiv** der MedUni-News-Übersichten je Jahr, weil die heutige Liste
  gekürzt ist.
* **Kliniks- und Institutsseiten**: Leitungswechsel mit Datum („leitet die Abteilung
  seit …"). Vorsicht, Abteilungsleitung ist nicht automatisch eine Professur.

### Diese 58 Namen sind bereits erfasst, bitte nicht doppelt liefern

Alwin Köhler, Andreas Sönnichsen, Andreas Zuckermann, Angelika Berger, Balázs Hangya,
Bruno Podesser, Caroline Hutter, Christian Hengstenberg, Christian Loewe, Christoph
Arnoldner, Christoph Aufricht, Clemens Aigner, Daniel Aletaha, Daniel Zimpfer, Daniela
Gompelmann, Dietmar Georg, Edda Tschernko, Elisabeth Förster-Waldl, Eva Compérat, Eva
Schernhammer, Florian Krammer, Francesco Moscato, Georg Stary, Gerhard Prager, Giulio
Superti-Furga, Günther Steger, Herbert Kiss, Herwig Czech, Joachim Widder, Josef
Penninger, Judith Aberle, Julia Walochnik, Jürgen Knoblich, Kaan Boztug, Konrad
Hötzenecker, Marco Idzko, Mariann Pavone-Gyöngyösi, Martin Fischer, Matthias Preusser,
Michael Bonelli, Nikolaus Klupp, Oliver Kimberger, Oliver Strobel, Oskar Aszmann,
Pascal Baltzer, Paul Plener, Petra Heffeter, Romana Höftberger, Stanisa Raspopovic,
Stathis Megas, Stephan Polterauer, Thomas Berger, Thomas Scherer, Tilman Kühn, Ulrike
Attenberger, Walter Klepetko, Winfried Franz Pickl, Xiaohui Rausch-Fan

### Zwei Regeln, die in Runde 1 verletzt wurden

* **Das Antrittsdatum muss aus der Quelle stammen, nicht aus dem Meldedatum.** Sechs
  Einträge waren daneben, zwei davon um zwei Jahre (Podesser, Georg: Quelle nennt
  Oktober 2014, Datensatz sagte 2016). Wenn die Quelle nur „im Herbst" oder gar
  nichts sagt, gehört das in `_kuratiert`.
* **Die Quelle muss die Berufung an der MedUni Wien belegen.** Ein Eintrag stützte
  sich auf eine Meldung über eine Professur am Messerli-Institut der Vetmeduni, einer
  auf eine Berufung in das Danish Research Council. Beide Personen waren schon vorher
  MedUni-Professor:innen.

Neue Datei diesmal: `scripts/backfill/kuratiert_meduni2.json`, damit die erste
Lieferung unverändert bleibt.
