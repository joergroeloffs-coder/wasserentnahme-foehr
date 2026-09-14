#!/usr/bin/env python3
"""
Überträgt die "Kern"-Dateien (identischer App-Code, unabhängig von der
Gemeinde) aus diesem Repository (wasserentnahme-foehr, als Referenz-
Quelle) in andere Gemeinde-Repositorys.

NICHT übertragen werden die ortsspezifischen Dateien - die bleiben in
jedem Ziel-Repo unverändert:
  - config.js               (Kartenmittelpunkt, Kontakt-Mail, Schlüssel-Präfix, ...)
  - daten/                  (stellen.geojson, eigene *.pmtiles-Kartendatei)
  - manifest.json (an 3 Stellen: /, nutzer/, nutzer-admin/)
  - icon*.png, icon.svg      (falls je Gemeinde eigenes Branding gewünscht)
  - README.md

Nutzung:
  python3 werkzeuge/sync_core.py /pfad/zu/wasserentnahme-leck [weitere-pfade...]

  Optional --push: committet und pusht die Änderung in jedem Ziel-Repo
  automatisch (sonst bleiben die Dateien nur lokal geändert, zum selbst
  Prüfen/Committen).

Muss aus dem wasserentnahme-foehr-Repo heraus aufgerufen werden (der Ordner,
in dem dieses Skript liegt, wird als Quelle verwendet).
"""

import shutil
import subprocess
import sys
from pathlib import Path

QUELLE = Path(__file__).resolve().parent.parent

# Einzeldateien, die 1:1 kopiert werden.
KERN_DATEIEN = [
    "index.html",
    "sw.js",
    "nutzer/index.html",
    "nutzer/sw.js",
    "nutzer-admin/index.html",
    "nutzer-admin/sw.js",
    "werkzeuge/korrektur_verarbeiten.py",
    "werkzeuge/mail_abrufen.py",
    "werkzeuge/Korrekturen_abrufen.bat",
]

# anleitung/index.html bewusst NICHT im Kern: enthält Ort-spezifischen
# Fließtext (Repo-Pfad, Ortsname "Föhr"/"Insel") statt Config-Werten.

# Ganze Ordner, die komplett gespiegelt werden (Zielinhalt wird vorher
# gelöscht, damit auch entfernte Dateien beim Ziel verschwinden).
KERN_ORDNER = [
    "vendor",
]

# Diese Pfade werden NIE angefasst, selbst wenn sie zufällig unter einem
# der obigen Ordner lägen (zur Sicherheit doppelt abgesichert).
NIEMALS_ANFASSEN = {"config.js", "daten", "manifest.json", "README.md"}


def kopiere_datei(rel_pfad, ziel_repo):
    quelle_datei = QUELLE / rel_pfad
    ziel_datei = ziel_repo / rel_pfad
    if not quelle_datei.exists():
        print(f"  WARNUNG: Quelle fehlt, übersprungen: {rel_pfad}")
        return False
    ziel_datei.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(quelle_datei, ziel_datei)
    return True


def kopiere_ordner(rel_pfad, ziel_repo):
    if rel_pfad in NIEMALS_ANFASSEN:
        return
    quelle_ordner = QUELLE / rel_pfad
    ziel_ordner = ziel_repo / rel_pfad
    if not quelle_ordner.exists():
        print(f"  WARNUNG: Quellordner fehlt, übersprungen: {rel_pfad}")
        return
    if ziel_ordner.exists():
        shutil.rmtree(ziel_ordner)
    shutil.copytree(quelle_ordner, ziel_ordner)


def sync_ziel(ziel_repo, push):
    print(f"\n=== {ziel_repo.name} ===")
    if not (ziel_repo / ".git").exists():
        print("  Kein Git-Repository an diesem Pfad, übersprungen.")
        return

    geaendert = []
    for rel in KERN_DATEIEN:
        if rel in NIEMALS_ANFASSEN:
            continue
        if kopiere_datei(rel, ziel_repo):
            geaendert.append(rel)

    for rel in KERN_ORDNER:
        kopiere_ordner(rel, ziel_repo)
        geaendert.append(rel + "/")

    print("  Kopiert:", ", ".join(geaendert))

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ziel_repo, capture_output=True, text=True
    ).stdout.strip()
    if not status:
        print("  Keine Änderungen (Ziel war bereits aktuell).")
        return

    print("  Geänderte Dateien laut git status:")
    for zeile in status.splitlines():
        print("   ", zeile)

    if not push:
        print("  --push nicht angegeben, nichts committet/gepusht.")
        return

    subprocess.run(["git", "add", "-A"], cwd=ziel_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Kern-Dateien synchronisiert (sync_core.py)"],
        cwd=ziel_repo, check=True
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=ziel_repo, check=True)
    print("  Committet und gepusht.")


def main():
    args = sys.argv[1:]
    push = "--push" in args
    ziele = [Path(a).resolve() for a in args if a != "--push"]
    if not ziele:
        print(__doc__)
        sys.exit(1)
    for ziel in ziele:
        sync_ziel(ziel, push)


if __name__ == "__main__":
    main()
