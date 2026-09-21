# Integration Löschbärt – Anwendung Föhr

Branch: `claude/integration-loeschbaert` (aufgesetzt auf `codex/zugriffsschutz-abo`)

Der vollständige Bericht über alle drei Projekte steht in
`loeschmeier-abo/INTEGRATION_LOESCHBAERT.md`.

## Übernommen aus der Codex-Fassung

- Wegfall der lokalen Testphase, des Freigabe-Parameters `?freigabe=1` und der
  rein kosmetischen Zugangsnummer
- echte Vertragsprüfung gegen den Worker statt einer Anzeige ohne Wirkung
- Umstellung der Grundkarte auf die mitgelieferte PMTiles-Datei
- Beschriftung überall auf „Löschbärt"

Die Umstellung auf PMTiles wurde bewusst beibehalten, obwohl `main` sie auf
`null` gesetzt hatte: Der frühere Weg lud die Kacheln vom öffentlichen
OpenStreetMap-Server, und der Knopf „Insel jetzt vorladen" lud sie in großer
Zahl auf einmal. Das steht in Spannung zur Nutzungsrichtlinie des Dienstes.
Die mitgelieferte Karte vermeidet das und funktioniert offline. Der Code für
das Vorladen ist erhalten geblieben; nur `vorladeBbox` steht auf `null`, die
Entscheidung ist also mit einer Zeile umkehrbar.

## Zusätzlich korrigiert

- Die Datenpflege unter der Wurzeladresse und `nutzer-admin/` waren **ohne
  jede Prüfung öffentlich erreichbar**. Beide verlangen jetzt ein vom Server
  bestätigtes Betreiberkonto.
- Die Betreibereigenschaft entscheidet ausschließlich der Worker über die
  Variable `BETREIBER_AUTH_EMAILS`, nie der Browser. Betreiberkonten brauchen
  kein Kundenabo.
- Neue gemeinsame Datei `zugangsschutz.js` statt dreifach eigener Logik.
- Bei verweigertem Zugang werden Zwischenspeicher geleert und der Service
  Worker abgemeldet, damit keine dauerhaft nutzbare Kopie zurückbleibt.
- Die Stellendaten liegen nicht mehr im dauerhaften Shell-Zwischenspeicher.
- Ohne Netzverbindung wird nicht freigegeben.
- Der Datenabruf läuft über den berechtigungsgeprüften Endpunkt
  `/api/stellen`, mit Rückfall auf die bisherige Datei, solange diese
  öffentlich ausgeliefert wird.
- `test-oldsum.html` war von keiner Seite verlinkt, lieferte die Stellendaten
  ohne Prüfung aus und trug die alte Beschriftung; entfernt. Die Datei ist im
  Verlauf und auf `main` weiterhin vorhanden.

## Geprüft im Browser

| Fall | Ergebnis |
|---|---|
| ohne Anmeldung | gesperrt |
| abgelaufenes Abo | gesperrt |
| Gerätelimit erreicht | gesperrt, Hinweis auf den Kundenbereich |
| aktives Abo | frei: 200 Listeneinträge, 784 Marker, Grundkarte gezeichnet |
| `?freigabe=1`, `?zugang=…`, `?test=1` | wirkungslos |
| manipuliertes `localStorage` | wirkungslos |
| Kunde ruft interne Bereiche auf | gesperrt |
| Betreiberkonto ruft die Datenpflege auf | frei |

Test: `test/zugangsschutz.test.js` (Playwright, gegen einen lokalen Server;
Supabase und Worker sind nachgebildet).

## Wichtig vor der Veröffentlichung

**`BETREIBER_AUTH_EMAILS` im Worker setzen, bevor diese Fassung
veröffentlicht wird.** Sonst ist die eigene Datenpflege nicht mehr
erreichbar. Einen Umgehungsweg gibt es bewusst nicht.

Solange dieses Repository öffentlich ist, bleibt `daten/stellen.geojson` frei
herunterladbar und der Zugriffsschutz damit eine Bequemlichkeitshürde. Siehe
Abschnitt 3.1 des Hauptberichts.

Der Worker-Name in `config.js` enthält noch „loeschmeier". Er ist technisch
und für Nutzer nicht sichtbar; eine Umbenennung würde die bestehende Adresse
und damit den laufenden Betrieb brechen und ist deshalb unterblieben.
