#!/usr/bin/env python3
"""
Werdegang/Herkunft-Handrecherche einpflegen (z.B. scripts/backfill/werdegang_*.json).

Matcht auf (name, universitat, quelle) — quelle_werdegang im Input muss exakt
der quelle im bestehenden Record entsprechen (wichtig bei Doppelberufungen
derselben Person zu unterschiedlichen Jahren). Füllt nur leere Felder, nie
Bestehendes überschreiben. _kuratiert wird ergänzt, nicht ersetzt.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"

FIELDS = ["werdegang", "herkunft", "herkunft_institution", "herkunft_land", "profil_url"]


def main():
    if len(sys.argv) < 2:
        print("Usage: merge_werdegang.py <input.json>")
        sys.exit(1)
    src = json.loads(Path(sys.argv[1]).read_text())
    data = json.loads(DATA_PATH.read_text())
    by_key = {(d["name"], d["universitat"], d.get("quelle")): d for d in data}

    n_filled = n_skipped_filled = n_nomatch = 0
    for entry in src:
        if not isinstance(entry, dict) or "name" not in entry:
            continue
        key = (entry["name"], entry["universitat"], entry.get("quelle_werdegang"))
        d = by_key.get(key)
        if d is None:
            # Fallback: eindeutig, wenn nur eine Berufung dieser Person an dieser Uni existiert
            cands = [x for x in data if x["name"] == entry["name"] and x["universitat"] == entry["universitat"]]
            if len(cands) == 1:
                d = cands[0]
            else:
                print(f"  ! kein Match: {entry['name']} ({entry['universitat']})")
                n_nomatch += 1
                continue
        if d.get("werdegang"):
            n_skipped_filled += 1
            continue
        for f in FIELDS:
            if entry.get(f):
                d[f] = entry[f]
        note = f"Handrecherche (Werdegang) via {entry.get('quelle_werdegang')}: {entry.get('_kuratiert', '')}"
        d["_kuratiert"] = f"{d['_kuratiert']}; {note}" if d.get("_kuratiert") else note
        n_filled += 1

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {n_filled} Records ergänzt, {n_skipped_filled} bereits gefüllt übersprungen, {n_nomatch} ohne Match")


if __name__ == "__main__":
    main()
