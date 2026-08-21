#!/usr/bin/env python3
"""
Holt die Vienna Research Groups (VRG) von wwtf.at und schreibt sie nach
vrg_grantees.json.

Die Programmseite verlinkt jede geförderte Gruppe mit ihrer kanonischen ID
(VRG10-001 … VRG25-019). Diese Liste ist die Quelle, es wird nichts geraten.
Pro Projektseite werden Leader, Institution, Call, Laufzeit, Fördersumme und
Disziplinen ausgelesen.

Läuft selten (ein Call pro Jahr), gehört nicht in update.sh.
Aufruf: python3 scripts/fetch_vrg.py [--offline]
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "vrg_grantees.json"
CACHE = Path(__file__).resolve().parent / ".vrg_cache"

PROGRAMM_URL = "https://wwtf.at/funding/programmes/vrg/"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

# WWTF-Schreibweisen sind uneinheitlich und lang, deshalb Teilstring-Regeln.
# Reihenfolge zählt: die spezifischere Regel steht zuerst.
INSTITUTION_REGELN = [
    ("medical university of vienna", "MedUni Wien"),
    ("medizinische universität", "MedUni Wien"),
    ("natural resources", "BOKU"),
    ("bodenkultur", "BOKU"),
    ("economics and business", "WU Wien"),
    ("wirtschaftsuniversität", "WU Wien"),
    ("wu -", "WU Wien"),
    ("veterinär", "Vetmeduni Wien"),
    ("technische universität wien", "TU Wien"),
    ("tu wien", "TU Wien"),
    ("university of vienna", "Uni Wien"),
    ("universität wien", "Uni Wien"),
    ("uni wien", "Uni Wien"),
    ("cemm", "CeMM"),
    ("molekulare pathologie", "IMP"),
    ("gregor mendel", "GMI"),
    ("institute of science and technology", "ISTA"),
]


# Die Projektseiten der jüngsten Calls tragen noch keinen Call-Kopf mit Thema.
# Eine Zeile pro Call, gepflegt nach der Programmseite wwtf.at/funding/programmes/vrg/
CALL_THEMEN = {
    2025: "Artificial Intelligence and Machine Learning",
    2026: "Environmental Systems Research",
}


def kurzname(institution):
    """Lange WWTF-Bezeichnung → Kurzname wie im Dashboard (UNIS)."""
    if not institution:
        return None
    lower = institution.lower()
    for muster, kurz in INSTITUTION_REGELN:
        if muster in lower:
            return kurz
    return institution


def hole(url):
    """Seite laden, mit Plattencache — die Projektseiten ändern sich nie."""
    CACHE.mkdir(exist_ok=True)
    datei = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url).strip("_") + ".html")
    if datei.exists():
        return datei.read_text(encoding="utf-8")
    if "--offline" in sys.argv:
        raise SystemExit(f"--offline, aber nicht im Cache: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    datei.write_text(html, encoding="utf-8")
    time.sleep(0.5)  # höflich bleiben
    return html


def zeilen(html):
    """HTML → Liste sichtbarer Textzeilen (Labels und Werte stehen getrennt)."""
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    ersetzungen = {
        "&nbsp;": " ", "&ndash;": "–", "&auml;": "ä", "&ouml;": "ö", "&uuml;": "ü",
        "&Auml;": "Ä", "&Ouml;": "Ö", "&Uuml;": "Ü", "&szlig;": "ß", "&euro;": "€",
        "&amp;": "&", "&bdquo;": "„", "&ldquo;": "“", "&quot;": '"', "&#039;": "'",
        "&rsquo;": "’", "&eacute;": "é", "&egrave;": "è", "&iacute;": "í",
    }
    for a, b in ersetzungen.items():
        txt = txt.replace(a, b)
    return [z.strip() for z in txt.split("\n") if z.strip()]


def wert_nach(zs, label, ab=0):
    """Wert, der direkt hinter einem Label steht."""
    for i in range(ab, len(zs)):
        if zs[i].rstrip(":") == label.rstrip(":"):
            return (zs[i + 1] if i + 1 < len(zs) else None), i
    return None, -1


def parse_projekt(vrg_id, url):
    zs = zeilen(hole(url))

    # Call-Kopf: "... Call 2018 - Information and Communication Technology"
    call_thema = None
    for z in zs:
        m = re.search(r"Call (\d{4})\s*[-–]\s*(.+)$", z)
        if m and "Vienna Research Groups" in z:
            call_thema = m.group(2).strip()
            break

    name, i = wert_nach(zs, "VRG leader")
    institution, _ = wert_nach(zs, "Institution", ab=max(i, 0))
    proponent, j = wert_nach(zs, "Proponent")
    prop_inst, _ = wert_nach(zs, "Institution", ab=max(j, 0)) if j >= 0 else (None, -1)
    titel, _ = wert_nach(zs, "Projekttitel")
    status_roh, _ = wert_nach(zs, "Status")
    doi, _ = wert_nach(zs, "GrantID")
    summe_roh, _ = wert_nach(zs, "Fördersumme")

    status, start, ende = None, None, None
    if status_roh:
        m = re.match(r"(\w+)\s*\((\d{2}\.\d{2}\.\d{4})\s*–\s*(\d{2}\.\d{2}\.\d{4})\)", status_roh)
        if m:
            status, start, ende = m.group(1), m.group(2), m.group(3)
        else:
            status = status_roh.split("(")[0].strip() or None

    summe = None
    if summe_roh:
        ziffern = re.sub(r"[^0-9]", "", summe_roh)
        summe = int(ziffern) if ziffern else None

    disziplinen = []
    _, di = wert_nach(zs, "Wissenschaftliche Disziplinen")
    if di >= 0:
        for z in zs[di + 1: di + 12]:
            if z in ("als PDF öffnen", "Nach oben Scrollen") or z.startswith("Keywords"):
                break
            if re.fullmatch(r"[|;]", z) or re.fullmatch(r"\(\d+%\)", z):
                continue
            d = re.sub(r"\s*\(\d+%\)$", "", z).strip(" |;")
            if d and not d.startswith("("):
                disziplinen.append(d)

    return {
        "id": vrg_id,
        "call_jahr": 2000 + int(vrg_id[3:5]),
        "call_thema": call_thema or CALL_THEMEN.get(2000 + int(vrg_id[3:5])),
        "name": name,
        "institution": institution,
        "institution_kurz": kurzname(institution),
        # Die Wiener Gastinstitution steht verlässlich beim Proponenten:
        # bei frisch bewilligten Gruppen ist die Leader-Institution noch die
        # ausländische Herkunft (EPFL, Stanford, Amazon).
        "gastinstitution": prop_inst,
        "gastinstitution_kurz": kurzname(prop_inst),
        "titel": titel,
        "proponent": proponent,
        "status": status,
        "start": start,
        "ende": ende,
        "grant_doi": doi,
        "summe_eur": summe,
        "disziplinen": disziplinen,
        "url": url,
    }


def main():
    programm = hole(PROGRAMM_URL)
    ids = {}
    for pfad in re.findall(r'href="(/funding/programmes/[^"]*?/(VRG\d{2}-\d{3})/)"', programm):
        ids[pfad[1]] = "https://wwtf.at" + pfad[0]
    print(f"{len(ids)} VRG-Projekte auf der Programmseite verlinkt")

    gruppen = [parse_projekt(vid, url) for vid, url in sorted(ids.items())]
    gruppen.sort(key=lambda g: (g["call_jahr"], g["id"]))
    OUT.write_text(json.dumps(gruppen, ensure_ascii=False, indent=1) + "\n")

    ohne_namen = [g["id"] for g in gruppen if not g["name"]]
    print(f"✓ {len(gruppen)} Gruppen → {OUT.name}"
          + (f" | ohne Leader-Namen: {ohne_namen}" if ohne_namen else ""))
    jahre = sorted({g["call_jahr"] for g in gruppen})
    print(f"  Calls {jahre[0]}–{jahre[-1]}, "
          f"Summe {sum(g['summe_eur'] or 0 for g in gruppen) / 1e6:.1f} Mio €")
    return gruppen


if __name__ == "__main__":
    gruppen = main()
    # Selbstcheck gegen einen bekannten Datensatz
    assert len(gruppen) >= 30, f"nur {len(gruppen)} Gruppen gefunden"
    assert all(g["name"] and g["institution"] and g["call_jahr"] for g in gruppen)
    probe = next(g for g in gruppen if g["id"] == "VRG18-013")
    assert probe["name"] == "Emanuel Sallinger", probe["name"]
    assert probe["institution_kurz"] == "TU Wien"
    assert probe["gastinstitution_kurz"] == "TU Wien"
    # frisch bewilligt: Leader sitzt noch im Ausland, Gastinstitution ist Wien
    neu = next(g for g in gruppen if g["id"] == "VRG25-008")
    assert neu["institution_kurz"] == "Stanford University", neu["institution_kurz"]
    assert neu["gastinstitution_kurz"] == "MedUni Wien", neu["gastinstitution_kurz"]
    assert all(g["gastinstitution_kurz"] for g in gruppen), "Gastinstitution fehlt"
    assert all(g["call_thema"] for g in gruppen), \
        [g["id"] for g in gruppen if not g["call_thema"]]
    assert probe["summe_eur"] == 1_600_000, probe["summe_eur"]
    print("✓ Selbstcheck ok")
