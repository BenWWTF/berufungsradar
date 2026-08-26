#!/usr/bin/env python3
"""
OpenAlex batch lookup for the 26 entries without bio_text and 25 with
unknown herkunft. Caches results to scripts/openalex_research.json.

Uses /authors?search=Name endpoint, takes the top result, and:
  - writes h_index, works_count, cited_by_count
  - writes last_known_institutions (most recent 3)
  - writes a 1-sentence bio from the top_concepts/topics
  - looks up the grantee FWF / FFG / EU funding by name+forschungsbereich

Be polite: 1 request/sec, polite pool, mailto contact.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dashboard_data_2025.json"
OUT = ROOT / "scripts" / "openalex_research.json"
OVERRIDES = ROOT / "scripts" / "openalex_overrides.json"

UA = "Berufungsradar/1.0 (mailto:benjamin.missbach@wwtf.at)"
MAILTO = "benjamin.missbach@wwtf.at"

COUNTRY_NAMES_DE = {
    "US": "USA",
    "GB": "Großbritannien",
    "DE": "Deutschland",
    "FR": "Frankreich",
    "CH": "Schweiz",
    "IT": "Italien",
    "AT": "Österreich",
    "NL": "Niederlande",
    "BE": "Belgien",
    "ES": "Spanien",
    "PT": "Portugal",
    "SE": "Schweden",
    "NO": "Norwegen",
    "FI": "Finnland",
    "DK": "Dänemark",
    "PL": "Polen",
    "CZ": "Tschechien",
    "SK": "Slowakei",
    "HU": "Ungarn",
    "RO": "Rumänien",
    "BG": "Bulgarien",
    "GR": "Griechenland",
    "TR": "Türkei",
    "IL": "Israel",
    "CA": "Kanada",
    "MX": "Mexiko",
    "BR": "Brasilien",
    "AR": "Argentinien",
    "AU": "Australien",
    "NZ": "Neuseeland",
    "JP": "Japan",
    "CN": "China",
    "KR": "Südkorea",
    "IN": "Indien",
    "ZA": "Südafrika",
    "RU": "Russland",
    "UA": "Ukraine",
    "EE": "Estland",
    "LV": "Lettland",
    "LT": "Litauen",
    "IE": "Irland",
    "LU": "Luxemburg",
}


def openalex_search_author(name: str) -> dict | None:
    """Return top match or None."""
    q = urllib.parse.quote(name)
    url = f"https://api.openalex.org/authors?search={q}&per_page=3&mailto={MAILTO}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            return data.get("results", [None])[0]
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 429 and versuch < 2:
                time.sleep(10 * (versuch + 1))      # Rate Limit: warten, nicht aufgeben
                continue
            print(f"  ! error fetching {name}: {e}", file=sys.stderr)
            # Unterschied zwischen "geprüft, kein Profil" und "Abfrage kaputt":
            # ein Fehler darf nicht als Negativ-Ergebnis im Cache landen.
            return "FEHLER"
    return "FEHLER"


def openalex_get_author(author_id: str) -> dict | None:
    """Fetch a specific author by ID (for verified overrides)."""
    url = f"https://api.openalex.org/authors/{author_id}?mailto={MAILTO}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ! error fetching {author_id}: {e}", file=sys.stderr)
        return None


def openalex_get_works(author_id: str, per_page=200) -> list:
    """Return all works of an author (paginated)."""
    works = []
    cursor = "*"
    while cursor:
        url = f"https://api.openalex.org/works?filter=authorships.author.id:{author_id}&per_page={per_page}&cursor={cursor}&mailto={MAILTO}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  ! works fetch err: {e}", file=sys.stderr)
            break
        works.extend(data.get("results", []))
        cursor = data.get("meta", {}).get("next_cursor")
        if not data.get("results"):
            break
    return works


def compute_h_index(works: list) -> int:
    """h = max{n : n papers each cited at least n times}."""
    counts = sorted((w.get("cited_by_count") or 0 for w in works), reverse=True)
    h = 0
    for i, c in enumerate(counts, 1):
        if c >= i:
            h = i
        else:
            break
    return h


def extract_last_institutions(author: dict) -> list:
    """Return list of (name, country, type, years) sorted by recency."""
    affs = author.get("affiliations", []) or []
    out = []
    for a in affs:
        inst = a.get("institution") or {}
        years = a.get("years") or []
        if not inst:
            continue
        out.append(
            {
                "name": inst.get("display_name"),
                "country": inst.get("country_code"),
                "type": inst.get("type"),
                "years": years,
                "most_recent": max(years) if years else None,
            }
        )
    out.sort(key=lambda x: x.get("most_recent") or 0, reverse=True)
    return out[:5]


def build_bio_text(author: dict, d: dict, h: int) -> str:
    """Build a short bio sentence from author data."""
    fb = d.get("forschungsbereich", "")
    insts = author.get("affiliations", []) or []
    last_inst = insts[0]["institution"]["display_name"] if insts else "—"
    works = author.get("works_count", 0)
    cited = author.get("cited_by_count", 0)
    name = d.get("name")
    parts = []
    if fb:
        parts.append(f"{fb}.")
    if h:
        parts.append(f"h-Index: {h} | Publikationen: {works} | Zitierungen: {cited}.")
    # Affiliation summary
    if len(insts) >= 2:
        # First is the latest
        countries = [
            i.get("institution", {}).get("country_code")
            for i in insts
            if i.get("institution")
        ]
        countries_de = [COUNTRY_NAMES_DE.get(c, c) for c in countries if c]
        if countries_de:
            seen = []
            for c in countries_de:
                if c not in seen:
                    seen.append(c)
            if len(seen) > 1:
                parts.append(f"Forschungstätigkeit u.a. in {', '.join(seen[:4])}.")
    return " ".join(parts)


def infer_herkunft(d: dict, author: dict) -> dict:
    """Decide: intern (was at the same Austrian uni before) vs extern.
    If extern, give institution + country.
    Strategy: find the latest affiliation that is NOT the current uni.
    If none such, the author is intern (has been at this uni all along).
    """
    if not author:
        return {}
    uni_now = d.get("universitat")
    affs = author.get("affiliations", []) or []
    if not affs:
        return {
            "herkunft": "unbekannt",
            "herkunft_institution": None,
            "herkunft_land": None,
        }
    AUSTRIAN_UNIS_TO_NOWUNI = {
        "TU Wien": "TU Wien",
        "Universität Wien": "Uni Wien",
        "University of Vienna": "Uni Wien",
        "Medizinische Universität Wien": "MedUni Wien",
        "Medical University of Vienna": "MedUni Wien",
        "BOKU": "BOKU",
        "Universität für Bodenkultur Wien": "BOKU",
        "University of Natural Resources and Life Sciences, Vienna": "BOKU",
        "WU Wien": "WU Wien",
        "Wirtschaftsuniversität Wien": "WU Wien",
        "Vienna University of Economics and Business": "WU Wien",
        "Vetmeduni Wien": "Vetmeduni Wien",
        "University of Veterinary Medicine Vienna": "Vetmeduni Wien",
        "Universität für Musik und darstellende Kunst Wien": "mdw",
        "mdw - Universität für Musik und darstellende Kunst Wien": "mdw",
        "Universität für angewandte Kunst Wien": "Angewandte",
        "University of Applied Arts Vienna": "Angewandte",
        "Angewandte": "Angewandte",
        # Clinical divisions of MedUni Wien — these are internal
        "Vienna General Hospital": "MedUni Wien",
        "Medical University of Vienna": "MedUni Wien",
        "Universitätsklinik für Chirurgie Wien": "MedUni Wien",
        "Ludwig Boltzmann Cluster Arthritis and Rehabilitation": "MedUni Wien",
        "Ludwig Boltzmann Institute for Traumatology, The Research Center in Cooperation with AUVA": "MedUni Wien",
        "Ludwig Boltzmann Institute for Digital Health and Prevention": "MedUni Wien",
        "Ludwig Boltzmann Institute Applied Diagnostics": "MedUni Wien",
        "Ludwig Boltzmann Institute of Osteology": "MedUni Wien",
        "Ludwig Boltzmann Institute for Lung Health": "MedUni Wien",
        # CD Labs are typically hosted at one of the major Viennese unis
        "Christian Doppler Laboratory for Thermoelectricity": "TU Wien",
        "Christian Doppler Forschungsgesellschaft": "TU Wien",
        # Max Perutz Labs is joint MedUni/Uni Wien
        "Max Perutz Labs": "Uni Wien",
        "Max F. Perutz Laboratories": "Uni Wien",
        # Comprehensive Cancer Center Vienna — joint MedUni/ÖAW
        "Comprehensive Cancer Center Vienna": "MedUni Wien",
        "Universitätszahnklinik Wien": "MedUni Wien",
        "University of Music and Performing Arts Vienna": "mdw",
    }
    # Wildcard rules — any institution whose name contains the key is mapped.
    AUSTRIAN_UNIS_WILDCARD = {
        "Vienna General Hospital": "MedUni Wien",
        "Universitätsklinik": "MedUni Wien",
        "Universitätszahnklinik": "MedUni Wien",
        "Comprehensive Cancer Center": "MedUni Wien",
        "Ludwig Boltzmann": "MedUni Wien",  # most LBI hosted by MedUni
        "Christian Doppler Laboratory": "TU Wien",
        "Max Perutz": "Uni Wien",
    }
    # Build list of (year, inst_name, inst_country) sorted by recency (desc)
    flat = []
    for a in affs:
        inst = a.get("institution", {}) or {}
        years = a.get("years") or []
        for y in years:
            flat.append(
                {
                    "year": y,
                    "name": inst.get("display_name", ""),
                    "country": inst.get("country_code", ""),
                }
            )
    flat.sort(key=lambda x: x.get("year") or 0, reverse=True)
    # Walk down: find the latest entry that is NOT the current uni
    target = None
    for entry in flat:
        if AUSTRIAN_UNIS_TO_NOWUNI.get(entry["name"], entry["name"]) != uni_now:
            target = entry
            break
    if not target:
        # All affiliations match current uni → intern
        if flat:
            latest = flat[0]
            return {
                "herkunft": "intern",
                "herkunft_institution": latest["name"],
                "herkunft_land": "Österreich"
                if latest["country"] == "AT"
                else latest["country"],
            }
        return {
            "herkunft": "unbekannt",
            "herkunft_institution": None,
            "herkunft_land": None,
        }
    # Check if target is an Austrian uni mapped to current uni (would mean intern)
    if AUSTRIAN_UNIS_TO_NOWUNI.get(target["name"], target["name"]) == uni_now:
        return {
            "herkunft": "intern",
            "herkunft_institution": target["name"],
            "herkunft_land": "Österreich"
            if target["country"] == "AT"
            else target["country"],
        }
    # Wildcard match
    for kw, mapped_uni in AUSTRIAN_UNIS_WILDCARD.items():
        if kw in target["name"] and mapped_uni == uni_now:
            return {
                "herkunft": "intern",
                "herkunft_institution": target["name"],
                "herkunft_land": "Österreich"
                if target["country"] == "AT"
                else target["country"],
            }
    # Long-career rule: if the person was at the current uni within 3 years
    # of "now" (i.e. 2023+), they're INTERNAL — they came back / were promoted.
    # This catches TU Wien lifers who took 2-year sabbaticals to OFAI/ÖAW/etc.
    for entry in flat:
        if (
            AUSTRIAN_UNIS_TO_NOWUNI.get(entry["name"], entry["name"]) == uni_now
            and entry.get("year", 0) >= 2023
        ):
            return {
                "herkunft": "intern",
                "herkunft_institution": entry["name"],
                "herkunft_land": "Österreich"
                if entry["country"] == "AT"
                else entry["country"],
            }
    return {
        "herkunft": "extern",
        "herkunft_institution": target["name"],
        "herkunft_land": COUNTRY_NAMES_DE.get(target["country"], target["country"])
        or None,
    }


def match_confidence(d: dict, author: dict) -> str:
    """Plausibility check for the top search hit — fail-safe gegen
    Namensvetter. Downstream-Stufen ignorieren 'low'-Treffer.

    high:   eine Affiliation liegt in Österreich (Berufungs-Kontext plausibel)
    medium: eine Affiliation liegt im bekannten Herkunftsland
    low:    keine geografische Plausibilität → nicht automatisch mergen
    """
    countries = {
        (a.get("institution") or {}).get("country_code")
        for a in (author.get("affiliations") or [])
    }
    countries.discard(None)
    if "AT" in countries:
        return "high"
    land = d.get("herkunft_land")
    iso_by_name = {v: k for k, v in COUNTRY_NAMES_DE.items()}
    if land and iso_by_name.get(land) in countries:
        return "medium"
    return "low"


def process_entry(d: dict, overrides: dict) -> dict:
    """Lookup one entry, return the OpenAlex-derived fields.

    overrides[name] can pin a verified openalex_id (bypasses Suche +
    Konfidenz-Gate) oder 'none' (Person hat kein Profil → Negativ-Cache).
    """
    name = d.get("name", "")
    print(f"  → {name} ...", end=" ", flush=True)
    ov = overrides.get(name) or {}
    conf = None
    if ov.get("openalex_id") == "none":
        print("override: kein Profil")
        return {"name": name, "_openalex": "not found", "match_confidence": "verified"}
    if ov.get("openalex_id"):
        author = openalex_get_author(ov["openalex_id"])
        conf = "verified"
    else:
        author = openalex_search_author(name)
    if author == "FEHLER":
        print("Abfrage fehlgeschlagen, kein Cache-Eintrag")
        return None
    if not author:
        print("not found")
        # Negativ-Cache: „geprüft, nicht vorhanden" ≠ „nie geprüft"
        return {"name": name, "_openalex": "not found"}
    author_id = author.get("id", "").replace("https://openalex.org/", "")
    if conf is None:
        conf = match_confidence(d, author)
    # Get all works for h-index
    works = openalex_get_works(author_id)
    h = compute_h_index(works)
    print(f"h={h} works={len(works)} cited={author.get('cited_by_count')} conf={conf}")
    insts = extract_last_institutions(author)
    bio = build_bio_text(author, d, h)
    hk = infer_herkunft(d, author)
    # Manuell recherchierte Herkunft im Override schlägt die Inferenz.
    # Nur dann gilt sie als 'verified' und darf kuratierte Werte umstoßen;
    # ein reiner ID-Pin (ohne herkunft) lässt die kuratierte Herkunft unberührt.
    herkunft_verified = bool(ov.get("herkunft"))
    for key in ("herkunft", "herkunft_institution", "herkunft_land"):
        if ov.get(key):
            hk[key] = ov[key]
    return {
        "name": name,
        "openalex_id": author_id,
        "match_confidence": conf,
        "herkunft_verified": herkunft_verified,
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "h_index": h,
        "last_known_institutions": insts,
        "bio_text": bio,
        "herkunft": hk.get("herkunft"),
        "herkunft_institution": hk.get("herkunft_institution"),
        "herkunft_land": hk.get("herkunft_land"),
        "grants": [],
    }


def main():
    if OUT.exists():
        with OUT.open() as f:
            results = json.load(f)
    else:
        results = {}

    with DATA.open() as f:
        data = json.load(f)

    overrides = {}
    if OVERRIDES.exists():
        overrides = {k: v for k, v in json.loads(OVERRIDES.read_text()).items()
                     if not k.startswith("_")}

    # Default: alle Einträge, die noch nie geprüft wurden (fail-safe: der
    # Cache enthält auch Negativ-Ergebnisse, daher keine Doppel-Lookups).
    # --gaps-only: nur Einträge ohne bio_text / mit unbekannter Herkunft.
    if "--gaps-only" in sys.argv:
        targets = set()
        for d in data:
            if not d.get("bio_text"):
                targets.add(d["name"])
            if d.get("herkunft") in (None, "unbekannt", "—"):
                targets.add(d["name"])
    else:
        targets = {d["name"] for d in data}
    # Override-Einträge neu verarbeiten, wenn sie noch nicht als 'verified'
    # (mit herkunft_verified-Flag) im Cache stehen — ersetzt alte
    # low-confidence-Treffer und ergänzt fehlende Schema-Felder.
    for name in overrides:
        cached = results.get(name, {})
        stale = cached.get("match_confidence") != "verified"
        if cached.get("_openalex") != "not found" and "herkunft_verified" not in cached:
            stale = True
        if stale:
            results.pop(name, None)
    todo = [n for n in targets if n not in results]
    print(f"Already cached: {len(results)}, new: {len(todo)}")

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        n = int(sys.argv[idx + 1])
        todo = todo[:n]
        print(f"Limited to {n} entries")

    for name in todo:
        # Find the entry
        d = next((x for x in data if x.get("name") == name), None)
        if not d:
            print(f"  ! not in data: {name}")
            continue
        result = process_entry(d, overrides)
        if result is not None:
            results[name] = result
            with OUT.open("w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        time.sleep(25.0)  # OpenAlex drosselt bei Serien: pro Person fallen
                         # Suchabfrage plus mehrere Werk-Seiten an; auch nach
                         # einem Fehlschlag warten, sonst kaskadieren die 429er.
                         # 2.0s und 10.0s reichten beide nicht (harter 429-Block,
                         # 2026-08-24), hochgesetzt auf 25s.

    print(f"\nWrote {len(results)} results → {OUT}")


if __name__ == "__main__":
    main()
