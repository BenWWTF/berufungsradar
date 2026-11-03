#!/usr/bin/env python3
"""
Stufe 2 der Fachprofile: Publikationsrohdaten je Person zu einem Profil
verdichten und nach fachprofile.json schreiben (wird vom Dashboard-Tab
"Fachprofile" nachgeladen, nicht in index.html eingebettet).

Je Person (openalex_id):
  sub    OpenAlex-Subfelder mit Anzahl Arbeiten (primäres Topic je Arbeit)
  field  OpenAlex-Felder, dito
  top    OpenAlex-Topics, dito
  kw     OpenAlex-Keywords mit Anzahl Arbeiten
  terms  gewichtete Begriffe aus Titeln, Abstracts, Topics und Keywords:
         TF-IDF über Personen als Dokumente, Ein- und Zweiwortbegriffe,
         Gewicht je Begriff = (Anteil der Arbeiten, die ihn nennen) × IDF.

Warum Personen als Dokumente: die Frage lautet "wer arbeitet woran", nicht
"welche Arbeit passt". Ein Begriff zählt je Arbeit höchstens einmal, damit
ein langer Abstract das Profil nicht dominiert. IDF bestraft Allerwelts-
begriffe ("results", "study", "wien"), ohne sie per Hand listen zu müssen.

Die Textvektoren (semantische Suche) erzeugt fachprofil_embed.mjs aus
denselben Rohdaten, weil Browser und Build dasselbe Modell nutzen müssen.

Aufruf: python3 scripts/fachprofil.py
"""

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
CACHE = Path(__file__).resolve().parent / ".fachprofil_cache"
OUT = ROOT / "fachprofile.json"

TOP_SUB, TOP_FIELD, TOP_TOPIC, TOP_KW, TOP_TERMS = 8, 4, 10, 20, 80
MIN_WERKE = 3  # darunter ist ein Profil Rauschen

# Funktionswörter EN/DE plus Wissenschaftsfloskeln, die in jedem Abstract stehen.
STOP = set("""
a an the and or of in on at to for from by with without within into onto as is are was
were be been being this that these those it its we our us they their them he she his her
which who whom whose what when where why how not no nor but if then than so such very
can could may might shall should will would do does did done has have had having also
between among about above below over under up down out off again further here there all
any both each few more most other some own same only too s t just don now
der die das des dem den ein eine einer eines einem einen und oder nicht von zu mit für
auf in im am an aus bei nach über unter vor durch gegen ohne um bis als wie ist sind war
waren wird werden wurde wurden hat haben hatte hatten kann können sich auch noch nur
sowie bzw dass daß dieser diese dieses diesen zwischen während wegen trotz
study studies results result based using use used approach approaches method methods
paper article data analysis analyses show shows shown showed propose proposed present
presented presents provide provides novel new two three one first second however thus
therefore moreover furthermore well high higher low lower large small different
significant significantly important role effect effects model models system systems
case cases work works research findings finding evidence aim aims objective objectives
background conclusion conclusions introduction methodology framework problem problems
performance potential development process processes level levels number total
abstract university vienna austria wien austrian institute department
""".split())

# OpenAlex-Arbeitstypen ohne Fachinhalt
TYPEN_RAUS = {"paratext", "erratum", "retraction", "editorial", "letter", "peer-review"}


def tokens(text):
    """Kleinbuchstaben, Diakritika weg, Wörter ab 3 Zeichen, keine reinen Zahlen."""
    if not text:
        return []
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"<[^>]+>", " ", t)  # OpenAlex-Abstracts enthalten gelegentlich HTML
    return [w for w in re.findall(r"[a-z][a-z0-9\-]{2,}", t)
            if w not in STOP and not re.fullmatch(r"[\d\-]+", w)]


def gramme(text):
    """Ein- und Zweiwortbegriffe; Bigramme nur über benachbarte Inhaltswörter."""
    roh = tokens(text)
    out = set(roh)
    for a, b in zip(roh, roh[1:]):
        out.add(f"{a} {b}")
    return out


def lade_profile():
    data = json.loads(DATA_PATH.read_text())
    ids = sorted({d["openalex_id"] for d in data if d.get("openalex_id")})
    roh = {}
    for aid in ids:
        f = CACHE / f"{aid}.json"
        if f.exists():
            w = [x for x in json.loads(f.read_text())["werke"]
                 if x.get("typ") not in TYPEN_RAUS and x.get("titel")]
            if len(w) >= MIN_WERKE:
                roh[aid] = w
    print(f"{len(ids)} Personen mit OpenAlex-ID, {len(roh)} mit mindestens {MIN_WERKE} Arbeiten im Cache")
    return roh


def main():
    roh = lade_profile()

    # Pass 1: Begriffsmengen je Person (für IDF)
    begriffe_pro_person = {}
    df = Counter()
    for aid, werke in roh.items():
        zaehler = Counter()
        for w in werke:
            menge = gramme(w["titel"])
            if w.get("abstract"):
                menge |= gramme(w["abstract"][:2500])
            # Topics und Keywords als kuratierte Begriffe mitzählen
            for t in w["topics"][:1]:
                menge |= gramme(t["name"]) | gramme(t["subfield"])
            for k in w["keywords"]:
                menge |= gramme(k["name"])
            zaehler.update(menge)
        begriffe_pro_person[aid] = zaehler
        df.update(zaehler.keys())

    n_pers = len(roh)
    idf = {g: math.log(n_pers / c) for g, c in df.items()}

    subfeld_meta = {}
    profile = {}
    for aid, werke in roh.items():
        n = len(werke)
        sub, field, top, kw = Counter(), Counter(), Counter(), Counter()
        for w in werke:
            if w["topics"]:
                t = w["topics"][0]  # primäres Topic
                sub[t["subfield"]] += 1
                field[t["field"]] += 1
                top[t["name"]] += 1
                subfeld_meta.setdefault(t["subfield"], {"field": t["field"], "domain": t["domain"]})
            for k in {k["name"].lower() for k in w["keywords"]}:
                kw[k] += 1

        zaehler = begriffe_pro_person[aid]
        gewichte = []
        for g, c in zaehler.items():
            if df[g] < 2 and " " not in g:
                continue  # Einwort-Unikate sind meist Tippfehler oder Eigennamen
            if c < 2 and n >= 10:
                continue  # einmal erwähnt ist kein Schwerpunkt
            gewichte.append((g, (c / n) * idf[g]))
        gewichte.sort(key=lambda x: -x[1])
        gewichte = gewichte[:TOP_TERMS]
        maxw = gewichte[0][1] if gewichte else 1.0

        jahre = [w["jahr"] for w in werke if w.get("jahr")]
        profile[aid] = {
            "n": n,
            "ab": sum(1 for w in werke if w.get("abstract")),
            "jahre": [min(jahre), max(jahre)] if jahre else None,
            "sub": sub.most_common(TOP_SUB),
            "field": field.most_common(TOP_FIELD),
            "top": top.most_common(TOP_TOPIC),
            "kw": kw.most_common(TOP_KW),
            "terms": [[g, round(wt / maxw, 3)] for g, wt in gewichte],
        }

    OUT.write_text(json.dumps({
        "stand": __import__("datetime").date.today().isoformat(),
        "quelle": "OpenAlex: je Person bis 100 meistzitierte und 40 jüngste Arbeiten seit 2005",
        "subfelder": subfeld_meta,
        "personen": profile,
    }, ensure_ascii=False, separators=(",", ":")) + "\n")

    groesse = OUT.stat().st_size / 1e6
    print(f"✓ {len(profile)} Profile → {OUT.name} ({groesse:.1f} MB), {len(subfeld_meta)} Subfelder")
    sub_gesamt = Counter()
    for p in profile.values():
        for s, c in p["sub"][:2]:
            sub_gesamt[s] += 1
    print("  häufigste Schwerpunkt-Subfelder:")
    for s, c in sub_gesamt.most_common(12):
        print(f"    {c:4}  {s}  ({subfeld_meta[s]['domain']})")
    return profile


if __name__ == "__main__":
    profile = main()
    assert len(profile) >= 900, f"nur {len(profile)} Profile — Cache unvollständig?"
    # Stichprobe: Herztransplantation muss bei Zuckermann (A5033263383) oben stehen
    z = profile.get("A5033263383")
    if z:
        terms = [t for t, _ in z["terms"][:15]]
        assert any("transplant" in t for t in terms), terms
        assert z["sub"][0][0] in ("Surgery", "Cardiology and Cardiovascular Medicine"), z["sub"]
    assert all(p["terms"] for p in profile.values())
    print("✓ Selbstcheck ok")
