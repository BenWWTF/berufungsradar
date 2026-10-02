#!/usr/bin/env python3
"""
Bericht über die Neuzugänge seit dem letzten Commit, als Markdown für den
Pull Request der wöchentlichen Suche (.github/workflows/neuzugaenge.yml).

Vergleicht dashboard_data_2025.json im Arbeitsverzeichnis mit dem Stand in
HEAD. Neue Datensätze, deren Name an derselben Universität schon in einem
anderen Jahr steht, werden markiert: das ist fast immer dieselbe Berufung mit
abweichendem Jahr in der Quelle, selten eine zweite Station (TT → UP).

Aufruf: python3 scripts/neuzugaenge.py (nach merge_backfill.py)
Ohne Neuzugänge bleibt stdout leer.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_backfill import DATA_PATH, ROOT, kurz  # noqa: E402


def schluessel(d):
    return d["universitat"], d["year"], kurz(d["name"])


def main():
    vorher = json.loads(subprocess.run(
        ["git", "show", f"HEAD:{DATA_PATH.relative_to(ROOT)}"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    nachher = json.loads(DATA_PATH.read_text())

    bekannt = {schluessel(d) for d in vorher}
    andere_jahre = {}
    for d in vorher:
        andere_jahre.setdefault((d["universitat"], kurz(d["name"])), []).append(d["year"])

    neu = [d for d in nachher if schluessel(d) not in bekannt]
    if not neu:
        return

    zeilen = [f"**{len(neu)} neue Berufung(en)** aus den laufend gepflegten Uni-Seiten.",
              "",
              "| Universität | Name | Antritt | Widmung | Quelle | Prüfen |",
              "|---|---|---|---|---|---|"]
    for d in sorted(neu, key=lambda d: (d["universitat"], d["year"], d["name"])):
        jahre = andere_jahre.get((d["universitat"], kurz(d["name"])))
        hinweis = f"⚠️ schon im Bestand: {', '.join(map(str, sorted(jahre)))}" if jahre else ""
        zeilen.append(
            f"| {d['universitat']} | {d['name']} | {(d.get('monat') or '?').title()} {d['year']} "
            f"| {d.get('forschungsbereich') or ''} | [Link]({d.get('profil_url') or d.get('quelle')}) | {hinweis} |")
    zeilen += ["",
               "Stufe 1: ÖFOS, Geschlecht und OpenAlex sind automatisch ergänzt, "
               "Herkunft nur wo der Lebenslauf sie hergibt. Vor dem Merge prüfen:",
               "",
               "- [ ] Name und Antrittsjahr stimmen mit der Quelle überein",
               "- [ ] ⚠️-Zeilen: Dublette oder echte zweite Station?",
               "- [ ] ÖFOS-Zuordnung plausibel"]
    print("\n".join(zeilen))


if __name__ == "__main__":
    main()
