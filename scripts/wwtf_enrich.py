#!/usr/bin/env python3
"""
Stage 5: WWTF-Anreicherung.

1. Strukturierte Metriken (h_index, publikationen, zitierungen) aus bio_text
   extrahieren + openalex_id aus openalex_research.json übernehmen.
2. wwtf_programme: heuristische Zuordnung ÖFOS-Code/-Label → WWTF-Programmfelder.

Läuft nach enrich.py, vor build_html.py. Idempotent.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
OA_PATH = ROOT / "scripts" / "openalex_research.json"

# WWTF-Programmfelder (Kürzel → Anzeige)
PROGRAMMES = {
    "LS": "Life Sciences",
    "ICT": "Information & Communication Technology",
    "CS": "Cognitive Sciences",
    "ESR": "Environmental Systems Research",
    "DH": "Digital Humanism",
    "MA": "Mathematik und …",
}

# ÖFOS-3-Steller → Programmfelder (Basiszuordnung)
OFOS_TO_PROG = {
    "101": ["MA"],
    "102": ["ICT"],
    "106": ["LS"],
    "202": ["ICT"],
    "207": ["ESR"],
    "301": ["LS"],
    "302": ["LS"],
    "304": ["LS"],
    "401": ["ESR"],
    "403": ["LS"],
    "501": ["CS"],
}

# Keyword-Zusätze auf ofos_label / forschungsbereich (case-insensitive)
KEYWORD_PROG = [
    (r"neuro", "CS"),
    (r"naturschutz|ökologie|wald|umwelt|wasser", "ESR"),
    (r"mensch-maschine|künstliche intelligenz|digital", "DH"),
]


def infer_programmes(d):
    progs = list(OFOS_TO_PROG.get(d.get("ofos_code") or "", []))
    text = f"{d.get('ofos_label') or ''} {d.get('forschungsbereich') or ''}".lower()
    for pattern, prog in KEYWORD_PROG:
        if re.search(pattern, text) and prog not in progs:
            progs.append(prog)
    return progs


def extract_metrics(bio):
    m = {}
    if not bio:
        return m
    for key, pattern in [
        ("h_index", r"h-Index:\s*(\d+)"),
        ("publikationen", r"Publikationen:\s*(\d+)"),
        ("zitierungen", r"Zitierungen:\s*(\d+)"),
    ]:
        hit = re.search(pattern, bio, re.I)
        if hit:
            m[key] = int(hit.group(1))
    return m


def main():
    data = json.loads(DATA_PATH.read_text())
    oa = json.loads(OA_PATH.read_text()) if OA_PATH.exists() else {}

    n_metrics = n_prog = 0
    for d in data:
        metrics = extract_metrics(d.get("bio_text"))
        # openalex_research.json überschreibt bio_text-Werte (aktuellere Quelle);
        # low-confidence Treffer (Namensvetter) werden ignoriert
        entry = oa.get(d["name"]) or {}
        if entry.get("match_confidence") == "low":
            entry = {}
        if entry.get("h_index") is not None:
            metrics["h_index"] = entry["h_index"]
        if entry.get("works_count") is not None:
            metrics["publikationen"] = entry["works_count"]
        if entry.get("cited_by_count") is not None:
            metrics["zitierungen"] = entry["cited_by_count"]
        if entry.get("openalex_id"):
            d["openalex_id"] = entry["openalex_id"]
        d.update({k: metrics.get(k) for k in ("h_index", "publikationen", "zitierungen")})
        if metrics:
            n_metrics += 1

        d["wwtf_programme"] = infer_programmes(d)
        if d["wwtf_programme"]:
            n_prog += 1

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")

    print(f"✓ {len(data)} Einträge: {n_metrics} mit Metriken, {n_prog} in WWTF-Programmfeldern")
    from collections import Counter

    c = Counter(p for d in data for p in d["wwtf_programme"])
    for k, v in c.most_common():
        print(f"  {k:4} {PROGRAMMES[k]:42} {v}")


if __name__ == "__main__":
    main()
    # Selbstcheck
    data = json.loads(DATA_PATH.read_text())
    assert all("wwtf_programme" in d for d in data)
    assert any(d.get("h_index") for d in data)
    assert "LS" in next(d for d in data if d["ofos_code"] == "302")["wwtf_programme"]
