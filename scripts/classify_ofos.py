#!/usr/bin/env python3
"""
Weist Berufungen ohne ÖFOS-Code eine Klassifikation zu.

Zwei Signale, in dieser Reihenfolge:
  1. Institutscode (TU Wien E-Codes sind eindeutig einer Disziplin zugeordnet)
  2. Stichwörter in der Professurbezeichnung, deutsch und englisch

Automatisch gesetzte Codes tragen `_ofos_auto: true` und ein grobes Label ohne
Spezialisierung in Klammern. Von Hand geprüfte Codes werden nie angetastet.
Was keine Regel trifft, bleibt leer und erscheint im Lückenreport.

Läuft nach merge_backfill.py, vor enrich.py (das erweitert 3-stellig → Bereich).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"

LABEL = {
    "101": "Mathematik", "102": "Informatik", "103": "Physik", "104": "Chemie",
    "105": "Geowissenschaften", "106": "Biologie",
    "201": "Bauingenieurwesen", "202": "Elektrotechnik", "203": "Maschinenbau",
    "204": "Chemieingenieurwesen", "205": "Materialwissenschaften",
    "206": "Medizintechnik", "207": "Umweltingenieurwesen",
    "210": "Nanotechnologie", "211": "Andere Technische Wissenschaften",
    "301": "Grundlagenmedizin", "302": "Klinische Medizin",
    "303": "Gesundheitswissenschaften", "304": "Medizinische Biotechnologie",
    "401": "Agrarwissenschaften", "403": "Veterinärmedizin",
    "501": "Psychologie", "502": "Wirtschaftswissenschaften", "503": "Bildungswissenschaften",
    "504": "Soziologie", "505": "Rechtswissenschaften", "506": "Politikwissenschaften",
    "507": "Humangeographie und Raumplanung", "509": "Andere Sozialwissenschaften",
    "601": "Geschichte und Archäologie", "602": "Sprach- und Literaturwissenschaften",
    "603": "Philosophie, Ethik, Religion", "604": "Kunstwissenschaften",
    "605": "Andere Geisteswissenschaften",
}

# TU-Wien-Institutscodes → ÖFOS. Quelle: Institutsnamen in enrich.py (TUWIEN_ECODE).
ECODE = [
    (r"^E10[123]", "101"), (r"^E104", "101"), (r"^E105", "105"),
    (r"^E1(2|3)\d", "103"), (r"^E141", "103"),
    (r"^E16[345]", "104"), (r"^E166", "204"),
    (r"^E18\d", "102"), (r"^E19\d", "102"),
    (r"^E20\d", "201"), (r"^E21\d", "211"), (r"^E22\d", "201"), (r"^E23\d", "201"),
    (r"^E25\d", "507"), (r"^E26\d", "211"), (r"^E28\d", "505"),
    (r"^E3(0|1|2)\d", "203"), (r"^E33\d", "502"), (r"^E34\d", "203"), (r"^E37\d", "203"),
    (r"^E38\d", "203"),
    (r"^E3(5|6)\d", "203"),
    (r"^E4\d\d", "202"),
]

# Stichwörter auf der Professurbezeichnung. Erste Regel gewinnt, spezifisch zuerst.
STICHWORT = [
    # Medizin
    (r"chirurg|surgery|kardiolog|cardiolog|onkolog|oncolog|radiolog|neurolog|"
     r"psychiatr|dermatolog|urolog|orthopäd|orthoped|gynäkolog|gynecolog|"
     r"anästhes|anesthes|pädiatr|pediatr|intensivmedizin|innere medizin|"
     r"klinische|clinical med|zahnmedizin|dental", "302"),
    (r"physiolog|anatomie|anatomy|pathophysiolog|immunolog|pharmakolog|pharmacolog|"
     r"molekulare medizin|molecular medicine|grundlagenmedizin", "301"),
    (r"public health|epidemiolog|pflegewissenschaft|nursing|gesundheitswissenschaft|"
     r"versorgungsforschung|health services|health econom", "303"),
    (r"biomedizintechnik|biomedical engineering|medizintechnik|medical engineering|"
     r"medical physic|medizinische strahlenphysik|bildgebung|imaging", "206"),
    (r"medizinische biotechnolog|medical biotechnolog|gentherapie|zelltherapie", "304"),
    # Naturwissenschaften
    (r"mathemat|analysis|geometrie|geometry|stochastik|statistik|statistic|"
     r"wahrscheinlichkeit|probability|numerik|numerical analysis|algebra|topolog", "101"),
    (r"informatik|computer science|computing|software|algorithm|"
     r"künstliche intelligenz|artificial intelligence|machine learning|"
     r"maschinelles lernen|data science|datenbank|database|kryptograph|cryptograph|"
     r"security|cyber|visualisierung|visual computing|graph|human-computer|"
     r"mensch-maschine|robotik|robotics|netzwerk|networks", "102"),
    (r"physik|physics|photonik|photonic|quantum|quanten|astronom|astrophys", "103"),
    (r"chemie|chemistry|katalys|catalys|elektrochem|electrochem|"
     r"synthese|synthetic chem|analytik|spektroskop", "104"),
    (r"geolog|geophysik|geophysic|geodäs|geodes|geoinformation|kartograph|"
     r"meteorolog|klimatolog|hydrolog", "105"),
    (r"biolog|biology|botanik|botany|zoolog|mikrobiolog|microbiolog|genetik|genetic|"
     r"ökolog|ecolog|evolution|biochem|molecular biolog|neurowissenschaft|neuroscience", "106"),
    # Technik
    (r"bauingenieur|civil engineering|hochbau|tragwerk|structural|geotechn|"
     r"baustatik|baubetrieb|verkehr|transport|wasserbau|building construction|"
     r"bauphysik|holzbau|stahlbau|betonbau", "201"),
    (r"elektrotechnik|electrical engineering|elektronik|electronic|"
     r"regelungstechnik|control engineering|automatisierung|automation|"
     r"nachrichtentechnik|telecommunication|energietechnik|power systems|"
     r"mikroelektronik|sensor|antriebe|drive systems|mechatronik|mechatronic", "202"),
    (r"maschinenbau|mechanical engineering|fahrzeug|automotive|thermodynamik|"
     r"strömungs|fluid|konstruktionslehre|fertigungstechnik|manufacturing|"
     r"produktionstechnik|luftfahrt|aerospace|energietechnik", "203"),
    (r"verfahrenstechnik|process engineering|chemieingenieur|chemical engineering|"
     r"lebensmitteltechnolog|food technolog|bioprozess|bioprocess", "204"),
    (r"werkstoff|material|polymer|keramik|ceramic|metallurg|oberflächen|surface|"
     r"korrosion|composite", "205"),
    (r"umwelttechnik|environmental engineering|abfall|waste|wasserwirtschaft|"
     r"water resources|luftreinhaltung|ressourcen", "207"),
    (r"nanotechnolog|nanoscience|nanostruktur", "210"),
    (r"architektur|architecture|denkmalpflege|baugeschichte|entwerfen|"
     r"industrial design|digital engineering", "211"),
    # Agrar und Veterinär
    (r"agrar|agricultur|pflanzenbau|crop|bodenkunde|soil|forst|forest|waldbau|"
     r"gartenbau|nutztier|animal science|landwirtschaft", "401"),
    (r"veterinär|veterinary|tiermedizin|tierschutz|tierhaltung|animal welfare", "403"),
    # Sozialwissenschaften
    (r"psycholog", "501"),
    (r"betriebswirtschaft|volkswirtschaft|economics|business|management|"
     r"marketing|finanz|finance|accounting|rechnungswesen|controlling|"
     r"wirtschaftsinformatik|operations research", "502"),
    (r"bildungswissenschaft|erziehungswissenschaft|pädagogik|education|didaktik", "503"),
    (r"soziolog|sociolog|sozialarbeit|social work|demograph", "504"),
    (r"recht|law|jurisprudenz|kriminolog|criminolog|öffentliches recht|public law|"
     r"privatrecht|strafrecht|völkerrecht", "505"),
    (r"politikwissenschaft|political science|internationale beziehungen|governance", "506"),
    (r"raumplanung|spatial planning|regionalplanung|regional development|"
     r"stadtplanung|urban planning|geograph|spatial sociolog", "507"),
    (r"kommunikationswissenschaft|medienwissenschaft|media studies|journalis", "509"),
    # Geisteswissenschaften
    (r"geschichte|history|archäolog|archaeolog|altertum|numismatik", "601"),
    (r"sprachwissenschaft|linguistik|linguistic|literatur|literature|philolog|"
     r"translation|übersetzen|romanistik|germanistik|anglistik|slawistik", "602"),
    (r"philosoph|ethik|ethics|theolog|religionswissenschaft", "603"),
    # Musikfächer: die mdw beruft auf Instrumente und Praxisfächer, nicht auf
    # Disziplinbezeichnungen. ÖFOS 604 deckt Kunst- und Musikwissenschaften ab.
    (r"violine|viola|violoncello|kontrabass|cello|geige|klavier|cembalo|orgel|"
     r"harfe|gitarre|blockflöte|flöte|oboe|klarinette|fagott|saxophon|trompete|"
     r"posaune|horn|tuba|schlaginstrument|schlagwerk|percussion|akkordeon|"
     r"gesang|lied|oratorium|stimmforschung|korrepetition|kammermusik|"
     r"orchester|dirigent|musikleitung|chorleitung|ensembleleitung|"
     r"tonsatz|gehörbildung|harmonielehre|kontrapunkt|musiktheorie|"
     r"musikpädagogik|instrumentalpädagogik|rhythmik|musiktherapie|"
     r"musikphysiologie|popularmusik|jazz|tasteninstrument|blasinstrument|"
     r"streichinstrument|alte musik|neue musik|tonmeister|musikproduktion|"
     r"elektroakustik|medienkomposition|regie|schauspiel|dramaturgie|"
     r"musikdramatisch|szenisch|bühne|tanz|choreograf|film|fernsehen|"
     r"produktion|kamera|schnitt|drehbuch|kulturmanagement|"
     r"rollengestaltung|körperliche gestaltung|musikalische akustik|"
     r"musikvermittlung|community music|ensemblearbeit", "604"),
    (r"kunstgeschichte|art history|kunstwissenschaft|musikwissenschaft|musicolog|"
     r"komposition|composition|dirigier|conducting|instrumental|gesang|voice|"
     r"schauspiel|acting|film|fotografie|photography|bildende kunst|fine art|"
     r"design|tonsatz|musikproduktion|elektroakustik|architekturtheorie", "604"),
    (r"kulturwissenschaft|cultural studies|gender studies|ethnolog|anthropolog", "605"),
]


def zuordnen(d):
    code = None
    kodex = str(d.get("fakultat_code") or "")
    if d.get("universitat") == "TU Wien" and kodex:
        for muster, c in ECODE:
            if re.match(muster, kodex):
                code = c
                break
    if not code:
        text = " ".join(filter(None, [d.get("forschungsbereich"), d.get("fakultat"),
                                      d.get("fakultat_institut")])).lower()
        for muster, c in STICHWORT:
            if re.search(muster, text):
                code = c
                break
    return code


def main():
    data = json.loads(DATA_PATH.read_text())
    gesetzt = 0
    for d in data:
        if d.get("ofos_code") and not d.get("_ofos_auto"):
            continue                                  # von Hand geprüft
        code = zuordnen(d)
        if not code:
            continue
        d["ofos_code"] = code
        d["ofos_label"] = LABEL[code]
        d["_ofos_auto"] = True
        gesetzt += 1

    offen = [d for d in data if not d.get("ofos_code")]
    if "--dry" not in sys.argv:
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"✓ ÖFOS automatisch gesetzt: {gesetzt} | ohne Code: {len(offen)} von {len(data)}")
    for d in offen[:12]:
        print(f"   offen: {d['name']} ({d['universitat']} {d['year']}) "
              f"— {d.get('forschungsbereich') or 'keine Bezeichnung'}")
    return data


if __name__ == "__main__":
    data = main()
    # Selbstcheck: Regeln greifen und kuratierte Codes bleiben stehen
    assert all(d["ofos_code"] in LABEL or not d.get("_ofos_auto")
               for d in data if d.get("ofos_code")), "unbekannter Code gesetzt"
    probe = {
        "universitat": "TU Wien", "fakultat_code": "E194",
        "forschungsbereich": "University Professor for Software and Systems Engineering",
    }
    assert zuordnen(probe) == "102", zuordnen(probe)
    assert zuordnen({"forschungsbereich": "Professur für Herzchirurgie"}) == "302"
    assert zuordnen({"forschungsbereich": "Professur für Tonsatz"}) == "604"
    assert zuordnen({"forschungsbereich": "Universitätsprofessur für Öffentliches Recht"}) == "505"
    assert zuordnen({"forschungsbereich": "Nichts dergleichen"}) is None
    print("✓ Selbstcheck ok")
