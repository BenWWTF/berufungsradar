# Berufungsradar Wien 2025

Interaktives Dashboard zur Visualisierung von Professorinnen- und Professorenberufungen an Wiener Universitäten im Jahr 2025.

**Live:** https://benwwtf.github.io/berufungsradar

## Datenstand (Juni 2026)

| Universität | Einträge | Status |
|-------------|----------|--------|
| TU Wien | 28 | ✅ Vollständig |
| Universität Wien | 23 | ✅ Vollständig |
| mdw – Musik und darst. Kunst | 11 | ✅ Vollständig |
| Medizinische Universität Wien | 10 | ✅ Vollständig |
| BOKU | 6 | ✅ Vollständig |
| Universität für angewandte Kunst | 4 | ✅ Vollständig |
| Akademie der bildenden Künste | 2 | ✅ Vollständig |
| WU Wien | 4 | ✅ Vollständig |
| Vetmeduni Wien | 2 | ✅ Vollständig |
| **Gesamt** | **90** | **100% ÖFOS-Abdeckung** |

## Visualisierungen

- **KPI-Zeile** – Gesamtanzahl, Geschlechterverteilung (40 W / 50 M), Art der Berufung
- **WWTF-Perspektive (eigener Tab)** – Zuordnung der Berufungen zu WWTF-Programmfeldern (Life Sciences, ICT, Cognitive Sciences, ESR, Digital Humanism, Mathematik und …); KPIs, Kernaussagen, Personen-Listen pro Programmfeld
- **Kernaussagen-Boxen** – automatisch berechnete Takeaways auf Übersicht, WWTF- und Mobilitäts-Tab
- **Mobilität (Sankey)** – Herkunftsland (14 Länder) → 9 Wiener Universitäten, volle Breite
- **Thematische Cluster (D3 Force-Graph)** – Knoten gefärbt nach Universität, positioniert nach ÖFOS-Bereich; Uni × Uni Heatmap der Forschungsüberlappung
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
- Universität Wien: Öffentliche Personalpages
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
