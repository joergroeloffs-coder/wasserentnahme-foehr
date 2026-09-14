#!/usr/bin/env python3
"""
Erzeugt eine Excel-Liste mit individuellen Zugangslinks für die
Nutzerversion (je Empfänger ein eigener ?zugang=-Code).

Jede Zeile enthält:
  - Zugangscode
  - Testlink (62 -> jetzt 31 Tage ab erstem Öffnen, automatisch)
  - Freigabe-Link (zusätzlich &freigabe=1 -> 365 Tage ab Öffnen dieses
    Links; erst verschicken, wenn der Empfänger sich für die dauerhafte
    Nutzung entschieden hat)
  - Ausgegeben am / Status: leer, zum selbst Eintragen

Nutzung:
  python3 werkzeuge/zugaenge_erzeugen.py [anzahl] [ausgabe.xlsx]
"""

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

BASIS_URL = "https://joergroeloffs-coder.github.io/wasserentnahme-foehr/nutzer/"
START_CODE = 10000001


def main():
    anzahl = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    ausgabe = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Zugaenge_Foehr.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "Zugänge"

    kopf = ["Nr.", "Zugangscode", "Testlink", "Freigabe-Link", "Ausgegeben am", "Empfänger", "Status"]
    ws.append(kopf)
    for zelle in ws[1]:
        zelle.font = Font(bold=True)

    for i in range(anzahl):
        code = START_CODE + i
        testlink = f"{BASIS_URL}?zugang={code}"
        freigabelink = f"{BASIS_URL}?zugang={code}&freigabe=1"
        ws.append([i + 1, code, testlink, freigabelink, "", "", ""])

    breiten = [5, 14, 46, 54, 14, 20, 14]
    for idx, breite in enumerate(breiten, start=1):
        ws.column_dimensions[chr(64 + idx)].width = breite

    ws.freeze_panes = "A2"
    wb.save(ausgabe)
    print(f"Erstellt: {ausgabe} ({anzahl} Zugänge)")


if __name__ == "__main__":
    main()
