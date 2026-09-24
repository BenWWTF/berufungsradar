#!/usr/bin/env python3
"""
Backfill Uni Wien aus der Personalliste der Universität (Dienstantritte von
Universitätsprofessor*innen und Tenure Track-Professor*innen, 2019 bis
September 2026, übermittelt an den WWTF am 24.09.2026).

Die Liste ist die Primärquelle für Dienstantrittsjahre. Was sie NICHT enthält:
  * Monate (nur das Jahr), deshalb monat = None statt eines Schätzwerts
  * befristete Professuren nach §99(1) ohne Tenure Track
  * assoziierte Professuren (§99(4)) vor der Beförderung
  * frühere Stationen derselben Person: pro Person eine Zeile, die jüngste
    (Semola TT 2024 fehlt, Semola UP 2026 steht drin)
  * Weggänge (wer die Uni inzwischen verlassen hat, steht trotzdem drin)
Datensätze im Bestand, die hier fehlen, sind deshalb nicht automatisch falsch.

Tenure Track wird als §99(1) geführt, wie in den Leistungsberichten der Uni
Wien ("Tenure-Track-Professur, 6-Jahres-Vertrag, §99 Abs. 1 UG"). Für
Universitätsprofessuren bleibt der Paragraf offen: darunter sind §98-Berufungen
ebenso wie §99(4)-Beförderungen, die Liste trennt das nicht.

Aufruf: python3 scripts/backfill_univie_hr.py --input <liste.tsv>
        (TSV: typ[UP|TT], fakultaet, widmung, name, jahr)
Danach: python3 scripts/merge_backfill.py backfill/univie_hr.json
"""

import argparse
import csv
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "backfill" / "univie_hr.json"
QUELLE = ("Universität Wien, Personalliste Dienstantritte UP/TT 2019–09/2026 "
          "(an WWTF übermittelt 24.09.2026)")
STELLE = {"UP": "Universitätsprofessur", "TT": "Tenure Track-Professur"}

# Gastprofessuren sind keine Berufungen
AUSSCHLUSS = {"Simon Strick"}   # Sir Peter Ustinov Gastprofessur 2026

# Schreibweise im Bestand ≠ Schreibweise der Liste, gleiche Person und Stelle.
# Der Bestandsname gewinnt, sonst legt der Merge eine Dublette an.
BESTANDSNAME = {
    "Balázs Szendröi": "Balázs Szendrői",
    "Maria Emmanuella Plakogiannaki": "Emmanuella Plakoyiannaki",
    "Michael Suter": "Mischa Suter",
    "Dorothea Maria Bosch": "Marjolein Bosch",
    "Rosella Ferrari": "Rossella Ferrari",
    "Stephanie Wienkoop": "Stefanie Wienkoop",
    "Solveig Elisabeth Nitzke": "Solvejg Nitzke",
}

# Offensichtliche Tippfehler der Liste (für neue Datensätze und OpenAlex)
TIPPFEHLER = {
    "Avaro Gonzalez Hacar": "Alvaro Hacar",
    "Maximillian Fochler": "Maximilian Fochler",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    zeilen = list(csv.DictReader(ap.parse_args().input.open(encoding="utf-8"),
                                 delimiter="\t"))
    daten = []
    for z in zeilen:
        name = z["name"].strip()
        if name in AUSSCHLUSS:
            continue
        name = BESTANDSNAME.get(name) or TIPPFEHLER.get(name) or name
        daten.append({
            "name": name,
            "universitat": "Uni Wien",
            "monat": None,
            "year": int(z["jahr"]),
            "art_berufung": "§99(1)" if z["typ"] == "TT" else None,
            "stellentyp": STELLE[z["typ"]],
            "fakultat": z["fakultaet"].strip(),
            "forschungsbereich": z["widmung"].strip(),
            "quelle": QUELLE,
            "_kuratiert": f"{QUELLE}: {STELLE[z['typ']]}, Dienstantritt {z['jahr']}.",
            "stufe": 1,
        })
    daten.sort(key=lambda d: (d["year"], d["name"]))
    OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(daten)} Dienstantritte → {OUT.name} "
          f"({len(zeilen) - len(daten)} ausgeschlossen)")
    return zeilen, daten


if __name__ == "__main__":
    zeilen, daten = main()
    namen = [d["name"] for d in daten]
    assert len(namen) == len(set(namen)), "Person doppelt in der Liste"
    assert all(2019 <= d["year"] <= 2026 for d in daten)
    assert {z["typ"] for z in zeilen} <= set(STELLE)
    print("✓ Selbstcheck ok")
