#!/usr/bin/env python3
"""
Stage 5: WWTF-Anreicherung.

1. Strukturierte Metriken (h_index, publikationen, zitierungen) aus bio_text
   extrahieren + openalex_id aus openalex_research.json übernehmen.
2. wwtf_programme: heuristische Zuordnung ÖFOS-Code/-Label → WWTF-Programmfelder.
3. vrg_id / vrg_call: Abgleich mit vrg_grantees.json (Vienna Research Groups).
4. wwtf_foerderung: Abgleich mit wwtf_projekte.json (alle WWTF-Projekte seit
   2003, PI wie Co-PI), mit Zeitbezug zur Berufung (vor/nach).
5. abgang: Abgleich mit abgaenge.json (öffentlich belegte Weggänge).

Läuft nach enrich.py, vor build_html.py. Idempotent.
"""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
OA_PATH = ROOT / "scripts" / "openalex_research.json"
VRG_PATH = ROOT / "vrg_grantees.json"
VRG_OVERRIDES = ROOT / "scripts" / "vrg_overrides.json"
PROJEKTE_PATH = ROOT / "wwtf_projekte.json"
PROJEKTE_OVERRIDES = ROOT / "scripts" / "wwtf_overrides.json"
ABGAENGE_PATH = ROOT / "abgaenge.json"

# WWTF-Programmfelder (Kürzel → Anzeige)
PROGRAMMES = {
    "LS": "Life Sciences",
    "ICT": "Information & Communication Technology",
    "CS": "Cognitive Sciences",
    "ESR": "Environmental Systems Research",
    "DH": "Digital Humanism",
    "MA": "Mathematik und …",
}

# ÖFOS-3-Steller → Programmfelder (Basiszuordnung)
OFOS_TO_PROG = {
    "101": ["MA"],
    "102": ["ICT"],
    "106": ["LS"],
    "202": ["ICT"],
    "207": ["ESR"],
    "301": ["LS"],
    "302": ["LS"],
    "304": ["LS"],
    "401": ["ESR"],
    "403": ["LS"],
    "501": ["CS"],
}

# Keyword-Zusätze auf ofos_label / forschungsbereich (case-insensitive)
KEYWORD_PROG = [
    (r"neuro", "CS"),
    (r"naturschutz|ökologie|wald|umwelt|wasser", "ESR"),
    (r"mensch-maschine|künstliche intelligenz|digital", "DH"),
]


def infer_programmes(d):
    progs = list(OFOS_TO_PROG.get(d.get("ofos_code") or "", []))
    text = f"{d.get('ofos_label') or ''} {d.get('forschungsbereich') or ''}".lower()
    for pattern, prog in KEYWORD_PROG:
        if re.search(pattern, text) and prog not in progs:
            progs.append(prog)
    return progs


def namensschluessel(name):
    """Namen vergleichbar machen: ohne Diakritika, klein, einfache Leerzeichen."""
    ohne = unicodedata.normalize("NFKD", name or "")
    ohne = ohne.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", ohne).strip().lower()


def verknuepfe_vrg(data):
    """Setzt vrg_id/vrg_call auf Berufungen, die einer VRG-Gruppe entsprechen.

    Der Abgleich läuft über den normalisierten Namen. Kein Fuzzy-Matching:
    lieber eine Lücke melden als zwei Personen verwechseln. Abweichende
    Schreibweisen kommen in scripts/vrg_overrides.json (VRG-ID → Name).
    """
    if not VRG_PATH.exists():
        print("  (kein vrg_grantees.json, VRG-Abgleich übersprungen)")
        return 0
    gruppen = json.loads(VRG_PATH.read_text())
    overrides = {}
    if VRG_OVERRIDES.exists():
        overrides = {k: v for k, v in json.loads(VRG_OVERRIDES.read_text()).items()
                     if not k.startswith("_")}

    nach_name = {}
    for g in gruppen:
        nach_name.setdefault(namensschluessel(g["name"]), []).append(g)
    for vrg_id, name in overrides.items():
        g = next((x for x in gruppen if x["id"] == vrg_id), None)
        if g and name:
            nach_name.setdefault(namensschluessel(name), []).append(g)

    treffer = 0
    for d in data:
        kandidaten = nach_name.get(namensschluessel(d["name"]), [])
        if len(kandidaten) > 1:
            print(f"  ! mehrdeutig: {d['name']} passt auf "
                  f"{[g['id'] for g in kandidaten]} — Override nötig")
            continue
        if kandidaten:
            d["vrg_id"] = kandidaten[0]["id"]
            d["vrg_call"] = kandidaten[0]["call_jahr"]
            treffer += 1
        else:
            d.pop("vrg_id", None)
            d.pop("vrg_call", None)
    print(f"  VRG-Abgleich: {treffer} von {len(gruppen)} Gruppen sind berufen worden")
    return treffer


def kurzschluessel(name):
    """Nur Vor- und Nachname: die Unis und der WWTF führen Mittelnamen
    unterschiedlich (Thomas Lennon Sheppard vs Thomas Sheppard)."""
    teile = namensschluessel(name).split(" ")
    return f"{teile[0]} {teile[-1]}" if len(teile) >= 2 else " ".join(teile)


def verknuepfe_projekte(data):
    """Setzt wwtf_foerderung: alle WWTF-Projekte, an denen die Person als PI,
    Co-PI oder VRG-Leitung beteiligt war, mit Zeitbezug zur Berufung.

    Abgleich über den normalisierten vollen Namen; fällt er aus, über Vor- und
    Nachname, aber nur wenn der Kurzname auf beiden Seiten eindeutig ist.
    Abweichende Schreibweisen (Doppelnamen, Umlaute, Heirat) kommen in
    scripts/wwtf_overrides.json: {"<Name im Radar>": ["<Name beim WWTF>", …]}.
    Ein Eintrag darf dort auch leer sein ([]) — dann wird der Treffer
    unterdrückt, falls ein Namensvetter fälschlich zugeordnet würde.
    """
    for d in data:
        d.pop("wwtf_foerderung", None)
    if not PROJEKTE_PATH.exists():
        print("  (kein wwtf_projekte.json, Projekt-Abgleich übersprungen)")
        return 0
    projekte = json.loads(PROJEKTE_PATH.read_text())
    overrides = {}
    if PROJEKTE_OVERRIDES.exists():
        overrides = {k: v for k, v in json.loads(PROJEKTE_OVERRIDES.read_text()).items()
                     if not k.startswith("_")}

    # WWTF-Seite: voller Schlüssel → [(projekt, rolle, institution)], Kurzschlüssel → Namen
    voll, kurz = {}, {}
    for p in projekte:
        for person in p["personen"]:
            if person["rolle"] == "Proponent":  # Gastgeber:in einer VRG, nicht gefördert
                continue
            k = namensschluessel(person["name"])
            voll.setdefault(k, []).append((p, person))
            kurz.setdefault(kurzschluessel(person["name"]), set()).add(k)
    # Radar-Seite: Kurzschlüssel → volle Schlüssel (für die Eindeutigkeitsprüfung)
    radar_kurz = {}
    for d in data:
        radar_kurz.setdefault(kurzschluessel(d["name"]), set()).add(namensschluessel(d["name"]))

    def rollen_fuer(d):
        if d["name"] in overrides:
            treffer = []
            for alias in overrides[d["name"]]:
                treffer += voll.get(namensschluessel(alias), [])
            return treffer
        k = namensschluessel(d["name"])
        if k in voll:
            return voll[k]
        kk = kurzschluessel(d["name"])
        kandidaten = kurz.get(kk, set())
        if len(kandidaten) == 1 and len(radar_kurz.get(kk, set())) == 1:
            return voll[next(iter(kandidaten))]
        return []

    personen, zuordnungen = 0, 0
    for d in data:
        liste = []
        for p, person in rollen_fuer(d):
            if any(x["id"] == p["id"] for x in liste):
                continue
            zeitbezug = None
            if p["call_jahr"] and d.get("year"):
                zeitbezug = "vor" if p["call_jahr"] < d["year"] else ("nach" if p["call_jahr"] > d["year"] else "im Berufungsjahr")
            liste.append({
                "id": p["id"], "programm": p["programm"], "programm_name": p["programm_name"],
                "call_jahr": p["call_jahr"], "rolle": person["rolle"],
                "institution": person.get("institution"), "titel": p["titel"],
                "summe_eur": p["summe_eur"], "status": p["status"], "zeitbezug": zeitbezug,
                "url": p["url"],
            })
        if liste:
            liste.sort(key=lambda x: (x["call_jahr"] or 0, x["id"]))
            d["wwtf_foerderung"] = liste
            personen += 1
            zuordnungen += len(liste)
    # VRG-Leitungen aus dem VRG-Abgleich müssen hier wieder auftauchen
    fehlt = [d["name"] for d in data if d.get("vrg_id")
             and not any(f["id"] == d["vrg_id"] for f in d.get("wwtf_foerderung", []))]
    print(f"  WWTF-Projekte: {personen} Berufene mit {zuordnungen} Projektrollen "
          f"(aus {len(projekte)} Projekten)" + (f" | VRG ohne Projekttreffer: {fehlt}" if fehlt else ""))
    return personen


def verknuepfe_abgaenge(data):
    """Setzt "abgang" auf die jüngste Berufung einer Person an der Uni, die sie verlassen hat.

    abgaenge.json ist von Hand kuratiert: nur Weggänge mit öffentlicher Quelle.
    Einträge ohne Berufung im Radar (etwa VRG-Leitungen) bleiben unverknüpft.
    """
    for d in data:
        d.pop("abgang", None)
    if not ABGAENGE_PATH.exists():
        return 0
    abgaenge = {(namensschluessel(a["name"]), a["universitat"]): a
                for a in json.loads(ABGAENGE_PATH.read_text())}
    juengste = {}
    for d in data:
        k = (namensschluessel(d["name"]), d["universitat"])
        if k in abgaenge and (k not in juengste or d["year"] > juengste[k]["year"]):
            juengste[k] = d
    for k, d in juengste.items():
        a = abgaenge[k]
        d["abgang"] = {f: a.get(f) for f in ("abgang_jahr", "abgang_monat", "ziel", "ziel_land", "art", "quelle")}
    ohne = sorted(a["name"] for k, a in abgaenge.items() if k not in juengste)
    print(f"  Abgänge: {len(juengste)} von {len(abgaenge)} einer Berufung zugeordnet"
          + (f" (ohne Berufung: {', '.join(ohne)})" if ohne else ""))
    return len(juengste)


def extract_metrics(bio):
    m = {}
    if not bio:
        return m
    for key, pattern in [
        ("h_index", r"h-Index:\s*(\d+)"),
        ("publikationen", r"Publikationen:\s*(\d+)"),
        ("zitierungen", r"Zitierungen:\s*(\d+)"),
    ]:
        hit = re.search(pattern, bio, re.I)
        if hit:
            m[key] = int(hit.group(1))
    return m


def main():
    data = json.loads(DATA_PATH.read_text())
    oa = json.loads(OA_PATH.read_text()) if OA_PATH.exists() else {}

    n_metrics = n_prog = 0
    for d in data:
        metrics = extract_metrics(d.get("bio_text"))
        # openalex_research.json überschreibt bio_text-Werte (aktuellere Quelle);
        # low-confidence Treffer (Namensvetter) werden ignoriert
        entry = oa.get(d["name"]) or {}
        if entry.get("match_confidence") == "low":
            entry = {}
        if entry.get("h_index") is not None:
            metrics["h_index"] = entry["h_index"]
        if entry.get("works_count") is not None:
            metrics["publikationen"] = entry["works_count"]
        if entry.get("cited_by_count") is not None:
            metrics["zitierungen"] = entry["cited_by_count"]
        # Auch leeren: eine alte ID (Namensvetter) darf nicht stehen bleiben
        if entry.get("openalex_id"):
            d["openalex_id"] = entry["openalex_id"]
        else:
            d.pop("openalex_id", None)
        d.update({k: metrics.get(k) for k in ("h_index", "publikationen", "zitierungen")})
        if metrics:
            n_metrics += 1

        d["wwtf_programme"] = infer_programmes(d)
        if d["wwtf_programme"]:
            n_prog += 1

    verknuepfe_vrg(data)
    verknuepfe_projekte(data)
    verknuepfe_abgaenge(data)

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")

    print(f"✓ {len(data)} Einträge: {n_metrics} mit Metriken, {n_prog} in WWTF-Programmfeldern")
    from collections import Counter

    c = Counter(p for d in data for p in d["wwtf_programme"])
    for k, v in c.most_common():
        print(f"  {k:4} {PROGRAMMES[k]:42} {v}")


if __name__ == "__main__":
    main()
    # Selbstcheck
    data = json.loads(DATA_PATH.read_text())
    assert all("wwtf_programme" in d for d in data)
    assert any(d.get("h_index") for d in data)
    assert "LS" in next(d for d in data if d["ofos_code"] == "302")["wwtf_programme"]
    # Sallinger ist VRG18-013 und seit Februar 2025 Professor an der TU Wien:
    # der Abgleich muss ihn finden, sonst greift die Namensnormalisierung nicht.
    if (ROOT / "vrg_grantees.json").exists():
        sallinger = next((d for d in data if d["name"] == "Emanuel Sallinger"), None)
        if sallinger:
            assert sallinger.get("vrg_id") == "VRG18-013", sallinger.get("vrg_id")
    if (ROOT / "wwtf_projekte.json").exists():
        mit = [d for d in data if d.get("wwtf_foerderung")]
        assert len(mit) >= 50, f"nur {len(mit)} Berufene mit WWTF-Projekt — Abgleich defekt?"
        sallinger = next((d for d in data if d["name"] == "Emanuel Sallinger"), None)
        if sallinger:
            f = next(x for x in sallinger["wwtf_foerderung"] if x["id"] == "VRG18-013")
            assert f["rolle"] == "VRG-Leitung" and f["zeitbezug"] == "vor", f
