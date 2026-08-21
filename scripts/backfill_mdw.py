#!/usr/bin/env python3
"""
Backfill Stufe 1 für die mdw (Universität für Musik und darstellende Kunst).

Quelle: die mdw pflegt eine Seite je Jahr ("Neue Professuren <Jahr>") mit einem
immer gleich gebauten Satz pro Person:

    Mit 1. Oktober trat Eszter Haffner ihre Professur für Violine am
    Fritz Kreisler Institut … an.

Daraus fallen Name, Monat, Fach, Institut und über "seine/ihre" auch das
Geschlecht an — bei der mdw ist das kein Rateschluss aus dem Vornamen, sondern
steht in der Quelle.

Die älteren Jahresseiten haben keine sprechende Adresse, sondern nur eine
TYPO3-Seitennummer. Für 2015, 2016 und 2018 ist keine Seite auffindbar; diese
Jahre bleiben offen (siehe SPEC.md).

Schreibt scripts/backfill/mdw.json.
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent / "backfill"
CACHE = Path(__file__).resolve().parent / ".backfill_cache"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

SEITEN = {
    2014: "https://www.mdw.ac.at/416/",
    2017: "https://www.mdw.ac.at/895/",
    2019: "https://www.mdw.ac.at/1225/",
    2020: "https://www.mdw.ac.at/1545/",
    2021: "https://www.mdw.ac.at/1614/",
    2022: "https://www.mdw.ac.at/1681/",
    2023: "https://www.mdw.ac.at/1805/",
    2024: "https://www.mdw.ac.at/1896/",
    2025: "https://www.mdw.ac.at/2026/",
    2026: "https://www.mdw.ac.at/neue-professuren-2026/",
}

MONATE = {
    "jänner": "JÄNNER", "januar": "JÄNNER", "februar": "FEBRUAR", "märz": "MÄRZ",
    "april": "APRIL", "mai": "MAI", "juni": "JUNI", "juli": "JULI",
    "august": "AUGUST", "september": "SEPTEMBER", "oktober": "OKTOBER",
    "november": "NOVEMBER", "dezember": "DEZEMBER",
}

# Die mdw formuliert in drei Varianten. Alle drei nennen Monat, Person, Fach
# und Institut, zwei davon zusätzlich das Geschlecht über Pronomen oder Titel.
DATUM = (r"(?:Mit|Ab|Seit)\s+\d{1,2}\.?\s*(?P<monat>Jänner|Januar|Februar|März|April|Mai|"
         r"Juni|Juli|August|September|Oktober|November|Dezember)\s*(?P<jahr>\d{4})?\s+")
ORT = r"(?:am|an der|an dem|an|beim|bei der|in der)\s+(?P<institut>[^.]{3,120}?)"

MUSTER = [
    # … trat/tritt <Name> seine/ihre Professur für <Fach> am <Institut> an.
    re.compile(DATUM + r"(?:trat|tritt)\s+(?P<vorlauf>.{0,200}?)\s+(?P<pronomen>seine|ihre)\s+"
               r"(?:neue\s+|befristete\s+)*Professur\s+(?:für|in|im|der)?\s*"
               r"(?P<fach>.+?)\s+" + ORT + r"\s+an\.", re.S),
    # … wurde <Name> zur Professorin für <Fach> am <Institut> berufen.
    re.compile(DATUM + r"wurde\s+(?P<vorlauf>.{0,200}?)\s+(?:auf\s+[^.]{0,30}?\s+)?"
               r"zu(?:r|m)\s+(?P<titel>Professorin|Professor)\s+(?:für|in)\s+"
               r"(?P<fach>.+?)\s+" + ORT + r"\s+berufen\.", re.S),
    # … kam <Name> als Universitätsprofessor für <Fach> am <Institut> an die mdw.
    re.compile(DATUM + r"kam\s+(?P<vorlauf>.{0,200}?)\s+als\s+"
               r"(?:Universitäts)?(?P<titel>Professorin|Professor)\s+(?:für|in)\s+"
               r"(?P<fach>.+?)\s+" + ORT + r"\s+an\s+die\s+mdw", re.S),
    # Ältere Jahresseiten sind Porträttexte mit anderer Satzstellung:
    # "<Name> erhielt im Oktober 2014 eine unbefristete Professur für <Fach> am <Institut>."
    re.compile(r"(?P<vorlauf>[^.]{5,200}?)\s+erhielt\s+(?:im|mit)\s+(?P<monat>Jänner|Januar|"
               r"Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|"
               r"Dezember)\s*(?P<jahr>\d{4})?\s+(?:eine|die)\s+(?:unbefristete\s+|befristete\s+)?"
               r"Professur\s+(?:für|in)\s+(?P<fach>.+?)\s+" + ORT + r"\.", re.S),
    # "<Name> tritt mit 1. Oktober am <Institut> seine Professur für <Fach> an der mdw an."
    re.compile(r"(?P<vorlauf>[^.]{5,200}?)\s+(?:tritt|trat)\s+mit\s+\d{1,2}\.?\s*(?P<monat>Jänner|"
               r"Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|"
               r"Dezember)\s*(?P<jahr>\d{4})?\s+" + ORT + r"\s+(?P<pronomen>seine|ihre)\s+"
               r"Professur\s+(?:für|in)\s+(?P<fach>.+?)\s+an\s+der\s+mdw\s+an\.", re.S),
]

# Verbindungswörter, die zu einem Namen gehören dürfen
NAMENSFUELLER = {"von", "van", "de", "del", "della", "di", "da", "dos", "el", "al",
                 "zu", "te", "ter", "op", "van't"}


def name_aus(vorlauf):
    """Letzte Großbuchstaben-Folge im Vorlauf ist der Name.

    Die mdw stellt gern Beschreibungen davor ("die in den USA geborene und in
    Finnland aufgewachsene Elina Vähälä", "der russisch-israelische Pianist
    Roman Zaslavsky").
    """
    tokens = [t for t in re.split(r"\s+", vorlauf.strip()) if t]
    teile = []
    for tok in reversed(tokens):
        sauber = tok.strip(",;")
        if not sauber:
            break
        if sauber[0].isupper() or (teile and sauber.lower() in NAMENSFUELLER):
            teile.insert(0, sauber)
            if len(teile) == 4:
                break
        elif teile:
            break
    # Beschreibende Großschreibung am Anfang abschneiden (Pianist, USA, Institut)
    while len(teile) > 2 and teile[0].lower() in {
        "pianist", "pianistin", "geiger", "geigerin", "sängerin", "sänger",
        "usa", "professor", "professorin", "dirigent", "dirigentin", "komponist",
        "komponistin", "schauspieler", "schauspielerin",
    }:
        teile.pop(0)
    # Auf den Porträtseiten steht der Name als Überschrift direkt vor dem Satz.
    # Dadurch taucht er doppelt auf ("Peter Hrncirik Peter Hrncirik"), teils
    # unvollständig abgeschnitten ("Hrncirik Peter Hrncirik").
    klein = [t.lower() for t in teile]
    for laenge in (3, 2):
        if len(teile) > laenge and klein[-laenge:] == klein[-2 * laenge: -laenge]:
            teile = teile[-laenge:]
            break
    else:
        if len(teile) > 2 and klein[0] == klein[-1]:
            teile = teile[1:]
    return " ".join(teile[-3:]) if len(teile) > 3 else " ".join(teile)


def hole(url):
    CACHE.mkdir(exist_ok=True)
    datei = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url).strip("_")[:120] + ".html")
    if datei.exists():
        return datei.read_text(encoding="utf-8")
    if "--offline" in sys.argv:
        raise SystemExit(f"--offline, aber nicht im Cache: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        html = r.read().decode("utf-8", errors="replace")
    datei.write_text(html, encoding="utf-8")
    time.sleep(0.5)
    return html


def text(seite):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", seite, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)                    # deckt á, š, ç, ndash … ab
    t = re.sub(r"\s+", " ", t)
    # "Mit 1. Oktober" → "Mit 1 Oktober": der Ordinalpunkt zählt sonst als
    # Satzende und zerschneidet die Muster mitten im Datum.
    return re.sub(r"(\d{1,2})\.\s*(?=(?:Jänner|Januar|Februar|März|April|Mai|Juni|Juli|"
                  r"August|September|Oktober|November|Dezember))", r"\1 ", t)


def parse_jahr(jahr, url):
    inhalt = text(hole(url))
    treffer, gesehen = [], set()
    for muster in MUSTER:
        for m in muster.finditer(inhalt):
            felder = m.groupdict()
            name = name_aus(felder["vorlauf"])
            if len(name.split()) < 2 or len(name) > 45:
                continue
            if name.lower() in gesehen:
                continue
            gesehen.add(name.lower())
            if felder.get("pronomen"):
                geschlecht = "M" if felder["pronomen"] == "seine" else "W"
            else:
                geschlecht = "W" if felder.get("titel") == "Professorin" else "M"
            treffer.append({
                "name": name,
                "universitat": "mdw",
                "monat": MONATE[felder["monat"].lower()],
                "year": int(felder["jahr"]) if felder.get("jahr") else jahr,
                "art_berufung": "§98",
                "forschungsbereich": re.sub(r"\s+", " ", felder["fach"]).strip(" ,;") or None,
                "fakultat": re.sub(r"\s+", " ", felder["institut"]).strip(" ,;") or None,
                "geschlecht": geschlecht,
                "profil_url": None,
                "quelle": url,
                "stufe": 1,
            })
    return treffer


def main():
    alle = []
    for jahr in sorted(SEITEN):
        gefunden = parse_jahr(jahr, SEITEN[jahr])
        print(f"   {jahr}: {len(gefunden)}")
        alle.extend(gefunden)

    gesehen, eindeutig = set(), []
    for e in alle:
        s = (e["name"].lower(), e["year"])
        if s in gesehen:
            continue
        gesehen.add(s)
        eindeutig.append(e)

    OUT_DIR.mkdir(exist_ok=True)
    ziel = OUT_DIR / "mdw.json"
    ziel.write_text(json.dumps(eindeutig, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(eindeutig)} Berufungen mdw → {ziel.relative_to(ROOT)}")
    print("   ohne Quelle und daher offen: 2015, 2016, 2018")
    return eindeutig


if __name__ == "__main__":
    daten = main()
    assert len(daten) > 60, f"nur {len(daten)} Einträge"
    assert all(d["name"] and d["forschungsbereich"] for d in daten)
    assert all(d["geschlecht"] in ("W", "M") for d in daten)
    haffner = [d for d in daten if d["name"] == "Eszter Haffner"]
    assert haffner and haffner[0]["year"] == 2023 and haffner[0]["geschlecht"] == "W", haffner
    assert haffner[0]["forschungsbereich"] == "Violine", haffner[0]["forschungsbereich"]
    print("✓ Selbstcheck ok")
