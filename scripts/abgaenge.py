#!/usr/bin/env python3
"""
Verbleib der Berufenen: wer hat die berufende Uni inzwischen verlassen?

Signal ist die Affiliationsgeschichte in OpenAlex (Jahre, in denen eine
Person mit einer Institution publiziert hat). Taucht die berufende Uni seit
zwei Jahren nicht mehr auf und publiziert die Person seither mit einer neuen
Institution, ist das ein Abgangskandidat. Bestätigt wird über die
ORCID-Beschäftigungsdaten, wo vorhanden.

Das ist ein Kandidatenfilter, kein Beleg: Publikationen hinken dem Wechsel
ein bis zwei Jahre hinterher, Doppelaffiliationen und Gastaufenthalte
erzeugen Fehlalarme, und OpenAlex vermischt mitunter Namensvettern.
Ruhestand ist aus Publikationen nicht von Inaktivität zu unterscheiden.

Aufruf: python3 scripts/abgaenge.py [--refresh]
        (--refresh lädt die OpenAlex-Profile neu, sonst Cache)
Schreibt scripts/.abgaenge_cache/verbleib.csv (nicht im Repo, ungeprüft).
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openalex_lookup import API_KEY_PARAM, MAILTO, UA  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / ".abgaenge_cache"
AUTHORS = CACHE / "authors.json"
ORCID = CACHE / "orcid.json"
OUT = CACHE / "verbleib.csv"

# OpenAlex-Institutionen, unter denen Berufene der jeweiligen Uni publizieren
HEIM = {
    "Uni Wien": {"I129774422", "I2802916955", "I4210142901", "I4210100980"},
    "MedUni Wien": {"I76134821", "I2802328216", "I4210092129"},
    "TU Wien": {"I145847075"},
    "BOKU": {"I92869138"},
    "WU Wien": {"I102248843"},
    "Vetmeduni Wien": {"I150540706"},
    "mdw": {"I173085932"},
    "Angewandte": {"I143923934"},
    "Akademie": {"I5075986"},
    "CEU": {"I198945027"},
}
WIEN = set().union(*HEIM.values()) | {
    "I138211613",   # ÖAW
    "I4210127611",  # CeMM
}

AKTUELL = date.today().year
# Publikationsjahre hinken nach: das laufende Jahr ist unvollständig, ein Jahr
# ohne Heim-Affiliation ist noch kein Abgang. Zwei volle Jahre ohne zählen.
STICHJAHR = AKTUELL - 1


def hole(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def lade_autoren(ids, refresh):
    autoren = json.loads(AUTHORS.read_text()) if AUTHORS.exists() and not refresh else {}
    fehlt = sorted(set(ids) - set(autoren))
    for i in range(0, len(fehlt), 50):
        teil = fehlt[i:i + 50]
        daten = hole("https://api.openalex.org/authors?filter=openalex:" + "|".join(teil)
                     + "&per_page=50&select=id,display_name,orcid,affiliations,counts_by_year"
                     + f"&mailto={MAILTO}{API_KEY_PARAM}")
        for a in daten["results"]:
            autoren[a["id"].rsplit("/", 1)[-1]] = a
        time.sleep(1)
    CACHE.mkdir(exist_ok=True)
    AUTHORS.write_text(json.dumps(autoren, ensure_ascii=False))
    return autoren


def orcid_stellen(orcid, cache):
    """Beschäftigungen laut ORCID: [(organisation, land, startjahr, endjahr)]."""
    oid = orcid.rsplit("/", 1)[-1]
    if oid not in cache:
        try:
            daten = hole(f"https://pub.orcid.org/v3.0/{oid}/employments")
        except Exception as e:  # ORCID gelegentlich nicht erreichbar: nicht cachen
            print(f"  ! ORCID {oid}: {e}", file=sys.stderr)
            return None
        stellen = []
        for gruppe in daten.get("affiliation-group", []):
            for s in gruppe.get("summaries", []):
                e = s.get("employment-summary", {})
                org = e.get("organization") or {}
                jahr = lambda d: int(d["year"]["value"]) if d and d.get("year") else None
                stellen.append((org.get("name"), (org.get("address") or {}).get("country"),
                                jahr(e.get("start-date")), jahr(e.get("end-date"))))
        cache[oid] = stellen
        time.sleep(0.5)
    return cache[oid]


def vrg_autoren(vrgs, autoren):
    """OpenAlex-Profile der VRG-Leitungen: Namenssuche, eingeschränkt auf die Gastinstitution."""
    for v in vrgs:
        key = "vrg:" + v["id"]
        if key in autoren:
            continue
        heim = "|".join(sorted(HEIM.get(v["gastinstitution_kurz"], ())))
        q = urllib.parse.quote(v["name"])
        daten = hole(f"https://api.openalex.org/authors?search={q}&filter=affiliations.institution.id:{heim}"
                     f"&per_page=1&select=id,display_name,orcid,affiliations,counts_by_year"
                     f"&mailto={MAILTO}{API_KEY_PARAM}")
        autoren[key] = (daten.get("results") or [None])[0]
        time.sleep(1)
    AUTHORS.write_text(json.dumps(autoren, ensure_ascii=False))


def bewerte(d, a):
    """Status, Ziel-Institution, Ziel-Land, letztes Heimjahr, Begründung."""
    heim = HEIM.get(d["universitat"], set())
    affs = [(f["institution"], sorted(f["years"])) for f in a.get("affiliations") or []]
    heimjahre = [y for i, ys in affs if i["id"].rsplit("/", 1)[-1] in heim for y in ys]
    aktiv = [c["year"] for c in a.get("counts_by_year") or [] if c.get("works_count")]
    letzte_aktiv = max(aktiv, default=None)
    if not heimjahre:
        if d["year"] >= STICHJAHR:
            return "zu früh", None, None, None, "noch keine Publikation mit der berufenden Uni"
        return "unklar", None, None, None, "nie mit der berufenden Uni publiziert"
    letzte_heim = max(heimjahre)
    if letzte_heim >= STICHJAHR:
        return "bleibt", None, None, letzte_heim, ""
    if d["year"] >= STICHJAHR:
        # Frisch Berufene publizieren noch unter der alten Adresse
        return "zu früh", None, None, letzte_heim, "Berufung zu jung für ein Urteil"
    if letzte_heim < d["year"]:
        # Seit der Berufung nie mit der Uni publiziert: eher falsches Profil als Abgang
        return "Profil prüfen", None, None, letzte_heim, f"berufende Uni zuletzt {letzte_heim}, vor der Berufung"
    # Institutionen nach dem letzten Heimjahr, auch frühere Arbeitgeber (Rückkehr);
    # ein Jahr Nachlauf, weil die Publikationen dem Wechsel hinterherhinken
    neu = [(i, [y for y in ys if y > letzte_heim]) for i, ys in affs
           if i["id"].rsplit("/", 1)[-1] not in heim and ys[-1] > letzte_heim
           and ys[-1] >= STICHJAHR - 1]
    if neu:
        i, ys = max(neu, key=lambda t: (len(t[1]), t[1][-1]))
        if i["id"].rsplit("/", 1)[-1] in WIEN:
            status = "Wechsel in Wien"
        else:
            # Ein einzelnes Jahr kann eine Kooperation oder ein Gastaufenthalt sein
            status = "Abgang wahrscheinlich" if len(ys) >= 2 else "Abgang möglich"
        return (status, i["display_name"],
                i.get("country_code"), letzte_heim,
                f"berufende Uni zuletzt {letzte_heim}, {i['display_name']} {ys[0]}–{ys[-1]}")
    if letzte_aktiv is not None and letzte_aktiv < STICHJAHR - 1:
        return "inaktiv", None, None, letzte_heim, f"keine Publikationen seit {letzte_aktiv}"
    return "unklar", None, None, letzte_heim, f"berufende Uni zuletzt {letzte_heim}, keine neue Institution"


def main():
    data = json.loads((ROOT / "dashboard_data_2025.json").read_text())
    # Pro Person zählt die jüngste Berufung; frühere sind Wechsel innerhalb des Radars
    juengste = {}
    for d in sorted(data, key=lambda d: d["year"]):
        juengste[d.get("openalex_id") or ("name:" + d["name"])] = d
    autoren = lade_autoren([k for k in juengste if not k.startswith("name:")], "--refresh" in sys.argv)
    orcid_cache = json.loads(ORCID.read_text()) if ORCID.exists() else {}

    # VRG-Leitungen, die (noch) nicht als Berufung im Radar stehen: Stichjahr
    # ist der Start der Gruppe, "Heim" die Gastinstitution
    namen = {d["name"] for d in data}
    vrgs = [v for v in json.loads((ROOT / "vrg_grantees.json").read_text()) if v["name"] not in namen]
    vrg_autoren(vrgs, autoren)
    for v in vrgs:
        a = autoren.get("vrg:" + v["id"])
        if a:
            juengste["vrg:" + v["id"]] = {"name": v["name"], "universitat": v["gastinstitution_kurz"],
                                          "year": int(v["start"][-4:]), "vrg": v["id"]}
            autoren["vrg:" + v["id"]] = a

    zeilen = []
    for key, d in juengste.items():
        a = autoren.get(key)
        if not a:
            status, ziel, land, letzte, grund = "kein Profil", None, None, None, ""
        else:
            status, ziel, land, letzte, grund = bewerte(d, a)
        orcid_beleg = ""
        if status.startswith("Abgang") and a.get("orcid"):
            stellen = orcid_stellen(a["orcid"], orcid_cache) or []
            # Stellen, die nach der Berufung beginnen und nicht in Wien liegen
            nach = [s for s in stellen if s[2] and s[2] > d["year"] and s[0]
                    and not any(w in s[0] for w in ("Vienna", "Wien", "Universität für", "BOKU"))]
            if nach:
                s = max(nach, key=lambda s: s[2])
                orcid_beleg = f"{s[0]} ({s[1]}) ab {s[2]}"
                status = "Abgang wahrscheinlich"
        zeilen.append({
            "name": d["name"], "universitat": d["universitat"],
            "berufung": f'{d["vrg"]} ab {d["year"]}' if d.get("vrg") else d["year"],
            "status": status, "ziel": ziel or "", "ziel_land": land or "",
            "letztes_heimjahr": letzte or "", "orcid_beleg": orcid_beleg,
            "begruendung": grund,
            "openalex_id": a["id"].rsplit("/", 1)[-1] if a else "",
        })
    ORCID.write_text(json.dumps(orcid_cache, ensure_ascii=False))
    zeilen.sort(key=lambda z: (z["status"], z["universitat"], z["name"]))
    print(f"davon VRG-Leitungen ohne Berufung im Radar: {sum('VRG' in str(z['berufung']) for z in zeilen)}")
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(zeilen[0]), delimiter=";")
        w.writeheader()
        w.writerows(zeilen)

    zaehl = {}
    for z in zeilen:
        zaehl[z["status"]] = zaehl.get(z["status"], 0) + 1
    print(f"{len(zeilen)} Personen (jüngste Berufung je Person), Stichjahr {STICHJAHR}:")
    for s, n in sorted(zaehl.items(), key=lambda t: -t[1]):
        print(f"  {s:24} {n}")
    print(f"✓ {OUT.relative_to(ROOT)}")
    return zeilen


if __name__ == "__main__":
    main()
