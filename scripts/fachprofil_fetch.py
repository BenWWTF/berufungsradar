#!/usr/bin/env python3
"""
Stufe 1 der Fachprofile: Publikationen je Person aus OpenAlex holen.

Für jede eindeutige openalex_id in dashboard_data_2025.json werden zwei
Listen geladen und zusammengeführt:
  - die 100 meistzitierten Arbeiten seit 2005 (das inhaltliche Gewicht),
  - die 40 jüngsten Arbeiten (die aktuelle Richtung).
Je Arbeit: Titel, Jahr, Zitierungen, Typ, OpenAlex-Topics (mit Subfield,
Field, Domain), Keywords und, wo OpenAlex ihn hat, der Abstract.

Rohdaten liegen in scripts/.fachprofil_cache/<openalex_id>.json und gehen
nicht ins Repo. fachprofil.py verdichtet sie zu fachprofile.json.

Aufruf: python3 scripts/fachprofil_fetch.py [--refresh]
  Ohne --refresh werden nur Personen ohne Cache-Datei geholt.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
CACHE = Path(__file__).resolve().parent / ".fachprofil_cache"

MAILTO = "benjamin.missbach@wwtf.at"
UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"
_KEY_PATHS = [Path.home() / ".berufungsradar_openalex_key", Path.home() / ".config" / "openalex" / "api_key"]
API_KEY = os.environ.get("OPENALEX_API_KEY") or next(
    (p.read_text().strip() for p in _KEY_PATHS if p.exists()), None)

SELECT = "id,title,publication_year,cited_by_count,type,topics,keywords,abstract_inverted_index"
AB_JAHR = 2005


def abstract_text(inv):
    """OpenAlex liefert Abstracts als invertierten Index: Wort → Positionen."""
    if not inv:
        return None
    pos = []
    for wort, stellen in inv.items():
        pos.extend((s, wort) for s in stellen)
    pos.sort()
    return " ".join(w for _, w in pos)


def hole(url, versuche=4):
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(3 * (i + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"OpenAlex antwortet nicht: {url[:120]}")


def werke(author_id, sort, per_page):
    url = (f"https://api.openalex.org/works?filter=authorships.author.id:{author_id},"
           f"publication_year:>{AB_JAHR - 1}&select={SELECT}&per-page={per_page}&sort={sort}"
           f"&mailto={MAILTO}" + (f"&api_key={API_KEY}" if API_KEY else ""))
    return hole(url)["results"]


def kompakt(w):
    return {
        "id": w["id"].rsplit("/", 1)[-1],
        "titel": w.get("title"),
        "jahr": w.get("publication_year"),
        "zit": w.get("cited_by_count") or 0,
        "typ": w.get("type"),
        "topics": [{
            "name": t["display_name"], "score": round(t.get("score") or 0, 3),
            "subfield": t["subfield"]["display_name"], "field": t["field"]["display_name"],
            "domain": t["domain"]["display_name"],
        } for t in (w.get("topics") or [])],
        "keywords": [{"name": k["display_name"], "score": round(k.get("score") or 0, 3)}
                     for k in (w.get("keywords") or [])],
        "abstract": abstract_text(w.get("abstract_inverted_index")),
    }


def main():
    CACHE.mkdir(exist_ok=True)
    data = json.loads(DATA_PATH.read_text())
    ids = sorted({d["openalex_id"] for d in data if d.get("openalex_id")})
    offen = [i for i in ids if "--refresh" in sys.argv or not (CACHE / f"{i}.json").exists()]
    print(f"{len(ids)} Personen mit OpenAlex-Profil, {len(offen)} zu laden"
          + ("" if API_KEY else " (ohne API-Key, langsam)"))
    fehler = 0
    for n, aid in enumerate(offen, 1):
        try:
            gesehen, liste = set(), []
            for w in werke(aid, "cited_by_count:desc", 100) + werke(aid, "publication_date:desc", 40):
                if w["id"] not in gesehen:
                    gesehen.add(w["id"])
                    liste.append(kompakt(w))
            (CACHE / f"{aid}.json").write_text(json.dumps(
                {"openalex_id": aid, "geholt": time.strftime("%Y-%m-%d"), "werke": liste},
                ensure_ascii=False))
        except Exception as e:
            fehler += 1
            print(f"  ! {aid}: {e}")
        if n % 50 == 0:
            print(f"  {n}/{len(offen)}")
        time.sleep(0.15 if API_KEY else 1.0)
    print(f"✓ {len(offen) - fehler} geladen, {fehler} Fehler, Cache: {CACHE}")


if __name__ == "__main__":
    main()
