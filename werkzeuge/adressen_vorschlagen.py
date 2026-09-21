#!/usr/bin/env python3
"""
Schlägt für Stellen ohne Lage-Text (Straße + Hausnummer oder ähnliches
Merkmal in der Nähe) automatisch eine Beschreibung vor, basierend auf der
gespeicherten Position. Nutzt die kostenlose OpenStreetMap-Adresssuche
(Nominatim).

Wichtig: Die Vorschläge werden NICHT automatisch übernommen. Sie landen in
einer CSV-Datei zur Prüfung. Erst nach Kontrolle und Markierung der
gewünschten Zeilen mit "j" in der Spalte "uebernehmen" werden sie mit
adressen_uebernehmen.py in die Karten-Datei eingetragen.

Nutzung:
  python3 werkzeuge/adressen_vorschlagen.py

Läuft mit 1 Anfrage pro Sekunde (Vorgabe von Nominatim für einmalige,
nicht-automatisierte Nutzung durch eine Person). Bei ca. 700 offenen
Punkten dauert der Lauf entsprechend ca. 12 Minuten.
"""

import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATEN_PFAD = REPO_ROOT / "daten" / "stellen.geojson"
AUSGABE_PFAD = REPO_ROOT / "werkzeuge" / "adressvorschlaege.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "LoeschbaertApp-Foehr-Adressvorschlag/1.0 (wasserentnahme-foehr@web.de, einmaliger manueller Lauf)"
PAUSE_SEKUNDEN = 1.1


def reverse_geocode(lat, lon):
    params = {
        "lat": lat, "lon": lon, "format": "jsonv2",
        "zoom": 18, "addressdetails": 1,
    }
    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def baue_vorschlag(adresse):
    strasse = adresse.get("road") or adresse.get("pedestrian") or adresse.get("footway") or ""
    hausnr = adresse.get("house_number") or ""
    if strasse and hausnr:
        return f"{strasse} {hausnr}"
    if strasse:
        return f"nahe {strasse}"
    merkmal = (adresse.get("hamlet") or adresse.get("suburb")
               or adresse.get("village") or adresse.get("neighbourhood") or "")
    return merkmal


def main():
    daten = json.loads(DATEN_PFAD.read_text(encoding="utf-8"))
    offen = [f for f in daten["features"] if not (f["properties"].get("name") or "").strip()]
    if not offen:
        print("Alle Stellen haben bereits einen Lage-Text. Nichts zu tun.")
        return

    minuten = len(offen) * PAUSE_SEKUNDEN / 60
    print(f"{len(offen)} Stellen ohne Lage-Text. Starte Abfrage (ca. {minuten:.0f} Minuten) ...")

    zeilen = []
    for i, feature in enumerate(offen, start=1):
        p = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        ref = p.get("ref", "")
        try:
            ergebnis = reverse_geocode(lat, lon)
            adresse = ergebnis.get("address", {})
            vorschlag = baue_vorschlag(adresse)
            osm_display = ergebnis.get("display_name", "")
        except Exception as e:
            vorschlag = ""
            osm_display = f"FEHLER: {e}"

        print(f"[{i}/{len(offen)}] Ref {ref}: {vorschlag or '(kein Vorschlag)'}")
        zeilen.append({
            "ref": ref,
            "ortschaft": p.get("addr:city", ""),
            "typ": p.get("art", ""),
            "vorschlag": vorschlag,
            "osm_adresse_komplett": osm_display,
            "lat": lat,
            "lon": lon,
            "uebernehmen": "",
        })
        time.sleep(PAUSE_SEKUNDEN)

    with AUSGABE_PFAD.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ref", "ortschaft", "typ", "vorschlag", "osm_adresse_komplett",
            "lat", "lon", "uebernehmen",
        ], delimiter=";")
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\nFertig. {len(zeilen)} Vorschläge in {AUSGABE_PFAD.name} gespeichert.")
    print("Bitte in Excel/LibreOffice öffnen, prüfen und bei gewünschten Zeilen")
    print('in der Spalte "uebernehmen" ein j eintragen. Danach:')
    print("  python3 werkzeuge/adressen_uebernehmen.py")


if __name__ == "__main__":
    main()
