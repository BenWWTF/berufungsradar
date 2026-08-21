#!/usr/bin/env python3
"""
Backfill für die BOKU über das Mitteilungsblatt.

Anders als Uni Wien und MedUni verlautbart die BOKU Berufungen tatsächlich mit
Namen — allerdings indirekt, über Senatsmeldungen:

    Aus dem Senat scheidet mit 1.1.2022 Univ.Prof. Dipl.-Ing. Dr. Alfred STRAUSS
    aufgrund seiner Berufung zum Universitätsprofessor als Mitglied des
    Mittelbaus aus.

Das erfasst §99(4)-Berufungen aus dem eigenen Haus. Dazu kommen direkte
Verlautbarungen ("wurde zum Universitätsprofessor berufen") und
Antrittsvorlesungs-Hinweise. Externe §98-Berufungen tauchen im Mitteilungsblatt
nur teils auf, deshalb bleibt die BOKU-Abdeckung "teilweise".

Das Mitteilungsblatt liegt ab dem Studienjahr 2019/20 als HTML je Stück vor,
davor als PDF (nicht ausgewertet).

Aufruf: python3 scripts/backfill_boku.py [--offline]
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from namen import namensform, plausibel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent / "backfill"
CACHE = Path(__file__).resolve().parent / ".boku_cache"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

BASIS = "https://boku.ac.at/mitteilungsblatt/mitteilungsblaetter-"
STUDIENJAHRE = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

MONATSNAME = ["JÄNNER", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI", "JULI",
              "AUGUST", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"]

# Berufung mit Namen, in beiden Richtungen formuliert
MUSTER = [
    # "… scheidet mit 1.1.2022 Univ.Prof. … STRAUSS aufgrund seiner Berufung zum
    #  Universitätsprofessor … aus"
    re.compile(r"mit\s+(?P<tag>\d{1,2})\.(?P<monat>\d{1,2})\.(?P<jahr>20\d\d)\s+"
               r"(?P<name>[^;:]{5,95}?)\s+aufgrund\s+(?P<pron>seiner|ihrer)\s+"
               r"Berufung\s+zu(?:r|m)\s+Universitätsprofessor", re.I),
    # "… wurde mit 1.10.2023 zum Universitätsprofessor für X berufen"
    re.compile(r"(?P<name>[^;:]{5,95}?)\s+wurde\s+mit\s+(?P<tag>\d{1,2})\.(?P<monat>\d{1,2})\."
               r"(?P<jahr>20\d\d)\s+zu(?:r|m)\s+(?P<titel>Universitätsprofessorin|Universitätsprofessor)"
               r"(?:\s+für\s+(?P<fach>[^.;]{3,80}?))?\s+berufen", re.I),
]

# Denomination aus §99(4)-Verlautbarungen, ohne Namen — nur als Kontext geloggt
VERLAUTBARUNG = re.compile(r"§\s?99\s?Abs\.?\s?4[^.]{0,120}?[„\"']([^„\"']{4,90})[\"'“]", re.I)


def hole(url, datei):
    CACHE.mkdir(exist_ok=True)
    ziel = CACHE / datei
    if ziel.exists():
        return ziel.read_text(encoding="utf-8")
    if "--offline" in sys.argv:
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            inhalt = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ! {type(e).__name__}: {url[-60:]}")
        return ""
    ziel.write_text(inhalt, encoding="utf-8")
    time.sleep(0.4)
    return inhalt


def text(seite):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", seite, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def stuecke(studienjahr):
    seite = hole(BASIS + studienjahr, f"index_{studienjahr}.html")
    if not seite:
        return []
    pfade = sorted(set(re.findall(
        rf"(mitteilungsblaetter-{studienjahr}/\d{{2}}-stueck-\d{{8}})", seite)))
    return [f"https://boku.ac.at/mitteilungsblatt/{p}" for p in pfade]


def parse_stueck(url):
    seite = hole(url, re.sub(r"[^A-Za-z0-9]+", "_", url.split("/")[-1]) + ".html")
    if not seite:
        return [], []
    inhalt = text(seite)
    treffer = []
    for muster in MUSTER:
        for m in muster.finditer(inhalt):
            felder = m.groupdict()
            # "(Liste BOKU)" und ähnliche Klammerzusätze sind kein Namensteil
            name = namensform(re.sub(r"\([^)]*\)", " ", felder["name"]))
            if not plausibel(name):
                continue
            monat = int(felder["monat"])
            if not 1 <= monat <= 12:
                continue
            weiblich = (felder.get("pron") == "ihrer"
                        or felder.get("titel") == "Universitätsprofessorin")
            treffer.append({
                "name": name,
                "universitat": "BOKU",
                "monat": MONATSNAME[monat - 1],
                "year": int(felder["jahr"]),
                "art_berufung": "§99(4)" if felder.get("pron") else "§98",
                "forschungsbereich": (felder.get("fach") or "").strip(" ,;") or None,
                "geschlecht": "W" if weiblich else "M",
                "profil_url": None,
                "quelle": url,
                "stufe": 1,
            })
    denoms = [d.strip() for d in VERLAUTBARUNG.findall(inhalt)]
    return treffer, denoms


def main():
    alle, alle_denoms = [], []
    for sj in STUDIENJAHRE:
        liste = stuecke(sj)
        gefunden = []
        for url in liste:
            treffer, denoms = parse_stueck(url)
            gefunden.extend(treffer)
            alle_denoms.extend(denoms)
        print(f"   {sj}: {len(liste)} Stücke, {len(gefunden)} Berufungen")
        alle.extend(gefunden)

    gesehen, eindeutig = set(), []
    for e in alle:
        s = (e["name"].lower(), e["year"])
        if s in gesehen:
            continue
        gesehen.add(s)
        eindeutig.append(e)

    OUT_DIR.mkdir(exist_ok=True)
    ziel = OUT_DIR / "boku.json"
    ziel.write_text(json.dumps(eindeutig, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(eindeutig)} Berufungen BOKU → {ziel.relative_to(ROOT)}")
    print(f"  dazu {len(set(alle_denoms))} Denominationen aus §99(4)-Verlautbarungen "
          f"(ohne Namen, nicht übernommen)")
    return eindeutig


if __name__ == "__main__":
    daten = main()
    assert all(plausibel(d["name"]) for d in daten), [d["name"] for d in daten][:5]
    assert all(d["monat"] in MONATSNAME and 2019 <= d["year"] <= 2027 for d in daten)
    print("✓ Selbstcheck ok")
