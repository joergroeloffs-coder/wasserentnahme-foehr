#!/usr/bin/env python3
"""
Ruft ungelesene Korrektur-Mails direkt aus dem Postfach ab (IMAP) und
verarbeitet sie automatisch (ohne Rückfrage, siehe
korrektur_verarbeiten.verarbeite_text_automatisch): eindeutige Korrekturen
(Abstand deutlich größer als die gemeldete GPS-Ungenauigkeit, nicht
unplausibel groß) werden sofort übernommen, committet und gepusht. Uneindeutige
Fälle werden NICHT übernommen, sondern nach werkzeuge/zu_pruefen.txt
geschrieben — die dort mit "python werkzeuge/korrektur_verarbeiten.py
werkzeuge/zu_pruefen.txt" interaktiv (mit j/n) geprüft werden können.

Zugangsdaten stehen NICHT im Code, sondern in werkzeuge/zugangsdaten.json
(diese Datei ist in .gitignore und wird nie eingecheckt).

Nutzung:
  python3 werkzeuge/mail_abrufen.py

Es werden nur ungelesene Mails mit Betreff, der mit "Korrektur" beginnt,
geholt (die App verschickt genau solche Betreffs). Nach Verarbeitung
werden die Mails als gelesen markiert, damit sie beim nächsten Aufruf
nicht erneut auftauchen (der Text ist bei unklaren Fällen ja in
zu_pruefen.txt gesichert).
"""

import email
import imaplib
import json
import sys
from email.header import decode_header
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from korrektur_verarbeiten import verarbeite_text_automatisch  # noqa: E402

ZUGANGSDATEN_PFAD = Path(__file__).resolve().parent / "zugangsdaten.json"
IMAP_SERVER = "imap.web.de"
BETREFF_FILTER = "Korrektur"


def lade_zugangsdaten():
    if not ZUGANGSDATEN_PFAD.exists():
        print(f"Keine Zugangsdaten gefunden: {ZUGANGSDATEN_PFAD}")
        print('Bitte Datei anlegen mit Inhalt: {"email": "...", "app_passwort": "..."}')
        sys.exit(1)
    daten = json.loads(ZUGANGSDATEN_PFAD.read_text(encoding="utf-8"))
    if not daten.get("email") or not daten.get("app_passwort"):
        print("zugangsdaten.json unvollständig (email / app_passwort fehlt).")
        sys.exit(1)
    return daten["email"], daten["app_passwort"]


def dekodiere(wert):
    teile = decode_header(wert or "")
    ergebnis = ""
    for text, enc in teile:
        if isinstance(text, bytes):
            ergebnis += text.decode(enc or "utf-8", errors="replace")
        else:
            ergebnis += text
    return ergebnis


def extrahiere_body(msg):
    if msg.is_multipart():
        for teil in msg.walk():
            if teil.get_content_type() == "text/plain" and not teil.get("Content-Disposition"):
                payload = teil.get_payload(decode=True)
                charset = teil.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def main():
    benutzer, passwort = lade_zugangsdaten()

    print(f"Verbinde mit {IMAP_SERVER} als {benutzer} ...")
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(benutzer, passwort)
    imap.select("INBOX")

    status, daten = imap.search(None, "UNSEEN")
    if status != "OK":
        print("IMAP-Suche fehlgeschlagen.")
        sys.exit(1)

    ids = daten[0].split()
    if not ids:
        print("Keine ungelesenen Mails.")
        imap.logout()
        return

    gefunden = 0
    gesamt_auto = 0
    gesamt_pruefen = 0
    for msg_id in ids:
        status, msg_daten = imap.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_daten[0][1])
        betreff = dekodiere(msg.get("Subject"))

        if not betreff.strip().lower().startswith(BETREFF_FILTER.lower()):
            continue

        gefunden += 1
        body = extrahiere_body(msg)
        print(f"\n=== Mail: {betreff} ===")
        anzahl_auto, anzahl_pruefen = verarbeite_text_automatisch(body)
        gesamt_auto += anzahl_auto
        gesamt_pruefen += anzahl_pruefen

        imap.store(msg_id, "+FLAGS", "\\Seen")

    if gefunden == 0:
        print(f'Keine ungelesenen Mails mit Betreff-Beginn "{BETREFF_FILTER}" gefunden.')
    else:
        print(f"\nZusammenfassung: {gesamt_auto} automatisch übernommen, "
              f"{gesamt_pruefen} zur manuellen Prüfung vorgemerkt.")

    imap.logout()


if __name__ == "__main__":
    main()
