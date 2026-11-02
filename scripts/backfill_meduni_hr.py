#!/usr/bin/env python3
"""
Abgleich der MedUni Wien mit der Personalliste der Universität
("WWTF_Professoren_extern.xls", Stand 22.10.2026, an den WWTF übermittelt im
Oktober 2026): alle derzeit aktiven Professor:innen mit Denomination, Paragraf
und Datum des Dienstantritts, 160 Zeilen.

Was die Liste leistet: sie ist die Primärquelle für den Paragrafen (§98, §99(1),
§99(4), §99(5)) und bestätigt Personen, die in den Recherchedurchgängen 2026-08
mangels erreichbarer Quelle verworfen wurden. Was sie NICHT leistet:
  * Wer die Uni verlassen hat, steht nicht drin (Klepetko, Kühn, Knoblich, …).
    Bestandsdatensätze ohne Treffer sind deshalb nicht falsch, siehe
    pruefung/meduni_nicht_in_hr_liste.csv.
  * Pro Person eine Zeile, die aktuelle Stelle. Eine frühere Professur derselben
    Person (Kimberger §99(1) 2021, dann §99(4) 2026) ist nur über andere Quellen
    belegt.
  * Die Datumsspalte hat Fülleffekte aus Excel: in Blöcken aufeinanderfolgender
    Zeilen steht dasselbe Datum (22 Zeilen "2015-08-01", darunter Beisteiner 2024
    und Bartko 2026). Gegengeprüft an Gruber (Professor seit 10/2014, Liste
    2023-09-01 wie die Zeile davor) und Wolzt (seit 08/2014, Liste 2026-05-15 wie
    Winkler davor). Regel: steht dasselbe Rohdatum in einer der zwei Zeilen
    darüber, gilt das Datum als Fülleffekt und wird nicht verwendet. Der
    Paragraf dieser Zeilen bleibt verwertbar, er wechselt innerhalb der Blöcke.
  * Drei Zeilen ohne Datum, eine mit Jahres-Tippfehler ("01.03.204").

Aufruf: python3 scripts/backfill_meduni_hr.py [--apply]
  ohne --apply: nur Report und backfill/meduni_hr.json schreiben
  mit  --apply: zusätzlich Korrekturen an Bestandsdatensätzen in
                dashboard_data_2025.json vornehmen (Paragraf, Monat)
Danach: python3 scripts/merge_backfill.py backfill/meduni_hr.json
"""

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_backfill import kurz, norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
VOR2019_PATH = ROOT / "dashboard_data_vor2019.json"
HERE = Path(__file__).resolve().parent
LISTE = HERE / "backfill" / "_meduni_hr" / "professoren_extern_2026-10-22.tsv"
OUT = HERE / "backfill" / "meduni_hr.json"
PRUEFUNG = HERE / "pruefung"
VERWORFEN = [PRUEFUNG / "meduni2_verworfen.json", PRUEFUNG / "meduni_aufgeklaert.json"]

QUELLE = ("MedUni Wien, Personalliste aktive Professor:innen mit Dienstantritt "
          "(WWTF_Professoren_extern.xls, Stand 22.10.2026, an WWTF übermittelt 10/2026)")
HEUTE = "2026-11-02"
MONATE = ["JÄNNER", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI", "JULI", "AUGUST",
          "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"]
PARAGRAF = {"98": "§98", "99/1": "§99(1)", "99/4": "§99(4)", "99 Abs. 4": "§99(4)",
            "99/5": "§99(5) Laufbahnstelle"}

# Schreibweise der Liste → Name im Bestand (sonst legt der Merge Dubletten an)
BESTANDSNAME = {
    "Judit Aberle": "Judith Aberle",
    "f Aletaha": "Daniel Aletaha",
    "Hendrik Ankersmit": "Henrik Jan Ankersmit",
    "Talin Barisani": "Talin Barisani-Asenbauer",
    "Philipp Bartko": "Philipp Emanuel Bartko",
    "Eva Maria Compèrat": "Eva Compérat",
    "Thomas Ernst Dorner": "Thomas E. Dorner",
    "Thomas Ashley Leonard": "Thomas Leonard",
    "Eva Masel": "Eva Katharina Masel",
    "Danny D. Nedialkova": "Danny Nedialkova",
    "Winfried Pickl": "Winfried Franz Pickl",
    "Sabine Pleschberger, Mph, Dgkp": "Sabine Pleschberger",
    "Johannes Schmid": "Johannes A. Schmid",
    "Elisabeth Puchhammer": "Elisabeth Puchhammer-Stöckl",
    "Michael J.M. Fischer": "Michael J. M. Fischer",
    "Daniela Pollak-Monje / Quiroga": "Daniela Pollak-Monje Quiroga",
}

# Die Liste zeigt den Paragrafen der AKTUELLEN Stelle. Wo die Presseinformation
# zur Berufung den Paragrafen selbst nennt, gilt sie (Stichprobe 2026-11-02: 12
# Meldungen nachgelesen, 10 decken sich mit der Liste, Attenberger und Pickl
# nicht). Angaben hier sind wörtlich aus der jeweils verlinkten Meldung.
PRESSE = {
    ("Judith Aberle", 2023): ("§99(1)", "MAI", None,
        "'hat mit 1. Mai 2023 die Professur für Virusimmunologie (§99 (1)) … angetreten'"),
    ("Ulrike Attenberger", 2024): ("§98", "JULI", None,
        "'hat mit 15. Juli 2024 die Professur für Radiologie (§98) … angetreten'; Liste sagt §99(4)"),
    ("Winfried Franz Pickl", 2023): ("§99(1)", "MAI", None,
        "'hat mit Anfang Mai die Professur für Translationale Immunologie (§99 (1)) … übernommen'; "
        "Liste sagt §99(4) ab 1.11.2023, vermutlich spätere Umwandlung"),
    ("Herbert Kiss", 2021): ("§98", "DEZEMBER", None,
        "'hat mit 1. Dezember 2021 die Professur für Geburtshilfe und feto-maternale Medizin (§98)'"),
    ("Gerhard Prager", 2021): ("§98", "SEPTEMBER", None,
        "'hat mit 1. September 2021 die Professur für Bariatrische Chirurgie (§ 98) angetreten'"),
    ("Johannes Gojo", 2023): ("§99(1)", "SEPTEMBER", None,
        "'Mit 1. September 2023 tritt Johannes Gojo die Professur für Pädiatrische Neuro-Onkologie (§99(1)) … an'"),
    ("Sigrid Sandner", 2026): ("§99(4)", "JULI", None,
        "'Mit Anfang Juli übernimmt Sigrid Sandner die Professur im Fachbereich Kardiovaskuläre Medizin (§ 99 (4))'"),
    ("Sabine Pleschberger", 2023): ("§99(1)", "DEZEMBER", None,
        "'tritt mit 1. Dezember 2023 die neu geschaffene Professur für Pflegewissenschaft (§99(1)) an'"),
    ("Thomas Scherer", 2025): ("§99(4)", "JULI",
        "https://www.meduniwien.ac.at/web/en/ueber-uns/news/2025/news-in-july-2025/"
        "thomas-scherer-takes-up-professorship-in-the-field-of-endocrinology-and-metabolism/",
        "MedUni-News 1.7.2025: Professur im Fachbereich Endokrinologie und Stoffwechsel (§99(4)) ab 1.7.2025"),
    ("Stephan Polterauer", 2025): ("§99(1)", "JULI",
        "https://www.meduniwien.ac.at/web/en/ueber-uns/news/2025/news-in-july-2025/"
        "stephan-polterauer-takes-over-professorship-for-gynecological-oncology/",
        "MedUni-News 7/2025: Professur für Gynäkologische Onkologie (§99(1)) ab 1.7.2025"),
    ("Francesco Moscato", 2025): ("§99(4)", "NOVEMBER",
        "https://www.meduniwien.ac.at/web/ueber-uns/news/2025/news-im-november-2025/"
        "francesco-moscato-uebernimmt-professur-im-fachbereich-biomedizinische-technik/",
        "MedUni-News 21.11.2025: Professur im Fachbereich Biomedizinische Technik (§99/4)"),
    ("Michael Bonelli", 2025): ("§99(1)", "AUGUST",
        "https://www.meduniwien.ac.at/web/en/ueber-uns/news/2025/news-in-september-2025/"
        "michael-bonelli-takes-up-professorship-in-experimental-rheumatology/",
        "MedUni-News 1.9.2025: Professur für Experimentelle Rheumatologie (§99(1)) seit Anfang August 2025; "
        "Listen-Datum 2015-08-01 ist Fülleffekt"),
}

# Bestandsdatensätze, deren Paragraf trotz Abweichung zur Liste bleibt
PARAGRAF_BEHALTEN = {
    ("Oskar Aszmann", 2021): "Wissensbilanz 2021 nennt ausdrücklich §99 Abs. 4, "
                             "Liste sagt §98 bei 'offener Call' (sonst immer §99(4))",
    ("Talin Barisani-Asenbauer", 2022): "Zeile widerspricht sich selbst: Denomination "
                                        "'Frauencall (§ 99 Abs. 4 UG)', Spalte '§ 98'; "
                                        "Wissensbilanz 2022 sagt §99(4)",
}

# Korrekturen aus eigener Nachrecherche zur Liste (Quelle jeweils genannt);
# 'felder' wird gesetzt, 'quelle' nur, wenn der Datensatz noch keine hat
EINZELKORREKTUREN = [
    {"name": "Stathis Megas", "year": 2025, "felder": {"art_berufung": "§99(5) Laufbahnstelle"},
     "quelle": "https://www.meduniwien.ac.at/web/en/ueber-uns/news/2025/news-in-december-2025/"
               "stathis-megas-takes-on-assistant-professorship-for-machine-learning-in-the-life-sciences/",
     "notiz": "Tenure-Track-Assistenzprofessur (§99 Abs. 5) laut MedUni-News 12/2025, "
              "nicht §99(4); fehlt in der Personalliste"},
    {"name": "Oliver Kimberger", "year": 2021,
     "felder": {"art_berufung": "§99(1)", "ofos_code": "302",
                "ofos_label": "Klinische Medizin (Anästhesie, perioperatives Informationsmanagement)",
                "_ofos_auto": None},
     "notiz": "MedUni-News 07/2026 zur Folgeprofessur: 2021 war eine §99(1)-Professur, "
              "nicht §98; die Personalliste führt nur die aktuelle Stelle (§99(4) ab 1.7.2026). "
              "ÖFOS von Hand: der Automat las 'Informationsmanagement' als Wirtschaftswissenschaft"},
    {"name": "Andreas Zuckermann", "year": 2025, "felder": {"art_berufung": "§99(1)"},
     "quelle": "https://www.meduniwien.ac.at/web/en/ueber-uns/news/2025/news-in-october-2025/"
               "andreas-zuckermann-takes-over-professorship-for-heart-transplantation/",
     "notiz": "§99(1) laut MedUni-News (Dienstantritt 1.10.2025, Antrittsvorlesung 24.10.2025); "
              "die Personalliste nennt 2024-01-01, der Widerspruch bleibt offen"},
]

# ÖFOS von Hand für neue Datensätze, bei denen die Stichwortregel nichts oder
# Falsches trifft ('Translational' → Sprachwissenschaft, 'Angiologie' → nichts)
OFOS_NEU = {
    ("Sabine Eichinger-Hasenauer", 2020): ("302", "Klinische Medizin (Hämatologie)"),
    ("Kathryn Hoffmann", 2023): ("302", "Klinische Medizin (Allgemeinmedizin, Primary Care)"),
    ("Roland Beisteiner", 2024): ("302", "Klinische Medizin (Neurologie)"),
    ("Sabine Steiner", 2024): ("302", "Klinische Medizin (Angiologie)"),
    ("Robert Kralovics", 2024): ("301", "Grundlagenmedizin (Translationale Hämatologie)"),
}

# Neue Datensätze: Paragraf laut Presseinformation, wo sie von der Liste abweicht
PRESSE_NEU = {
    ("Kathryn Hoffmann", 2023): ("§99(1)",
        "'hat mit 1. Februar 2023 die Professur für Primary Care Medicine (§99 (1))'"),
}
# Denomination der Liste ist nur 'Professur - Professorinnencall'
FACH_NACHGETRAGEN = {
    ("Sabine Eichinger-Hasenauer", 2020): (
        "Hämatologie und Hämostaseologie",
        "aus der Klinischen Abteilung für Hämatologie und Hämostaseologie (MedUni-Klinikseite)"),
}

# Neue Datensätze, die nicht allein aus der Liste folgen (Datum dort Fülleffekt
# oder Person schon mit früherer Stelle im Bestand), aber anderweitig belegt sind
ZUSAETZLICH = [
    {"name": "Roland Beisteiner", "year": 2024, "monat": "APRIL", "art_berufung": "§99(1)",
     "forschungsbereich": "Experimentelle Hirnstimulation (Stiftungsprofessur)",
     "aus_verworfen": True,
     "notiz": "Personalliste bestätigt Person und §99(1) (Stiftungsprofessur für experimentelle "
              "Hirnstimulation), ihr Datum 2015-08-01 ist Fülleffekt; Jahr/Monat aus der "
              "archivierten Presseinformation 2024-06-11 (Dienstantritt Anfang April 2024)"},
    {"name": "Oliver Kimberger", "year": 2026, "monat": "JULI", "art_berufung": "§99(4)",
     "forschungsbereich": "Anästhesie (perioperative Datenwissenschaft)", "geschlecht": "M",
     "herkunft": "intern", "herkunft_institution": "Medizinische Universität Wien",
     "herkunft_land": "Österreich",
     "quelle": "https://www.meduniwien.ac.at/web/en/about-us/news/2026/news-in-july-2026/"
               "oliver-kimberger-takes-up-a-professorship-in-the-field-of-anaesthesia/",
     "notiz": "Zweite Professur derselben Person: §99(4) im Fachbereich Anästhesie ab 1.7.2026 "
              "laut MedUni-News und Personalliste; die §99(1)-Professur 2021 bleibt als eigener "
              "Datensatz. Der Verwurf vom 2026-08-29 ('interne Rollenerweiterung') war falsch."},
]


def parse_datum(raw):
    """→ (jahr, monat_index 1-12, tag, fehler)"""
    s = raw.strip().removeprefix("ab ").strip()
    if not s:
        return None, None, None, "leer"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return int(m[1]), int(m[2]), int(m[3]), None
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{3,4})", s)
    if m and len(m[3]) == 4:
        return int(m[3]), int(m[2]), int(m[1]), None
    return None, None, None, f"unlesbar ({s})"


def parse_paragraf(raw):
    s = raw.replace("UG", "").replace("§", "").strip()
    for k, v in PARAGRAF.items():
        if s.startswith(k):
            return v
    raise ValueError(f"Paragraf unbekannt: {raw!r}")


def denomination(prof):
    t = re.sub(r"\s+", " ", prof).strip()
    t = re.sub(r"\s*-\s*(gem\. )?§ ?98( UG)?$", "", t)
    for muster in (r"^(offener Call|Frauencall \(§ 99 Abs\. 4 UG\))\s*-\s*Fachbereich\s*",
                   r"^Professur für den Fachbereich\s*", r"^Professur\s*-\s*Fachbereich\s*",
                   r"^Fachbereich\s*", r"^(Stiftungs|LBI-Stiftungs)?[Pp]rofess[ou]r (für )?",
                   r"^-\s*Professorinnencall$"):
        t = re.sub(muster, "", t)
    t = t.strip(' "„“')
    return t or None


def lies_liste():
    zeilen = list(csv.DictReader(LISTE.open(encoding="utf-8"), delimiter="\t"))
    rows = []
    for i, z in enumerate(zeilen):
        nach = " ".join("-".join(p.capitalize() for p in w.split("-"))
                        for w in z["nachname"].lower().split())
        name = f'{z["vorname"].strip()} {nach}'
        name = BESTANDSNAME.get(name, name)
        jahr, mon, tag, fehler = parse_datum(z["dienstantritt"])
        roh = z["dienstantritt"].strip()
        # Fülleffekt: gleiches Rohdatum in einer der zwei Zeilen darüber
        fuell = bool(roh) and any(zeilen[j]["dienstantritt"].strip() == roh
                                  for j in range(max(0, i - 2), i))
        rows.append({
            "zeile": i + 2, "name": name, "professur": z["professur"].strip(),
            "paragraf": parse_paragraf(z["paragraf"]), "roh": roh,
            "jahr": jahr, "monat": MONATE[mon - 1] if mon else None, "tag": tag,
            "fehler": "Fülleffekt" if fuell else fehler,
            "forschungsbereich": denomination(z["professur"]),
        })
    return rows


def lade_verworfen():
    """Runde-2-Datensätze, die wegen toter Links verworfen wurden; liefern
    Forschungsbereich, Herkunft, Geschlecht und Presse-Quelle."""
    out = {}
    for p in VERWORFEN:
        for e in json.loads(p.read_text()):
            out.setdefault(kurz(e["name"]), e)
    return out


def main():
    apply = "--apply" in sys.argv
    data = json.loads(DATA_PATH.read_text())
    alt = json.loads(VOR2019_PATH.read_text())
    bestand = [d for d in data + alt if d["universitat"] == "MedUni Wien"]
    nach_name = {}
    for d in bestand:
        nach_name.setdefault(kurz(d["name"]), []).append(d)
    verworfen = lade_verworfen()
    rows = lies_liste()

    bestaetigt, korrekturen, konflikte, neu, fuelleffekt, ohne_datum = [], [], [], [], [], []
    getroffen = set()

    for r in rows:
        treffer = nach_name.get(kurz(r["name"]), [])
        for t in treffer:
            getroffen.add(id(t))
        if r["fehler"] == "Fülleffekt":
            fuelleffekt.append(r)
        elif r["fehler"]:
            ohne_datum.append(r)

        gleiches_jahr = [t for t in treffer if r["jahr"] and t["year"] == r["jahr"]]
        if not treffer:
            if r["fehler"] or not (2019 <= r["jahr"] <= 2026):
                continue
            neu.append(r)
            continue
        if gleiches_jahr or (r["fehler"] and treffer):
            # Fülleffekt-Zeilen: Jahr unbrauchbar, Paragraf aber verwertbar.
            # Bei mehreren Datensätzen derselben Person (Aszmann 2020/2021) den
            # jüngsten nehmen, die Liste zeigt die aktuelle Stelle.
            t = gleiches_jahr[0] if gleiches_jahr else max(treffer, key=lambda x: x["year"])
            if t["year"] < 2019:
                continue
            aenderungen = []
            key = (t["name"], t["year"])
            if key in PRESSE:
                para, monat, url, zitat = PRESSE[key]
                if t.get("art_berufung") != para:
                    aenderungen.append(("art_berufung", t.get("art_berufung"), para))
                if t.get("monat") != monat:
                    aenderungen.append(("monat", t.get("monat"), monat))
                beleg = f"Presseinformation: {zitat}"
                if url and not t.get("quelle"):
                    aenderungen.append(("quelle", None, url))
            else:
                beleg = (f"Personalliste MedUni (Zeile {r['zeile']}, '{r['professur']}', "
                         f"{r['roh'] or 'ohne Datum'})")
                if t.get("art_berufung") != r["paragraf"] and key not in PARAGRAF_BEHALTEN:
                    aenderungen.append(("art_berufung", t.get("art_berufung"), r["paragraf"]))
                if not r["fehler"]:
                    abgeleitet = re.search(r"abgeleitet|Monat nicht|Monat .*unsicher",
                                           t.get("_kuratiert") or "")
                    if t.get("monat") != r["monat"] and (not t.get("monat") or abgeleitet):
                        aenderungen.append(("monat", t.get("monat"), r["monat"]))
            if aenderungen:
                korrekturen.append((t, r, aenderungen, beleg))
            else:
                bestaetigt.append((t, r))
            continue
        # Person bekannt, aber anderes Jahr: offener Widerspruch, keine Änderung
        # (außer die Person ist unten ausdrücklich behandelt)
        behandelt = {k["name"] for k in EINZELKORREKTUREN} | {z["name"] for z in ZUSAETZLICH}
        if r["name"] not in behandelt and (
                r["jahr"] and 2019 <= r["jahr"] <= 2026 or any(x["year"] >= 2019 for x in treffer)):
            konflikte.append((r, treffer))

    # ── Korrekturen am Bestand ──────────────────────────────────────────────
    for k in EINZELKORREKTUREN:
        t = next(d for d in data if d["name"] == k["name"] and d["year"] == k["year"])
        ae = [(f, t.get(f), v) for f, v in k["felder"].items() if t.get(f) != v]
        if not ae:
            continue
        if k.get("quelle") and not t.get("quelle"):
            ae.append(("quelle", None, k["quelle"]))
        korrekturen.append((t, {"zeile": "—", "professur": "", "roh": ""}, ae, k["notiz"]))
    STILL = ("quelle", "ofos_label", "_ofos_auto")
    for t, r, aenderungen, beleg in korrekturen:
        notiz = []
        for feld, von, nach in aenderungen:
            if feld not in STILL:
                notiz.append(f"{feld} {von or '—'} → {nach}")
            if apply:
                if nach is None:
                    t.pop(feld, None)
                else:
                    t[feld] = nach
        if apply:
            t["_kuratiert"] = ((t.get("_kuratiert") or "") +
                               f" | {HEUTE}: {'; '.join(notiz)}. {beleg}")

    # ── Neue Datensätze ─────────────────────────────────────────────────────
    ernte = []
    for r in neu:
        v = verworfen.get(kurz(r["name"]))
        e = {
            "name": r["name"], "universitat": "MedUni Wien",
            "monat": r["monat"], "year": r["jahr"], "art_berufung": r["paragraf"],
            "forschungsbereich": (v or {}).get("forschungsbereich") or r["forschungsbereich"],
            # die Antrittsvorlesungs-Sammelseite belegt nichts mehr, dann gilt die Liste
            "quelle": (v or {}).get("quelle") if v and "antrittsvorlesungen" not in v["quelle"]
                      else QUELLE,
            "stufe": 1,
        }
        for feld in ("geschlecht", "herkunft", "herkunft_institution", "herkunft_land",
                     "werdegang", "fakultat"):
            if v and v.get(feld):
                e[feld] = v[feld]
        kur = (f"Personalliste MedUni (Zeile {r['zeile']}): '{r['professur']}', "
               f"{r['paragraf']}, Dienstantritt {r['roh']}.")
        if v:
            kur += f" Deckt sich mit der 2026-08 verworfenen Recherche ({v['_kuratiert']})"
            kur += (f"; dort Jahr {v['year']} aus der Antrittsvorlesung, die Liste gilt."
                    if v["year"] != r["jahr"] else ".")
        elif r["paragraf"] == "§99(4)" and r["jahr"] == 2020 and r["monat"] == "DEZEMBER":
            kur += (" Nur Personalliste; Zeile ist Anker eines Datumsblocks (Folgezeilen "
                    "Fülleffekt), passt zur §99(4)-Professorinnencall-Welle 11–12/2020.")
        else:
            kur += " Nur Personalliste, keine Presseinformation gefunden."
        if (r["name"], r["jahr"]) in PRESSE_NEU:
            para, zitat = PRESSE_NEU[(r["name"], r["jahr"])]
            e["art_berufung"] = para
            kur += f" Paragraf aus der Presseinformation: {zitat}; Liste sagt {r['paragraf']}."
        if (r["name"], r["jahr"]) in FACH_NACHGETRAGEN:
            e["forschungsbereich"], woher = FACH_NACHGETRAGEN[(r["name"], r["jahr"])]
            kur += f" Forschungsbereich nicht in der Liste, {woher}."
        if (r["name"], r["jahr"]) in OFOS_NEU:
            e["ofos_code"], e["ofos_label"] = OFOS_NEU[(r["name"], r["jahr"])]
        e["_kuratiert"] = f"Handrecherche {HEUTE}: " + kur
        ernte.append(e)
    for z in ZUSAETZLICH:
        v = verworfen.get(kurz(z["name"])) if z.get("aus_verworfen") else None
        e = {"universitat": "MedUni Wien", "stufe": 1, "quelle": QUELLE}
        if v:
            e.update({k: v[k] for k in ("forschungsbereich", "herkunft", "herkunft_institution",
                                        "herkunft_land", "geschlecht", "quelle", "werdegang")
                      if v.get(k)})
        e.update({k: val for k, val in z.items() if k not in ("notiz", "aus_verworfen")})
        if (z["name"], z["year"]) in OFOS_NEU:
            e["ofos_code"], e["ofos_label"] = OFOS_NEU[(z["name"], z["year"])]
        e["_kuratiert"] = f"Handrecherche {HEUTE}: {z['notiz']}"
        ernte.append(e)
    ernte.sort(key=lambda d: (d["year"], d["name"]))
    OUT.write_text(json.dumps(ernte, ensure_ascii=False, indent=1) + "\n")

    # ── Bestand ohne Treffer in der Liste ───────────────────────────────────
    fehlend = sorted((d for d in data if d["universitat"] == "MedUni Wien"
                      and id(d) not in getroffen), key=lambda d: (d["year"], d["name"]))
    with (PRUEFUNG / "meduni_nicht_in_hr_liste.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["name", "year", "monat", "art_berufung", "forschungsbereich", "quelle"])
        for d in fehlend:
            w.writerow([d["name"], d["year"], d.get("monat") or "", d.get("art_berufung") or "",
                        d.get("forschungsbereich") or "", d.get("quelle") or ""])

    # ── Report ──────────────────────────────────────────────────────────────
    L = [f"# Abgleich MedUni Wien mit der Personalliste ({HEUTE})", "",
         f"Quelle: {QUELLE}. {len(rows)} Zeilen, davon {sum(1 for r in rows if r['jahr'] and r['jahr'] >= 2019)} "
         f"mit Dienstantritt ab 2019, {len(fuelleffekt)} mit Fülleffekt-Datum, {len(ohne_datum)} ohne lesbares Datum.", "",
         "| | Anzahl |", "|---|---|",
         f"| Bestand bestätigt (Jahr und Paragraf stimmen) | {len(bestaetigt)} |",
         f"| Bestand korrigiert (Paragraf oder Monat) | {len(korrekturen)} |",
         f"| Neue Datensätze 2019–2026 | {len(ernte)} |",
         f"| Offene Widersprüche (anderes Jahr) | {len(konflikte)} |",
         f"| Bestand 2019–2026 ohne Treffer in der Liste | {len(fehlend)} |", ""]
    L += ["## Korrekturen am Bestand", "", "| Person | Jahr | Änderung | Beleg |", "|---|---|---|---|"]
    for t, r, ae, beleg in korrekturen:
        L.append(f"| {t['name']} | {t['year']} | "
                 + "; ".join(f"{f} {v or '—'} → {n}" for f, v, n in ae if f not in STILL)
                 + f" | {beleg} |")
    L += ["", "## Neue Datensätze", "", "| Person | Jahr | Monat | § | Fach | Beleg |", "|---|---|---|---|---|---|"]
    for e in ernte:
        L.append(f"| {e['name']} | {e['year']} | {e.get('monat') or '—'} | {e['art_berufung']} | "
                 f"{e.get('forschungsbereich') or '—'} | {e['_kuratiert'][:160]}… |")
    L += ["", "## Offene Widersprüche (Bestand und Liste nennen verschiedene Jahre; keine Änderung)", "",
          "| Person | Bestand | Liste | Lesart |", "|---|---|---|---|"]
    for r, treffer in konflikte:
        b = "; ".join(f"{t['year']} {t.get('monat') or '—'} {t.get('art_berufung') or '—'}" for t in treffer)
        L.append(f"| {r['name']} | {b} | {r['roh']} {r['paragraf']} ({r['professur']}) | "
                 "Liste zeigt die aktuelle Stelle; Bestand belegt per Presseinformation einen "
                 "früheren Antritt. Möglich: spätere Umwandlung (wie Kimberger §99(1)→§99(4)). |")
    L += ["", "## Zeilen mit Fülleffekt-Datum (Datum nicht verwendet)", "",
          "| Zeile | Person | Rohdatum | § | Bestand |", "|---|---|---|---|---|"]
    for r in fuelleffekt:
        b = "; ".join(f"{t['year']}" for t in nach_name.get(kurz(r["name"]), [])) or "—"
        L.append(f"| {r['zeile']} | {r['name']} | {r['roh']} | {r['paragraf']} | {b} |")
    L += ["", "## Zeilen ohne lesbares Datum", ""]
    L += [f"* Zeile {r['zeile']}: {r['name']}, {r['paragraf']}, '{r['roh'] or 'leer'}'" for r in ohne_datum]
    L += ["", "## Bestand 2019–2026 ohne Treffer in der Liste", "",
          "Nicht gelöscht: die Liste führt nur aktive Professor:innen. Siehe meduni_nicht_in_hr_liste.csv.", ""]
    L += [f"* {d['year']} {d.get('monat') or '—'} {d.get('art_berufung') or '—'} {d['name']}" for d in fehlend]
    (PRUEFUNG / "meduni_hr_abgleich.md").write_text("\n".join(L) + "\n")

    if apply:
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"Liste: {len(rows)} Zeilen | bestätigt {len(bestaetigt)} | korrigiert {len(korrekturen)} | "
          f"neu {len(ernte)} | Widersprüche {len(konflikte)} | Fülleffekt {len(fuelleffekt)} | "
          f"ohne Treffer {len(fehlend)}")
    print(f"→ {OUT.relative_to(ROOT)}, pruefung/meduni_hr_abgleich.md, pruefung/meduni_nicht_in_hr_liste.csv"
          + ("" if apply else "  (--apply fehlt: Bestand unverändert)"))
    return ernte, korrekturen


if __name__ == "__main__":
    ernte, korrekturen = main()
    namen = [(e["name"], e["year"]) for e in ernte]
    assert len(namen) == len(set(namen)), "Dublette in der Ernte"
    assert all(2019 <= e["year"] <= 2026 and e["monat"] in MONATE for e in ernte)
    print("✓ Selbstcheck ok")
