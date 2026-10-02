#!/usr/bin/env python3
"""
Laufende Erfassung MedUni Wien über die News-Kategorie "Menschen der MedUni Wien".

Eine Übersichtsseite wie bei TU Wien gibt es nicht. Berufungen erscheinen aber
verlässlich als eigene Meldung in dieser Kategorie, mit festem Titelmuster:

    "Peter Marhofer übernimmt Professur für Kinderanästhesie"
    "Pedro Wendel Garcia übernimmt Tenure-Track-Assistenzprofessur an der MedUni Wien"

Der erste Satz der Meldung trägt Antritt und Paragraf:

    "(Wien, 01-10-2026) Peter Marhofer hat mit 1. Oktober 2026 eine Professur
     für Kinderanästhesie (§ 99 Abs. 1) an der Medizinischen Universität Wien
     übernommen."

Ausgeschlossen sind Berufstitel, Gast- und Ehrenprofessuren, die dasselbe
Wort im Titel tragen. Gelesen werden nur die ersten Seiten der Kategorie
(7 Meldungen je Seite); für die wöchentliche Suche reicht das, ältere
Jahrgänge sind über Wissensbilanzen und Handrecherche erfasst.

Schreibt scripts/backfill/meduni_live.json.
Aufruf: python3 scripts/backfill_meduni_live.py [--seiten N]   (Standard 3)
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "backfill" / "meduni_live.json"

BASIS = "https://www.meduniwien.ac.at"
SEITE_1 = BASIS + "/web/ueber-uns/news/menschen-der-meduni-wien/"
# Ab Seite 2 über die allgemeine News-Liste mit Kategorie-Filter. Der cHash
# gilt für alle Seiten, TYPO3 bindet ihn an die Filterparameter.
SEITE_N = (BASIS + "/web/ueber-uns/news/page-{n}/?tx_news_pi1%5BoverwriteDemand%5D"
           "%5Bcategories%5D=4&cHash=3efb3b828c80ce9c52b8fba223c5c730")
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

MONATE = {"jänner": "JÄNNER", "januar": "JÄNNER", "februar": "FEBRUAR",
          "märz": "MÄRZ", "april": "APRIL", "mai": "MAI", "juni": "JUNI",
          "juli": "JULI", "august": "AUGUST", "september": "SEPTEMBER",
          "oktober": "OKTOBER", "november": "NOVEMBER", "dezember": "DEZEMBER"}
REIHE = list(dict.fromkeys(MONATE.values()))

TITEL = re.compile(r"^(?P<name>[^,:]+?) (?:übernimmt|tritt|tritt an:?) (?:die |eine )?"
                   r"(?P<rest>.*?Professur.*)$", re.I)
KEINE_BERUFUNG = re.compile(r"gastprofessur|berufstitel|honorary|ehrenprofessur|visiting",
                            re.I)


def hole(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        text = r.read().decode("utf-8", errors="replace")
    time.sleep(1)
    return text


def text(seite):
    seite = re.sub(r"<(script|style)\b.*?</\1>", " ", seite, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", seite)))


def meldungen(seiten):
    gesehen = set()
    for n in range(1, seiten + 1):
        liste = hole(SEITE_1 if n == 1 else SEITE_N.format(n=n))
        for titel, pfad in re.findall(
                r'<h2 class="news-teaser__title"><a title="([^"]+)" href="([^"]+)"', liste):
            if pfad not in gesehen:
                gesehen.add(pfad)
                yield html.unescape(titel).strip(), BASIS + pfad


def paragraf(satz):
    m = re.search(r"§\s*(98|99)\b(?:\s*(?:Abs\.?|\(|-|/)\s*(\d))?", satz)
    if not m:
        return None
    return "§98" if m.group(1) == "98" else (f"§99({m.group(2)})" if m.group(2) else None)


def eintrag(titel, url):
    m = TITEL.match(titel)
    if not m or KEINE_BERUFUNG.search(titel):
        return None
    inhalt = text(hole(url))
    i = inhalt.find("(Wien, ")
    satz = inhalt[i: i + 600] if i >= 0 else ""
    antritt = re.search(r"mit (?:\d{1,2}\.\s*|Anfang\s+)?(" + "|".join(MONATE) + r")(?:\s+(\d{4}))?",
                        satz, re.I)
    datum = re.search(r"\(Wien, \d{2}-(\d{2})-(\d{4})\)", satz)
    if antritt and (antritt.group(2) or datum):
        # "mit Anfang August" ohne Jahr: das Jahr der Meldung
        monat = MONATE[antritt.group(1).lower()]
        jahr = int(antritt.group(2) or datum.group(2))
    elif datum:
        monat, jahr = REIHE[int(datum.group(1)) - 1], int(datum.group(2))
    else:
        return None
    fach = re.search(r"Professur (?:für|im Fachbereich) (.+?)(?: an der MedUni Wien)?$", m["rest"])
    return {
        "name": m["name"].strip(),
        "universitat": "MedUni Wien",
        "monat": monat,
        "year": jahr,
        "art_berufung": paragraf(satz),
        "forschungsbereich": fach.group(1).strip("„“\" ") if fach else None,
        "quelle": url,
        "stufe": 1,
    }


def main():
    seiten = int(sys.argv[sys.argv.index("--seiten") + 1]) if "--seiten" in sys.argv else 3
    liste = list(meldungen(seiten))
    daten = [e for e in (eintrag(t, u) for t, u in liste if "rofessur" in t) if e]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(daten)} Berufungen aus {len(liste)} Meldungen MedUni → {OUT.relative_to(ROOT)}")
    return liste, daten


if __name__ == "__main__":
    liste, daten = main()
    # Selbstcheck: die Kategorie-Seite muss Meldungen liefern, sonst hat sich
    # das Markup geändert. Berufungen selbst darf es in drei Seiten keine geben.
    assert len(liste) >= 7, f"nur {len(liste)} Meldungen gelesen, Markup geändert?"
    assert all(d["monat"] in MONATE.values() for d in daten)
    print("✓ Selbstcheck ok")
