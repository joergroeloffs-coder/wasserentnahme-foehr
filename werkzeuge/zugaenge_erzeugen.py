#!/usr/bin/env python3
"""
Erzeugt eine Excel-Liste mit individuellen Zugangslinks für die
Nutzerversion (je Empfänger ein eigener ?zugang=-Code).

Geräte-Limit über die erste Ziffer des Codes festgelegt (siehe Cloudflare-
Worker): Codes, die mit "1" beginnen, funktionieren auf 1 Gerät; Codes, die
mit "2" beginnen, auf 2 Geräten.

Jede Zeile enthält:
  - Zugangscode (mit Geräte-Limit als erste Ziffer)
  - Testlink (31 Tage ab erstem Öffnen, automatisch)
  - Freigabe-Link (zusätzlich &freigabe=1 -> 365 Tage ab Öffnen dieses
    Links; erst verschicken, wenn der Empfänger sich für die dauerhafte
    Nutzung entschieden hat)
  - Ausgegeben am / Status: leer, zum selbst Eintragen

Nutzung:
  python3 werkzeuge/zugaenge_erzeugen.py [anzahl_1geraet] [anzahl_2geraete] [ausgabe.xlsx]
"""

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

BASIS_URL = "https://foehr.roewise.com/nutzer/"
START_1GERAET = 10000001
START_2GERAETE = 20000001


def zeile(ws, nr, code, geraete):
    testlink = f"{BASIS_URL}?zugang={code}"
    freigabelink = f"{BASIS_URL}?zugang={code}&freigabe=1"
    ws.append([nr, code, geraete, testlink, freigabelink, "", "", ""])


def main():
    anzahl_1 = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    anzahl_2 = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    ausgabe = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("Zugaenge_Foehr.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "Zugänge"

    kopf = ["Nr.", "Zugangscode", "Geräte-Limit", "Testlink", "Freigabe-Link", "Ausgegeben am", "Empfänger", "Status"]
    ws.append(kopf)
    for zelle in ws[1]:
        zelle.font = Font(bold=True)

    nr = 1
    for i in range(anzahl_1):
        zeile(ws, nr, START_1GERAET + i, 1)
        nr += 1
    for i in range(anzahl_2):
        zeile(ws, nr, START_2GERAETE + i, 2)
        nr += 1

    breiten = [5, 14, 12, 42, 50, 14, 20, 14]
    for idx, breite in enumerate(breiten, start=1):
        ws.column_dimensions[chr(64 + idx)].width = breite

    ws.freeze_panes = "A2"
    wb.save(ausgabe)
    print(f"Erstellt: {ausgabe} ({anzahl_1} Zugänge mit 1 Gerät, {anzahl_2} Zugänge mit 2 Geräten)")


if __name__ == "__main__":
    main()
