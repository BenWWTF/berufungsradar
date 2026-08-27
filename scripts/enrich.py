#!/usr/bin/env python3
"""
Berufungsradar enrichment pipeline.

Stages (run with --stage N):
  1. Sophie Thun year fix
  2. Geschlecht heuristic for unknown (25)
  3. ÖFOS 1-digit Bereich + 2-digit Hauptgruppe extension
  4. TU Wien E-code → faculty name reverse map
  5. Herkunft research (manual data, see herkunft_research.json)
  6. OpenAlex bio enrichment for 26 entries (uses cached results)
  7. Write enriched JSON

Run with --dry to preview changes.
"""

import json
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dashboard_data_2025.json"
RESEARCH = ROOT / "scripts" / "herkunft_research.json"
OPENALEX = ROOT / "scripts" / "openalex_research.json"


def load():
    with DATA.open() as f:
        return json.load(f)


def save(data):
    with DATA.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(data)} entries → {DATA}")


# ─────────────────────────────────────────────────────────────────
# ÖFOS 2012 — 1-digit Bereich + 2-digit Hauptgruppe
# ─────────────────────────────────────────────────────────────────
# Source: Statistik Austria, ÖFOS 2012 (3-stellige Gliederung)
# The 2-digit codes are an aggregation; the 1-digit codes the
# "Bereich" (super-category). ÖFOS 2012 itself uses 1-3 digit codes.
# We extend to add a 1-digit Bereich label and a 2-digit Hauptgruppe
# label as the "second level" requested by the user.
#
# Mapping rules:
#   - 1xx (Naturwissenschaften)          → Bereich 1
#   - 2xx (Technische Wissenschaften)   → Bereich 2
#   - 3xx (Medizin, Gesundheit)         → Bereich 3
#   - 4xx (Agrar, Vetmed)               → Bereich 4
#   - 5xx (Sozialwissenschaften)        → Bereich 5
#   - 6xx (Geisteswissenschaften)       → Bereich 6
#
# 2-digit Hauptgruppen (use the first 2 digits of the 3-digit code):
#   10  Mathematik, Naturwissenschaften  (101..106, 107, 109, 110)
#   20  Technische Wissenschaften       (201..207, ...)
#   30  Medizin                          (301..305, ...)
#   40  Agrarwissenschaften, Veterinär  (401..403, 404)
#   50  Sozialwissenschaften            (501..509, ...)
#   60  Geisteswissenschaften           (601..605, ...)

OFOS_BEREICH = {
    "1": "Naturwissenschaften",
    "2": "Technische Wissenschaften",
    "3": "Medizin, Gesundheitswissenschaften",
    "4": "Agrarwissenschaften, Veterinärmedizin",
    "5": "Sozialwissenschaften",
    "6": "Geisteswissenschaften",
}

OFOS_HAUPTGRUPPE = {
    "10": "Mathematik, Naturwissenschaften (Hauptgruppe)",
    "20": "Technische Wissenschaften (Hauptgruppe)",
    "30": "Medizin, Gesundheitswissenschaften (Hauptgruppe)",
    "40": "Agrarwissenschaften, Veterinärmedizin (Hauptgruppe)",
    "50": "Sozialwissenschaften (Hauptgruppe)",
    "60": "Geisteswissenschaften (Hauptgruppe)",
}


def ofos_extend(code: str) -> dict:
    """Return {bereich, bereich_code, hauptgruppe, hauptgruppe_code}."""
    if not code:
        return {
            "bereich": None,
            "bereich_code": None,
            "hauptgruppe": None,
            "hauptgruppe_code": None,
        }
    code = str(code)
    # 1-digit Bereich
    bcode = code[0]
    # 2-digit Hauptgruppe
    hcode = code[:2] if len(code) >= 2 else code
    return {
        "bereich_code": bcode,
        "bereich": OFOS_BEREICH.get(bcode, f"ÖFOS-Bereich {bcode}"),
        "hauptgruppe_code": hcode,
        "hauptgruppe": OFOS_HAUPTGRUPPE.get(hcode, f"ÖFOS-Hauptgruppe {hcode}"),
    }


# ─────────────────────────────────────────────────────────────────
# TU Wien E-code → Faculty name (reverse map)
# ─────────────────────────────────────────────────────────────────
# Source: TU Wien Organisatorische Struktur (https://www.tuwien.at)
# Stand: 2026 — Fakultäten sind in 2022 reorganisiert worden. Die hier
# verwendeten E-Codes sind die offiziellen Institutscodes der TU Wien
# (erscheinen z.B. in Telefonbüchern, E-Mail-Adressen, Gebäudenummern).

TUWIEN_ECODE = {
    # Fakultät für Mathematik und Geoinformation
    "E101": "Institut für Analysis und Scientific Computing",
    "E102": "Institut für Diskrete Mathematik und Geometrie",
    "E103": "Institut für Mathematik in Bauwesen und Naturwissenschaften",
    "E104": "Institut für Statistik und Wahrscheinlichkeitstheorie",
    "E105": "Institut für Geoinformation und Kartographie",
    # Fakultät für Physik
    "E134": "Institut für Angewandte Physik",
    "E135": "Institut für Festkörperphysik",
    "E136": "Institut für Photonik",
    "E137": "Institut für Theoretische Physik",
    "E138": "Institut für Kernphysik",
    "E141": "Atominstitut",
    # Fakultät für Technische Chemie
    "E163": "Institut für Angewandte Synthesechemie",
    "E164": "Institut für Chemische Technologien und Analytik",
    "E165": "Institut für Materialchemie",
    "E166": "Institut für Verfahrenstechnik, Umwelttechnik und technische Biowissenschaften",
    # Fakultät für Informatik
    "E183": "Institut für Logic and Computation",
    "E184": "Institut für Computer Engineering",
    "E185": "Institut für Information Systems Engineering",
    "E186": "Institut für Visual Computing & Human-Centered Technology",
    "E187": "Institut für Artificial Intelligence",
    "E188": "Institut für Data Science, Statistics and Probability",
    "E189": "Institut für Information Security",
    "E190": "Institut für Software Engineering (vorm. E185/2)",
    "E191": "Institut für Rechnergestützte Automation",
    "E192": "Institut für Computergraphik und Algorithmen",
    "E193": "Institut für Wissensbasierte Mathematische Systeme",
    # Fakultät für Bauingenieurwesen (E200)
    "E201": "Institut für Geotechnik",
    "E202": "Institut für Konstruktiven Ingenieurbau",
    "E203": "Institut für Baustatik",
    "E204": "Institut für Betonbau",
    "E205": "Institut für Stahlbau",
    "E206": "Institut für Hochbau und Bauphysik",
    "E207": "Institut für Verkehrswissenschaften",
    "E208": "Institut für Raumplanung (TU)",
    "E210": "Institut für Wasserbau und Ingenieurhydrologie",
    "E211": "Institut für Wassergüte und Ressourcenmanagement",
    "E212": "Institut für Geodäsie und Geoinformation",
    "E220": "Institut für Geotechnik (Forschungsbereich Bodendynamik)",
    "E226": "Institut für Wassergüte und Ressourcenmanagement",
    "E230": "Institut für Verkehrswissenschaften (Forschungsbereich Verkehrswegbau)",
    # Fakultät für Architektur und Raumplanung (E250)
    "E251": "Institut für Architektur und Entwerfen",
    "E252": "Institut für Kunst und Gestaltung",
    "E253": "Institut für Städtebau und Landschaftsarchitektur",
    "E259": "Institut für Architekturwissenschaften",
    "E260": "Institut für Raumplanung (Architektur-Fakultät)",
    "E264": "Institut für Wohnbauten und Entwerfen",
    "E266": "Institut für Gebäudelehre und Entwerfen",
    "E267": "Institut für Denkmalpflege und Bauen im Bestand",
    "E270": "Institut für Energiewesen und nachhaltige Gebäude",
    "E275": "Institut für Interdisziplinäres Bauprozessmanagement",
    "E280": "Institut für Soziologie (Raumplanung)",
    # Fakultät für Maschinenwesen und Betriebswissenschaften (E300)
    "E301": "Institut für Maschinenbau- und Betriebsinformatik",
    "E302": "Institut für Mechanik und Mechatronik",
    "E303": "Institut für Konstruktionslehre und Maschinenelemente",
    "E304": "Institut für Leichtbau und Struktur-Biomechanik",
    "E305": "Institut für Werkstoffwissenschaft und Werkstofftechnologie",
    "E306": "Institut für Fertigungstechnik und Photonische Technologien",
    "E307": "Institut für Managementwissenschaften",
    "E308": "Institut für Energietechnik und Thermodynamik",
    "E310": "Institut für Automatisierungs- und Regelungstechnik",
    "E311": "Institut für Mechanik (E311)",
    "E315": "Institut für Strömungsmechanik und Wärmeübertragung",
    "E317": "Institut für Verbrennungskraftmaschinen und Thermodynamik",
    # Fakultät für Elektrotechnik und Informationstechnik (E350)
    "E354": "Institut für Automatisierungs- und Regelungstechnik (ETIT)",
    "E356": "Institut für Computertechnik",
    "E360": "Institut für Energiesysteme und elektrische Antriebe",
    "E362": "Institut für Elektrische Anlagen und Netze",
    "E366": "Institut für Elektrodynamik, Mikrowellen- und Schaltungstechnik",
    "E370": "Institut für Festkörperelektronik",
    "E373": "Institut für Halbleiter- und Festkörperphysik",
    "E376": "Institut für Signalverarbeitung und Sprachkommunikation",
    "E384": "Institut für Telekommunikation",
    "E389": "Institut für Nachrichtentechnik und Hochfrequenztechnik",
}


# ─────────────────────────────────────────────────────────────────
# Geschlecht inference by first name
# ─────────────────────────────────────────────────────────────────
# Curated from real 2025/2026 Berufungsradar data. First names only —
# academic titles (Univ.Prof., Dr., etc.) are stripped first.

NAME_GENDER = {
    # Ergänzt für den Backfill 2019–2026 (TU Wien)
    "albana": "W",
    "amela": "W",
    "angelika": "W",
    "ariane": "W",
    "azra": "W",
    "bojana": "W",
    "dongheui": "W",
    "ekaterina": "W",
    "emanuela": "W",
    "golta": "W",
    "heike": "W",
    "iva": "W",
    "ivona": "W",
    "jessica": "W",
    "katja": "W",
    "maricruz": "W",
    "raquel": "W",
    "susann": "W",
    "aaron": "M",
    "adrian": "M",
    "aleix": "M",
    "aleksandr": "M",
    "allan": "M",
    "amalio": "M",
    "emanuel": "M",
    "erwin": "M",
    "ezio": "M",
    "fabio": "M",
    "fazel": "M",
    "gareth": "M",
    "georg": "M",
    "gerald": "M",
    "guenther": "M",
    "günther": "M",
    "hannes": "M",
    "henderik": "M",
    "hinrich": "M",
    "ivan": "M",
    "juri": "M",
    "lado": "M",
    "marcin": "M",
    "nawid": "M",
    "nysret": "M",
    "pawel": "M",
    "paweł": "M",
    "pier": "M",
    "spasoje": "M",
    "stavros": "M",
    "uwe": "M",
    "victor": "M",
    "viktor": "M",
    "walter": "M",
    "wouter": "M",
    "yury": "M",
    # Female
    "elena": "W",
    "elena-maria": "W",
    "elisabeth": "W",
    "eva": "W",
    "franziska": "W",
    "friederike": "W",
    "katharina": "W",
    "kathrin": "W",
    "constanza": "W",
    "sabine": "W",
    "susanne": "W",
    "nina": "W",
    "manuela": "W",
    "angela": "W",
    "elisa": "W",
    "olga": "W",
    "christine": "W",
    "tülay": "W",
    "sophie": "W",
    "julia": "W",
    "svetlana": "W",
    "yan": "W",
    "anthea": "W",
    "lena": "W",
    "mélanie": "W",
    "melanie": "W",
    "sonja": "W",
    "hannah": "W",
    "verena": "W",
    "sandra": "W",
    "maria": "W",
    "marie": "W",
    "marie christine": "W",
    "monika": "W",
    "nicole": "W",
    "sarah": "W",
    "stefanie": "W",
    "stefani": "W",
    "birgit": "W",
    "daniela": "W",
    "katrin": "W",
    "irmgard": "W",
    "andrea": "W",
    "antje": "W",
    "antonia": "W",
    "claudia": "W",
    "doris": "W",
    "eva-maria": "W",
    "gabriele": "W",
    "helga": "W",
    "isabel": "W",
    "judith": "W",
    "kirsten": "W",
    "lisa": "W",
    "margit": "W",
    "petra": "W",
    "renate": "W",
    "silke": "W",
    "ulrike": "W",
    "ute": "W",
    "yvonne": "W",
    "jana": "W",
    "paula": "W",
    "mia": "W",
    "rosa": "W",
    "anna": "W",
    "anne": "W",
    "anke": "W",
    "antje-marie": "W",
    "astrid": "W",
    "barbara": "W",
    "beate": "W",
    "beatrice": "W",
    "bettina": "W",
    "brigitte": "W",
    "carolin": "W",
    "caroline": "W",
    "charlotte": "W",
    "christiane": "W",
    "cornelia": "W",
    "diana": "W",
    "dragana": "W",
    "dragica": "W",
    "dubravka": "W",
    "dagmar": "W",
    "dorothea": "W",
    "edith": "W",
    "elfriede": "W",
    "elisabetha": "W",
    "else": "W",
    "emily": "W",
    "emma": "W",
    "erika": "W",
    "esther": "W",
    "evelyn": "W",
    "frieda": "W",
    "gerda": "W",
    "gertraud": "W",
    "gisela": "W",
    "gudrun": "W",
    "hanna": "W",
    "hannelore": "W",
    "hilde": "W",
    "ilse": "W",
    "inge": "W",
    "ingeborg": "W",
    "irene": "W",
    "isolde": "W",
    "johanna": "W",
    "josefine": "W",
    "karin": "W",
    "karla": "W",
    "kathleen": "W",
    "kristina": "W",
    "laura": "W",
    "leonie": "W",
    "liane": "W",
    "lieselotte": "W",
    "linda": "W",
    "lotte": "W",
    "louise": "W",
    "magdalena": "W",
    "maja": "W",
    "margarete": "W",
    "margaretha": "W",
    "margit": "W",
    "marianne": "W",
    "marita": "W",
    "martina": "W",
    "michaela": "W",
    "miriam": "W",
    "natalie": "W",
    "nora": "W",
    "ottilie": "W",
    "patricia": "W",
    "pauline": "W",
    "pia": "W",
    "ramona": "W",
    "rebekka": "W",
    "regina": "W",
    "reingard": "W",
    "renate": "W",
    "romana": "W",
    "ruth": "W",
    "sabrina": "W",
    "saskia": "W",
    "sieglinde": "W",
    "simone": "W",
    "sophia": "W",
    "stella": "W",
    "stephanie": "W",
    "susi": "W",
    "sylvia": "W",
    "tamara": "W",
    "tanja": "W",
    "teresa": "W",
    "theresa": "W",
    "ursula": "W",
    "uta": "W",
    "vanessa": "W",
    "veronika": "W",
    "walburga": "W",
    "wera": "W",
    "wiltrud": "W",
    "yvonne": "W",
    "zoe": "W",
    "zoë": "W",
    # Male
    "abdelmalek": "M",
    "ahmed": "M",
    "alessandro": "M",
    "alexander": "M",
    "amir": "M",
    "ari": "M",
    "assaf": "M",
    "avi": "M",
    "alfred": "M",
    "ali": "M",
    "andreas": "M",
    "anton": "M",
    "antonio": "M",
    "arnold": "M",
    "armin": "M",
    "arnulf": "M",
    "arthur": "M",
    "attila": "M",
    "aydin": "M",
    "aykut": "M",
    "balazs": "M",
    "barnabás": "M",
    "barnabas": "M",
    "bastian": "M",
    "benedikt": "M",
    "benjamin": "M",
    "bernd": "M",
    "bernhard": "M",
    "bjoern": "M",
    "björn": "M",
    "boris": "M",
    "bruno": "M",
    "burkhard": "M",
    "carl": "M",
    "carlos": "M",
    "carsten": "M",
    "christian": "M",
    "christoph": "M",
    "claudio": "M",
    "clemens": "M",
    "constantin": "M",
    "cornelius": "M",
    "cristian": "M",
    "damian": "M",
    "daniel": "M",
    "david": "M",
    "dennis": "M",
    "derek": "M",
    "dieter": "M",
    "dietmar": "M",
    "dirk": "M",
    "dominik": "M",
    "eckhard": "M",
    "eduard": "M",
    "egon": "M",
    "elias": "M",
    "emmerich": "M",
    "erhard": "M",
    "eric": "M",
    "erich": "M",
    "erik": "M",
    "ernst": "M",
    "ernst-josef": "M",
    "eugen": "M",
    "falk": "M",
    "federico": "M",
    "felix": "M",
    "ferdinand": "M",
    "florian": "M",
    "francesco": "M",
    "frank": "M",
    "franz": "M",
    "franz-josef": "M",
    "fred": "M",
    "frederik": "M",
    "fritz": "M",
    "gabriel": "M",
    "gernot": "M",
    "gert": "M",
    "gottfried": "M",
    "günter": "M",
    "gunter": "M",
    "guenther": "M",
    "gunther": "M",
    "hans": "M",
    "hans-jürgen": "M",
    "hans-peter": "M",
    "harald": "M",
    "harry": "M",
    "hartmut": "M",
    "helmut": "M",
    "henning": "M",
    "henri": "M",
    "henrik": "M",
    "henry": "M",
    "herbert": "M",
    "hermann": "M",
    "holger": "M",
    "horst": "M",
    "hubert": "M",
    "hugo": "M",
    "ingo": "M",
    "ingomar": "M",
    "jakob": "M",
    "james": "M",
    "jan": "M",
    "jens": "M",
    "joachim": "M",
    "jochen": "M",
    "johann": "M",
    "johannes": "M",
    "john": "M",
    "jonas": "M",
    "jorge": "M",
    "jose": "M",
    "josef": "M",
    "joseph": "M",
    "juan": "M",
    "julius": "M",
    "jürgen": "M",
    "juergen": "M",
    "karl": "M",
    "karl-heinz": "M",
    "karl-friedrich": "M",
    "kasper": "M",
    "kay": "M",
    "kazimierz": "M",
    "kenneth": "M",
    "kevin": "M",
    "klemens": "M",
    "klaus": "M",
    "konrad": "M",
    "kurt": "M",
    "leon": "M",
    "leopold": "M",
    "lothar": "M",
    "louis": "M",
    "lucas": "M",
    "ludwig": "M",
    "luigi": "M",
    "lukas": "M",
    "magnus": "M",
    "manfred": "M",
    "manuel": "M",
    "marc": "M",
    "marco": "M",
    "marcus": "M",
    "mario": "M",
    "marius": "M",
    "mark": "M",
    "marko": "M",
    "markus": "M",
    "marlon": "M",
    "marten": "M",
    "martin": "M",
    "matthew": "M",
    "matthias": "M",
    "maurice": "M",
    "max": "M",
    "maximilian": "M",
    "michael": "M",
    "michel": "M",
    "michele": "M",
    "miguel": "M",
    "mikael": "M",
    "mike": "M",
    "milan": "M",
    "moritz": "M",
    "nico": "M",
    "nicolas": "M",
    "niklas": "M",
    "nikolaus": "M",
    "noah": "M",
    "norbert": "M",
    "olaf": "M",
    "oliver": "M",
    "olivier": "M",
    "oscar": "M",
    "oskar": "M",
    "osman": "M",
    "oswald": "M",
    "otto": "M",
    "patrick": "M",
    "paul": "M",
    "pavel": "M",
    "peter": "M",
    "philipp": "M",
    "philippe": "M",
    "rafael": "M",
    "rainer": "M",
    "ramin": "M",
    "raphael": "M",
    "reinhard": "M",
    "reinhold": "M",
    "remy": "M",
    "rené": "M",
    "rene": "M",
    "richard": "M",
    "robert": "M",
    "roberto": "M",
    "robin": "M",
    "rodney": "M",
    "roger": "M",
    "roland": "M",
    "roman": "M",
    "ronald": "M",
    "rüdiger": "M",
    "rudolf": "M",
    "sebastian": "M",
    "sergej": "M",
    "siegfried": "M",
    "sigurd": "M",
    "silvio": "M",
    "simon": "M",
    "stanislaus": "M",
    "stefan": "M",
    "stephan": "M",
    "steve": "M",
    "steven": "M",
    "sven": "M",
    "thaddäus": "M",
    "theo": "M",
    "theodor": "M",
    "thomas": "M",
    "tibor": "M",
    "tilo": "M",
    "tim": "M",
    "titus": "M",
    "tobias": "M",
    "tomas": "M",
    "torsten": "M",
    "udo": "M",
    "ulrich": "M",
    "ulv": "M",
    "urban": "M",
    "vitus": "M",
    "volker": "M",
    "werner": "M",
    "wieland": "M",
    "wilfried": "M",
    "willi": "M",
    "william": "M",
    "willibald": "M",
    "wim": "M",
    "winfried": "M",
    "wladimir": "M",
    "wolf": "M",
    "wolfgang": "M",
    "xaver": "M",
    "yannick": "M",
    "yannik": "M",
    "yariv": "M",
    "yunus": "M",
    "zekirija": "M",
    "zekir": "M",
    "zlatko": "M",
}


def infer_geschlecht(name: str) -> str | None:
    """Heuristic: pick the first token of the first word, lowercase."""
    if not name:
        return None
    # strip titles
    n = re.sub(
        r"^(Univ\.?\s*Prof\.?|Prof\.?|Dr\.?|Mag\.?|DI|Ing\.?|Assoc\.?\s*Prof\.?)\s+",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    first = n.split()[0].lower() if n else ""
    return NAME_GENDER.get(first)


# ─────────────────────────────────────────────────────────────────
# Stages
# ─────────────────────────────────────────────────────────────────
def stage1_sophie_thun(data, dry=False):
    """Sophie Thun has bio 'Mit 1. Jänner 2026 berufen' but year=2025.
    The Berufung is officially 2026, so move her to year=2026.
    """
    changes = []
    for d in data:
        if (
            "thun" in d.get("name", "").lower()
            and "sophie" in d.get("name", "").lower()
        ):
            if d.get("year") == 2025:
                d["year"] = 2026
                d["monat"] = "JÄNNER"
                d["berufung_effektiv"] = "2026-01-01"
                d["_note"] = "Berufung mit Wirksamkeit 1.1.2026, Berufungsjahr ist 2026"
                changes.append(d["name"])
    return changes


def stage2_geschlecht(data, dry=False):
    """Heuristic: 25 unknown → infer from first name."""
    changes = []
    for d in data:
        if d.get("geschlecht") in (None, "", "unbekannt"):
            g = infer_geschlecht(d.get("name", ""))
            if g:
                d["geschlecht"] = g
                d["_geschlecht_inferred"] = True
                d["_note"] = (
                    d.get("_note", "") + f" Geschlecht aus Vorname inferiert ({g})."
                )
                changes.append(f"{d['name']} → {g}")
    return changes


def stage3_ofos(data, dry=False):
    """Add 1-digit Bereich and 2-digit Hauptgruppe."""
    n = 0
    for d in data:
        ext = ofos_extend(d.get("ofos_code"))
        d["ofos_bereich_code"] = ext["bereich_code"]
        d["ofos_bereich"] = ext["bereich"]
        d["ofos_hauptgruppe_code"] = ext["hauptgruppe_code"]
        d["ofos_hauptgruppe"] = ext["hauptgruppe"]
        n += 1
    return n


def stage4_ecode(data, dry=False):
    """TU Wien E-code → faculty name. Reverse map for 28 TU Wien entries."""
    n = 0
    for d in data:
        if d.get("universitat") == "TU Wien" and d.get("fakultat_code"):
            c = str(d["fakultat_code"])
            faculty = TUWIEN_ECODE.get(c)
            if faculty:
                d["fakultat_institut"] = faculty
                n += 1
            else:
                d["fakultat_institut"] = None
        else:
            d["fakultat_institut"] = None
    return n


def stage5_herkunft(data, dry=False):
    """Apply manually-researched herkunft data for unknown entries."""
    if not RESEARCH.exists():
        return []
    with RESEARCH.open() as f:
        research = json.load(f)
    changes = []
    for d in data:
        key = d["name"]
        if key not in research:
            continue
        if d.get("herkunft") in (None, "unbekannt", "—") or not d.get(
            "herkunft_institution"
        ):
            r = research[key]
            old_hk = d.get("herkunft")
            d["herkunft"] = r.get("herkunft", d["herkunft"])
            d["herkunft_institution"] = r.get("herkunft_institution")
            d["herkunft_land"] = r.get("herkunft_land")
            d["_herkunft_research"] = r.get("source", "")
            changes.append(
                f"{key}: {old_hk!r} → {r.get('herkunft')!r} | {r.get('herkunft_institution')}, {r.get('herkunft_land')}"
            )
    return changes


def stage6_openalex(data, dry=False):
    """Apply manually-collected OpenAlex data for entries without bio_text."""
    if not OPENALEX.exists():
        return []
    with OPENALEX.open() as f:
        oa = json.load(f)
    changes = []
    for d in data:
        if d.get("name") not in oa:
            continue
        r = oa[d["name"]]
        # Always record OpenAlex metadata
        d["_openalex"] = {
            "works_count": r.get("works_count"),
            "cited_by_count": r.get("cited_by_count"),
            "h_index": r.get("h_index"),
            "last_known_institutions": r.get("last_known_institutions", []),
            "openalex_id": r.get("openalex_id"),
        }
        # Add bio_text if missing
        if not d.get("bio_text") and r.get("bio_text"):
            d["bio_text"] = r.get("bio_text")
        # Apply herkunft if unknown or institution missing.
        # Fail-safe: low-confidence Treffer (Namensvetter) nie mergen;
        # bestehendes herkunft nie umstoßen, nur fehlende Institution ergänzen.
        # Ausnahme: 'verified' (manuell recherchierter Override) ist maßgeblich.
        hk = r.get("herkunft")
        if hk in ("unbekannt", "—"):
            hk = None
        conf = r.get("match_confidence")
        if conf == "low":
            continue
        existing = d.get("herkunft")
        if r.get("herkunft_verified") and hk:
            d["herkunft"] = hk
            d["herkunft_institution"] = r.get("herkunft_institution")
            d["herkunft_land"] = r.get("herkunft_land")
        elif existing in (None, "unbekannt", "—") and hk:
            d["herkunft"] = hk
            d["herkunft_institution"] = r.get("herkunft_institution")
            d["herkunft_land"] = r.get("herkunft_land")
        elif not d.get("herkunft_institution") and hk == existing:
            d["herkunft_institution"] = r.get("herkunft_institution")
            if not d.get("herkunft_land"):
                d["herkunft_land"] = r.get("herkunft_land")
            changes.append(
                f"{d['name']}: → {hk} | {r.get('herkunft_institution')}, {r.get('herkunft_land')}"
            )
    return changes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int, default=0, help="0 = all")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--report", action="store_true", help="just report, no write")
    args = p.parse_args()

    data = load()
    print(f"Loaded {len(data)} entries")
    print()

    if args.stage in (0, 1):
        changes = stage1_sophie_thun(data, args.dry)
        print(f"[1] Sophie Thun fix: {len(changes)} entries → {changes}")
    if args.stage in (0, 2):
        changes = stage2_geschlecht(data, args.dry)
        print(f"[2] Geschlecht inferred: {len(changes)} entries")
        for c in changes:
            print(f"    {c}")
    if args.stage in (0, 3):
        n = stage3_ofos(data, args.dry)
        print(f"[3] ÖFOS Bereich/Hauptgruppe: {n} entries")
    if args.stage in (0, 4):
        n = stage4_ecode(data, args.dry)
        print(f"[4] TU Wien E-code → Institut: {n} entries mapped")
    if args.stage in (0, 5):
        changes = stage5_herkunft(data, args.dry)
        print(f"[5] Herkunft research: {len(changes)} entries")
        for c in changes:
            print(f"    {c}")
    if args.stage in (0, 6):
        changes = stage6_openalex(data, args.dry)
        print(f"[6] OpenAlex enrichment: {len(changes)} entries")
        for c in changes:
            print(f"    {c}")

    if args.report:
        return

    if not args.dry:
        save(data)


if __name__ == "__main__":
    main()
