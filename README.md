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
| WU Wien | 4 | ✅ Vollständig |
| Vetmeduni Wien | 2 | ✅ Vollständig |
| **Gesamt** | **88** | **100% ÖFOS-Abdeckung** |

## Visualisierungen

- **KPI-Zeile** – Gesamtanzahl, Geschlechterverteilung (38 W / 50 M), Art der Berufung
- **Mobilität (Sankey)** – Herkunftsland (14 Länder) → 8 Wiener Universitäten, volle Breite
- **Thematische Cluster (D3 Force-Graph)** – Knoten gefärbt nach Universität, positioniert nach ÖFOS-Bereich; Uni × Uni Heatmap der Forschungsüberlappung
- **ÖFOS-Bereiche (1-stellig)** – Hauptkategorien 1–6
- **Universitäten × ÖFOS-Bereich (Heatmap)** – Aktivitätsprofile der 8 Unis
- **ÖFOS-Fachbereiche (3-stellig, Top 15)** – Feinere Gliederung
- **Geschlecht × Universität** – Gestapeltes Balkendiagramm über alle Unis
- **Timeline** – Berufungen nach Monat (12 Monate)
- **Profilkarten** – Filterbare Karten mit Werdegang, Metriken, Fördergebern

## Deployment (GitHub Pages)

```bash
# bereits konfiguriert
git push origin main
# GitHub Pages: Settings → Pages → Branch: main / root
```

## Datenquellen

- TU Wien: Öffentliche Berufungsmeldungen
- Universität Wien: Öffentliche Personalpages
- MedUni Wien, BOKU, WU Wien, mdw, Vetmeduni, Angewandte: öffentliche Berufungsbekanntmachungen
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

Die Datenanreicherung erfolgt über zwei Skripte:

```bash
python3 scripts/openalex_lookup.py     # OpenAlex Metriken + Herkunfts-Inferenz
python3 scripts/enrich.py              # Sophie-Thun Fix, Geschlecht, ÖFOS-Ebenen, TU Wien E-Code
python3 scripts/build_html.py          # Generiert index.html mit eingebettetem DATA
```

## Kontakt

Benjamin Missbach – WWTF · benjamin.missbach@wwtf.at
