#!/usr/bin/env python3
"""
Übernimmt geprüfte Adressvorschläge aus werkzeuge/adressvorschlaege.csv
(erzeugt von adressen_vorschlagen.py) in daten/stellen.geojson.

Nur Zeilen, bei denen in der Spalte "uebernehmen" ein "j" steht, werden
übernommen. Am Ende wird gefragt, ob committet und gepusht werden soll.

Nutzung:
  python3 werkzeuge/adressen_uebernehmen.py
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATEN_PFAD = REPO_ROOT / "daten" / "stellen.geojson"
CSV_PFAD = REPO_ROOT / "werkzeuge" / "adressvorschlaege.csv"


def main():
    if not CSV_PFAD.exists():
        print(f"Keine Datei gefunden: {CSV_PFAD}")
        print("Erst werkzeuge/adressen_vorschlagen.py ausführen.")
        sys.exit(1)

    with CSV_PFAD.open(newline="", encoding="utf-8-sig") as f:
        zeilen = list(csv.DictReader(f, delimiter=";"))

    uebernahmen = {
        z["ref"]: z["vorschlag"] for z in zeilen
        if z.get("uebernehmen", "").strip().lower() == "j" and z.get("vorschlag", "").strip()
    }

    if not uebernahmen:
        print('Keine Zeile mit "j" in der Spalte uebernehmen gefunden. Nichts zu tun.')
        return

    rohdaten = DATEN_PFAD.read_bytes()
    hatte_trailing_newline = rohdaten.endswith(b"\n")
    daten = json.loads(rohdaten)

    geaendert = []
    for feature in daten["features"]:
        ref = feature["properties"].get("ref")
        if ref in uebernahmen:
            feature["properties"]["name"] = uebernahmen[ref]
            geaendert.append(ref)

    if not geaendert:
        print("Keine passenden Refs in stellen.geojson gefunden.")
        return

    ausgabe = json.dumps(daten, ensure_ascii=False, indent=1)
    if hatte_trailing_newline:
        ausgabe += "\n"
    DATEN_PFAD.write_text(ausgabe, encoding="utf-8")

    print(f"{len(geaendert)} Lage-Texte übernommen: {', '.join(geaendert)}")

    antwort = input("Jetzt committen und pushen? (j/n): ").strip().lower()
    if antwort != "j":
        print("Datei ist geändert, aber noch nicht committet/gepusht.")
        return

    commit_msg = f"Lage-Texte ergaenzt fuer {len(geaendert)} Stellen (Adressvorschlaege)"
    subprocess.run(["git", "add", str(DATEN_PFAD)], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
    print("Fertig — gepusht.")


if __name__ == "__main__":
    main()
