# Berufungsradar Wien 2025

Interaktives Dashboard zur Visualisierung von Professorinnen- und Professorenberufungen an Wiener Universitäten im Jahr 2025.

**Live:** https://benwwtf.github.io/berufungsradar

## Pilotdaten

| Universität | Einträge | Status |
|-------------|----------|--------|
| TU Wien | 28 | ✅ Vollständig |
| Universität Wien | 23 | ✅ Vollständig |
| Medizinische Universität Wien | – | Phase 2 |
| WU Wien | – | Phase 2 |
| Vetmeduni Wien | – | Phase 2 |

## Visualisierungen

- **KPI-Zeile** – Gesamtanzahl, Geschlechterverteilung, Art der Berufung
- **Mobilität (Sankey)** – Herkunft → Wiener Universität
- **Thematische Cluster (D3 Force-Graph)** – Professuren nach ÖFOS-Hauptgruppe
- **ÖFOS-Breakdown** – Top-15-Fachbereiche
- **Geschlecht × Universität** – Gestapeltes Balkendiagramm
- **Timeline** – Berufungen nach Monat
- **Profilkarten** – Filterbare Karten mit Werdegang, Metriken und Fördergebern

## Deployment (GitHub Pages)

```bash
git init
git add index.html README.md
git commit -m "Initial release"
git remote add origin https://github.com/benwwtf/berufungsradar.git
git push -u origin main
# GitHub Pages aktivieren: Settings → Pages → Branch: main / root
```

## Datenquellen

- TU Wien: Öffentliche Berufungsmeldungen
- Universität Wien: Öffentliche Personalpages
- OpenAlex: Forschungsmetriken (h-Index, Publikationen, Zitierungen), Fördergeber

## Datenstruktur

Jeder Eintrag im `DATA`-Array enthält:

```js
{
  name, universitat, fakultat, fakultat_code,
  forschungsbereich,
  art_berufung,           // §98 | §99(4) | unbekannt
  geschlecht,             // M | W | unbekannt
  herkunft,               // intern | extern | unbekannt
  herkunft_institution,   // Herkunftseinrichtung oder null
  herkunft_land,          // Herkunftsland oder null
  ofos_code,              // ÖFOS 2012 (4-stellig)
  ofos_label,             // Bezeichnung
  grants,                 // Array von Fördergebernamen
  bio_text,               // Freitext mit optionalem "h-Index: X | Publikationen: Y | Zitierungen: Z"
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

## Kontakt

Benjamin Missbach – WWTF · benjamin.missbach@wwtf.at
