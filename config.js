/* Ortsspezifische Einstellungen. Diese Datei ist die EINZIGE Stelle, die sich
   zwischen den verschiedenen Gemeinde-Versionen der App unterscheiden soll -
   alle anderen Dateien (index.html, nutzer/, nutzer-admin/, sw.js, vendor/)
   bleiben zwischen den Versionen identisch und werden per Sync-Skript
   (werkzeuge/sync_core.py) synchron gehalten. */
self.APP_CONFIG = {
  ortName: "Föhr",

  // Startposition/Zoom der Karte
  kartenMitte: [54.693, 8.530],
  kartenZoomUebersicht: 12,
  kartenZoomPeil: 13,
  kartenZoomDetail: 14,

  // Dateiname der Offline-Kartendatei in daten/ (ohne Pfad). Auf null lassen,
  // solange für diese Gemeinde noch keine PMTiles-Datei erzeugt wurde -
  // die App nutzt dann automatisch normale Online-Kartenkacheln als Fallback.
  // Bewusst auf null: echter OpenStreetMap-Kartenstil gewünscht statt Protomaps.
  // Jeder Nutzer lädt die Kacheln einmal von seinem eigenen Gerät/Anschluss
  // herunter (siehe vorladeBbox) - das verteilt sich auf viele IP-Adressen und
  // ist normale, einmalige Nutzung (kein Massendownload-Skript von einer Stelle).
  pmtilesDatei: null,

  // Nur Hauptversion: Rechteck (Bounding Box) für den "Insel jetzt vorladen"-
  // Knopf, der echte OSM-Kacheln herunterlädt und offline speichert. Max.
  // Zoomstufe bewusst auf 16 begrenzt (siehe index.html), um die Downloadmenge
  // je Nutzer klein zu halten. NIE mehrfach hintereinander von derselben Stelle
  // aus testen (Entwicklung/Debugging) - nur simuliert testen, echte Downloads
  // nur einmalig je echtem Gerät.
  vorladeBbox: { west: 8.40, south: 54.64, east: 8.63, north: 54.77 },

  // Basis für alle localStorage-Schlüssel dieser Version (muss sich von allen
  // anderen Gemeinden UND von den anderen Apps derselben Gemeinde unterscheiden,
  // sonst teilen sich Versionen auf github.io denselben Browser-Speicher).
  speicherPraefix: "wasserentnahme.foehr",

  // Nur Nutzerversion: Zieladresse für Positions-/Korrekturmeldungen.
  kontaktEmail: "wasserentnahme-foehr@web.de",

  // Nur Hauptversion: Zusammenfassung benachbarter Ortsteile in der Ortschafts-
  // Auswahl/Filterung. Leer lassen ({}), wenn nicht gebraucht.
  ortschaftGruppen: {
    "Utersum": "Utersum / Dunsum / Witsum / Hedehusum",
    "Dunsum": "Utersum / Dunsum / Witsum / Hedehusum",
    "Witsum": "Utersum / Dunsum / Witsum / Hedehusum",
    "Hedehusum": "Utersum / Dunsum / Witsum / Hedehusum",
    "Nieblum": "Nieblum / Goting",
    "Goting": "Nieblum / Goting"
  }
};
