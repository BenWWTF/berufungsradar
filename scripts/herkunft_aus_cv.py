#!/usr/bin/env python3
"""
Leitet Herkunft und Herkunftsland aus dem Lebenslauf ab (Stufe 3, automatisch).

Die Uni-Wien-Einträge aus dem Webarchiv bringen ihren Lebenslauf mit, chronologisch
und mit Jahreszahlen:

    2011-2015 Assistant Professor, University of Vienna ·
    2013 Habilitation in Operations Research, University of Vienna ·
    seit April 2015 Associate Professor, Department of Statistics …

Die letzte Station VOR dem Berufungsjahr ist die Herkunft. Liegt sie an der
berufenden Universität, ist die Berufung intern, sonst extern; das Land kommt
aus einer Ortsliste.

Sicherheitsregeln:
  * Nur Einträge ohne bestehende Herkunftsangabe werden angefasst.
  * Ist die Station nicht eindeutig zuzuordnen, bleibt das Feld leer und
    erscheint weiter im Lückenreport. Lieber eine Lücke als ein falsches Land.
  * Alles Abgeleitete trägt `_herkunft_auto: true`.

Läuft nach fill_gaps.py, vor build_html.py.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"

# Ortsnamen und Institutionen → Land. Reihenfolge: spezifisch vor allgemein.
LAENDER = [
    (r"universit(?:y|ät|é|à) of vienna|universität wien|univie|"
     r"vienna university|technische universität wien|tu wien|"
     r"medizinische universität wien|medical university of vienna|"
     r"wirtschaftsuniversität|boku|vetmeduni|akademie der bildenden|"
     r"universität für (?:musik|angewandte|bodenkultur)|"
     r"institute of science and technology austria|ist austria|ista|"
     r"cemm|imba|imp \(|gmi |oeaw|österreichische akademie der wissenschaften|"
     r"wien|vienna|austria|österreich|innsbruck|graz|salzburg|linz|klagenfurt|"
     r"krems|leoben", "Österreich"),
    (r"germany|deutschland|berlin|münchen|munich|hamburg|frankfurt|köln|cologne|"
     r"heidelberg|göttingen|tübingen|freiburg|dresden|leipzig|bonn|mainz|"
     r"stuttgart|karlsruhe|aachen|bielefeld|konstanz|jena|halle|potsdam|"
     r"max planck|helmholtz|charité|kit |lmu|tum|rwth", "Deutschland"),
    (r"switzerland|schweiz|zürich|zurich|basel|bern|lausanne|genève|geneva|"
     r"\\bepfl\\b|eth zürich|eth zurich|\\bethz?\\b", "Schweiz"),
    (r"united kingdom|england|scotland|great britain|london|oxford|cambridge|"
     r"edinburgh|manchester|bristol|glasgow|imperial college|ucl|"
     r"university of leeds|st andrews", "Großbritannien"),
    (r"united states|\\busa\\b|u\\.s\\.|harvard|stanford|massachusetts institute|"
     r"berkeley|yale|princeton|"
     r"columbia university|chicago|caltech|michigan|texas|boston|new york|"
     r"california|pennsylvania|cornell|johns hopkins|national institutes of health|"
     r"\\bucla\\b|\\bucsd\\b|"
     r"north carolina|wisconsin|illinois|minnesota|seattle|san diego", "USA"),
    (r"netherlands|niederlande|amsterdam|utrecht|leiden|delft|nijmegen|"
     r"groningen|rotterdam|wageningen|maastricht|eindhoven", "Niederlande"),
    (r"france|frankreich|paris|lyon|marseille|toulouse|grenoble|strasbourg|"
     r"bordeaux|montpellier|cnrs|inria|sorbonne", "Frankreich"),
    (r"italy|italien|rom|rome|milan|mailand|turin|bologna|padua|padova|pisa|"
     r"trieste|napoli|florence|firenze", "Italien"),
    (r"sweden|schweden|stockholm|uppsala|lund|göteborg|\\bkth\\b|karolinska", "Schweden"),
    (r"denmark|dänemark|copenhagen|kopenhagen|aarhus|odense|dtu", "Dänemark"),
    (r"norway|norwegen|oslo|bergen|trondheim|ntnu", "Norwegen"),
    (r"finland|finnland|helsinki|espoo|aalto|turku|tampere", "Finnland"),
    (r"belgium|belgien|leuven|louvain|brussels|brüssel|gent|ghent|antwerp", "Belgien"),
    (r"spain|spanien|madrid|barcelona|valencia|sevilla|granada|bilbao", "Spanien"),
    (r"portugal|lisbon|lissabon|porto|coimbra", "Portugal"),
    (r"poland|polen|warsaw|warschau|krakow|krakau|poznan|wroclaw", "Polen"),
    (r"czech|tschechien|prag|prague|brno|brünn", "Tschechien"),
    (r"hungary|ungarn|budapest|szeged|debrecen", "Ungarn"),
    (r"slovenia|slowenien|ljubljana|maribor", "Slowenien"),
    (r"slovakia|slowakei|bratislava|kosice", "Slowakei"),
    (r"canada|kanada|toronto|montreal|vancouver|ottawa|mcgill|"
     r"university of british columbia", "Kanada"),
    (r"australia|australien|sydney|melbourne|canberra|brisbane|perth", "Australien"),
    (r"japan|tokyo|tokio|kyoto|osaka|riken", "Japan"),
    (r"china|beijing|peking|shanghai|hong kong|tsinghua|shenzhen", "China"),
    (r"israel|jerusalem|tel aviv|haifa|weizmann|technion", "Israel"),
    (r"turkey|türkei|istanbul|ankara|izmir|metu|bogazici", "Türkei"),
    (r"ireland|irland|dublin|cork|galway", "Irland"),
    (r"greece|griechenland|athen|athens|thessaloniki|crete", "Griechenland"),
    (r"brazil|brasilien|sao paulo|rio de janeiro", "Brasilien"),
    (r"india|indien|delhi|mumbai|bangalore|chennai", "Indien"),
    (r"south korea|südkorea|seoul|kaist|pohang", "Südkorea"),
    (r"singapore|singapur|nanyang|national university of singapore", "Singapur"),
]

# Wiener Institutionen zur Intern/Extern-Unterscheidung
BERUFENDE = {
    "Uni Wien": r"universit(?:y|ät|é) of vienna|universität wien|univie|university of vienna",
    "TU Wien": r"tu wien|technische universität wien|vienna university of technology|tuw",
    "MedUni Wien": r"medizinische universität wien|medical university of vienna|meduni",
    "WU Wien": r"wirtschaftsuniversität|wu wien|vienna university of economics",
    "BOKU": r"boku|bodenkultur|natural resources and life sciences",
    "mdw": r"universität für musik|mdw|music and performing arts",
    "Angewandte": r"angewandte kunst|applied arts",
    "Akademie": r"akademie der bildenden künste|fine arts vienna",
    "Vetmeduni Wien": r"veterinärmedizinische|vetmeduni|veterinary medicine vienna",
}

# Eine Station im Lebenslauf: "2011-2015 Assistant Professor, University of Vienna"
STATION = re.compile(r"^(?:seit\s+\w+\s+)?(?P<von>(?:19|20)\d\d)"
                     r"(?:\s*[-–]\s*(?P<bis>(?:19|20)\d\d|heute))?\s+(?P<text>.{6,200})$")

# Stationen, die keine reguläre Anstellung beschreiben. Eine Gastprofessur oder
# ein Forschungsaufenthalt ist nicht die Herkunft, aus der jemand berufen wird.
KEINE_STATION = re.compile(
    r"habilitation|promotion|dissertation|sponsion|diplom|studium|"
    r"master|bachelor|magister|doktorat|\bphd\b|preis|award|stipendium|"
    r"fellowship|auszeichnung|venia|gastprofess|visiting|vertretung|"
    r"forschungsaufenthalt|lehrauftrag|mitglied|sprecher|herausgeber|"
    r"vortrag|kongress|ruf\b|elternzeit|karenz", re.I)

# Eine Herkunft braucht eine Einrichtung, nicht bloß eine Tätigkeitsbeschreibung
EINRICHTUNG = re.compile(
    r"universit|university|hochschule|college|institut|akademie|academy|"
    r"max planck|helmholtz|leibniz|fraunhofer|cnrs|inserm|inria|cemm|imba|"
    r"\bimp\b|oeaw|ista|epfl|\beth\b|\bkth\b|charité|klinik|hospital|"
    r"school|centre|center|zentrum|labor|laboratory|museum|bibliothek|"
    r"gmbh|\bag\b|company|unternehmen|ministerium|agency|behörde", re.I)


def land_aus(text):
    lower = text.lower()
    for muster, land in LAENDER:
        if re.search(muster, lower):
            return land
    return None


def stationen(werdegang):
    """Lebenslauf-Text → Liste (jahr, text), chronologisch."""
    if not werdegang:
        return []
    ergebnis = []
    for teil in re.split(r"\s+·\s+|\s*;\s*", werdegang):
        m = STATION.match(teil.strip())
        if not m:
            continue
        text = m.group("text").strip()
        if KEINE_STATION.search(text) or not EINRICHTUNG.search(text):
            continue
        ende = m.group("bis")
        jahr = int(ende) if (ende and ende.isdigit()) else int(m.group("von"))
        ergebnis.append((jahr, text))
    return sorted(ergebnis, key=lambda s: s[0])


def herkunft_fuer(d):
    """Letzte Station vor dem Berufungsjahr → (herkunft, institution, land)."""
    vorher = [s for s in stationen(d.get("werdegang")) if s[0] <= d["year"]]
    if not vorher:
        return None
    jahr, text = vorher[-1]

    # Das Land muss aus dem Einrichtungsteil kommen, nicht aus dem Fließtext:
    # "Professorin für Italienische Literatur" macht niemanden zur Italienerin.
    teile = [t.strip(" .;") for t in text.split(",") if t.strip()]
    einrichtungsteile = [t for t in teile if EINRICHTUNG.search(t)] or teile[-1:]
    einrichtung = ", ".join(einrichtungsteile[-2:])
    land = land_aus(einrichtung)
    if not land:
        return None

    muster = BERUFENDE.get(d["universitat"])
    intern = bool(muster and re.search(muster, einrichtung.lower()))
    if len(einrichtung) > 90:
        einrichtung = einrichtung[:90].rstrip() + "…"
    return ("intern" if intern else "extern"), einrichtung, land


def main():
    data = json.loads(DATA_PATH.read_text())
    gesetzt = uneindeutig = 0
    for d in data:
        if d.get("herkunft") or d.get("herkunft_land"):
            continue                       # kuratiert oder schon abgeleitet
        ergebnis = herkunft_fuer(d)
        if not ergebnis:
            if d.get("werdegang"):
                uneindeutig += 1
            continue
        d["herkunft"], d["herkunft_institution"], d["herkunft_land"] = ergebnis
        d["_herkunft_auto"] = True
        gesetzt += 1

    if "--dry" not in sys.argv:
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    offen = sum(1 for d in data if not d.get("herkunft_land"))
    print(f"✓ Herkunft abgeleitet: {gesetzt} | Lebenslauf vorhanden, aber nicht "
          f"eindeutig: {uneindeutig} | ohne Herkunftsland: {offen} von {len(data)}")
    return data


if __name__ == "__main__":
    data = main()
    # Selbstcheck an einem bekannten Fall: Bernhard Lamel war vor der Berufung
    # 2017 an der Universität Wien, das ist eine interne Berufung.
    probe = next((d for d in data if d["name"] == "Bernhard Lamel"), None)
    if probe and probe.get("_herkunft_auto"):
        assert probe["herkunft"] == "intern", probe
        assert probe["herkunft_land"] == "Österreich", probe
    assert all(d.get("herkunft") in (None, "intern", "extern") for d in data)
    # Kein Eintrag darf ein Land ohne Herkunftsart haben
    assert not [d for d in data if d.get("herkunft_land") and not d.get("herkunft")]
    print("✓ Selbstcheck ok")
