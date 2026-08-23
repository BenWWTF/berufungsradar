#!/usr/bin/env python3
"""
Backfill für die Universität Wien über das Webarchiv.

Warum das Archiv: die heutige Seite lädt ihre Inhalte per JavaScript, im HTML
steht kein einziger Name. Das Mitteilungsblatt verlautbart nur Verfahren
(Berufungskommissionen), nicht die Berufung selbst. Im Webarchiv liegen dagegen
die CV-Seiten des früheren Medienportals, je eine pro berufener Person:

    Univ.-Prof. Bernhard Lamel, PhD
    Professur für Komplexe Analysis an der Fakultät für Mathematik
    Lebenslauf:
    …
    seit September 2017 Professur für Komplexe Analysis an der Fakultät …

Daraus fallen Name, Denomination, Fakultät, Berufungsmonat und der Lebenslauf
an — für die Uni Wien also Stufe 1 und 2 plus Werdegang in einem Zug.

Unvollständig: archiviert ist, was der Crawler erwischt hat. Die Abdeckung ist
in datenabdeckung.json entsprechend als "teilweise" geführt.

Aufruf: python3 scripts/backfill_univie.py [--limit N] [--offline]
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
CACHE = Path(__file__).resolve().parent / ".univie_cache"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

CDX = ("http://web.archive.org/cdx/search/cdx?url=medienportal.univie.ac.at/uniview/"
       "professuren/*&collapse=urlkey&fl=original,timestamp&limit=3000&output=json")

AB_JAHR = 2019          # Auswertungszeitraum beginnt 2019, siehe datenabdeckung.json

MONATE = {
    "jänner": "JÄNNER", "januar": "JÄNNER", "februar": "FEBRUAR", "märz": "MÄRZ",
    "april": "APRIL", "mai": "MAI", "juni": "JUNI", "juli": "JULI",
    "august": "AUGUST", "september": "SEPTEMBER", "oktober": "OKTOBER",
    "november": "NOVEMBER", "dezember": "DEZEMBER",
}

# Die Berufung steht im Lebenslauf, in mehreren Formulierungen:
#   "seit September 2017 Professur für Komplexe Analysis an der …"
#   "seit Juni 2019 Assoziierte Professur am Department für …"
#   "2019 Universitätsprofessur für …"
SEIT = re.compile(
    r"(?:seit\s+)?(?P<monat>Jänner|Januar|Februar|März|April|Mai|Juni|Juli|August|"
    r"September|Oktober|November|Dezember)?\s*(?P<jahr>20\d\d)\s*"
    r"(?:[–-]\s*(?:heute|laufend)\s*)?"
    r"(?P<art>[Aa]ssoziierte\s+Professur|Universitätsprofessur|Professur)", re.I)

# Kopfzeile der Denomination, mit und ohne "für"
DENOM = re.compile(
    r"^(?:Assoziierte\s+)?(?:Universitäts)?Professur"
    r"(?:\s+(?:für|in)\s+(?P<fach>[^,\n]{3,90}?))?"
    r"(?:\s+(?:an\s+der|an\s+dem|am|an)\s+(?P<fakultat>[^,\n]{3,90}?))?\s*$", re.I)


def hole(url, datei):
    CACHE.mkdir(exist_ok=True)
    ziel = CACHE / datei
    if ziel.exists():
        return ziel.read_text(encoding="utf-8")
    if "--offline" in sys.argv:
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                inhalt = r.read().decode("utf-8", errors="replace")
            ziel.write_text(inhalt, encoding="utf-8")
            time.sleep(1.0)                      # das Archiv ist geduldig zu behandeln
            return inhalt
        except Exception as e:
            if versuch == 2:
                print(f"  ! {type(e).__name__} bei {url[:80]}")
                return ""
            time.sleep(4)
    return ""


def zeilen(seite):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", seite, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [z.strip() for z in t.split("\n") if len(z.strip()) > 2]


def parse_person(seite, quelle):
    zs = zeilen(seite)
    # Der Kopf steht doppelt (Titel-Tag und Überschrift); die Überschrift ist die
    # letzte Zeile, die vor der Denomination steht.
    idx_denom = next((i for i, z in enumerate(zs) if DENOM.match(z)), None)
    if idx_denom is None:
        return None
    kopf = None
    for z in reversed(zs[:idx_denom]):
        if re.search(r"Prof|Dr|Mag|PhD", z) and len(z) < 90:
            kopf = z
            break
    if not kopf:
        return None
    name = namensform(kopf)
    if not plausibel(name):
        return None

    m = DENOM.match(zs[idx_denom])
    fach = (m.group("fach") or "").strip() if m else ""
    fakultat = (m.group("fakultat") or "").strip() if m else ""
    if not fach:
        # "Assoziierte Professur am Department für Pharmakognosie" — dann ist
        # die Einrichtung die einzige Sachangabe, die die Quelle hergibt.
        fach = fakultat or None

    # Berufungsdatum: das späteste "seit <Monat> <Jahr> Professur" im Lebenslauf
    monat = jahr = None
    for z in zs[idx_denom:]:
        for t in SEIT.finditer(z):
            j = int(t.group("jahr"))
            if jahr is None or j >= jahr:
                jahr = j
                monat = MONATE.get((t.group("monat") or "").lower()) or monat
    if not jahr:
        return None

    assoziiert = bool(re.search(r"assoz", kopf, re.I)) or bool(
        re.search(r"assoziierte\s+professur", zs[idx_denom], re.I))

    # Lebenslauf als Werdegang: die Zeilen mit Jahresangaben
    lebenslauf = [z for z in zs[idx_denom: idx_denom + 40]
                  if re.match(r"(?:seit\s+)?(?:19|20)\d\d", z)]

    return {
        "name": name,
        "universitat": "Uni Wien",
        "monat": monat or "OKTOBER",          # Uni Wien beruft überwiegend zum Semester
        "monat_unsicher": monat is None,
        "year": jahr,
        "art_berufung": "§99(4)" if assoziiert else "§98",
        "forschungsbereich": fach,
        "fakultat": fakultat or None,
        "werdegang": (" · ".join(lebenslauf[:12]) or None),
        "profil_url": quelle,
        "quelle": quelle,
        "stufe": 1,
    }


def main():
    liste = hole(CDX, "cdx.json")
    if not liste:
        raise SystemExit("CDX-Liste nicht verfügbar")
    eintraege = json.loads(liste)[1:]
    seiten = [(o, t) for o, t in eintraege if "/cv/artikel/" in o]
    print(f"{len(seiten)} archivierte CV-Seiten")

    if "--limit" in sys.argv:
        n = int(sys.argv[sys.argv.index("--limit") + 1])
        seiten = seiten[:n]
        print(f"auf {n} begrenzt")

    treffer, ohne = {}, 0
    for i, (orig, ts) in enumerate(seiten, 1):
        datei = re.sub(r"[^A-Za-z0-9]+", "_", orig.split("/artikel/")[-1])[:100] + ".html"
        seite = hole(f"http://web.archive.org/web/{ts}id_/{orig}", datei)
        if not seite:
            ohne += 1
            continue
        person = parse_person(seite, orig)
        if not person:
            ohne += 1
            continue
        if person["year"] < AB_JAHR:
            continue
        # Dieselbe Person kann mehrfach archiviert sein
        schluessel = person["name"].lower()
        vorher = treffer.get(schluessel)
        if not vorher or (person["year"], not person["monat_unsicher"]) > (vorher["year"], not vorher["monat_unsicher"]):
            treffer[schluessel] = person
        if i % 40 == 0:
            print(f"   {i}/{len(seiten)} geprüft, {len(treffer)} Personen")

    daten = sorted(treffer.values(), key=lambda d: (d["year"], d["name"]))
    OUT_DIR.mkdir(exist_ok=True)
    ziel = OUT_DIR / "univie.json"
    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")

    jahre = {}
    for d in daten:
        jahre[d["year"]] = jahre.get(d["year"], 0) + 1
    print(f"✓ {len(daten)} Berufungen Uni Wien ab {AB_JAHR} → {ziel.relative_to(ROOT)}"
          f" | {ohne} Seiten ohne verwertbaren Inhalt")
    for j in sorted(jahre):
        print(f"   {j}: {jahre[j]}")
    return daten


if __name__ == "__main__":
    daten = main()
    assert daten, "keine Berufungen gefunden"
    assert all(d["name"] and d["year"] >= AB_JAHR for d in daten)
    assert all(d["monat"] in MONATE.values() for d in daten)
    unsicher = sum(1 for d in daten if d["monat_unsicher"])
    print(f"✓ Selbstcheck ok ({unsicher} Einträge ohne Monatsangabe, auf Oktober gesetzt)")
