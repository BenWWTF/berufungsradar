#!/usr/bin/env python3
"""
Wöchentliche Kandidatensuche für die Unis ohne "Neue Professuren"-Seite.

Anders als die backfill_*_live.py-Skripte erzeugt dieses Skript keine
Datensätze, sondern Hinweise für eine Handprüfung (GitHub-Issue). Die Quellen
sind zu unscharf für automatische Datensätze: bei der MedUni-Recherche hielten
19 von 49 Pressefunden der Prüfung stand.

Zwei Arten von Quellen:

  Pressequellen   Links auf Presse-/News-Seiten, deren Text oder URL nach
                  Berufung klingt. Gemeldet wird jeder Link genau einmal.
  Verzeichnisse   Professor:innen-Listen, Woche für Woche verglichen. Neue
                  Namen, die im Bestand fehlen, sind Kandidaten. Kein
                  Verzeichnis ist vollständig (WU ohne Christoph Schmidt,
                  VetDoc ohne Liehmann), sie ergänzen die Presse nur.

Dazu ein Lebenszeichen-Check für people.ceu.edu, das am 2.10.2026 mit
HTTP 500 antwortet; sobald es wieder läuft, steht das im Bericht.

Gedächtnis zwischen den Läufen: scripts/kandidaten/stand.json (gemeldete
Links, Verzeichnisstände). Ein Verzeichnis ohne Stand wird beim ersten Lauf
nur eingelesen, nicht gemeldet.

Aufruf: python3 scripts/kandidaten.py [--basis]
        --basis: alles Aktuelle als bekannt eintragen, nichts melden
Bericht als Markdown auf stdout, leer wenn es nichts Neues gibt.
"""

import csv
import gzip
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_backfill import DATA_PATH, kurz  # noqa: E402

STAND = Path(__file__).resolve().parent / "kandidaten" / "stand.json"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"

BERUFUNG = re.compile(r"professor|professur|berufen|berufung|antrittsvorlesung|"
                      r"verstärkung für forschung", re.I)
KEINE = re.compile(r"gastprofess|visiting|honorary|ehrenprofess|emerit|berufungskommission|"
                   r"fulbright|berufstitel|trauer|jobs", re.I)

PRESSE = {
    "WU Wien": ["https://www.wu.ac.at/presse/presseaussendungen"],
    "Angewandte": ["https://www.dieangewandte.at/presse"],
    "BOKU": [
        "https://boku.ac.at/universitaetsleitung/rektorat/stabsstellen/oeffentlichkeitsarbeit/"
        "themen/presseaussendungen/presseaussendungen-{jahr}",
        "https://boku.ac.at/universitaetsleitung/rektorat/stabsstellen/"
        "stabsstelle-veranstaltungsmanagement/themen/veranstaltungen-fotos-videos",
    ],
    "Vetmeduni Wien": ["https://www.vetmeduni.ac.at/universitaet/infoservice/news"],
}


def hole(url, accept=None):
    kopf = {"User-Agent": UA}
    if accept:
        kopf["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=kopf), timeout=60) as r:
        roh = r.read()
    if roh[:2] == b"\x1f\x8b":          # WU liefert gzip, auch ungefragt
        roh = gzip.decompress(roh)
    time.sleep(2)
    return roh.decode("utf-8", errors="replace")


def klartext(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def presselinks(uni, url):
    """(Titel, absolute URL) aller Links, die nach Berufung klingen."""
    seite = hole(url)
    basis = re.match(r"https?://[^/]+", url).group(0)
    # BOKU führt das Pressearchiv als <select>, die übrigen als <a>
    treffer = re.findall(r"<a\b[^>]*href=\"([^\"#]+)\"[^>]*>(.*?)</a>", seite, re.S)
    treffer += re.findall(r"<option value='([^']+)'>(.*?)</option>", seite, re.S)
    for href, text in treffer:
        text = klartext(text)
        if len(text) < 15:
            continue
        ziel = href if href.startswith("http") else basis + "/" + href.lstrip("/")
        probe = f"{text} {href}"
        if BERUFUNG.search(probe) and not KEINE.search(probe):
            yield text, ziel


# Verzeichnisse: jede Funktion liefert {Schlüssel: Anzeigename}

def wu_verzeichnis():
    seite = hole("https://www.wu.ac.at/universitaet/organisation/akademische-einheiten/"
                 "professor-inn-en-dozent-inn-en")
    # "Ljubic, Ivana" → Schlüssel bleibt, angezeigt und abgeglichen wird "Ivana Ljubic"
    namen = re.findall(r'<h3 class="hyphenate">([^<]+)</h3>', seite)
    return {n: " ".join(reversed(html.unescape(n).split(", ", 1))) for n in map(str.strip, namen)}


def angewandte_verzeichnis():
    start = hole("https://www.dieangewandte.at/")
    pfade = sorted(set(re.findall(r'href="(?:https://www\.dieangewandte\.at)?(/institute/[^"#?]+)"',
                                  start)))
    namen = {}
    for pfad in pfade:
        # <a href="…&Pe-Id=9694">Chermayeff, Sam&nbsp;Univ.-Prof.&nbsp;BSA</a>
        for pe_id, nachname, vorname in re.findall(
                r'Pe-Id=(\d+)">([^<,]{2,40}),\s*([^<]{2,40}?)(?:&nbsp;|\s)+Univ\.-Prof',
                hole("https://www.dieangewandte.at" + pfad)):
            namen[pe_id] = html.unescape(f"{vorname} {nachname}").strip()
    return namen


def akbild_verzeichnis():
    # Nur die drei nötigen Felder: 200 KB statt 2 MB mit fullobjects
    daten = json.loads(hole("https://www.akbild.ac.at/de/@search?portal_type=Employee&b_size=1000"
                            "&metadata_fields=degree&metadata_fields=first_name"
                            "&metadata_fields=last_name", accept="application/json"))
    return {p["@id"]: f"{p['first_name']} {p['last_name']}"
            for p in daten["items"] if "Univ.-Prof" in (p.get("degree") or "")}


VETDOC = "https://vetdoc.vetmeduni.ac.at"


def vetdoc_verzeichnis():
    """Alle Personen (auch Nicht-Professuren); gefiltert wird erst bei neuen IDs."""
    roh = hole(VETDOC + "/vivo/search?type=http%3A%2F%2Fvetmeduni.ac.at%2Fontology%23Person"
               "&csv=1&hitsPerPage=5000")
    zeilen = csv.reader(io.StringIO(roh[roh.find("Name,"):]))
    next(zeilen)
    personen = {}
    for z in zeilen:
        if len(z) >= 5 and z[4].startswith("/vivo/display/"):
            nachname, _, vorname = z[0].partition(",")
            personen[z[4]] = f"{vorname.strip()} {nachname.strip()}"
    return personen


def vetdoc_professur(pfad):
    m = re.search(r"Titel\s+(.{0,40}?)\s+(?:ORCID|Publikationen|E-Mail)", klartext(hole(VETDOC + pfad)))
    return m and "Prof" in m.group(1)


VERZEICHNISSE = {
    "WU Wien": wu_verzeichnis,
    "Angewandte": angewandte_verzeichnis,
    "Akademie": akbild_verzeichnis,
    "Vetmeduni Wien": vetdoc_verzeichnis,
}


def ceu_erreichbar():
    try:
        hole("https://people.ceu.edu/unit/economics")
        return True
    except (urllib.error.URLError, TimeoutError):
        return False


def main():
    basis = "--basis" in sys.argv
    stand = json.loads(STAND.read_text()) if STAND.exists() else {}
    gemeldet = set(stand.get("gemeldet", []))
    verzeichnisse = stand.get("verzeichnisse", {})
    bestand = {(d["universitat"], kurz(d["name"])) for d in json.loads(DATA_PATH.read_text())}

    abschnitte, fehler = {}, []

    for uni, urls in PRESSE.items():
        for url in urls:
            url = url.format(jahr=date.today().year)
            try:
                for titel, ziel in presselinks(uni, url):
                    if ziel not in gemeldet:
                        gemeldet.add(ziel)
                        abschnitte.setdefault(uni, []).append(f"- [ ] Presse: [{titel}]({ziel})")
            except (urllib.error.URLError, TimeoutError) as e:
                fehler.append(f"{uni}: {url} ({e})")

    for uni, quelle in VERZEICHNISSE.items():
        try:
            aktuell = quelle()
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
            fehler.append(f"{uni}: Verzeichnis ({e})")
            continue
        if len(aktuell) < 20:
            fehler.append(f"{uni}: Verzeichnis liefert nur {len(aktuell)} Einträge, Aufbau geändert?")
            continue
        bisher = verzeichnisse.get(uni)
        if bisher is not None:
            for schluessel, name in aktuell.items():
                if schluessel in bisher or (uni, kurz(name)) in bestand:
                    continue
                if uni == "Vetmeduni Wien" and not vetdoc_professur(schluessel):
                    continue
                link = f" ([VetDoc]({VETDOC + schluessel}))" if uni == "Vetmeduni Wien" else ""
                abschnitte.setdefault(uni, []).append(f"- [ ] Verzeichnis: neu gelistet **{name}**{link}")
        # Vereinigung statt Ersatz: wer kurz verschwindet, wird nicht neu gemeldet
        verzeichnisse[uni] = sorted(set(bisher or []) | set(aktuell))

    ceu = ceu_erreichbar()
    if ceu and not stand.get("ceu_erreichbar"):
        abschnitte.setdefault("CEU", []).append(
            "- [ ] people.ceu.edu antwortet wieder: Verzeichnisvergleich für CEU einbauen")

    STAND.parent.mkdir(exist_ok=True)
    STAND.write_text(json.dumps({"gemeldet": sorted(gemeldet), "verzeichnisse": verzeichnisse,
                                 "ceu_erreichbar": ceu}, ensure_ascii=False, indent=1) + "\n")

    if basis or not (abschnitte or fehler):
        return
    zeilen = ["Hinweise auf Berufungen an Unis ohne laufend gepflegte Übersichtsseite. "
              "Verzeichnis-Namen fehlen im Bestand; Pressemeldungen sind nicht gegen den "
              "Bestand geprüft. Bestätigte Fälle als `kuratiert_*.json` erfassen und mit "
              "`merge_backfill.py` einspielen.", ""]
    for uni in sorted(abschnitte):
        zeilen += [f"### {uni}", *abschnitte[uni], ""]
    if fehler:
        zeilen += ["### ⚠️ Nicht erreichbar oder geändert", *[f"- {f}" for f in fehler]]
    print("\n".join(zeilen))


if __name__ == "__main__":
    main()
