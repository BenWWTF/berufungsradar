#!/bin/bash
# Kompletter Daten-Refresh + Rebuild in einem Aufruf.
# Fail-safe: jede Stufe ist idempotent, manuell gepflegte Felder
# werden nie überschrieben (siehe fill_gaps.py).
set -euo pipefail
cd "$(dirname "$0")"

echo "── 1/7 OpenAlex-Lookup (nur ungeprüfte Einträge) ──"
python3 openalex_lookup.py

echo "── 2/7 ÖFOS-Zuordnung für neue Einträge ──"
python3 classify_ofos.py

echo "── 3/7 Basis-Anreicherung (Geschlecht, ÖFOS, E-Codes) ──"
python3 enrich.py

echo "── 4/7 WWTF-Anreicherung (Metriken, Programmfelder, VRG) ──"
python3 wwtf_enrich.py

echo "── 5/7 Lücken füllen (Werdegang, Profil-Links) ──"
python3 fill_gaps.py

echo "── 6/7 Herkunft aus Lebensläufen ableiten ──"
python3 herkunft_aus_cv.py

echo "── 7/7 HTML-Build ──"
python3 build_html.py

echo ""
python3 audit_gaps.py
