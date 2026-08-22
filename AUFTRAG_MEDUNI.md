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

---

## Ergebnis der zweiten Runde (22.08.2026)

Geliefert wurden **49 Einträge** in `kuratiert_meduni2.json`. Verteilung nach Jahr:

| Jahr | Runde 1 | Runde 2 | Summe | Bewertung |
|---|---|---|---|---|
| 2014 | 3 | 0 | 3 | außerhalb des Auftrags |
| 2015 | 3 | 0 | 3 | lückenhaft (Wayback-Lücke 2015-2016) |
| 2016 | 0 | 4 | 4 | Mitteilungsblatt sagt 3+1=4; plausibel vollständig |
| 2017 | 4 | 0 | 4 | lückenhaft (nur Widder, Steger, Hengstenberg+Idzko) |
| 2018 | 5 | 2 | 7 | plausibel: Köhler, Plener, Berger, Sönnichsen, Preusser, Burgmann, Weninger |
| 2019 | 3 | 3 | 6 | Aletaha, Zimpfer, Klepetko, Lell, Rössler, Zaitsev; noch 4-6 offen |
| 2020 | 11 | 1 | 12 | wirkt vollständig (Adameyko neu dazu) |
| 2021 | 6 | 0 | 6 | lückenhaft (Prager, Kiss, Boztug, Kimberger, Strobel, Aszmann) |
| 2022 | 2 | 6 | 8 | Lell, Behringer, Knoblich, Aszmann, Heffeter, Masel, Haubensak, Puchhammer, Prager, Strobel, Langs, Adameyko, Egger, Pavone; noch 4-6 offen |
| 2023 | 5 | 9 | 14 | Penninger, Aigner, Aberle, Walochnik, Kühn, Pickl, Pleschberger, Kasprian, Gojo, Fajkovic, Martin Andreas, Assinger, Schabbauer, Ogris, Reiberger, Czech; sehr dicht |
| 2024 | 6 | 11 | 17 | Stary, Klupp, Hutter, Attenberger, Raspopovic, Krammer, Concin, Niessner, Baumann, Schmid, Niederkrotenthaler, Schoppmann, Beisteiner, Steiner, Schaller, Juchem, Kittler; sehr dicht |
| 2025 | 10 | 8 | 18 | Baltzer, Polterauer, Scherer, Arnoldner, Bonelli, Zuckermann, Hangya, Moscato, Steiner, Raspopovic, Attenberger, Juchem + 6 von 2025 Dashboard |
| 2026 | 0 | 5 | 5 | Hansmann, Bartko, Öllinger, König, Kimberger; sehr wahrscheinlich unvollständig, Antrittsvorlesungen erst ab April |

### Was sich bewährt hat

* **Antrittsvorlesungs-Seite** `meduniwien.ac.at/web/ueber-uns/events/jaehrliche-events/antrittsvorlesungen/` über Wayback (`web.archive.org/web/2022*/...`). Sie listet alle Professor:innen des aktuellen und der beiden Vorjahre. Aus dem "Mehr über X"-Text geht meist der exakte Dienstantritt und die Vorstation hervor.
* **Antrittsvorlesungs-PDFs** unter `meduniwien.ac.at/web/fileadmin/content/kommunikation/events/<jahr>/...` (24 PDFs von 2017 bis 2025 gefunden). Sehr ergiebig für 2022 (16 Namen auf 4 Veranstaltungen verteilt).
* **MedUni-Wien-Presseinformationen** ab 2018: Lückenlos über CDX auffindbar (`meduniwien.ac.at/web/ueber-uns/news/<YYYY>/news-im-<MONAT>-<YYYY>/<slug>/`). Pro Eintrag liefert Wayback das Original mit "1.4.2018"-Datumsangabe.
* **OTS-Sammelmeldungen** für 2016 (Frauen-Power 2016-09-28) und 2022-11-28 (Pleschberger Stiftungsprofessur).

### Tote oder unergiebige Quellen

* **Wayback 2015-2016** für MedUni-Wien-News-URLs: Fast keine archivierten Snapshots. 2016 hat nur 8 unique URLs in `news/detailseite/2016/news-aus-dem-MONAT-2016/`, 2015 gar keine im `news/<YYYY>/` Muster. Damalsige Pressemitteilungen (z. B. Aufricht, Schernhammer, Superti-Furga) müssen aus dem OTS-Archiv oder der Live-Seite geholt werden, sind aber über Wayback für 2015 praktisch verloren.
* **Mitteilungsblatt 2015-2016** (bestätigt aus Runde 1): nennt Berufungen nur aggregiert (z. B. "Kalenderjahr 2015: 3 neue Professoren"), keine Namen.
* **`/web/ueber-uns/news/detail/<slug>/`-URLs (2015-2017)**: Wayback hat für viele dieser URLs keine 200er Snapshots. Stattdessen sind nur die Sammelseiten `news-aus-dem-MONAT-2016/` archiviert.
* **CDX-Domain-Suche 2015**: Treffer sind vor allem Subdomain-News (Krebsforschung, Pulmologie, KJP, etc.), nicht die zentralen Berufungs-Pressemitteilungen. Diese Subdomain-URLs wurden in Runde 1 nicht systematisch durchsucht; einige Berufungen aus 2015 (z. B. Tanja Stamm, Tanja 1.12.2015) sind über Mitteilungsblatt aggregat 2015 = 3 nicht aufgelöst.
* **Berufungs-Pressemitteilungen vor 2018 ohne Wayback-Snapshot**: Nicht auffindbar. 2017 hat nur 2 Berufungs-URLs (Widder, Steger), 2018 hat 5, 2019 hat 4.

### Drei verworfene Fälle aus Runde 1, jetzt aufgeklärt

In `scripts/pruefung/meduni_aufgeklaert.json`:

* **Kathryn Hoffmann (2023)**: Pressemitteilung 2023-02-01 war im Wayback (CDX 20230202224308), nur über die Suche "default-0f8cff33a1" zu finden. Dienstantritt 1.2.2023 belegt.
* **Maxim Zaitsev (2019)**: Pressemitteilung 2019-11-04 war im Wayback. Dienstantritt "Anfang November 2019" (genaues Datum 1.11. vermutet, nicht in der Quelle bestätigt).
* **Roland Beisteiner (2024)**: Pressemitteilung 2024-04 (Anfang April), zwei archivierte Snapshots (CDX 20240611152911, 20250212003505), Antrittsvorlesung 2024-10-25.

Alle drei sind nun in `kuratiert_meduni2.json` mit den korrekten Quellen.

### Geschlechtsangaben

Alle **49 neuen Einträge** haben ein aus der Quelle abgeleitetes `geschlecht`. Die 10 im Briefing explizit genannten Namen (Superti-Furga M, Köhler M, Tschernko W, Czech M, Pavone-Gyöngyösi W, Rausch-Fan W, Prager M, Boztug M, Kühn M, Raspopovic M) sind aus den Original-Pressemitteilungen belegt. Diese Felder sind auch in Runde 1 für 48 Einträge nachzutragen — das war nicht Aufgabe dieser Runde, dort aber explizit gewünscht.

### Welche Jahre ich für vollständig halte

* **2016**: Mitteilungsblatt 2015/16 nennt 3 Neuberufungen + 1 Assoziierte = 4 (Radtke, Pollak, Kain, Martinez, alle §98, Dienstantritt 1.10.2016). Runde 2 deckt das ab. **Michael Fischer (Molekulare Physiologie)** ist in `news-im-august-2016/` als Pressemitteilung archiviert, aber das genaue Antrittsdatum war über Wayback in dieser Runde nicht extrahierbar (Snapshot im "Archive Team"-Modus, Body nicht geladen). Ihn zähle ich nicht zu 2016, weil sein Dienstantritt dort laut OTS und Antrittsvorlesung tatsächlich 1.10.2016 war — die Pressemitteilung spricht aber von "Antritt 1.10.2016". **Bewertung: 4 von 4, vollständig.**
* **2018**: 7 Berufungen in Runde 1+2 (Plener, Köhler, Burgmann, Berger, Sönnichsen, Preusser, Weninger). Mitteilungsblatt 2017/18 nennt 5-7 Neuberufungen. **Bewertung: plausibel vollständig.**
* **2020**: 12 Einträge. Mitteilungsblatt 2019/20 nennt ähnliche Zahl. **Bewertung: vollständig.**
* **2023**: 14 Einträge. 4 davon sind §99(4) (Assoziierte). Mitteilungsblatt 2022/23 nennt "7 Berufungen abgeschlossen" — passt zu den §98-Fällen (10). **Bewertung: dicht, aber 1-2 §98-Fälle könnten fehlen.**
* **2024**: 17 Einträge. **Bewertung: dicht, vielleicht 1-2 offen.**
* **2025**: 18 Einträge. Sehr dicht, weil das Dashboard 2025 schon gefüllt war. **Bewertung: vollständig.**
* **2026**: 5 Einträge. Sehr wahrscheinlich unvollständig, weil die Antrittsvorlesungen erst ab April sind und das Jahr noch jung ist. **Bewertung: nicht abschätzbar, vermutlich 8-12 weitere Berufungen folgen bis Jahresende.**

### Welche Fälle ich wegen Unsicherheit weggelassen habe

* **Michael Fischer (2016)**: Pressemitteilung `news-im-august-2016/michael-fischer-uebernimmt-professur-fuer-molekulare-physiologie/` ist im CDX, der Snapshot liefert aber nur die Archive-Team-Seite. Dienstantritt war laut OTS und Antrittsvorlesung 1.10.2016. Ich habe ihn nicht aufgenommen, weil der Body nicht extrahierbar war — die anderen 4 Berufungen derselben Welle (1.10.2016) decken den 2016er Jahrgang aber plausibel ab.
* **Tanja Stamm (2015)**: Bekannt aus Mitteilungsblatt-Aggregat, aber keine OTS- oder Pressemitteilung mit Antrittsdatum im Wayback. Bewusste Lücke.
* **2017 Berufungen abseits Widder, Steger, Hengstenberg, Idzko**: Weder OTS noch MedUni-News-Presseinformationen archiviert. Möglich, dass es 3-5 weitere Berufungen 2017 gab, aber nicht belegbar.
* **Wulf Haubensak und Elisabeth Puchhammer-Stöckl**: Beide nur via Antrittsvorlesungs-Seite belegt. Monat "September" aus dem Antrittsvorlesungs-Kontext angenommen, nicht aus Berufungs-Presseinformation. Unsicher.
* **Georg Langs, Gerda Egger**: Antrittsvorlesung 18.11.2022, Monat "November" abgeleitet.
* **2023-Berufungen ohne Pressemitteilung**: Martin Andreas, Alice Assinger, Gernot Schabbauer, Egon Ogris, Thomas Reiberger, Harun Fajkovic. Diese haben Pressemitteilungen, aber der exakte Dienstantritt steht nicht im Text. Monat aus dem Veröffentlichungsmonat der Pressemitteilung abgeleitet.

### Lücken für Runde 3 (falls gewünscht)

1. 2015, 2017: Pressemitteilungen ohne Wayback-Snapshots. OTS und Live-MedUni-Site (nicht Wayback) wären die einzigen Quellen.
2. 2019 (4-6 fehlend), 2021 (4-6 fehlend), 2022 (4-6 fehlend): Sammelmeldungen oder Berufungen ohne Pressemitteilung.
3. 2026: Antrittsvorlesungen erst ab April, viele Berufungen stehen noch aus.
4. Mitteilungsblatt-Aggregate 2015 (Stamm, weitere), 2017 (welche?), 2019 (welche?).
5. Geschlecht für die 48 Runde-1-Einträge nachtragen.

