#!/usr/bin/env python3
"""
Holt die WWTF-Projektdatenbank (wwtf.at/funding/project-database/) und
schreibt sie nach wwtf_projekte.json: ein Eintrag je Projekt mit allen
beteiligten Personen (PI, Co-PIs, Proponent bei VRG) samt Rolle und
Institution.

Zwei Stufen, beide mit Plattencache in scripts/.wwtf_cache/:
  1. Die Datenbankseite listet alle Projekt-Schlüssel (data-pkey); die
     Kurzfassungen kommen in Paketen über den AJAX-Gateway der Seite.
  2. Je Projekt die Detailseite (Personen, Status, Laufzeit, Disziplinen).

Läuft selten (die Datenbank wächst mit den Calls), gehört nicht in update.sh.
Aufruf: python3 scripts/fetch_wwtf_projekte.py [--offline] [--refresh]
  --refresh lädt die Datenbankseite und die Kurzfassungen neu (neue Calls),
  die Detailseiten bleiben im Cache, weil sie sich praktisch nie ändern.
"""

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "wwtf_projekte.json"
CACHE = Path(__file__).resolve().parent / ".wwtf_cache"

DB_URL = "https://wwtf.at/funding/project-database/"
AJAX_URL = "https://wwtf.at/modules/ajax_gateway.php?act=presult"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

# Programmkürzel wie im Dropdown der Datenbank; der Rest der ID ist der Call.
PROGRAMME = {
    "VRG": "Vienna Research Groups", "LS": "Life Sciences", "MA": "Mathematik und …",
    "CS": "Cognitive Sciences", "ICT": "Information & Communication Technology",
    "SSH": "Social Sciences & Humanities", "UIP": "Universitäts-Infrastrukturprogramm",
    "ESR": "Environmental Systems Research", "CI": "Science for Creative Industries",
    "NXT": "NEXT Transfer", "CRR": "COVID-19 Rapid Response",
    "EI": "Ergänzende Instrumente", "ESS": "Empirical Social Sciences",
    "ME-CFS": "ME/CFS", "DH": "Digital Humanism", "AI": "Artificial Intelligence",
    "AT": "Austria-Tunisia", "CU": "Cultural Studies", "NG": "Nachwuchsgruppen",
    "DF": "Digitalisierung & Gesellschaft", "PWT": "Public Wealth Transfer",
    "SC": "Science Chairs (Stiftungsprofessuren)", "DARE": "Digital Research Enablers",
    "RO": "Roadmaps", "SF": "Sonderförderung", "DCDH": "Doctoral College Digital Humanism",
    "EPG": "Sonderförderung",
}
# Rollen, die eine Förderung an die Person selbst bedeuten. Der Proponent einer
# VRG ist die Wiener Gastgeberin, nicht die Geförderte, und bleibt deshalb nur
# in wwtf_projekte.json dokumentiert.
GEFOERDERT = ("PI", "Co-PI", "VRG-Leitung")


def hole(url, data=None):
    CACHE.mkdir(exist_ok=True)
    datei = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url + (data or "")).strip("_")[:200] + ".html")
    frisch = "--refresh" in sys.argv and (url == DB_URL or data is not None)
    if datei.exists() and not frisch:
        return datei.read_text(encoding="utf-8")
    if "--offline" in sys.argv:
        raise SystemExit(f"--offline, aber nicht im Cache: {url}")
    req = urllib.request.Request(url, data=data.encode() if data else None, headers={
        "User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "Referer": DB_URL})
    for versuch in range(3):  # der Server wirft sporadisch 500er
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                txt = r.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as e:
            if e.code < 500 or versuch == 2:
                raise
            time.sleep(2 * (versuch + 1))
    datei.write_text(txt, encoding="utf-8")
    time.sleep(0.4)
    return txt


def zeilen(seite):
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", seite, flags=re.S)
    txt = re.sub(r"<br\s*/?>", "\n", txt)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    return [z.strip() for z in html.unescape(txt).split("\n") if z.strip()]


def wert_nach(zs, label, ab=0):
    for i in range(ab, len(zs)):
        if zs[i].rstrip(":") == label.rstrip(":"):
            return (zs[i + 1] if i + 1 < len(zs) else None), i
    return None, -1


def projekt_urls():
    """Alle Projekt-URLs der Datenbank, über Seite plus AJAX-Kurzfassungen."""
    seite = hole(DB_URL)
    keys = [k for k in re.findall(r'data-pkey="([^"]+)"', seite) if re.fullmatch(r"\d+_[A-Z]{2}_[A-Z]", k)]
    kurz = dict(re.findall(r'<div data-pkey="([^"]+)">(<article.*?</article>)</div>', seite, re.S))
    offen = [k for k in keys if k not in kurz]
    for i in range(0, len(offen), 40):
        data = urllib.parse.urlencode([("obj[]", k) for k in offen[i:i + 40]])
        kurz.update(json.loads(hole(AJAX_URL, data)))
    urls, kurzfassungen = {}, {}
    for k in keys:
        m = re.search(r'href="(/funding/programmes/[^"]+/)"', kurz.get(k, ""))
        if m:
            urls[k] = "https://wwtf.at" + m.group(1)
            kurzfassungen[urls[k]] = kurz[k]
    print(f"{len(keys)} Projekte in der Datenbank, {len(urls)} mit Detailseite")
    return urls, kurzfassungen


def aus_kurzfassung(url, artikel):
    """Notnagel für Detailseiten, die der Server mit 500 beantwortet (Stand
    11/2026: 14 Projekte, darunter VRG13-007 und VRG14-021). Die Kurzfassung
    der Datenbankliste kennt ID, PI, Institution, Titel und Fördersumme."""
    zs = zeilen(artikel)
    kopf = zs[0] if zs else ""
    pid = url.rstrip("/").rsplit("/", 1)[-1]
    m = re.match(re.escape(pid) + r"\s*(?:–\s*)?(.*?)\s*(?:\((.*)\))?\s*$", kopf)
    name = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    inst = m.group(2) if m else None
    titel = zs[1] if len(zs) > 1 and not zs[1].startswith(("Dauer", "Fördersumme")) else None
    summe_roh = next((z for z in zs if "Fördersumme" in z), "")
    ziffern = re.sub(r"[^0-9]", "", summe_roh.split("Fördersumme")[-1])
    rolle = "VRG-Leitung" if pid.startswith("VRG") else "PI"
    return {
        "titel": titel,
        "personen": [{"name": name, "institution": inst, "rolle": rolle}] if name else [],
        "status": None, "start": None, "ende": None, "grant_doi": None,
        "summe_eur": int(ziffern) if ziffern else None, "disziplinen": [],
        "_quelle": "Kurzfassung (Detailseite nicht abrufbar)",
    }


def personen_block(zs, label):
    """Namen (mit Institution in Klammern) hinter einem Personen-Label.

    Die Seite setzt "Name (Institution)" mal in eine Zeile, mal getrennt:
    "Sabine Taschner-Mandl" / "(St. Anna ...)". Beides wird zusammengeführt.
    Ende des Blocks ist das nächste Label (endet auf Doppelpunkt).
    """
    _, i = wert_nach(zs, label)
    if i < 0:
        return []
    personen, j = [], i + 1
    while j < len(zs) and not zs[j].endswith(":"):
        z = re.sub(r"\s+", " ", zs[j]).strip()
        if z.startswith("(") and z.endswith(")") and personen and not personen[-1]["institution"]:
            personen[-1]["institution"] = z[1:-1].strip()
        else:
            m = re.match(r"^(.*?)\s*\((.*)\)\s*$", z)
            namen, inst = (m.group(1), m.group(2)) if m else (z, None)
            # Ältere SSH-Projekte führen mehrere Leitungen in einer Zeile:
            # "Christoph Reinprecht, Ayse Caglar & Roland Verwiebe"
            for name in re.split(r"\s*(?:,|&| und )\s*", namen):
                if name:
                    personen.append({"name": name, "institution": inst})
        j += 1
    return personen


def programm_und_call(pid):
    # LS25-044, VRG18-013, ME-CFS26-005, ME-CFS-CC26-003, EI-VRG24-001, UIP09-MUW …
    m = re.match(r"^(?:EI-)?([A-Z]+(?:-[A-Z]+)*?)-?(\d{2})-", pid)
    programm = m.group(1) if m else pid.split("-")[0]
    call_jahr = 2000 + int(m.group(2)) if m else None
    if programm.startswith("ME-CFS"):
        programm = "ME-CFS"
    if pid.startswith("EI-"):
        programm = "EI"
    return programm, call_jahr


def parse_projekt(url, kurzfassung=None):
    pid = url.rstrip("/").rsplit("/", 1)[-1]
    programm, call_jahr = programm_und_call(pid)
    try:
        zs = zeilen(hole(url))
    except urllib.error.HTTPError as e:
        if e.code >= 500 and kurzfassung:
            return {"id": pid, "programm": programm, "programm_name": PROGRAMME.get(programm, programm),
                    "call_jahr": call_jahr, **aus_kurzfassung(url, kurzfassung), "url": url}
        raise
    titel, _ = wert_nach(zs, "Projekttitel")
    status_roh, _ = wert_nach(zs, "Status")
    doi, _ = wert_nach(zs, "GrantID")
    summe_roh, _ = wert_nach(zs, "Fördersumme")

    personen = []
    for label, rolle in [("Principal Investigator", "PI"), ("VRG leader", "VRG-Leitung"),
                         ("Co-Principal Investigator(s)", "Co-PI"), ("Proponent", "Proponent"),
                         ("Projektleitung", "PI"), ("Projektleiter", "PI"), ("Projektleiterin", "PI")]:
        for p in personen_block(zs, label):
            if p["name"] and not any(x["name"] == p["name"] for x in personen):
                personen.append({**p, "rolle": rolle})
    # PI/VRG-Leitung: Institution steht als eigenes Feld direkt danach
    for p in personen:
        if p["rolle"] in ("PI", "VRG-Leitung") and not p["institution"]:
            _, i = wert_nach(zs, p["name"])
            inst, _ = wert_nach(zs, "Institution", ab=max(i, 0))
            p["institution"] = inst

    status, start, ende = None, None, None
    if status_roh:
        m = re.match(r"(.+?)\s*\((\d{2}\.\d{2}\.\d{4})\s*–\s*(\d{2}\.\d{2}\.\d{4})\)", status_roh)
        if m:
            status, start, ende = m.group(1).strip(), m.group(2), m.group(3)
        else:
            status = status_roh.split("(")[0].strip() or None

    summe = None
    if summe_roh:
        ziffern = re.sub(r"[^0-9]", "", summe_roh)
        summe = int(ziffern) if ziffern else None

    disziplinen = []
    _, di = wert_nach(zs, "Wissenschaftliche Disziplinen")
    if di >= 0:
        for z in zs[di + 1: di + 14]:
            if z in ("als PDF öffnen", "Nach oben Scrollen") or z.endswith(":"):
                break
            if re.fullmatch(r"[|;]", z) or re.fullmatch(r"\(\d+%\)", z):
                continue
            d = re.sub(r"\s*\(\d+%\)$", "", z).strip(" |;")
            if d and not d.startswith("("):
                disziplinen.append(d)

    return {
        "id": pid,
        "programm": programm,
        "programm_name": PROGRAMME.get(programm, programm),
        "call_jahr": call_jahr,
        "titel": titel,
        "personen": personen,
        "status": status,
        "start": start,
        "ende": ende,
        "grant_doi": doi,
        "summe_eur": summe,
        "disziplinen": disziplinen,
        "url": url,
    }


def main():
    urls, kurzfassungen = projekt_urls()
    projekte = []
    for n, (k, url) in enumerate(sorted(urls.items(), key=lambda kv: kv[1]), 1):
        try:
            projekte.append(parse_projekt(url, kurzfassungen.get(url)))
        except Exception as e:  # eine kaputte Seite darf den Lauf nicht beenden
            print(f"  ! {url}: {e}")
        if n % 100 == 0:
            print(f"  {n}/{len(urls)}")
    projekte.sort(key=lambda p: (p["call_jahr"] or 0, p["id"]))
    OUT.write_text(json.dumps(projekte, ensure_ascii=False, indent=1) + "\n")

    ohne_personen = [p["id"] for p in projekte if not p["personen"] and p["programm"] != "UIP"]
    print(f"✓ {len(projekte)} Projekte → {OUT.name}, "
          f"{sum(len(p['personen']) for p in projekte)} Personenrollen"
          + (f" | ohne Personen: {len(ohne_personen)} ({', '.join(ohne_personen[:8])}…)" if ohne_personen else ""))
    from collections import Counter
    for prog, n in Counter(p["programm"] for p in projekte).most_common():
        print(f"  {prog:7} {PROGRAMME.get(prog, '?'):40} {n}")
    return projekte


if __name__ == "__main__":
    projekte = main()
    assert len(projekte) >= 650, f"nur {len(projekte)} Projekte"
    notnagel = [p["id"] for p in projekte if p.get("_quelle")]
    print(f"  aus Kurzfassung (Detailseite 500): {len(notnagel)} {notnagel}")
    vrg13 = next(p for p in projekte if p["id"] == "VRG13-007")
    assert vrg13["personen"] and vrg13["personen"][0]["rolle"] == "VRG-Leitung", vrg13
    assert all(p["call_jahr"] for p in projekte), [p["id"] for p in projekte if not p["call_jahr"]]
    assert not any("  " in x["name"] for p in projekte for x in p["personen"])

    probe = next(p for p in projekte if p["id"] == "LS25-044")
    assert probe["personen"][0] == {"name": "George Cresswell", "institution": "St. Anna Kinderkrebsforschung GmbH (CCRI)", "rolle": "PI"}, probe["personen"]
    assert {"name": "Sabine Taschner-Mandl", "institution": "St. Anna Kinderkrebsforschung GmbH (CCRI)", "rolle": "Co-PI"} in probe["personen"], probe["personen"]
    assert probe["summe_eur"] == 999_538 and probe["call_jahr"] == 2025 and probe["programm"] == "LS"
    vrg = next(p for p in projekte if p["id"] == "VRG18-013")
    assert vrg["personen"][0]["name"] == "Emanuel Sallinger" and vrg["personen"][0]["rolle"] == "VRG-Leitung", vrg["personen"]
    ict = next(p for p in projekte if p["id"] == "ICT25-056")
    assert ict["start"] == "01.02.2026" and ict["status"] == "Laufend", ict
    print("✓ Selbstcheck ok")
