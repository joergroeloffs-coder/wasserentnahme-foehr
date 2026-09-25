#!/usr/bin/env python3
"""
Verarbeitet Korrektur-Meldungen aus der Nutzer-App (E-Mails an die in
config.js hinterlegte Kontaktadresse)
und übernimmt sie nach Bestätigung in daten/stellen.geojson.

Nutzung:
  1. E-Mail-Text (Betreff egal, Body wichtig) in eine .txt-Datei kopieren
     (mehrere Meldungen können zusammen in einer Datei stehen).
  2. python3 werkzeuge/korrektur_verarbeiten.py pfad/zur/datei.txt
  3. Für jede erkannte Korrektur wird die aktuelle und gemeldete Position
     sowie der Abstand in Metern angezeigt. Mit j/n einzeln bestätigen.
  4. Bestätigte Korrekturen werden in daten/stellen.geojson übernommen,
     committet und per "git push" veröffentlicht.

Erkennt nur Blöcke vom Typ "MELDUNG: Korrektur" (mit Ref-Nummer). Ein Block
kann eine neue Position, geänderte Angaben (Ortschaft, Straße/Lage, Typ,
Bemerkung) oder beides enthalten - je nachdem, was in der App ausgefüllt
wurde.
Blöcke vom Typ "MELDUNG: Eigene Position" (ohne Ref, z.B. Hinweis auf
fehlende Wasserstelle) werden nur angezeigt, nicht automatisch verarbeitet.
"""

import json
import math
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATEN_PFAD = REPO_ROOT / "daten" / "stellen.geojson"

BLOCK_RE = re.compile(r"MELDUNG:\s*(.+)")

# Manche Mail-Apps schicken den Text ohne Zeilenumbrüche (alles eine Zeile,
# durch Leerzeichen getrennt) statt wie von der App vorgesehen mit \n. Vor
# jedem bekannten Feldnamen wird deshalb ein Zeilenumbruch erzwungen, egal
# wie der Text tatsächlich ankommt - das macht die Erkennung robust gegen
# solche Mail-Client-Eigenheiten.
FELD_LABEL_RE = re.compile(
    r"\s*(?=(MELDUNG:|Ref:|Bezeichnung:|Neue Position:|Genauigkeit:|Bisherige Position \(App\):"
    r"|Neue Ortschaft:|Neue Straße/Lage:|Neuer Typ:|Neue Bemerkung:))"
)

# Ordnet ein Feldlabel aus der Mail der zugehoerigen GeoJSON-Eigenschaft zu.
# "Straße/Lage" landet auf "name", weil geoJsonZuStellen() in der App genau
# dieses Feld zuerst fuer s.ort liest (siehe nutzer/index.html).
DATENFELD_ZU_EIGENSCHAFT = {
    "neue ortschaft": "addr:city",
    "neue straße/lage": "name",
    "neuer typ": "art",
    "neue bemerkung": "description",
}


def normalisiere_zeilenumbrueche(text):
    return FELD_LABEL_RE.sub("\n", text).strip()


def parse_meldungen(text):
    """Zerlegt den Text in einzelne MELDUNG-Blöcke."""
    text = normalisiere_zeilenumbrueche(text)
    starts = [m.start() for m in BLOCK_RE.finditer(text)]
    starts.append(len(text))
    bloecke = []
    for i in range(len(starts) - 1):
        block_text = text[starts[i]:starts[i + 1]]
        typ_match = BLOCK_RE.search(block_text)
        typ = typ_match.group(1).strip() if typ_match else "?"
        felder = {}
        for zeile in block_text.splitlines()[1:]:
            if ":" in zeile:
                key, _, val = zeile.partition(":")
                felder[key.strip().lower()] = val.strip()
        bloecke.append((typ, felder))
    return bloecke


def parse_koordinate(wert):
    teile = [t.strip() for t in wert.split(",")]
    if len(teile) != 2:
        return None
    try:
        return float(teile[0]), float(teile[1])
    except ValueError:
        return None


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def verarbeite_text(text):
    """Verarbeitet den Text einer oder mehrerer MELDUNG-Mails interaktiv
    (Rückfrage je Korrektur, am Ende Rückfrage für Commit + Push)."""
    bloecke = parse_meldungen(text)
    if not bloecke:
        print("Keine MELDUNG-Blöcke gefunden.")
        return

    rohdaten = DATEN_PFAD.read_bytes()
    hatte_trailing_newline = rohdaten.endswith(b"\n")
    daten = json.loads(rohdaten)
    features_nach_ref = {f["properties"].get("ref"): f for f in daten["features"]}

    uebernommene_refs = []

    for typ, felder in bloecke:
        if typ.strip().lower() != "korrektur":
            if felder:
                print(f"\n--- MELDUNG: {typ} (nicht automatisch verarbeitet) ---")
                for k, v in felder.items():
                    print(f"  {k}: {v}")
            continue

        ref = felder.get("ref", "").strip()
        neue_pos = parse_koordinate(felder.get("neue position", ""))
        datenaenderungen = {
            DATENFELD_ZU_EIGENSCHAFT[label]: felder[label]
            for label in DATENFELD_ZU_EIGENSCHAFT
            if felder.get(label)
        }
        if not ref or (not neue_pos and not datenaenderungen):
            print(f"\n--- Korrektur ohne verwertbare Ref/Position/Angaben übersprungen: {felder} ---")
            continue

        feature = features_nach_ref.get(ref)
        if feature is None:
            print(f"\n--- Ref '{ref}' nicht in {DATEN_PFAD.name} gefunden — übersprungen ---")
            continue

        print(f"\n--- Korrektur Ref {ref} ({felder.get('bezeichnung', '')}) ---")

        neu_lat = neu_lon = None
        if neue_pos:
            alt_lon, alt_lat = feature["geometry"]["coordinates"]
            neu_lat, neu_lon = neue_pos
            distanz = haversine_m(alt_lat, alt_lon, neu_lat, neu_lon)
            print(f"  Bisher:   {alt_lat:.5f}, {alt_lon:.5f}")
            print(f"  Gemeldet: {neu_lat:.5f}, {neu_lon:.5f}")
            print(f"  Abstand:  {distanz:.0f} m")
            if felder.get("genauigkeit"):
                print(f"  Genauigkeit der Meldung: {felder['genauigkeit']}")
            if distanz > 200:
                print("  ACHTUNG: großer Abstand — bitte besonders sorgfältig prüfen.")

        if datenaenderungen:
            print("  Geänderte Angaben:")
            for eigenschaft, neuer_wert in datenaenderungen.items():
                bisheriger_wert = feature["properties"].get(eigenschaft, "")
                print(f"    {eigenschaft}: '{bisheriger_wert}' -> '{neuer_wert}'")

        antwort = input("  Übernehmen? (j/n): ").strip().lower()
        if antwort == "j":
            if neu_lat is not None:
                feature["geometry"]["coordinates"] = [neu_lon, neu_lat]
            for eigenschaft, neuer_wert in datenaenderungen.items():
                feature["properties"][eigenschaft] = neuer_wert
            uebernommene_refs.append(ref)
        else:
            print("  -> verworfen")

    if not uebernommene_refs:
        print("\nKeine Korrektur übernommen, nichts zu tun.")
        return

    ausgabe = json.dumps(daten, ensure_ascii=False, indent=1)
    if hatte_trailing_newline:
        ausgabe += "\n"
    DATEN_PFAD.write_text(ausgabe, encoding="utf-8")

    commit_msg = "Positionskorrektur: Ref " + ", ".join(uebernommene_refs)
    print(f"\nÜbernommen: {', '.join(uebernommene_refs)}")

    antwort = input("Jetzt committen und pushen? (j/n): ").strip().lower()
    if antwort != "j":
        print("Datei ist geändert, aber noch nicht committet/gepusht.")
        return

    subprocess.run(["git", "add", str(DATEN_PFAD)], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, check=True)

    # Vor dem Push zuerst mit GitHub abgleichen, damit ein Push nicht wegen
    # zwischenzeitlich anderswo veroeffentlichter Aenderungen abgelehnt wird.
    print("Aktualisiere zuerst mit dem neuesten Stand von GitHub …")
    pull = subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=REPO_ROOT)
    if pull.returncode != 0:
        print(
            "\nAchtung: Das automatische Abgleichen mit GitHub ist fehlgeschlagen "
            "(z. B. weil dieselbe Stelle gleichzeitig woanders geändert wurde).\n"
            "Dein Commit ist lokal sicher, aber noch nicht hochgeladen.\n"
            "Bitte im Terminal prüfen: 'git status', Konflikt lösen, dann "
            "'git rebase --continue' und 'git push origin main'."
        )
        return

    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
    print("Fertig — gepusht.")


def main():
    if len(sys.argv) != 2:
        print("Nutzung: python3 werkzeuge/korrektur_verarbeiten.py pfad/zur/mail.txt")
        sys.exit(1)
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    verarbeite_text(text)


if __name__ == "__main__":
    main()
