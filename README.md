# Berufungsradar Wien 2025

Interaktives Dashboard zur Visualisierung von Professorinnen- und Professorenberufungen an Wiener Universitäten im Jahr 2025.

**Live:** https://benwwtf.github.io/berufungsradar

## Auswertungszeitraum

**2019 bis 2026.** TU Wien und mdw führen ihre Übersichten erst ab 2019, und diese
beiden Häuser stellen rund die Hälfte aller Wiener Berufungen. Für frühere Jahre
liegt die Abdeckung zwischen 15 und 45 Prozent, das trägt keine Zeitreihe. Die 136
Datensätze aus 2014 bis 2018 liegen archiviert in `dashboard_data_vor2019.json`.

## Automatisierung

Die Datenbasis wird per GitHub Action (`.github/workflows/datenbasis.yml`) aktualisiert:
Ende Februar, Ende Mai, Anfang September und Ende November, jeweils 05:00 UTC.
Der Lauf startet `scripts/update.sh` (OpenAlex-Anreicherung, Lücken füllen, HTML-Build)
und committet nur, wenn sich etwas geändert hat. Der Lückenreport steht in der
Zusammenfassung des jeweiligen Runs.

Am Monatsersten läuft zusätzlich ein Prüflauf, der nur den Report schreibt und das
Datum unten stempelt. Er hält die Zeitpläne aktiv, weil GitHub Cron in öffentlichen
Repos nach 60 Tagen ohne Aktivität abschaltet und zwischen den Quartalsterminen bis
zu 92 Tage liegen.

Wichtig: der Lauf frischt die Anreicherung auf, er findet keine neuen Berufungen.
Neue Jahrgänge brauchen einen eigenen Scrape- und Recherchedurchgang.

Letzte automatische Pruefung: 2026-10-01 (Prueflauf)

## Datenstand (Oktober 2026)

Zeitraum 2019–2026, siehe `datenabdeckung.json` für die vollständige
Methodik je Universität und Jahr.

| Universität | Einträge | Status |
|-------------|----------|--------|
| Uni Wien | 465 | 🟡 Teilweise (2019–2020 offen, 2026 laufend) |
| TU Wien | 190 | ✅ Vollständig |
| mdw | 117 | ✅ Vollständig |
| MedUni Wien | 90 | ✅ Vollständig (2026 laufend) |
| CEU | 84 | 🟡 Teilweise (HR-Snapshot, keine Kennzahl-Quelle, siehe unten) |
| Vetmeduni Wien | 62 | ✅ Vollständig (2026 laufend) |
| WU Wien | 55 | ✅ Vollständig (2026 laufend) |
| Akademie | 44 | 🟡 Teilweise (2020 offen: zwei §99(1)-Architekturstellen) |
| Angewandte | 42 | ✅ Vollständig |
| BOKU | 63 | ✅ Vollständig für §98 (2026 laufend), §99 nur aus öffentlichen Quellen |
| **Gesamt** | **1212** | **100% ÖFOS-Abdeckung (1212/1212)** |

"2026 laufend" heißt: das Jahr ist noch nicht abgeschlossen, keine Lücke im
Sinne von `datenabdeckung.json`. CEU ist privat und läuft methodisch anders
als die 9 öffentlichen Unis: die Quelle ist ein einmaliger HR-Datenexport
der aktuell aktiven Fakultät, keine laufende Ankündigungsseite — frühere
Berufungen von inzwischen ausgeschiedenen Personen fehlen deshalb
systembedingt, siehe `scripts/backfill_ceu.py` und den CEU-Eintrag in
`datenabdeckung.json`.

## Verbleib der Berufenen

`abgaenge.json` führt Berufene, die ihre Universität nachweislich wieder
verlassen haben (50 zugeordnet): Ziel, Land, Jahr, Art (Professur
anderswo, Befristung beendet, Ruhestand, Wirtschaft) und eine öffentliche
Quelle je Eintrag. Die Datei ist von Hand kuratiert; aufgenommen wird nur,
was eine öffentliche Quelle ausdrücklich sagt. `wwtf_enrich.py` hängt den
Weggang als `abgang` an die jüngste Berufung der Person, das Dashboard zeigt
ihn auf der Profilkarte und als Filter "Verbleib".

Kandidaten liefern zwei Skripte, deren Ergebnisse nicht ins Repo gehen
(`scripts/.abgaenge_cache/`), sondern als Prüfliste dienen:

- `scripts/abgaenge.py`: OpenAlex-Affiliationen; verschwindet die berufende
  Uni zwei Jahre lang und taucht eine neue Institution auf, ist das ein
  Kandidat (ORCID bestätigt, wo vorhanden). Gut die Hälfte der Kandidaten
  hält der Prüfung stand; Jahre und Ziele hinken oft ein bis drei Jahre nach.
- `scripts/abgaenge_fl.py`: die Monatsrubrik "Habilitationen und Berufungen"
  von Forschung & Lehre, gefiltert auf Rufe aus und nach Wien.

## Visualisierungen

- **KPI-Zeile** – Gesamtanzahl, Geschlechterverteilung (40 W / 50 M), Art der Berufung
- **WWTF-Perspektive (eigener Tab)** – Zuordnung der Berufungen zu WWTF-Programmfeldern (Life Sciences, ICT, Cognitive Sciences, ESR, Digital Humanism, Mathematik und …); KPIs, Kernaussagen, Personen-Listen pro Programmfeld
- **Kernaussagen-Boxen** – automatisch berechnete Takeaways auf Übersicht, WWTF- und Mobilitäts-Tab
- **VRG-Pipeline (WWTF-Tab)** – 35 Vienna Research Groups der Calls 2010–2025 mit Gastinstitution und, wo erfasst, der späteren Professur; Badge und Filter auf den Personenkarten
- **Mobilität (Sankey)** – Herkunftsland (14 Länder) → Wiener Universitäten (9 öffentliche + CEU), volle Breite
- **ÖFOS-Bereiche (1-stellig)** – Hauptkategorien 1–6
- **Universitäten × ÖFOS-Bereich (Heatmap)** – Aktivitätsprofile der 9 Unis
- **ÖFOS-Fachbereiche (3-stellig, Top 15)** – Feinere Gliederung
- **Geschlecht × Universität** – Gestapeltes Balkendiagramm über alle Unis
- **Timeline** – Berufungen nach Monat (12 Monate)
- **Profilkarten** – Filterbare, sortierbare Karten (Monat, Name, h-Index, Uni) mit Werdegang, Metriken, Fördergebern; Filter für WWTF-Programmfeld
- **CSV-Export** – gefilterte Ansicht als Excel-kompatibles CSV (Semikolon, BOM)
- **Teilbare Links** – Filter- und Tab-Zustand liegt in der URL (`#tab=alle&filter-uni=TU+Wien`)

## Deployment (GitHub Pages)

```bash
# bereits konfiguriert
git push origin main
# GitHub Pages: Settings → Pages → Branch: main / root
```

## Datenquellen

- TU Wien: Öffentliche Berufungsmeldungen
- Universität Wien: Öffentliche Personalpages; Leistungsberichte und Wissensbilanzen
- MedUni Wien, BOKU, WU Wien, mdw, Vetmeduni, Angewandte, Akademie der bildenden Künste: öffentliche Berufungsbekanntmachungen
- OpenAlex: Forschungsmetriken (h-Index, Publikationen, Zitierungen), Affiliations

## Datenstruktur

Jeder Eintrag im `DATA`-Array enthält:

```js
{
  name, universitat, fakultat, fakultat_code, fakultat_institut,
  forschungsbereich,
  art_berufung,           // §98 | §99(4) | §99(1) | §99(5) BEST
  geschlecht,             // M | W
  herkunft,               // intern | extern
  herkunft_institution,   // Herkunftseinrichtung
  herkunft_land,          // Herkunftsland (DE-Name)
  ofos_code,              // ÖFOS 2012 (3-stellig)
  ofos_label,             // Bezeichnung
  ofos_bereich_code,      // ÖFOS-Bereich (1-stellig: 1-6)
  ofos_bereich,           // Bereichs-Bezeichnung
  ofos_hauptgruppe_code,  // ÖFOS-Hauptgruppe (2-stellig)
  ofos_hauptgruppe,       // Hauptgruppen-Bezeichnung
  grants,                 // Array von Fördergebernamen
  wwtf_programme,         // Array von WWTF-Programmfeld-Kürzeln: LS|ICT|CS|ESR|DH|MA
  abgang,                 // {abgang_jahr, abgang_monat, ziel, ziel_land, art, quelle} oder fehlt
  h_index, publikationen, zitierungen,  // strukturierte OpenAlex-Metriken
  openalex_id,            // OpenAlex-Autoren-ID (sofern gefunden)
  bio_text,               // Freitext mit "h-Index: X | Publikationen: Y | Zitierungen: Z"
  werdegang,              // CV-Text
  profil_url,             // Link zur Universitätsseite
  monat, year
}
```

## Technologie

- Reines HTML/CSS/JS, kein Build-Schritt
- D3.js v7 + d3-sankey v0.12 (CDN)
- Chart.js v4 (CDN)
- WWTF Design System: Inter, #003366, #0055A4

## Reproduktion

Die Datenanreicherung erfolgt über eine idempotente Pipeline (ein Befehl):

```bash
scripts/update.sh                      # Alles in einem: Lookup → Anreicherung → Lücken → Build → Report
```

Einzelstufen:

```bash
python3 scripts/openalex_lookup.py     # OpenAlex für alle ungeprüften Einträge (Negativ-Cache, Match-Validierung)
python3 scripts/enrich.py              # Geschlecht, ÖFOS-Ebenen, TU Wien E-Code
python3 scripts/wwtf_enrich.py         # Strukturierte Metriken + WWTF-Programmfeld-Zuordnung
python3 scripts/fill_gaps.py           # Werdegang/Profil-Links auto-füllen (manuell > API > generiert)
python3 scripts/build_html.py          # Generiert index.html mit eingebettetem DATA
python3 scripts/audit_gaps.py          # Lücken-Report → data_gaps.csv (manuelle Recherche-Warteschlange)
```

## Kontakt

Benjamin Missbach – WWTF · benjamin.missbach@wwtf.at
