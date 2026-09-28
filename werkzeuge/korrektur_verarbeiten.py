#!/usr/bin/env python3
"""
Verarbeitet Korrektur-Meldungen aus der Nutzer-App (E-Mails an die in
config.js hinterlegte Kontaktadresse)
und übernimmt sie nach Bestätigung in daten/stellen.geojson.

Nutzung:
  1. E-Mail-Text (Betreff egal, Body wichtig) in eine .txt-Datei kopieren
     (mehrere Meldungen können zusammen in einer Datei stehen).
  2. python3 werkzeuge/korrektur_verarbeiten.py pfad/zur/datei.txt
  3. Für jede Ref-Nummer werden alle gefundenen Meldungen zusammen
     angezeigt (auch aus mehreren Mails, z.B. bei einer Funk- und
     Fahrübung mit mehreren Fahrzeugen). Bei mehreren Positionsmeldungen
     zum selben Hydranten wird der Mittelwert vorgeschlagen; bei
     widersprüchlichen Textangaben (Ortschaft, Bemerkung usw.) wird zur
     Auswahl gestellt. Eine Kartenvorschau (bisherige vs. neue Position)
     öffnet sich automatisch im Browser. Mit j/n je Ref bestätigen.
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
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATEN_PFAD = REPO_ROOT / "daten" / "stellen.geojson"
VORSCHAU_PFAD = Path(__file__).resolve().parent / "_vorschau_temp.html"

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


def erzeuge_kartenvorschau(alt_lat, alt_lon, neu_lat, neu_lon, bezeichnung):
    """Erstellt eine kleine HTML-Seite mit Leaflet-Karte (bisherige Position
    rot, neu gemeldete Position grün) und öffnet sie im Standardbrowser, damit
    vor der Übernahme sichtbar ist, ob die neue Position wirklich plausibler
    liegt. Nutzt die im Repo vorhandenen Leaflet-Dateien (kein Download
    nötig), die Kartenkacheln selbst kommen live von OpenStreetMap - dafür
    ist eine Internetverbindung nötig."""
    inhalt = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Kartenvorschau: {bezeichnung}</title>
<link rel="stylesheet" href="../vendor/leaflet.css">
<style>html,body,#karte{{height:100%;margin:0;font-family:system-ui,sans-serif}}</style>
</head><body><div id="karte"></div>
<script src="../vendor/leaflet.js"></script>
<script>
var karte = L.map('karte');
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19, attribution: '&copy; OpenStreetMap-Mitwirkende'
}}).addTo(karte);
var alt = L.circleMarker([{alt_lat}, {alt_lon}], {{radius:10, color:'#e23c22', fillColor:'#e23c22', fillOpacity:0.85}})
  .addTo(karte).bindTooltip("Bisherige Position", {{permanent:true, direction:'left'}});
var neu = L.circleMarker([{neu_lat}, {neu_lon}], {{radius:10, color:'#22c55e', fillColor:'#22c55e', fillOpacity:0.85}})
  .addTo(karte).bindTooltip("Neu gemeldet", {{permanent:true, direction:'right'}});
karte.fitBounds([[{alt_lat},{alt_lon}],[{neu_lat},{neu_lon}]], {{padding:[80,80], maxZoom:19}});
</script></body></html>"""
    VORSCHAU_PFAD.write_text(inhalt, encoding="utf-8")
    webbrowser.open(VORSCHAU_PFAD.resolve().as_uri())


def parse_alle_meldungen(quellen):
    """quellen: Liste von (label, text) - i.d.R. eine pro E-Mail. Gibt eine
    flache Liste (ref, typ, felder, label) zurück."""
    alle = []
    for label, text in quellen:
        for typ, felder in parse_meldungen(text):
            ref = felder.get("ref", "").strip() if typ.strip().lower() == "korrektur" else ""
            alle.append((ref, typ, felder, label))
    return alle


def speichere_und_veroeffentliche(daten, hatte_trailing_newline, uebernommene_refs):
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
    # Wenn die gemeldeten Werte exakt den bereits gespeicherten entsprechen
    # (z. B. Position auf 0 m genau bestaetigt), gibt es nichts zu committen -
    # 'git commit' wuerde dann mit "nothing to commit" fehlschlagen. Trotzdem
    # wird unten weiter zu pushen versucht, falls noch fruehere, lokal
    # committete aber nie hochgeladene Aenderungen warten.
    keine_aenderung = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT
    ).returncode == 0
    if keine_aenderung:
        print("Keine inhaltliche Änderung an der Datei - nichts Neues zu committen.")
    else:
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


def verarbeite_mails(quellen):
    """quellen: Liste von (label, text), i.d.R. eine pro E-Mail. Meldungen mit
    derselben Ref-Nummer aus verschiedenen Mails werden zusammen behandelt
    (z.B. mehrere Fahrzeuge bei einer Übung, die denselben Hydranten
    anfahren), statt jede Mail isoliert zu verarbeiten."""
    alle = parse_alle_meldungen(quellen)
    if not alle:
        print("Keine MELDUNG-Blöcke gefunden.")
        return

    for ref, typ, felder, label in alle:
        if typ.strip().lower() != "korrektur" and felder:
            print(f"\n--- [{label}] MELDUNG: {typ} (nicht automatisch verarbeitet) ---")
            for k, v in felder.items():
                print(f"  {k}: {v}")

    gruppiert = {}
    for ref, typ, felder, label in alle:
        if typ.strip().lower() == "korrektur" and ref:
            gruppiert.setdefault(ref, []).append((felder, label))

    if not gruppiert:
        return

    rohdaten = DATEN_PFAD.read_bytes()
    hatte_trailing_newline = rohdaten.endswith(b"\n")
    daten = json.loads(rohdaten)
    features_nach_ref = {f["properties"].get("ref"): f for f in daten["features"]}

    uebernommene_refs = []

    for ref, eintraege in gruppiert.items():
        feature = features_nach_ref.get(ref)
        if feature is None:
            print(f"\n--- Ref '{ref}' nicht in {DATEN_PFAD.name} gefunden — übersprungen ---")
            continue

        bezeichnung = eintraege[0][0].get("bezeichnung", "")
        anzahl_meldungen = len(eintraege)
        zusatz = f" — {anzahl_meldungen} Meldungen" if anzahl_meldungen > 1 else ""
        print(f"\n=== Korrektur Ref {ref} ({bezeichnung}){zusatz} ===")

        alt_lon, alt_lat = feature["geometry"]["coordinates"]

        positionen = []
        for felder, label in eintraege:
            pos = parse_koordinate(felder.get("neue position", ""))
            if pos:
                positionen.append((pos[0], pos[1], label, felder.get("genauigkeit", "")))

        neu_lat = neu_lon = None
        if positionen:
            if len(positionen) == 1:
                neu_lat, neu_lon, label, genauigkeit = positionen[0]
                zusatz2 = f" (Genauigkeit: {genauigkeit})" if genauigkeit else ""
                print(f"  [{label}] gemeldet: {neu_lat:.5f}, {neu_lon:.5f}{zusatz2}")
            else:
                print("  Mehrere Positionsmeldungen für diesen Hydranten:")
                for lat, lon, label, genauigkeit in positionen:
                    d = haversine_m(alt_lat, alt_lon, lat, lon)
                    zusatz2 = f", Genauigkeit: {genauigkeit}" if genauigkeit else ""
                    print(f"    [{label}] {lat:.5f}, {lon:.5f}  (Abstand zur bisherigen Position: {d:.0f} m{zusatz2})")
                neu_lat = sum(p[0] for p in positionen) / len(positionen)
                neu_lon = sum(p[1] for p in positionen) / len(positionen)
                streuung = max(
                    haversine_m(neu_lat, neu_lon, lat, lon) for lat, lon, _, _ in positionen
                )
                print(f"  -> Mittelwert: {neu_lat:.5f}, {neu_lon:.5f} (max. Streuung zum Mittelwert: {streuung:.0f} m)")

            distanz = haversine_m(alt_lat, alt_lon, neu_lat, neu_lon)
            print(f"  Bisher:   {alt_lat:.5f}, {alt_lon:.5f}")
            print(f"  Neu:      {neu_lat:.5f}, {neu_lon:.5f}")
            print(f"  Abstand:  {distanz:.0f} m")
            if distanz > 200:
                print("  ACHTUNG: großer Abstand — bitte besonders sorgfältig prüfen.")

            try:
                erzeuge_kartenvorschau(alt_lat, alt_lon, neu_lat, neu_lon, bezeichnung)
                print("  (Kartenvorschau im Browser geöffnet — bisher rot, neu grün)")
            except Exception as fehler:
                print(f"  (Kartenvorschau konnte nicht erstellt werden: {fehler})")

        datenaenderungen = {}
        for feld_label, eigenschaft in DATENFELD_ZU_EIGENSCHAFT.items():
            werte = [(felder[feld_label], label) for felder, label in eintraege if felder.get(feld_label)]
            if not werte:
                continue
            eindeutige_werte = list(dict.fromkeys(w for w, _ in werte))
            if len(eindeutige_werte) == 1:
                datenaenderungen[eigenschaft] = eindeutige_werte[0]
            else:
                print(f"  Widersprüchliche Angaben bei '{feld_label}':")
                for i, wert in enumerate(eindeutige_werte, 1):
                    von = ", ".join(label for w, label in werte if w == wert)
                    print(f"    {i}) '{wert}'  (gemeldet von: {von})")
                auswahl = input(f"    Welchen Wert übernehmen? (1-{len(eindeutige_werte)}, leer = überspringen): ").strip()
                if auswahl.isdigit() and 1 <= int(auswahl) <= len(eindeutige_werte):
                    datenaenderungen[eigenschaft] = eindeutige_werte[int(auswahl) - 1]

        if datenaenderungen:
            print("  Zu übernehmende Angaben:")
            for eigenschaft, neuer_wert in datenaenderungen.items():
                bisheriger_wert = feature["properties"].get(eigenschaft, "")
                print(f"    {eigenschaft}: '{bisheriger_wert}' -> '{neuer_wert}'")

        if neu_lat is None and not datenaenderungen:
            print("  -> keine verwertbaren Angaben, übersprungen")
            continue

        antwort = input("  Übernehmen? (j/n): ").strip().lower()
        if antwort == "j":
            if neu_lat is not None:
                feature["geometry"]["coordinates"] = [neu_lon, neu_lat]
            for eigenschaft, neuer_wert in datenaenderungen.items():
                feature["properties"][eigenschaft] = neuer_wert
            uebernommene_refs.append(ref)
        else:
            print("  -> verworfen")

    speichere_und_veroeffentliche(daten, hatte_trailing_newline, uebernommene_refs)


def verarbeite_text(text):
    """Verarbeitet den Text einer einzelnen Quelle (z.B. eine Datei mit
    einer oder mehreren MELDUNG-Mails). Für den Aufruf per Kommandozeile mit
    einer .txt-Datei."""
    verarbeite_mails([("Datei", text)])


def main():
    if len(sys.argv) != 2:
        print("Nutzung: python3 werkzeuge/korrektur_verarbeiten.py pfad/zur/mail.txt")
        sys.exit(1)
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    verarbeite_text(text)


if __name__ == "__main__":
    main()
