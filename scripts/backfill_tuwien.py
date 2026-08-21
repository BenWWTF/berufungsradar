#!/usr/bin/env python3
"""
Backfill Stufe 1 für die TU Wien.

Quelle: die TU Wien pflegt eine Übersichtsseite "Neue Professor_innen seit 2019"
als Akkordeon je Jahr, darin Monatsüberschriften mit je einem Absatz pro Person:

    <h4>JUNE 2026</h4>
    <p><a href="…"><strong>Univ.Prof. … Teresa Weber, MSc</strong></a>,
       University Professor of Public Law (E280)</p>

Geliefert werden nur die Stufe-1-Felder: Name, Universität, Monat, Jahr, Art der
Berufung, Forschungsbereich, Institutscode, Profil-Link. ÖFOS, Geschlecht und
Metriken macht danach die bestehende Pipeline (enrich.py, wwtf_enrich.py).

Schreibt scripts/backfill/tuwien.json. Der Merge in die Hauptdatei ist ein
eigener Schritt (merge_backfill.py), damit man die Rohernte prüfen kann.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent / "backfill"
CACHE = Path(__file__).resolve().parent / ".backfill_cache"

URL = ("https://www.tuwien.at/en/tu-wien/organisation/central-divisions/"
       "professorships-at-tu-wien/new-professors-since-2019")
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

MONATE = {
    "JANUARY": "JÄNNER", "JANUAR": "JÄNNER", "FEBRUARY": "FEBRUAR", "FEBRUAR": "FEBRUAR",
    "MARCH": "MÄRZ", "MÄRZ": "MÄRZ", "APRIL": "APRIL", "MAY": "MAI", "MAI": "MAI",
    "JUNE": "JUNI", "JUNI": "JUNI", "JULY": "JULI", "JULI": "JULI",
    "AUGUST": "AUGUST", "SEPTEMBER": "SEPTEMBER", "OCTOBER": "OKTOBER", "OKTOBER": "OKTOBER",
    "NOVEMBER": "NOVEMBER", "DECEMBER": "DEZEMBER", "DEZEMBER": "DEZEMBER",
}

# Namensbestandteile enthalten keine Punkte, akademische Grade fast immer
# ("Dipl.-Ing.", "Dr.rer.soc.oec.", "phil."). Punkt-Token fliegen deshalb raus,
# die punktlosen Grade stehen als Liste daneben.
GRADE_OHNE_PUNKT = {
    "univ", "prof", "profin", "dr", "drin", "mag", "maga", "dipl", "ing", "di",
    "msc", "ma", "bsc", "ba", "phd", "mba", "doz", "habil", "techn", "mont",
    "phil", "iur", "med", "nat", "rer", "soc", "oec", "scient", "sc", "associate",
    "assoc", "assistant", "ass", "professor", "professorin", "emeritus", "bakk",
    "llm", "mres", "meng", "dphil", "mphil", "dsc", "msci",
    # fremdsprachige Grade und Schreibvarianten
    "docteur", "diplom", "diplomingenieur", "dott", "dottore", "ir", "drs",
    "statistiker", "chem", "biol", "phys", "math", "inform", "wirt",
}


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
    return html


def entschluessle(t):
    for a, b in {
        "&nbsp;": " ", "&amp;": "&", "&auml;": "ä", "&ouml;": "ö", "&uuml;": "ü",
        "&Auml;": "Ä", "&Ouml;": "Ö", "&Uuml;": "Ü", "&szlig;": "ß", "&ndash;": "–",
        "&#8211;": "–", "&rsquo;": "’", "&quot;": '"', "&#039;": "'", "&eacute;": "é",
        "&egrave;": "è", "&iacute;": "í", "&oacute;": "ó", "&ccedil;": "ç",
    }.items():
        t = t.replace(a, b)
    return t


def sauber(t):
    return re.sub(r"\s+", " ", entschluessle(re.sub(r"<[^>]+>", " ", t))).strip()


def namensform(roh):
    """'Univ.Prof. Dipl.-Ing. Dr.rer.nat. Siegfried KRAINER' → 'Siegfried Krainer'."""
    teile = []
    for wort in re.split(r"[\s,;]+", roh):
        wort = wort.strip("-–()")
        if not wort or "." in wort:
            continue                                    # Grad, kein Name
        if wort.lower().strip("-") in GRADE_OHNE_PUNKT:
            continue
        if wort.isupper() and len(wort) > 1:
            # Nachnamen stehen in Großbuchstaben, Bindestriche beibehalten
            wort = "-".join(w.capitalize() for w in wort.split("-"))
        teile.append(wort)
    return " ".join(teile).strip()


def art_der_berufung(roh, titel):
    text = f"{roh} {titel}".lower()
    if "associate" in text or "assoc." in text:
        return "§99(4)"
    if "assistant" in text or "ass.prof" in text:
        return "§99(1)"
    return "§98"


def parse():
    html = hole(URL)
    # Nur der Inhaltsbereich, sonst fängt man Navigationslinks
    start = html.find('class="col-xl-8 main-content"')
    ende = html.find('class="col-xl-3', start + 10)
    inhalt = html[start: ende if ende > start else len(html)]
    # Am Ende der Seite stehen die Abgänge ("Former Employees since 2019").
    # Die tragen nur eine Zeitspanne statt einer Professurbezeichnung und
    # gehören nicht in die Berufungen.
    abgang = re.search(r"Former Employees", inhalt, re.I)
    if abgang:
        inhalt = inhalt[: abgang.start()]

    eintraege = []
    monat = jahr = None
    # h4 = Monatsüberschrift, p = eine Berufung
    for tag, roh in re.findall(r"<(h4|p)\b[^>]*>(.*?)</\1>", inhalt, re.S | re.I):
        text = sauber(roh)
        if not text:
            continue
        if tag.lower() == "h4":
            m = re.match(r"([A-ZÄÖÜa-zäöü]+)\s*/?\s*([A-ZÄÖÜa-zäöü]*)\s*(\d{4})", text)
            if m:
                monat = MONATE.get(m.group(1).upper())
                jahr = int(m.group(3))
            continue
        if jahr is None or monat is None:
            continue
        # Name steht im ersten <strong>, danach folgt die Professurbezeichnung
        stark = re.findall(r"<strong>(.*?)</strong>", roh, re.S)
        name_roh = sauber(stark[0]) if stark else text.split(",")[0]
        if not name_roh or len(name_roh) < 4:
            continue
        rest = text
        if name_roh in text:
            rest = text.split(name_roh, 1)[1]
        titel = rest.strip(" ,;")
        # Institutscode steht in Klammern, nicht immer am Ende
        code = None
        m = re.search(r"\((E\d{3}(?:/E?\d{3})*)\)", titel)
        if m:
            code = m.group(1)
            titel = (titel[: m.start()] + " " + titel[m.end():]).strip(" ,;")
        # Zusätze wie "(permanently appointed, appointed since April 2016)" weg
        titel = re.sub(r"\([^)]*appointed[^)]*\)", "", titel, flags=re.I)
        titel = re.sub(r"\(\s*\d{1,2}\.\d{1,2}\.\d{4}[^)]*\)", "", titel)
        titel = re.sub(r"\s{2,}", " ", titel).strip(" ,;")
        if not titel or re.fullmatch(r"[\d.\s–-]*", titel):
            continue                      # keine Bezeichnung, nur Datumsangaben
        link = re.search(r'href="(/[^"]*new-professors[^"]*)"', roh)

        name = namensform(name_roh)
        if not name or " " not in name:
            continue
        eintraege.append({
            "name": name,
            "universitat": "TU Wien",
            "monat": monat,
            "year": jahr,
            "art_berufung": art_der_berufung(name_roh, titel),
            "forschungsbereich": titel or None,
            "fakultat_code": code,
            "profil_url": ("https://www.tuwien.at" + link.group(1)) if link else None,
            "quelle": URL,
            "stufe": 1,
        })
    return eintraege


def main():
    eintraege = parse()
    # Dubletten innerhalb der Quelle (eine Person kann mehrfach gelistet sein)
    gesehen, eindeutig = set(), []
    for e in eintraege:
        schluessel = (e["name"].lower(), e["year"])
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        eindeutig.append(e)

    OUT_DIR.mkdir(exist_ok=True)
    ziel = OUT_DIR / "tuwien.json"
    ziel.write_text(json.dumps(eindeutig, ensure_ascii=False, indent=1) + "\n")

    print(f"✓ {len(eindeutig)} Berufungen TU Wien → {ziel.relative_to(ROOT)}")
    jahre = {}
    for e in eindeutig:
        jahre[e["year"]] = jahre.get(e["year"], 0) + 1
    for j in sorted(jahre):
        print(f"   {j}: {jahre[j]}")
    return eindeutig


if __name__ == "__main__":
    daten = main()
    # Selbstcheck: Struktur und ein bekannter Datensatz
    assert len(daten) > 100, f"nur {len(daten)} Einträge, Parser greift nicht"
    assert all(d["name"] and d["monat"] and d["year"] for d in daten)
    assert all(d["monat"] in MONATE.values() for d in daten), \
        {d["monat"] for d in daten} - set(MONATE.values())
    assert {d["year"] for d in daten} <= set(range(2019, 2030))
    sallinger = [d for d in daten if d["name"] == "Emanuel Sallinger"]
    assert sallinger, "Sallinger fehlt, der ist Februar 2025 TU-Professor geworden"
    assert sallinger[0]["year"] == 2025 and sallinger[0]["monat"] == "FEBRUAR", sallinger[0]
    print("✓ Selbstcheck ok")
