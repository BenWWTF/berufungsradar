#!/usr/bin/env python3
"""
Führt die Backfill-Ernte (scripts/backfill/*.json) in die Hauptdatei ein.

Regeln:
  * Bestehende Datensätze werden NIE überschrieben. Sie sind kuratiert
    (Herkunft, Werdegang, ÖFOS von Hand geprüft), die Ernte ist Stufe 1.
  * Leere Stufe-1-Felder eines bestehenden Datensatzes dürfen gefüllt werden
    (Institutscode, Profil-Link) — das ist additiv, nicht destruktiv.
  * Alles, was nicht zugeordnet werden kann, kommt als neuer Datensatz dazu.

Namensabgleich: Umlaute werden ausgeschrieben (Steinböck = Steinboeck), dann
Diakritika entfernt. Zweiter Schlüssel ist Vorname+Nachname ohne Mittelnamen,
weil die Unis Mittelnamen unterschiedlich führen (Thomas Lennon Sheppard vs
Thomas Sheppard).

Aufruf: python3 scripts/merge_backfill.py [--dry]
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
BACKFILL_DIR = Path(__file__).resolve().parent / "backfill"

# Felder, die bei bestehenden Datensätzen nachgetragen werden dürfen
NACHTRAGBAR = ("fakultat_code", "profil_url", "forschungsbereich", "art_berufung",
               "geschlecht", "fakultat", "werdegang")

# Felder, deren automatisch erzeugte Fassung von der Quelle überschrieben werden
# darf: ein Lebenslauf aus der Uni-Seite ist besser als die aus OpenAlex
# abgeleiteten Stationen.
STAERKER_ALS_AUTO = {"werdegang": "werdegang_auto"}


def norm(name):
    t = (name or "").lower()
    for a, b in (("ö", "oe"), ("ä", "ae"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[.\-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def kurz(name):
    """Vorname + Nachname, Mittelnamen und Initialen fallen weg."""
    teile = [t for t in norm(name).split() if len(t) > 1]
    return f"{teile[0]} {teile[-1]}" if len(teile) >= 2 else norm(name)


def main():
    dry = "--dry" in sys.argv
    data = json.loads(DATA_PATH.read_text())

    lang = {}
    knapp = {}
    for d in data:
        lang[(d["universitat"], d["year"], norm(d["name"]))] = d
        knapp.setdefault((d["universitat"], d["year"], kurz(d["name"])), d)

    quellen = sorted(BACKFILL_DIR.glob("*.json")) if BACKFILL_DIR.exists() else []
    if not quellen:
        raise SystemExit("keine Dateien in scripts/backfill/")

    neu, bekannt, ergaenzt = [], 0, 0
    for datei in quellen:
        ernte = json.loads(datei.read_text())
        for e in ernte:
            schluessel = (e["universitat"], e["year"], norm(e["name"]))
            treffer = lang.get(schluessel) or knapp.get(
                (e["universitat"], e["year"], kurz(e["name"])))
            if treffer:
                bekannt += 1
                for feld in NACHTRAGBAR:
                    marker = STAERKER_ALS_AUTO.get(feld)
                    ersetzbar = bool(marker and treffer.get(marker))
                    if (not treffer.get(feld) or ersetzbar) and e.get(feld):
                        treffer[feld] = e[feld]
                        if marker:
                            treffer.pop(marker, None)   # ab jetzt Quellenangabe
                        ergaenzt += 1
                continue
            # Neuer Datensatz: Stufe-1-Felder plus die Struktur, die die
            # Pipeline erwartet (Rest füllen classify_ofos, enrich, fill_gaps)
            neu.append({
                "name": e["name"],
                "universitat": e["universitat"],
                "fakultat": e.get("fakultat"),
                "fakultat_code": e.get("fakultat_code"),
                "forschungsbereich": e.get("forschungsbereich"),
                "art_berufung": e.get("art_berufung"),
                # Die mdw nennt das Geschlecht in der Quelle ("seine/ihre"),
                # das ist besser als jede Vornamensheuristik.
                "geschlecht": e.get("geschlecht"),
                "herkunft": None,
                "herkunft_institution": None,
                "herkunft_land": None,
                "ofos_code": None,
                "ofos_label": None,
                "bio_text": None,
                # Lebensläufe aus der Quelle (Uni Wien) sind wertvoller als die
                # später abgeleiteten OpenAlex-Stationen, deshalb ohne
                # werdegang_auto-Marker.
                "werdegang": e.get("werdegang"),
                "profil_url": e.get("profil_url"),
                "monat": e["monat"],
                "year": e["year"],
                "quelle": e.get("quelle"),
                "stufe": 1,
            })
            lang[schluessel] = neu[-1]

    print(f"Quellen: {[q.name for q in quellen]}")
    print(f"  bereits erfasst: {bekannt} (davon {ergaenzt} Felder nachgetragen)")
    print(f"  neu:             {len(neu)}")
    jahre = {}
    for e in neu:
        jahre[e["year"]] = jahre.get(e["year"], 0) + 1
    for j in sorted(jahre):
        print(f"     {j}: {jahre[j]}")

    if dry:
        print("(--dry, nichts geschrieben)")
        return data, neu

    data.extend(neu)
    data.sort(key=lambda d: (d["year"], d["universitat"], d["name"]))
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ {len(data)} Datensätze in {DATA_PATH.name}")
    return data, neu


if __name__ == "__main__":
    data, neu = main()
    # Selbstcheck: keine Dubletten, kuratierte Daten unversehrt
    schluessel = [(d["universitat"], d["year"], kurz(d["name"])) for d in data]
    doppelt = {s for s in schluessel if schluessel.count(s) > 1}
    assert not doppelt, f"Dubletten nach dem Merge: {sorted(doppelt)[:5]}"
    sallinger = next(d for d in data if d["name"] == "Emanuel Sallinger")
    assert sallinger.get("werdegang"), "kuratierter Werdegang verloren"
    assert sallinger.get("vrg_id") == "VRG18-013", "VRG-Verknüpfung verloren"
    print("✓ Selbstcheck ok")
