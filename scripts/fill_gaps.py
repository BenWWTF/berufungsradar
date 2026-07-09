#!/usr/bin/env python3
"""
Stage 6: Lücken automatisch füllen — aus dem OpenAlex-Cache, fail-safe.

Merge-Regel (Vertrauenshierarchie): manuell > API > generiert.
Auto-gefüllte Felder tragen einen Marker (werdegang_auto / profil_url_auto),
damit sie bei späteren Läufen regeneriert werden dürfen — manuell gepflegte
Felder (ohne Marker) werden NIE überschrieben.

Füllt:
  - werdegang    ← Stationen aus der OpenAlex-Affiliationshistorie
  - profil_url   ← OpenAlex-Autorenseite als Fallback
  - herkunft_institution/-land ← aus Cache, nur wenn leer und Konfidenz ≥ medium

Läuft nach wwtf_enrich.py, vor build_html.py. Idempotent.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
OA_PATH = ROOT / "scripts" / "openalex_research.json"


def year_range(years):
    if not years:
        return ""
    lo, hi = min(years), max(years)
    return str(lo) if lo == hi else f"{lo}–{hi}"


def build_werdegang(oa_entry):
    """Stationen-Text aus der Affiliationshistorie, chronologisch absteigend."""
    insts = oa_entry.get("last_known_institutions") or []
    parts = []
    for inst in insts:
        if not inst.get("name"):
            continue
        rng = year_range(inst.get("years"))
        land = inst.get("country")
        seg = inst["name"]
        if land and land != "AT":
            seg += f" ({land})"
        if rng:
            seg += f", {rng}"
        parts.append(seg)
    if not parts:
        return None
    return "Stationen laut OpenAlex-Publikationshistorie: " + " · ".join(parts) + "."


def main():
    data = json.loads(DATA_PATH.read_text())
    oa = json.loads(OA_PATH.read_text()) if OA_PATH.exists() else {}

    n_wg = n_url = n_hk = 0
    for d in data:
        entry = oa.get(d["name"]) or {}
        usable = entry.get("openalex_id") and entry.get("match_confidence", "high") != "low"

        # werdegang: nur wenn leer oder von uns generiert
        if usable and (not d.get("werdegang") or d.get("werdegang_auto")):
            wg = build_werdegang(entry)
            if wg:
                d["werdegang"] = wg
                d["werdegang_auto"] = True
                n_wg += 1

        # profil_url: OpenAlex-Autorenseite als Fallback
        if usable and (not d.get("profil_url") or d.get("profil_url_auto")):
            d["profil_url"] = f"https://openalex.org/{entry['openalex_id']}"
            d["profil_url_auto"] = True
            n_url += 1

        # Herkunft: nur leere Felder, nie Bestehendes anfassen
        if usable and not d.get("herkunft_institution") and entry.get("herkunft_institution"):
            if d.get("herkunft") in (None, entry.get("herkunft")):
                d["herkunft_institution"] = entry["herkunft_institution"]
                if not d.get("herkunft_land") and entry.get("herkunft_land"):
                    d["herkunft_land"] = entry["herkunft_land"]
                n_hk += 1

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ auto-gefüllt: {n_wg} werdegang, {n_url} profil_url, {n_hk} herkunft_institution")


if __name__ == "__main__":
    main()
    # Selbstcheck
    data = json.loads(DATA_PATH.read_text())
    auto = [d for d in data if d.get("werdegang_auto")]
    assert all(d["werdegang"].startswith("Stationen laut OpenAlex") for d in auto)
