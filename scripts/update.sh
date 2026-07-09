#!/bin/bash
# Kompletter Daten-Refresh + Rebuild in einem Aufruf.
# Fail-safe: jede Stufe ist idempotent, manuell gepflegte Felder
# werden nie überschrieben (siehe fill_gaps.py).
set -euo pipefail
cd "$(dirname "$0")"

echo "── 1/5 OpenAlex-Lookup (nur ungeprüfte Einträge) ──"
python3 openalex_lookup.py

echo "── 2/5 Basis-Anreicherung (Geschlecht, ÖFOS, E-Codes) ──"
python3 enrich.py

echo "── 3/5 WWTF-Anreicherung (Metriken, Programmfelder) ──"
python3 wwtf_enrich.py

echo "── 4/5 Lücken füllen (Werdegang, Profil-Links) ──"
python3 fill_gaps.py

echo "── 5/5 HTML-Build ──"
python3 build_html.py

echo ""
python3 audit_gaps.py
