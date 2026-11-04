#!/usr/bin/env python3
"""
Daten-Lücken-Report: was fehlt wem, und wo recherchiert man es nach?

Schreibt data_gaps.csv (Recherche-Warteschlange für manuelle Ergänzung)
und druckt eine Zusammenfassung. Reine Analyse, verändert nichts.
"""

import csv
import json
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
OUT_PATH = ROOT / "data_gaps.csv"
OA_PATH = ROOT / "scripts" / "openalex_research.json"

# Feld → (Beschreibung, automatisch füllbar?)
FIELDS = {
    "werdegang": "Werdegang/CV",
    "profil_url": "Profil-Link",
    "bio_text": "Kurzbeschreibung",
    "herkunft_institution": "Herkunftsinstitution",
    "herkunft_land": "Herkunftsland",
    "fakultat_institut": "Fakultät/Institut",
    "h_index": "OpenAlex-Metriken",
}

UNI_SEARCH = {
    "TU Wien": "https://www.tuwien.at/suche?tx_solr[q]={q}",
    "Uni Wien": "https://ufind.univie.ac.at/de/search.html?query={q}",
    "MedUni Wien": "https://www.meduniwien.ac.at/web/index.php?id=suche&L=0&q={q}",
    "WU Wien": "https://www.wu.ac.at/suche?q={q}",
    "BOKU": "https://boku.ac.at/suche?q={q}",
    "mdw": "https://www.mdw.ac.at/suche/?q={q}",
    "Angewandte": "https://www.dieangewandte.at/suche?q={q}",
    "Vetmeduni Wien": "https://www.vetmeduni.ac.at/suche?q={q}",
}


def ohne_profil(d, oa):
    """OpenAlex geprüft, aber kein passendes Profil (meist künstlerische Professuren)."""
    e = oa.get(d["name"]) or {}
    return e.get("_openalex") == "not found" or e.get("match_confidence") == "low"


def vorhanden(d, f, oa):
    if f == "h_index":
        # 0 ist ein Wert; „geprüft, kein Profil" ist ein Ergebnis, keine Lücke
        return d.get(f) is not None or ohne_profil(d, oa)
    if f == "fakultat_institut":
        return bool(d.get(f) or d.get("fakultat"))   # so zeigt es das Dashboard
    return bool(d.get(f))


def main():
    data = json.loads(DATA_PATH.read_text())
    oa = json.loads(OA_PATH.read_text()) if OA_PATH.exists() else {}
    rows = []
    field_counts = Counter()

    for d in data:
        # Auto-gefüllte Felder zählen als „vorhanden, aber nur API-Qualität"
        missing = [f for f in FIELDS if not vorhanden(d, f, oa)]
        auto = [f for f in ("werdegang", "profil_url") if d.get(f + "_auto")]
        for f in missing:
            field_counts[f] += 1
        if not missing and not auto:
            continue
        q = urllib.parse.quote(d["name"])
        rows.append({
            "name": d["name"],
            "universitaet": d["universitat"],
            "fehlend": ", ".join(FIELDS[f] for f in missing),
            "nur_auto_befuellt": ", ".join(FIELDS[f] for f in auto),
            "uni_suche": UNI_SEARCH.get(d["universitat"], "").format(q=q),
            "google": f"https://www.google.com/search?q={q}+{urllib.parse.quote(d['universitat'])}+Professur",
        })

    rows.sort(key=lambda r: (-len(r["fehlend"]), r["universitaet"], r["name"]))

    with OUT_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
        w.writeheader()
        w.writerows(rows)

    print(f"Lücken-Report ({len(data)} Einträge):")
    for f, label in FIELDS.items():
        n = field_counts[f]
        bar = "█" * n
        print(f"  {label:22} {n:3} fehlen  {bar}")
    n_ohne = sum(1 for d in data if d.get("h_index") is None and ohne_profil(d, oa))
    print(f"  {'(kein OpenAlex-Profil)':22} {n_ohne:3}  geprüft, keine Lücke")
    n_auto = sum(1 for d in data if d.get("werdegang_auto") or d.get("profil_url_auto"))
    print(f"  {'(auto-befüllt via API)':22} {n_auto:3}")
    print(f"\n✓ Recherche-Warteschlange: {len(rows)} Personen → {OUT_PATH.name}")


if __name__ == "__main__":
    main()
