#!/usr/bin/env python3
"""
Laufende Erfassung Akademie der bildenden Künste über die News-Ordner.

Die Akademie meldet jede Berufung mit festem Titelmuster, Name, Fach und
Antritt stehen schon im Titel:

    "Neue Professorin für Architekturentwurf ab 17.2.: Imke Woelk"
    "Neuer Professor für Architekturtheorie und Architekturentwurf HTC ab 1.10.: Lutz Robbers"

Die Seite ist ein Plone-CMS; mit "Accept: application/json" liefert der
Jahresordner seine Einträge als JSON (REST-API), ohne HTML-Parsing.
Gelesen werden das laufende und das vorige Jahr.

Schreibt scripts/backfill/akbild_live.json.
"""

import json
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "backfill" / "akbild_live.json"

ORDNER = "https://www.akbild.ac.at/de/news/{jahr}?b_size=300"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"
MONATE = ["JÄNNER", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI", "JULI",
          "AUGUST", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"]

TITEL = re.compile(r"^Neue[r]? Professor(?:in)? für (?P<fach>.+?) ab "
                   r"(?P<tag>\d{1,2})\.\s*(?P<monat>\d{1,2})\.(?P<jahr>\d{4})?\s*:\s*(?P<name>.+)$")


def hole(jahr):
    req = urllib.request.Request(ORDNER.format(jahr=jahr),
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r).get("items", [])
    except urllib.error.HTTPError as e:
        if e.code == 404:        # Ordner fürs neue Jahr existiert im Jänner noch nicht
            return []
        raise


def main():
    heuer = date.today().year
    meldungen, daten = 0, []
    for ordnerjahr in (heuer - 1, heuer):
        for item in hole(ordnerjahr):
            meldungen += 1
            m = TITEL.match(item.get("title") or "")
            if not m:
                continue
            daten.append({
                "name": m["name"].strip(),
                "universitat": "Akademie",
                "monat": MONATE[int(m["monat"]) - 1],
                "year": int(m["jahr"] or ordnerjahr),
                "forschungsbereich": m["fach"].strip(),
                "geschlecht": "W" if "Professorin" in item["title"] else "M",
                "quelle": item["@id"],
                "stufe": 1,
            })
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(daten)} Berufungen aus {meldungen} Meldungen Akademie → {OUT.relative_to(ROOT)}")
    return meldungen, daten


if __name__ == "__main__":
    meldungen, daten = main()
    assert meldungen >= 20, f"nur {meldungen} Meldungen gelesen, API geändert?"
    print("✓ Selbstcheck ok")
