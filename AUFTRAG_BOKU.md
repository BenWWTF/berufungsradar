# Auftrag: Berufungen der BOKU 2015–2024 erfassen

Kurzbriefing für einen zweiten Agenten. Aufbau und Regeln sind dieselben wie in
`AUFTRAG_MEDUNI.md`; hier stehen nur die BOKU-spezifischen Befunde.

## Was gebraucht wird

Alle Berufungen von Universitätsprofessor:innen an der **Universität für Bodenkultur
Wien** (im Datensatz `"BOKU"`) für **2015 bis 2024**, geschätzt 70 bis 90 Personen
bei etwa 6 bis 10 Berufungen im Jahr. Erfasst sind bisher nur sieben: sechs
kuratierte für 2025 und ein Einzelfall 2022.

Ergebnis: **eine JSON-Datei** `scripts/backfill/kuratiert_boku.json` nach dem
Schema aus `AUFTRAG_MEDUNI.md`. Die Hauptdatei nicht bearbeiten.

## Was geprüft ist

**Presseaussendungen, je Jahr eine Seite.** Adresse:
`boku.ac.at/universitaetsleitung/rektorat/stabsstellen/oeffentlichkeitsarbeit/themen/presseaussendungen/presseaussendungen-<jahr>`
Vorhanden für 2015, 2016, 2017 und 2020 bis 2026; **2018 und 2019 antworten mit
404**. Der Ertrag ist dünn: über 2015 bis 2026 nur 13 Meldungen mit
Berufungsbezug, für 2015 bis 2020 und 2024 keine einzige. Meist sind es
Antrittsvorlesungen, nicht Berufungsmeldungen. Das ist als Quelle also nur eine
Ergänzung, kein Rückgrat.

**Mitteilungsblatt.** Ab Studienjahr 2019/20 als HTML je Stück:
`boku.ac.at/mitteilungsblatt/mitteilungsblaetter-<jj-jj>` listet die Stücke,
rund 27 pro Jahr. Ältere Jahrgänge liegen als PDF unter
`boku.ac.at/fileadmin/data/H01000/mitteilungsblatt/MB_<jjjj>_<jj>/MB<nn>/`.
Ich habe **alle 197 Stücke von 2019/20 bis 2025/26 im Volltext durchsucht**:
28 Konstituierungen von Berufungskommissionen mit Denomination und Datum, aber
nur **eine** namentliche Berufung. Die stand in einer Senatsmeldung:

> „Aus dem Senat scheidet mit 1.1.2022 Univ.Prof. Dipl.-Ing. Dr. Alfred STRAUSS
> (Liste BOKU) aufgrund seiner Berufung zum Universitätsprofessor als Mitglied
> des Mittelbaus aus."

Dieses Muster erfasst nur Hausinterne, die aus dem Mittelbau aufsteigen. Es lohnt,
die **PDF-Jahrgänge vor 2019/20** nach genau diesem Satzmuster zu durchsuchen
(`aufgrund seiner Berufung`, `aufgrund ihrer Berufung`, `zum Universitätsprofessor
berufen`), aber die Ausbeute wird klein bleiben.

**Antrittsvorlesungs-Archiv.** `boku.ac.at/akademie-fuer-weiterbildung/open-content-frei-zugaengliche-inhalte/themen-fuers-21-jahrhundert-boku-antrittsvorlesungen`
nennt rund 22 Professor:innen mit Videoaufzeichnung, **aber ohne Berufungsdatum**.
Gut als Namensliste zum Abgleichen, nicht als Datenquelle für sich. Jede neu
berufene Person hält eine Antrittsvorlesung, das ist der zuverlässigste Trigger.

**Nicht ergiebig, bitte nicht wiederholen:** unidata.gv.at, Wissensbilanz und
Universitätsbericht liefern nur Bestandszahlen ohne Namen. Ausschreibungen im
Mitteilungsblatt sind Verfahren, keine Berufungen.

## Noch nicht ausgeschöpft

* **Antrittsvorlesungen in der Veranstaltungsankündigung** je Jahr. Die
  Presseaussendungen nennen einzelne („Antrittsvorlesung von Matthias Kuba am
  27. November"), es gibt aber auch Terminlisten und Einladungen als PDF.
  Aus einer Antrittsvorlesung lässt sich der Dienstbeginn meist im Text
  ablesen („trat im April die Professur an").
* **BOKU Magazin** und Newsletter, Rubriken zu Personalia.
* **Institutsseiten und BOKU-Personenverzeichnis (BOKUonline / FIS)**: dort steht
  häufig „seit 2017 Universitätsprofessor für …". Das liefert Jahr und Denomination,
  die Vorstation oft dazu.
* **Webarchiv** (`web.archive.org/cdx/search/cdx?url=boku.ac.at&matchType=domain&…`).
  Bei Uni Wien und Vetmeduni war das der Schlüssel; die BOKU-Seiten von 2015 bis
  2019 liegen dort in älteren Fassungen, teils mit Nachrichtenlisten, die heute
  verschwunden sind.
* **OTS und APA-Science**: die BOKU verschickt Berufungsmeldungen teils über OTS,
  auch wenn sie auf der eigenen Seite fehlen.

## Erwartbare Fallen

* Die BOKU beruft viele **Stiftungsprofessuren** (Beispiel: Matthias Kuba,
  thermochemische Gaserzeugung, finanziert über BEST). Die zählen dazu, Art der
  Berufung ist dann `§99(5)`, aber nur wenn die Quelle das so benennt.
* **Antrittsvorlesung ≠ Berufung.** Die Vorlesung findet oft ein bis zwei Jahre
  nach dem Dienstbeginn statt. Simone Gingrich etwa wurde im September 2024
  berufen, die Antrittsvorlesung war im März 2025. In `year` gehört der
  Dienstbeginn; wenn nur das Datum der Vorlesung bekannt ist, gehört das in
  `_kuratiert` und der Eintrag bleibt besser weg.
* Die BOKU heißt seit 2025 offiziell „BOKU University". Im Datensatz bleibt der
  Kurzname `"BOKU"`, sonst zerfällt die Zeitreihe.
* Departmentnamen sind lang und wechseln; ins Feld `fakultat` gehört das Institut,
  nicht das Department, wenn beides genannt ist.

## Einpflegen

```bash
cd ~/Desktop/berufungsradar
python3 scripts/merge_backfill.py --dry
python3 scripts/merge_backfill.py
python3 scripts/classify_ofos.py     # meldet Fächer ohne ÖFOS-Regel namentlich
bash scripts/update.sh
```

Für BOKU-Fächer sind ÖFOS 401 (Agrarwissenschaften), 403 (Veterinärmedizin),
207 (Umweltingenieurwesen), 204 (Chemieingenieurwesen), 105 (Geowissenschaften)
und 106 (Biologie) vorbereitet. Fehlt eine Regel, ergänze sie in der Liste
`STICHWORT` in `scripts/classify_ofos.py`.

Zum Schluss `datenabdeckung.json` für BOKU aktualisieren, mit Jahresliste und
Quellenangabe.
