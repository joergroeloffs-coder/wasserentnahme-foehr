#!/usr/bin/env python3
"""
Erzeugt eine übersichtliche, farbige Excel-Liste mit individuellen
Zugangslinks für die Nutzerversion (je Empfänger ein eigener ?zugang=-Code).

Geräte-Limit über die erste Ziffer des Codes festgelegt (siehe Cloudflare-
Worker): Codes, die mit "1" beginnen, funktionieren auf 1 Gerät; Codes, die
mit "2" beginnen, auf 2 Geräten.

Jede Zeile enthält:
  - Zugangscode (mit Geräte-Limit als erste Ziffer), farbig nach Geräte-Limit
  - Testlink (31 Tage ab erstem Öffnen, automatisch)
  - Freigabe-Link (zusätzlich &freigabe=1 -> 365 Tage ab Öffnen dieses
    Links; erst verschicken, wenn der Empfänger sich für die dauerhafte
    Nutzung entschieden hat)
  - Ausgegeben am / Empfänger: leer, zum selbst Eintragen
  - Status: Dropdown-Auswahl mit Farbmarkierung (Frei / Vergeben / Testphase /
    Freigegeben / Gekündigt)

Nutzung:
  python3 werkzeuge/zugaenge_erzeugen.py [anzahl_1geraet] [anzahl_2geraete] [ausgabe.xlsx]
"""

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

BASIS_URL = "https://foehr.roewise.com/nutzer/"
START_1GERAET = 10000001
START_2GERAETE = 20000001

FARBE_KOPF = "1F2937"
FARBE_1GERAET = "DCEEFB"
FARBE_2GERAETE = "D8F5E3"
FARBE_STATUS_FREI = "F3F4F6"
FARBE_STATUS_VERGEBEN = "FDE68A"
FARBE_STATUS_TEST = "BFDBFE"
FARBE_STATUS_FREIGEGEBEN = "BBF7D0"
FARBE_STATUS_GEKUENDIGT = "FCA5A5"

STATUS_OPTIONEN = ["Frei", "Vergeben", "Testphase", "Freigegeben", "Gekündigt"]

DUENNER_RAHMEN = Border(
    left=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="D1D5DB"),
    top=Side(style="thin", color="D1D5DB"),
    bottom=Side(style="thin", color="D1D5DB"),
)


def zeile(ws, zeilennr, nr, code, geraete):
    testlink = f"{BASIS_URL}?zugang={code}"
    freigabelink = f"{BASIS_URL}?zugang={code}&freigabe=1"
    werte = [nr, code, geraete, testlink, freigabelink, "", "", "Frei"]
    for spalte, wert in enumerate(werte, start=1):
        zelle = ws.cell(row=zeilennr, column=spalte, value=wert)
        zelle.border = DUENNER_RAHMEN
        zelle.alignment = Alignment(vertical="center")

    geraete_zelle = ws.cell(row=zeilennr, column=3)
    geraete_zelle.fill = PatternFill("solid", fgColor=FARBE_1GERAET if geraete == 1 else FARBE_2GERAETE)
    geraete_zelle.alignment = Alignment(horizontal="center", vertical="center")

    code_zelle = ws.cell(row=zeilennr, column=2)
    code_zelle.alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[zeilennr].height = 22


def main():
    anzahl_1 = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    anzahl_2 = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    ausgabe = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("Zugaenge_Foehr.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "Zugänge"

    kopf = ["Nr.", "Zugangscode", "Geräte", "Testlink", "Freigabe-Link", "Ausgegeben am", "Empfänger", "Status"]
    ws.append(kopf)
    ws.row_dimensions[1].height = 30
    for zelle in ws[1]:
        zelle.font = Font(bold=True, color="FFFFFF", size=11)
        zelle.fill = PatternFill("solid", fgColor=FARBE_KOPF)
        zelle.alignment = Alignment(horizontal="center", vertical="center")

    zeilennr = 2
    nr = 1
    for i in range(anzahl_1):
        zeile(ws, zeilennr, nr, START_1GERAET + i, 1)
        zeilennr += 1
        nr += 1
    for i in range(anzahl_2):
        zeile(ws, zeilennr, nr, START_2GERAETE + i, 2)
        zeilennr += 1
        nr += 1

    letzte_zeile = zeilennr - 1

    # Dropdown-Auswahl für Status
    dv = DataValidation(type="list", formula1=f'"{",".join(STATUS_OPTIONEN)}"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H2:H{letzte_zeile}")

    # Farbmarkierung je nach gewähltem Status
    status_farben = {
        "Frei": FARBE_STATUS_FREI,
        "Vergeben": FARBE_STATUS_VERGEBEN,
        "Testphase": FARBE_STATUS_TEST,
        "Freigegeben": FARBE_STATUS_FREIGEGEBEN,
        "Gekündigt": FARBE_STATUS_GEKUENDIGT,
    }
    for text, farbe in status_farben.items():
        ws.conditional_formatting.add(
            f"H2:H{letzte_zeile}",
            CellIsRule(operator="equal", formula=[f'"{text}"'], fill=PatternFill("solid", fgColor=farbe)),
        )

    breiten = [6, 14, 9, 42, 50, 15, 22, 14]
    for idx, breite in enumerate(breiten, start=1):
        ws.column_dimensions[chr(64 + idx)].width = breite

    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = False
    wb.save(ausgabe)
    print(f"Erstellt: {ausgabe} ({anzahl_1} Zugänge mit 1 Gerät, {anzahl_2} Zugänge mit 2 Geräten)")


if __name__ == "__main__":
    main()
