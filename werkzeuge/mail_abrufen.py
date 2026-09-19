#!/usr/bin/env python3
"""
Ruft ungelesene Korrektur- und Foto-Mails direkt aus dem Postfach ab (IMAP).
Korrektur-Mails werden zur Prüfung an korrektur_verarbeiten.verarbeite_text()
übergeben — jede Korrektur wird einzeln mit j/n bestätigt, keine automatische
Übernahme. Foto-Mails werden nicht automatisch verarbeitet, ihre Bild-Anhänge
werden nur in den Ordner werkzeuge/eingegangene_fotos/ gespeichert.

Zugangsdaten stehen NICHT im Code, sondern in werkzeuge/zugangsdaten.json
(diese Datei ist in .gitignore und wird nie eingecheckt).

Nutzung:
  python3 werkzeuge/mail_abrufen.py

Es werden nur ungelesene Mails geholt, deren Betreff mit "Korrektur" oder
"Foto" beginnt (genau die Betreffs, die die App verschickt). Nach
Verarbeitung werden die Mails als gelesen markiert, damit sie beim nächsten
Aufruf nicht erneut auftauchen.
"""

import email
import imaplib
import json
import sys
from email.header import decode_header
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from korrektur_verarbeiten import verarbeite_text  # noqa: E402

ZUGANGSDATEN_PFAD = Path(__file__).resolve().parent / "zugangsdaten.json"
FOTO_ORDNER = Path(__file__).resolve().parent / "eingegangene_fotos"
IMAP_SERVER = "imap.web.de"
BETREFF_FILTER = ("Korrektur", "Foto")


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


def speichere_fotos(msg, betreff, msg_id):
    FOTO_ORDNER.mkdir(exist_ok=True)
    praefix = "".join(c if c.isalnum() else "_" for c in betreff).strip("_")
    anzahl = 0
    for teil in msg.walk():
        if teil.get_content_maintype() != "image":
            continue
        dateiname = teil.get_filename() or "foto.jpg"
        dateiname = dekodiere(dateiname)
        ziel = FOTO_ORDNER / f"{praefix}_{msg_id.decode()}_{dateiname}"
        payload = teil.get_payload(decode=True)
        if not payload:
            continue
        ziel.write_bytes(payload)
        anzahl += 1
        print(f"  Foto gespeichert: {ziel}")
    return anzahl


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
    for msg_id in ids:
        status, msg_daten = imap.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_daten[0][1])
        betreff = dekodiere(msg.get("Subject"))

        if not betreff.strip().lower().startswith(tuple(f.lower() for f in BETREFF_FILTER)):
            continue

        gefunden += 1
        print(f"\n=== Mail: {betreff} ===")

        if betreff.strip().lower().startswith("foto"):
            anzahl = speichere_fotos(msg, betreff, msg_id)
            if not anzahl:
                print("  Kein Bild-Anhang gefunden.")
        else:
            body = extrahiere_body(msg)
            verarbeite_text(body)

        imap.store(msg_id, "+FLAGS", "\\Seen")

    if gefunden == 0:
        filter_text = '" / "'.join(BETREFF_FILTER)
        print(f'Keine ungelesenen Mails mit Betreff-Beginn "{filter_text}" gefunden.')

    imap.logout()


if __name__ == "__main__":
    main()
