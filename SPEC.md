# Berufungsradar Wien 2025 — Spezifikation & Methodenbericht

**Stand:** Juni 2026
**Verantwortlich:** Benjamin Missbach, WWTF
**Live-Dashboard:** https://benwwtf.github.io/berufungsradar/
**Quellcode:** https://github.com/BenWWTF/berufungsradar

---

## 1. Zielsetzung

Der **Berufungsradar Wien 2025** ist ein interaktives Web-Dashboard, das die Berufungen
von Universitätsprofessor:innen an Wiener Universitäten im Berufungsjahr 2025
systematisch erfasst, anreichert und visualisiert. Das Dashboard beantwortet vier
zentrale Fragen:

1. **Wer wurde berufen?** — Geschlechterverteilung, Herkunft, ÖFOS-Klassifikation.
2. **Woher kommen die Berufenen?** — Internationale Mobilität, nationale vs.
   internationale Rekrutierung, Verteilung der Herkunftsländer.
3. **Welche Disziplinen sind vertreten?** — ÖFOS-2012-Klassifikation auf 1-, 2- und
   3-stelliger Ebene; thematische Überlappungen zwischen Universitäten.
4. **Wie verteilt sich das auf die Universitäten?** — Aktivitätsprofile,
   Berufungsmuster, Profile der 9 Wiener Universitäten.

Das Dashboard richtet sich an Wissenschaftsmanager:innen, Forschungsförder­organisationen,
Universitätsleitungen, Berufungskommissionen und Journalist:innen, die einen
schnellen, datenbasierten Überblick über den Wiener Berufungsmarkt 2025 suchen.

## 2. Datenstand

| Universität | Einträge | Status |
|---|---|---|
| TU Wien | 28 | ✅ vollständig |
| Universität Wien | 23 | ✅ vollständig |
| mdw – Musik und darst. Kunst | 11 | ✅ vollständig |
| Medizinische Universität Wien | 10 | ✅ vollständig |
| BOKU | 6 | ✅ vollständig |
| Universität für angewandte Kunst | 4 | ✅ vollständig |
| Akademie der bildenden Künste | 2 | ✅ vollständig |
| WU Wien | 4 | ✅ vollständig |
| Vetmeduni Wien | 2 | ✅ vollständig |
| **Gesamt** | **90** | **100 % ÖFOS-Abdeckung** |

Erfasst sind alle 9 öffentlichen Wiener Universitäten, die Berufungen gemäß §98,
§99(1), §99(4) und §99(5) Stiftungsprofessuren (BEST) ausgesprochen haben.

## 3. Datenquellen

| Quelle | Was wird erhoben | Rechtsgrundlage |
|---|---|---|
| **Universitäts-Websites** (Berufungsbekanntmachungen, Personalpages) | Name, Universität, Institut, Fakultät, Forschungsbereich, Berufungsdatum, Art der Berufung | Öffentlich zugänglich |
| **Mitteilungsblätter** der Universitäten (z.B. Vetmeduni Stück 06/2023/24) | Offizielle Berufungsausschreibungen und -entscheidungen | Öffentlich |
| **OpenAlex** (https://api.openalex.org) | h-Index, Publikationen, Zitierungen, Affiliations-Historie, letzte bekannte Institution | CC0-Datenbank, kostenlos nutzbar |
| **Web-Recherche** (Uni-Websites, Lebensläufe, MDW-Presseaussendungen) | Geschlecht (aus Vorname), Herkunftsinstitution, Herkunftsland | Öffentlich |

Es werden **keine personenbezogenen Daten** jenseits der ohnehin öffentlich
zugänglichen Berufungsinformationen erhoben. OpenAlex liefert ausschließlich
aggregierte Metriken (Publikationszahl, Zitierungen, h-Index) und öffentliche
Affiliationshistorien aus Crossref-Datenquellen.

## 4. Datenanreicherungs-Pipeline

Die Verarbeitung erfolgt in mehreren Stufen (4.1–4.6) und ist als reproduzierbare
Python-Pipeline unter `scripts/` abgelegt.

### 4.1 OpenAlex-Lookup (`scripts/openalex_lookup.py`)

Für jede der 88 Berufungen wird eine OpenAlex-Autoren­suche
(`/authors?search=Name`) durchgeführt. Aus dem Top-Treffer werden extrahiert:

- `works_count` — Gesamtanzahl Publikationen
- `cited_by_count` — Gesamtanzahl Zitierungen
- `h_index` — berechnet aus den abgerufenen Werken (h = max {n : n Paper mit ≥ n Zitaten})
- `last_known_institutions` — Affiliationshistorie mit Jahr, Land, Typ
- `bio_text` — automatisch generierter Kurztext aus Forschungsbereich + Metriken
- `herkunft` — automatische Klassifikation (intern/extern) auf Basis der Affiliationshistorie

**Klassifikationsregel „intern" vs. „extern":**
- `intern`, wenn die Person innerhalb der letzten 3 Jahre (Jahr ≥ 2023) an der
  Berufungs­universität affiliert war (z.B. als Senior Scientist, Habilitand)
- `extern`, sonst — die zuletzt affiliierte Institution wird als `herkunft_institution`
  erfasst, das Land in deutscher Bezeichnung als `herkunft_land`

**Spezialfälle, die als „intern" der Berufungsuniversität gewertet werden:**

| Universitätszugehörigkeit | Mapping |
|---|---|
| Universitätskliniken der MedUni Wien (HNO, Chirurgie, Frauenheilkunde, …) | MedUni Wien |
| AKH Wien / Vienna General Hospital | MedUni Wien |
| Ludwig Boltzmann Institute (Hämato-Onkologie, Traumatologie, …) | MedUni Wien |
| Comprehensive Cancer Center Vienna | MedUni Wien |
| Universitätszahnklinik Wien | MedUni Wien |
| Max Perutz Laboratories | Uni Wien |
| Christian Doppler Laboratories (typischerweise an einer Wiener Großuni) | TU Wien |
| mdw – Universität für Musik und darstellende Kunst Wien | mdw |

Insgesamt 41 Einträge wurden so über OpenAlex angereichert. 4 Einträge
(Iva Hunger Brezinova, Mischa Janisch, Wilhelm Spuller, Jorge Sánchez-Chiong)
sind in OpenAlex nicht oder nur unvollständig erfasst (überwiegend mdw-Professuren
mit künstlerischem Schwerpunkt) und wurden über manuelle Web-Recherche
ergänzt (siehe `scripts/herkunft_research.json`).

### 4.2 Geschlechts-Inferenz (`scripts/enrich.py`, Stage 2)

Vor der Anreicherung wiesen 25 der 88 Einträge das Feld `geschlecht: "unbekannt"`
auf. Die Geschlechtszuordnung erfolgt über eine kuratierte Liste von ~400
Vornamen (überwiegend deutschsprachig, ergänzt um slawische, romanische,
griechische, türkische, israelische und iranische Namen). Akademische Titel
(Univ.Prof., Dr., Mag., DI) und zusammengesetzte Vornamen werden vorgängig
gestrippt.

- Trefferquote: **25 / 25 = 100 %**
- Endstand: 38 W (43 %), 50 M (57 %)

Manuelle Korrekturen sind nicht erforderlich; alle 88 Einträge haben
eindeutig zugeordnetes Geschlecht.

### 4.3 TU-Wien-E-Code → Institut (`scripts/enrich.py`, Stage 4)

Die TU Wien vergibt an jedes Institut einen internen E-Code (z.B. `E164` für
„Institut für Chemische Technologien und Analytik"). 28 der 88 Einträge sind
TU-Wien-Berufungen; davon enthalten 27 einen `fakultat_code`. Eine
offizielle Referenz der E-Codes ist über die TU-Wien-Organisationsstruktur
zugänglich; die hier verwendete Zuordnung wurde stichprobenartig gegen die
jeweiligen Personalpages und die Repositoriums-Einträge verifiziert.

Mapping-Datei: `scripts/enrich.py` → `TUWIEN_ECODE` (27 Codes abgedeckt).

### 4.4 ÖFOS-Hierarchie (`scripts/enrich.py`, Stage 3)

Die ÖFOS 2012 (Österreichische Systematik der Wissenschaftszweige) ist eine
3-stellige Klassifikation mit 6 Bereichen (1-stellig) und ca. 40
Hauptgruppen (2-stellig). Jeder 3-stellige Code wird automatisch in
übergeordnete Codes aufgelöst:

| Eingabe (3-stellig) | 1-stellig (Bereich) | 2-stellig (Hauptgruppe) |
|---|---|---|
| `101` Mathematik | `1` Naturwissenschaften | `10` Mathematik, Naturwiss. |
| `302` Klinische Medizin | `3` Medizin, Gesundheit | `30` Medizin, Gesundheit |
| `604` Kunstwissenschaften | `6` Geisteswissenschaften | `60` Geisteswissenschaften |
| … | … | … |

Im Dashboard werden alle drei Ebenen sichtbar:
- **Top-15-Balkendiagramm** (3-stellig) – konkrete Disziplinen
- **Bereichs-Balkendiagramm** (1-stellig) – grobe Verteilung
- **Heatmap Universität × Bereich** (1-stellig) – Aktivitätsprofile
- **ÖFOS-Label auf jeder Profilkarte** (3-stellig mit Sub-Bezeichnung)

### 4.5 WWTF-Anreicherung (`scripts/wwtf_enrich.py`)

Zwei Schritte:

1. **Strukturierte Metriken**: `h_index`, `publikationen`, `zitierungen` werden aus
   `bio_text` extrahiert und — wo vorhanden — durch die aktuelleren Werte aus
   `scripts/openalex_research.json` überschrieben (inkl. `openalex_id`).
   76 der 88 Einträge haben Metriken.
2. **WWTF-Programmfeld-Zuordnung** (`wwtf_programme`, Array): heuristische
   Zuordnung über den ÖFOS-3-Steller plus Schlagwort-Abgleich auf
   `ofos_label`/`forschungsbereich`:

| Programmfeld | ÖFOS-Basis | Keyword-Zusatz |
|---|---|---|
| Life Sciences (LS) | 106, 301, 302, 304, 403 | — |
| ICT | 102, 202 | — |
| Cognitive Sciences (CS) | 501 | „neuro" |
| Environmental Systems Research (ESR) | 207, 401 | „naturschutz/ökologie/wald/umwelt/wasser" |
| Digital Humanism (DH) | — | „mensch-maschine/künstliche intelligenz/digital" |
| Mathematik und … (MA) | 101 | — |

Mehrfachzuordnung ist möglich (z.B. Neurophysiologie → LS + CS). Ergebnis:
**29 der 88 Berufungen** liegen in mindestens einem WWTF-Programmfeld
(LS 13, ICT 8, ESR 5, CS 3, DH 3, MA 2). Die Zuordnung ist eine thematische
Näherung, keine Aussage über Antragsberechtigung.

### 4.6 Lücken füllen (`scripts/fill_gaps.py`) & Lücken-Report (`scripts/audit_gaps.py`)

**Datenstrategie (fail-safe):** Jedes Feld hat eine Vertrauenshierarchie
**manuell > API > generiert**. Auto-gefüllte Felder tragen Marker
(`werdegang_auto`, `profil_url_auto`) und dürfen bei späteren Läufen
regeneriert werden; Felder ohne Marker gelten als manuell gepflegt und werden
**nie überschrieben**. Der OpenAlex-Cache enthält auch Negativ-Ergebnisse
(„geprüft, nicht vorhanden") — so wird zwischen „nie geprüft" und „nicht in
OpenAlex" unterschieden und kein Lookup doppelt ausgeführt.

`fill_gaps.py` füllt aus dem OpenAlex-Cache:
- `werdegang` ← Stationen aus der Affiliationshistorie (mit Kennzeichnung
  „Stationen laut OpenAlex-Publikationshistorie")
- `profil_url` ← OpenAlex-Autorenseite als Fallback (im Dashboard als
  „OpenAlex →" statt „Profil →" ausgewiesen)
- `herkunft_institution`/`-land` ← nur wenn leer

**Match-Validierung:** `openalex_lookup.py` bewertet jeden Suchtreffer
(`match_confidence`): *high* = Affiliation in Österreich, *medium* =
Affiliation im bekannten Herkunftsland, *low* = keine geografische
Plausibilität. `low`-Treffer (potenzielle Namensvetter) werden von allen
Downstream-Stufen ignoriert.

**Manuelle Overrides (`scripts/openalex_overrides.json`):** Für Fälle, die die
automatische Suche nicht korrekt findet — Diakritika (Březinová), Bindestrich-
oder Doppelnamen (Riedl-Tragenreif), Namensvetter (die Delhi-„Milica Vujović"
statt der TU-Wien-Architektin) — hält diese Datei die per Hand geprüfte
Zuordnung:

- `openalex_id: "A…"` — pinnt die verifizierte Autoren-ID (umgeht Suche und
  Konfidenz-Gate, `match_confidence: "verified"`).
- `openalex_id: "none"` — Person hat kein akademisches Profil (Künstler:innen
  an mdw/Angewandter/Akademie) → sauberer Negativ-Cache, keine Fehlzuordnung.
- optional `herkunft`/`herkunft_institution`/`herkunft_land` — nur wenn hier
  explizit gesetzt, gilt die Herkunft als recherchiert (`herkunft_verified`)
  und darf einen kuratierten Wert korrigieren; ein reiner ID-Pin lässt die
  Herkunft unberührt.

So ist jede manuelle Recherche als re-runnbare Daten festgehalten und geht bei
keinem Rebuild verloren. Aktuell: 6 ID-Pins + 8 „kein Profil". Die Pipeline ist
idempotent (zweiter Lauf ohne API erzeugt bytegleiche Daten).

`audit_gaps.py` erzeugt `data_gaps.csv` — die Recherche-Warteschlange für
alles, was APIs nicht wissen können (v.a. künstlerische Professuren an mdw
und Angewandter): pro Person die fehlenden Felder plus fertige Suchlinks
(Uni-Website-Suche, Google).

**Kompletter Refresh:** `scripts/update.sh` führt alle Stufen in Reihenfolge
aus und druckt am Ende den Lücken-Report.

## 5. Architektur

### 5.1 Tech-Stack

| Schicht | Technologie | Begründung |
|---|---|---|
| Frontend | Reines HTML + CSS + Vanilla JS | Kein Build-Schritt nötig, maximale Portabilität |
| Visualisierung | D3.js v7 (Force-Graph, Sankey, Heatmaps) | Flexible, deklarative Datenvisualisierung |
| Charts | Chart.js v4 (Balken, Stacked Bar) | Standard-Browser-Charts ohne D3-Ceremonie |
| Sankey | d3-sankey v0.12 | Plugin für D3 |
| Schrift | Inter (Google Fonts) | WWTF-Designsystem |
| Hosting | GitHub Pages | Statisch, kostenlos, Versionierung über Git |
| Daten-Pipeline | Python 3.13 + OpenAlex-API | Reproduzierbar, auditierbar |

Es gibt **keine Datenbank, kein Backend, keine Cookies, kein Tracking**. Das
gesamte Dashboard ist eine einzige statische HTML-Datei (`index.html`, ~250 KB)
mit eingebettetem Daten-Array. Die Originaldaten liegen in
`dashboard_data_2025.json` (172 KB).

### 5.2 Datenmodell

```js
{
  name:                "Sophie Thun",
  universitat:         "TU Wien" | "Uni Wien" | "MedUni Wien" | …,
  fakultat:            "Fakultätsname (sofern öffentlich)",
  fakultat_code:       "E164" (TU-Wien-E-Code, sonst null),
  fakultat_institut:   "Institut für Chemische Technologien und Analytik" (aufgelöst),
  forschungsbereich:   "Universitätsprofessor für …",
  art_berufung:        "§98" | "§99(1)" | "§99(4)" | "§99(5) Stiftungsprofessur (BEST)",
  geschlecht:          "W" | "M",
  herkunft:            "intern" | "extern",
  herkunft_institution:"University of …",
  herkunft_land:       "Deutschland" | "USA" | "Österreich" | …,
  ofos_code:           "604"  (3-stellig),
  ofos_label:          "Kunstwissenschaften (Fotografie)",
  ofos_bereich_code:   "6",
  ofos_bereich:        "Geisteswissenschaften",
  ofos_hauptgruppe_code: "60",
  ofos_hauptgruppe:    "Geisteswissenschaften (Hauptgruppe)",
  grants:              ["FWF", "ERC", "Horizon Europe"],
  wwtf_programme:      ["LS", "CS"],   // WWTF-Programmfelder (heuristisch, s. 4.5)
  h_index:             32,             // strukturierte OpenAlex-Metriken
  publikationen:       139,
  zitierungen:         3443,
  openalex_id:         "A5033263383",  // sofern in OpenAlex gefunden
  bio_text:            "Kurzbeschreibung. h-Index: 32 | Publikationen: 139 | Zitierungen: 3443",
  werdegang:           "CV-Text (sofern verfügbar)",
  profil_url:          "https://www.tuwien.at/…",
  monat:               "JÄNNER" | "FEBRUAR" | …,
  year:                2025
}
```

## 6. Visualisierungen im Detail

### 6.1 KPI-Zeile (Übersicht)
- **90** Berufungen gesamt
- **40 W / 50 M** (44 % / 56 % Frauenanteil)
- **69 extern** (§98 Wettbewerbsberufungen)
- **17 intern** (§99 Abs. 4 Qualifikationsstellen)

### 6.2 Geschlecht × Universität (gestapeltes Balkendiagramm)
Zeigt für jede der 8 Universitäten die Aufteilung W/M. Auffällig:
TU Wien (28) und Uni Wien (23) dominieren erwartungsgemäß; MedUni Wien (10) und
mdw (11) sind stark überrepräsentiert bei Männern bzw. ausgewogen.

### 6.3 Berufungen nach Monat (Balkendiagramm)
Spitzen im **Oktober (31)** – typisches Berufungssemester; ein zweites,
kleineres Maximum im März. Sehr wenige Berufungen im Juni (1).

### 6.4 ÖFOS-Bereiche (1-stellig) – horizontales Balkendiagramm
Sechs Bereiche:
- 1 Naturwissenschaften (22)
- 6 Geisteswissenschaften (22)
- 5 Sozialwissenschaften (17)
- 2 Technische Wissenschaften (14)
- 3 Medizin, Gesundheit (9)
- 4 Agrar, Veterinärmedizin (4)

### 6.5 Universitäten × ÖFOS-Bereich (Heatmap)
Aktivitätsprofil: Welche Universität hat in welchem Bereich wie viele Berufungen?
- **TU Wien**: 14 Naturwiss. + 12 Technik + 2 Sozialwiss.
- **Uni Wien**: 6 Naturwiss. + 8 Sozialwiss. + 9 Geisteswiss.
- **MedUni Wien**: 9 Medizin (dominant) + 1 Naturwiss.
- **mdw**: 9 Geisteswiss. (Kunst/Musik) + 2 Sozialwiss.
- **BOKU**: breit gestreut (1/2/2/1)
- **Angewandte**: 4 Geisteswiss.
- **WU Wien**: 4 Sozialwiss.
- **Vetmeduni**: 2 Agrar/Vetmed.

### 6.6 Sankey-Diagramm: Herkunft → Universität (Vollbreite, 600+ px hoch)
14 Herkunftsländer × 8 Universitäten. Die Strichdicke entspricht der
Anzahl der Berufungen. Sichtbar:
- **Intern (Wien)**: 45 Berufungen (51 % aller Berufungen) – interner Wiener
  Arbeitsmarkt dominiert
- **Deutschland**: 13 (größtes externes Herkunftsland)
- **Österreich (extern)**: 8 (von anderen österr. Unis)
- **USA**: 6
- **Italien, Slowakei, Slowenien, Türkei, Argentinien, Russland, Israel,
  Kanada, Schweiz, Niederlande, Norwegen**: je 1–2

### 6.7 Force-Graph: Universitäten × ÖFOS-Bereiche
- **Knoten**: jede Professur
- **Farbe**: Universität (8 Uni-Farben)
- **Position**: ÖFOS-Bereich (1–6) – 6 Cluster-Zentren
- **Größe**: h-Index

Die Visualisierung macht sichtbar, welche Unis in welchen Bereichen aktiv sind
und wo Überlappungen bestehen (z.B. Uni Wien und BOKU teilen sich den Bereich 1).

### 6.8 Uni × Uni Überlappungs-Matrix (Heatmap)
Zeigt für jedes Uni-Paar, wie viele ÖFOS-3-Steller-Bereiche sie gemeinsam besetzen.
Hohe Werte = viel thematische Überlappung (mögliche Konkurrenzsituation oder
komplementäre Stärkefelder).

### 6.9 Tab „WWTF-Perspektive"
Eigener Tab, der die Berufungen 2025 als strategische Ressource für den WWTF
aufbereitet — neu berufene Professor:innen sind potenzielle Antragsteller:innen,
Kooperationspartner:innen und Jury-/Gutachter:innen-Kontakte:

- **KPI-Zeile**: 29 in WWTF-Programmfeldern (33 %), davon extern/international
  rekrutiert, Frauenanteil, Median h-Index
- **Kernaussagen**: automatisch berechnete Takeaways (Top-Uni, internationale
  Rekrutierungen, sichtbarste Neuzugänge)
- **Balkendiagramm** pro Programmfeld (Mehrfachzuordnung möglich)
- **Programmfeld-Karten** mit Personen-Chips (Name, Uni, Herkunft, h-Index),
  klickbar → springt zur gefilterten Profilkarte
- **Methodik-Hinweis** zur heuristischen Natur der Zuordnung (s. 4.5)

### 6.10 Werkzeuge
- **CSV-Export**: die aktuell gefilterte Kartenansicht als Excel-AT-kompatibles
  CSV (Semikolon-Separator, UTF-8-BOM, 18 Spalten inkl. WWTF-Programmfelder
  und Metriken)
- **Sortierung** der Profilkarten: Monat (Default), Name, h-Index, Universität
- **Teilbare Links**: Tab- und Filterzustand wird in der URL-Fragment-Kennung
  gehalten (`#tab=alle&filter-wwtf=LS`) und beim Laden wiederhergestellt

## 7. Bekannte Einschränkungen

1. **§99(4) Zuordnung Stathis Megas**: ein MedUni-Wien-Eintrag ist als §99(4)
   (intern) geführt, obgleich der OpenAlex-Track eine externe Karriere zeigt.
   Möglicher Datenfehler in der Originalquelle; bei nächster Aktualisierung zu prüfen.
2. **3 fehlende `bio_text`-Felder** (Iva Hunger Brezinova, Mischa Janisch,
   Wilhelm Spuller): keine OpenAlex-Treffer (rein künstlerische bzw. Industrie-Karrieren).
3. **Christine Sheppard (BOKU)**: Herkunftsinstitution und -land nicht öffentlich
   dokumentiert – bleibt `null`.
4. **Herkunft Österreich vs. AT**: Land ist in den Quelldaten teilweise als
   ISO-Code („AT") und teilweise als Name („Österreich") erfasst. Bei der
   Anreicherung normalisiert.
5. **Herkunft „Universität Wien" → MedUni Wien** (Andreas Zuckermann,
   Thomas Scherer, Balázs Hangya, Michael Bonelli): diese Personen waren
   formal an der Uni Wien beschäftigt, wurden aber für die §98-Stelle an der
   MedUni Wien berufen. Korrekt als extern klassifiziert.

## 8. Reproduzierbarkeit

Ein Befehl führt die gesamte idempotente Pipeline aus und druckt am Ende den
Lücken-Report:

```bash
scripts/update.sh
```

Einzelstufen (in Reihenfolge):

```bash
python3 scripts/openalex_lookup.py   # OpenAlex für ungeprüfte Einträge + Overrides (~2 Min. beim ersten Lauf)
python3 scripts/enrich.py            # Geschlecht, ÖFOS-Ebenen, E-Codes, Herkunft-Merge (~5 Sek.)
python3 scripts/wwtf_enrich.py       # strukturierte Metriken + WWTF-Programmfelder
python3 scripts/fill_gaps.py         # Werdegang/Profil-Links auto-füllen (manuell > API > generiert)
python3 scripts/build_html.py        # HTML-Generierung (~1 Sek.)
python3 scripts/audit_gaps.py        # Lücken-Report → data_gaps.csv
```

Manuell recherchierte Sonderfälle liegen in zwei Dateien:
- `scripts/herkunft_research.json` — frühe manuelle Herkunfts-Recherche
- `scripts/openalex_overrides.json` — geprüfte OpenAlex-IDs und „kein Profil"-
  Markierungen (s. 4.6)

## 9. Lizenz & Nutzung

- **Daten**: CC-BY 4.0 (mit Quellenangabe WWTF / Berufungsradar Wien 2025)
- **Code**: MIT
- **OpenAlex-Daten**: CC0

Für eine Weiterverwendung der Daten bitten wir um Quellenangabe und kurze
Mitteilung an benjamin.missbach@wwtf.at.

## 10. Versionshistorie

| Datum | Commit | Änderung |
|---|---|---|
| 04.06.2026 | `2d00211` | Initial release (51 Einträge, TU Wien + Uni Wien Pilot) |
| 08.06.2026 | `144f378` | 88 Einträge, 100 % ÖFOS, alle 8 Unis |
| 08.06.2026 | `b0dc722` | Anreicherungs-Pipeline, Heatmap, Uni-Overlap, Force-Graph by Uni |
| 09.06.2026 | `f4c5072` | UNIS-Array-Fix, ÖFOS-Kategorienamen auf Heatmap-Achsen |
| 09.07.2026 | — | WWTF-Perspektive-Tab, strukturierte Metriken, CSV-Export, Sortierung, teilbare Filter-Links, Kernaussagen-Boxen, Farb-Fix Uni Wien/MedUni Wien |
| 09.07.2026 | — | 9. Universität ergänzt (Akademie der bildenden Künste: Brorson, Schachinger → 90 Einträge); fail-safe Datenstrategie: OpenAlex-Lookup für alle Einträge mit Match-Validierung + Negativ-Cache, fill_gaps.py (Werdegang/Profil-Links auto, manuell > API > generiert), audit_gaps.py (data_gaps.csv), update.sh; Geschlechts-Badges m/f |

## 11. Kontakt

**Benjamin Missbach**
Wiener Wissenschafts-, Forschungs- und Technologiefonds (WWTF)
benjamin.missbach@wwtf.at
