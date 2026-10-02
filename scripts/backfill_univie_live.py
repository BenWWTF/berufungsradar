#!/usr/bin/env python3
"""
Laufende Erfassung Uni Wien über die Seite "Neue Professuren".

Quelle: univie.ac.at/aktuelles/neue-professuren. Die Seite liefert die
aktuellen Jahrgänge als Karten im statischen HTML (anders als die übrigen
Uni-Wien-Seiten, die per JavaScript nachladen):

    <article class="… tag_103">            (tag_103 Tenure Track, tag_59 Professur)
      <a href="/aktuelles/neue-professuren/detail/buechter-theresa">
      <span itemprop="headline">Büchter, Theresa</span>
      <time datetime="2026-09-15">           (Veröffentlichung, nicht Dienstantritt)
      <span class="ml-4 font-semibold">Tenure Track-Professur</span>

Ältere Jahre stehen darunter als Akkordeon nur mit Namen und Widmung, die sind
über die Leistungsberichte erfasst und
werden hier übergangen.

Jede Detailseite bringt Widmung, Fakultät und Lebenslauf. Der Dienstantritt
steht im Lebenslauf ("seit September 2026 … Universität Wien"), nur wenn der
fehlt, gilt das Veröffentlichungsdatum. Der Lebenslauf geht als werdegang mit,
im Format, das herkunft_aus_cv.py erwartet (Stationen mit " · " getrennt).

Detailseiten werden gecacht, die Übersicht nie: sie ist das, was sich ändert.

Schreibt scripts/backfill/univie_live.json.
"""

import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "backfill" / "univie_live.json"
CACHE = Path(__file__).resolve().parent / ".univie_live_cache"

URL = "https://www.univie.ac.at/aktuelles/neue-professuren"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

MONATE = ["JÄNNER", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI", "JULI",
          "AUGUST", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"]
MONAT_TEXT = {"januar": 0, "jänner": 0, "februar": 1, "märz": 2, "april": 3,
              "mai": 4, "juni": 5, "juli": 6, "august": 7, "september": 8,
              "oktober": 9, "november": 10, "dezember": 11}


def hole(url, cache=True):
    datei = CACHE / (url.rsplit("/", 1)[-1] + ".html")
    if cache and datei.exists():
        return datei.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        text = r.read().decode("utf-8", errors="replace")
    if cache:
        CACHE.mkdir(exist_ok=True)
        datei.write_text(text, encoding="utf-8")
        time.sleep(1)
    return text


def zeilen(fragment):
    fragment = re.sub(r"<(script|style|svg)\b.*?</\1>", "", fragment, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", fragment))
    return [re.sub(r"\s+", " ", z).strip() for z in text.splitlines() if z.strip()]


def karten(seite):
    for art in re.findall(r"<article\b.*?</article>", seite, re.S):
        link = re.search(r'href="(/aktuelles/neue-professuren/detail/[^"]+)"', art)
        kopf = re.search(r'itemprop="headline">([^<]+)<', art)
        datum = re.search(r'datetime="(\d{4})-(\d{2})-\d{2}"', art)
        typ = re.search(r'font-semibold">([^<]+)<', art)
        if link and kopf and datum:
            yield {
                "url": "https://www.univie.ac.at" + link.group(1),
                "kopf": html.unescape(kopf.group(1)).strip(),
                "jahr": int(datum.group(1)),
                "monat": MONATE[int(datum.group(2)) - 1],
                "typ": typ.group(1).strip() if typ else "",
            }


def detail(url):
    seite = hole(url)
    # Die Beschreibung bricht mitunter über zwei <p> um, deshalb als ein Text
    m = re.search(r'itemprop="description"[^>]*>(.*?)</div>', seite, re.S)
    beschreibung = " ".join(zeilen(m.group(1))) if m else ""
    z = zeilen(seite)
    cv = []
    if "Lebenslauf" in z:
        for x in z[z.index("Lebenslauf") + 1:]:
            if x == "Kontakt":
                break
            cv.append(x)
    return beschreibung, cv


def antritt(cv):
    """'seit September 2026 … Universität Wien' → ('SEPTEMBER', 2026)."""
    for x in reversed(cv):
        m = re.match(r"(?:seit|ab)\s+(?:\d{1,2}\.\s*)?([A-Za-zÄäöü]+)\s+(\d{4})", x, re.I)
        if m and m.group(1).lower() in MONAT_TEXT and re.search(r"Universität Wien|University of Vienna", x):
            return MONATE[MONAT_TEXT[m.group(1).lower()]], int(m.group(2))
    return None


def eintrag(k):
    nachname, _, vorname = k["kopf"].partition(",")
    beschreibung, cv = detail(k["url"])
    # "… für X, Fakultät für Y" oder "… für X an der Rechtswissenschaftlichen
    # Fakultät"; der Dativ wird zum Nominativ, wie im Bestand
    m = re.search(r"(?:,\s*|\s+an der\s+|\s+am\s+)(\S*\s?(?:Fakultät|Zentrum)\b.*)$", beschreibung)
    widmung = beschreibung[: m.start()] if m else beschreibung
    fakultaet = re.sub(r"(\w)en Fakultät", r"\1e Fakultät", m.group(1)) if m else ""
    fakultaet = fakultaet.replace(" und der Fakultät", "; Fakultät")
    monat, jahr = antritt(cv) or (k["monat"], k["jahr"])
    tt = "Tenure" in k["typ"]
    return {
        "name": f"{vorname.strip()} {nachname.strip()}",
        "universitat": "Uni Wien",
        "monat": monat,
        "year": jahr,
        # Tenure Track = §99(1) wie in den Leistungsberichten; bei Professuren
        # trennt die Seite §98 nicht von §99(4), der Paragraf bleibt offen
        "art_berufung": "§99(1)" if tt else None,
        "stellentyp": "Tenure Track-Professur" if tt else "Universitätsprofessur",
        "fakultat": fakultaet or None,
        "forschungsbereich": re.sub(r"^(Tenure[ -]Track-)?Professur(\s+für)?\s*", "", widmung).strip() or None,
        "werdegang": " · ".join(cv) or None,
        "quelle": k["url"],
        "stufe": 1,
    }


def main():
    seite = hole(URL, cache=False)
    liste = list(karten(seite))
    daten = [eintrag(k) for k in liste]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(daten)} Karten Uni Wien → {OUT.relative_to(ROOT)}")
    return daten


if __name__ == "__main__":
    daten = main()
    # Selbstcheck: greift der Parser noch? Die Seite führt laufend 20+ Karten.
    assert len(daten) >= 20, f"nur {len(daten)} Karten, Seitenaufbau geändert?"
    assert all(d["name"].count(" ") >= 1 and d["monat"] in MONATE for d in daten)
    ohne = [d["name"] for d in daten if not (d["forschungsbereich"] or d["fakultat"])]
    if len(ohne) > len(daten) // 4:
        sys.exit(f"Widmung und Fakultät fehlen bei {len(ohne)} von {len(daten)}, Detailseiten geändert?")
    b = next((d for d in daten if d["name"] == "Theresa Büchter"), None)
    assert b is None or (b["monat"], b["year"]) == ("SEPTEMBER", 2026), b
    print("✓ Selbstcheck ok")
