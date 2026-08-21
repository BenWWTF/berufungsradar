#!/usr/bin/env python3
"""
Namen aus Quelltexten normalisieren. Gemeinsam genutzt von den Backfill-Skripten.

Grundregel: Namensbestandteile enthalten keine Punkte, akademische Grade fast
immer ("Dipl.-Ing.", "Dr.rer.soc.oec.", "Assoz. Prof."). Punkt-Token fliegen
raus, punktlose Grade stehen als Liste daneben.
"""

import re

GRADE_OHNE_PUNKT = {
    "univ", "prof", "profin", "dr", "drin", "mag", "maga", "dipl", "ing", "di",
    "msc", "ma", "bsc", "ba", "phd", "mba", "doz", "habil", "techn", "mont",
    "phil", "iur", "med", "nat", "rer", "soc", "oec", "scient", "sc", "associate",
    "assoc", "assoz", "assistant", "ass", "professor", "professorin", "emeritus",
    "bakk", "llm", "mres", "meng", "dphil", "mphil", "dsc", "msci",
    "docteur", "diplom", "diplomingenieur", "dott", "dottore", "ir", "drs",
    "statistiker", "chem", "biol", "phys", "math", "inform", "wirt",
}

# Kleingeschriebene Namensbestandteile, die dazugehören
NAMENSFUELLER = {"von", "van", "de", "del", "della", "di", "da", "dos", "el",
                 "al", "zu", "te", "ter", "op", "den", "der"}


def namensform(roh):
    """'Assoz. Prof. Mag. Dr. Ivana LJUBIC' → 'Ivana Ljubic'."""
    teile = []
    for wort in re.split(r"[\s,;]+", roh or ""):
        wort = wort.strip("-–()")
        if not wort or "." in wort:
            continue
        if wort.lower().strip("-") in GRADE_OHNE_PUNKT:
            continue
        if wort.isupper() and len(wort) > 1:
            wort = "-".join(w.capitalize() for w in wort.split("-"))
        teile.append(wort)
    return " ".join(teile).strip()


def plausibel(name):
    """Grober Filter gegen Fehlgriffe: zwei bis vier Teile, keine Ziffern."""
    if not name or any(c.isdigit() for c in name):
        return False
    teile = name.split()
    return 2 <= len(teile) <= 4 and all(len(t) > 1 for t in teile)


if __name__ == "__main__":
    assert namensform("Assoz. Prof. Mag. Dr. Ivana Ljubic") == "Ivana Ljubic"
    assert namensform("Univ.Prof. Dipl.-Ing. Dr.rer.nat. Siegfried KRAINER") == "Siegfried Krainer"
    assert namensform("Univ.-Prof. Dr. Anna-Maria Müller-Weiss") == "Anna-Maria Müller-Weiss"
    assert plausibel("Ivana Ljubic")
    assert not plausibel("Neue Professuren 2015")
    assert not plausibel("Ljubic")
    print("✓ namen.py Selbstcheck ok")
