#!/usr/bin/env python3
"""
Backfill fuer CEU (Central European University, Wien).

Quelle ist kein Scrape wie bei den 9 oeffentlichen Unis, sondern ein
HR-Datenexport (Personalliste mit Rang-Historie je Person: personId,
displayName, class, rank, effStartDate, effEndDate, promotion). Kein
oeffentlicher "Neue Professuren"-Feed vorhanden, deshalb --input statt Scrape;
manuell erneut laufen lassen, wenn ein neuer Export kommt.

Filter:
  * class == "Faculty Member" (Visiting Faculty faellt raus)
  * rank in PROFESSOR_RAENGE (nur Professuren, keine Lecturer/Postdocs)
  * pro Person nur die fruehste Zeile = Ersternennung an der CEU
  * Personen, deren fruehste Zeile exakt der 2020-09-01-Stichtag ist, fallen
    raus: das ist der Umzug Budapest->Wien, keine Neuberufung.

Aufruf: python3 scripts/backfill_ceu.py --input /pfad/zum/export.xlsx
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import openpyxl

OUT_DIR = Path(__file__).resolve().parent / "backfill"
AB_JAHR = 2019
UMZUGSSTICHTAG = datetime(2020, 9, 1)

PROFESSOR_RAENGE = {"Assistant Professor", "Associate Professor",
                    "Full Professor", "University Professor"}

MONATE = ["JÄNNER", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI", "JULI",
          "AUGUST", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"]


def norm(name):
    t = unicodedata.normalize("NFKD", (name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.lower()).strip()


def lade(pfad):
    wb = openpyxl.load_workbook(pfad, read_only=True, data_only=True)
    ws = wb["resident-faculty"]
    zeilen = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] is not None]
    return zeilen  # personId, displayName, class, rank, effStartDate, effEndDate, promotion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Pfad zum Faculty-Export (.xlsx)")
    args = ap.parse_args()

    zeilen = lade(args.input)

    nach_person = {}
    for pid, name, klasse, rang, start, ende, promo in zeilen:
        nach_person.setdefault(pid, []).append((start, name, klasse, rang))
    for v in nach_person.values():
        v.sort(key=lambda r: r[0])

    ergebnis = []
    uebersprungen_umzug = 0
    for pid, v in nach_person.items():
        start, name, klasse, rang = v[0]          # fruehste Zeile = Ersternennung
        if start == UMZUGSSTICHTAG:
            uebersprungen_umzug += 1
            continue
        if klasse != "Faculty Member" or rang not in PROFESSOR_RAENGE:
            continue
        if start.year < AB_JAHR:
            continue
        ergebnis.append({
            "name": name,
            "universitat": "CEU",
            "monat": MONATE[start.month - 1],
            "year": start.year,
            "art_berufung": "CEU (privat)",
            "werdegang": f"Seit {MONATE[start.month - 1].title()} {start.year} "
                         f"{rang} an der CEU (Central European University), Wien.",
            "quelle": "CEU Faculty-Datenexport (HR), bereitgestellt von der Universitaet",
            "stufe": 1,
        })

    ergebnis.sort(key=lambda d: (d["year"], d["name"]))
    OUT_DIR.mkdir(exist_ok=True)
    ziel = OUT_DIR / "ceu.json"
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1) + "\n")

    jahre = {}
    for d in ergebnis:
        jahre[d["year"]] = jahre.get(d["year"], 0) + 1
    print(f"✓ {len(ergebnis)} Neuberufungen CEU ab {AB_JAHR} → {ziel}")
    print(f"  Umzugsstichtag 2020-09-01 uebersprungen: {uebersprungen_umzug} Personen")
    for j in sorted(jahre):
        print(f"   {j}: {jahre[j]}")
    return ergebnis


if __name__ == "__main__":
    daten = main()
    assert daten, "keine Neuberufungen gefunden"
    assert all(d["name"] and d["year"] >= AB_JAHR for d in daten)
    assert all(d["monat"] in MONATE for d in daten)
    namen = [norm(d["name"]) for d in daten]
    assert len(namen) == len(set(namen)), "Dubletten im Ergebnis"
    print("✓ Selbstcheck ok")
