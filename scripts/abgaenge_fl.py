#!/usr/bin/env python3
"""
Rufe aus und nach Wien laut Forschung & Lehre.

Forschung & Lehre (Deutscher Hochschulverband) veröffentlicht monatlich
"Habilitationen und Berufungen": je Eintrag ein Satz nach festem Muster,

    Prof. Dr. X, Universität Wien (Österreich), hat zum 1. März 2025 den Ruf
    auf die W3-Professur für Y an der Universität Z angenommen.

Erfasst werden Einträge, deren Herkunft eine Wiener Einrichtung ist
(Abgang, abgelehnter Ruf = Bleibeerfolg, erhaltener Ruf = Frühwarnung),
und zum Abgleich solche mit Wiener Ziel (Zugang). Die Rubrik deckt vor
allem Rufe an deutsche Universitäten ab; Österreich und die Schweiz nur,
soweit gemeldet.

Aufruf: python3 scripts/abgaenge_fl.py
Schreibt scripts/.abgaenge_cache/fl_wien.csv (nicht im Repo).
"""

import csv
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / ".abgaenge_cache" / "fl"
OUT = CACHE.parent / "fl_wien.csv"
BASIS = "https://www.forschung-und-lehre.de"
INDEX = BASIS + "/karriere/habilitationen-und-berufungen"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

MONATE = ["januar", "februar", "maerz", "april", "mai", "juni", "juli",
          "august", "september", "oktober", "november", "dezember"]

WIEN = re.compile(r"\bWien\b|\bVienna\b|Wirtschaftsuniversität|Veterinärmedizinische Universität"
                  r"|Universität für Bodenkultur|\bBOKU\b|Central European University|\bCEU\b")

# Zwei Wortstellungen: "den Ruf auf die Professur X an der Uni Y" und
# "einen Ruf an die Uni Y auf die Professur X"
EINTRAG = re.compile(
    r"^(?P<person>.+?),\s+(?P<herkunft>.+?),\s+hat\s+(?:zum\s+(?P<datum>[^,]+?)\s+)?"
    r"(?:den|einen)\s+Rufe?\s+(?:der\s+(?P<rufer>.+?)\s+)?auf\s+(?:die|eine|den)\s+(?P<stelle>.+?)"
    r"(?:\s+(?:an\s+der|an\s+die|an\s+das|am|an|in)\s+(?P<ziel>[^,]+?))?\s+"
    r"(?P<aktion>angenommen|abgelehnt|erhalten)(?P<rest>.*)$")
EINTRAG_AN = re.compile(
    r"^(?P<person>.+?),\s+(?P<herkunft>.+?),\s+hat\s+(?:zum\s+(?P<datum>[^,]+?)\s+)?"
    r"(?:den|einen)\s+Rufe?\s+an\s+(?:die|das|den)\s+(?P<ziel>.+?),?\s+auf\s+(?:die|eine|den)\s+"
    r"(?P<stelle>.+?)\s+(?P<aktion>angenommen|abgelehnt|erhalten)(?P<rest>.*)$")
TITEL = re.compile(r"^(?:(?:Prof\.|Dr\.|PD|Jun\.-Prof\.|apl\.|Dipl\.-\w+\.?|h\.\s?c\.|mult\.|med\.|"
                   r"phil\.|rer\.\s?nat\.|habil\.|Ass\.-Prof\.|Assoc\.|Univ\.-Prof\.|Priv\.-Doz\.|"
                   r"M\.\w+\.?|Ph\.?D\.?)\s*)+")


def lade(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def hole(url, cache=True):
    """Direkt, sonst die jüngste Kopie im Webarchiv: F&L sperrt Serienabrufe zeitweise."""
    datei = CACHE / (url.rstrip("/").rsplit("/", 1)[-1] + ".html")
    if cache and datei.exists():
        return datei.read_text(encoding="utf-8")
    for versuch in range(1, 6):
        try:
            text = lade(url)
            break
        except OSError as e:
            # F&L verweigert nach einigen Abrufen zeitweise die Verbindung
            print(f"  ! {e}, warte {60 * versuch}s", file=sys.stderr)
            time.sleep(60 * versuch)
    else:
        text = lade(f"https://web.archive.org/web/2030id_/{url}")
    if cache:
        CACHE.mkdir(parents=True, exist_ok=True)
        datei.write_text(text, encoding="utf-8")
    time.sleep(10)
    return text


def zeilen(seite):
    seite = re.sub(r"<(script|style)\b.*?</\1>", "", seite, flags=re.S)
    seite = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", seite)
    text = html.unescape(re.sub(r"<[^>]+>", "", seite))
    return [re.sub(r"\s+", " ", z).strip() for z in text.splitlines() if "Ruf" in z]


def main():
    index = hole(INDEX, cache=False)
    seiten = sorted(set(re.findall(r'href="(/karriere/habilitationen-und-berufungen/'
                                   r'habilitationen-und-berufungen-[a-z]+-\d{4}-\d+)"', index)))
    treffer, gesamt, ungeparst = [], 0, 0
    for pfad in seiten:
        m = re.search(r"-([a-z]+)-(\d{4})-\d+$", pfad)
        heft_monat = MONATE.index(m.group(1)) + 1 if m.group(1) in MONATE else None
        heft_jahr = int(m.group(2))
        if heft_jahr < 2019:
            continue
        for z in zeilen(hole(BASIS + pfad)):
            gesamt += 1
            e = EINTRAG.match(z) or EINTRAG_AN.match(z)
            if not e:
                if WIEN.search(z):
                    ungeparst += 1
                    treffer.append({"richtung": "ungeparst", "heft": f"{heft_jahr}-{heft_monat:02d}",
                                    "satz": z, "quelle": BASIS + pfad})
                continue
            von_wien = bool(WIEN.search(e["herkunft"]))
            nach_wien = bool(e["ziel"] and WIEN.search(e["ziel"])) or bool(e.groupdict().get("rufer") and WIEN.search(e["rufer"]))
            if not (von_wien or nach_wien):
                continue
            if von_wien and not nach_wien:
                richtung = {"angenommen": "Abgang", "abgelehnt": "Bleibeerfolg",
                            "erhalten": "Ruf erhalten"}[e["aktion"]]
            elif nach_wien and not von_wien:
                richtung = {"angenommen": "Zugang", "abgelehnt": "Zugang abgelehnt",
                            "erhalten": "Ruf nach Wien"}[e["aktion"]]
            else:
                richtung = "innerhalb Wien"
            treffer.append({
                "richtung": richtung, "heft": f"{heft_jahr}-{heft_monat:02d}",
                "name": TITEL.sub("", e["person"]).strip(), "herkunft": e["herkunft"],
                "stelle": e["stelle"], "ziel": e["ziel"] or e.groupdict().get("rufer") or "",
                "datum": e["datum"] or "", "satz": z, "quelle": BASIS + pfad,
            })
    felder = ["richtung", "heft", "name", "herkunft", "stelle", "ziel", "datum", "satz", "quelle"]
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=felder, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(treffer, key=lambda t: (t["richtung"], t["heft"])))
    zaehl = {}
    for t in treffer:
        zaehl[t["richtung"]] = zaehl.get(t["richtung"], 0) + 1
    print(f"{len(seiten)} Hefte, {gesamt} Ruf-Einträge ab 2019, {len(treffer)} mit Wien-Bezug:")
    for r, n in sorted(zaehl.items(), key=lambda t: -t[1]):
        print(f"  {r:18} {n}")
    print(f"✓ {OUT.relative_to(ROOT)}")
    return treffer


if __name__ == "__main__":
    main()
