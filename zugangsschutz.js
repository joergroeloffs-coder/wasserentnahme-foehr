/* Gemeinsamer Zugangsschutz für alle Seiten dieser Anwendung.

   Grundsatz: Die Entscheidung "darf diese Person die App nutzen?" faellt
   ausschliesslich auf dem Server (Cloudflare Worker + Supabase). Im Browser
   gibt es bewusst keinen Schalter, keinen Freigabecode und keinen
   URL-Parameter, mit dem sich die Pruefung umgehen liesse.

   Zwei Stufen:
   - normal:   aktiver Jahreszugang noetig (nutzer/)
   - betreiber: zusaetzlich muss der Server das Konto als Betreiberkonto
                bestaetigen (index.html, nutzer-admin/, Testseiten)

   Wird der Zugang verweigert, werden zusaetzlich die zwischengespeicherten
   Dateien geloescht und der Service Worker abgemeldet. Sonst bliebe eine
   vollstaendig nutzbare Kopie der Anwendung auf dem Geraet zurueck. */

(function () {
  "use strict";

  const BIBLIOTHEK = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";

  const TEXTE = {
    nicht_angemeldet: "Bitte mit der E-Mail-Adresse des Jahreszugangs anmelden.",
    kein_profil: "Für dieses Konto besteht kein Jahreszugang.",
    kein_abo: "Für dieses Konto besteht kein Jahreszugang.",
    manuell_gesperrt: "Dieser Zugang ist gesperrt. Bitte Kontakt aufnehmen.",
    bezahlter_zeitraum_beendet: "Der bezahlte Zeitraum ist beendet.",
    kuendigung_wirksam: "Der Vertrag ist beendet.",
    vertragsende_ungeklaert: "Das Vertragsende ist noch nicht geklärt. Bitte Kontakt aufnehmen.",
    geraetelimit_erreicht:
      "Der Zugang wird bereits auf der vereinbarten Anzahl Geräte genutzt. Im Kundenbereich lässt sich ein Gerät entfernen.",
    kein_betreiberkonto: "Dieser Bereich ist dem Betrieb vorbehalten.",
    netzfehler: "Die Zugangsprüfung ist nicht erreichbar. Bitte später erneut versuchen.",
  };

  function geraeteId() {
    const schluessel = APP_CONFIG.speicherPraefix + ".geraeteid";
    let id = null;
    try {
      id = localStorage.getItem(schluessel);
    } catch (e) {
      /* privater Modus: dann eben je Sitzung eine neue Kennung */
    }
    if (!id || !/^[0-9a-f-]{36}$/i.test(id)) {
      id =
        window.crypto && crypto.randomUUID
          ? crypto.randomUUID()
          : "00000000-0000-4000-8000-" + String(Date.now()).slice(-12).padStart(12, "0");
      try {
        localStorage.setItem(schluessel, id);
      } catch (e) {}
    }
    return id;
  }

  // Nach entzogenem Zugang darf keine benutzbare Kopie zurueckbleiben.
  async function zwischenspeicherLeeren() {
    try {
      if (window.caches && caches.keys) {
        const namen = await caches.keys();
        await Promise.all(namen.map((name) => caches.delete(name)));
      }
    } catch (e) {}
    try {
      if (navigator.serviceWorker && navigator.serviceWorker.getRegistrations) {
        const registrierungen = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrierungen.map((r) => r.unregister()));
      }
    } catch (e) {}
  }

  function sperreAufbauen() {
    const sperre = document.createElement("div");
    sperre.id = "zugang-sperre";
    sperre.setAttribute("role", "dialog");
    sperre.setAttribute("aria-modal", "true");
    sperre.setAttribute("aria-label", "Zugang zu Löschbärt Föhr");
    sperre.style.cssText =
      "position:fixed;inset:0;z-index:2147483647;background:#0d1116;color:#e6edf3;" +
      "display:flex;align-items:center;justify-content:center;padding:24px;" +
      "font-family:system-ui,-apple-system,'Segoe UI',sans-serif";
    sperre.innerHTML =
      '<div style="width:min(420px,100%);text-align:center">' +
      '<h1 style="font-size:22px;margin:0 0 10px">Löschbärt Föhr</h1>' +
      '<p id="zugang-hinweis" style="color:#93a3b3;min-height:3em" role="status" aria-live="polite">Zugang wird geprüft …</p>' +
      '<div id="zugang-anmeldung" hidden>' +
      '<label for="zugang-email" style="display:block;text-align:left;font-size:13px;color:#93a3b3">E-Mail-Adresse</label>' +
      '<input id="zugang-email" type="email" autocomplete="email" ' +
      'style="width:100%;padding:12px;margin-top:4px;border-radius:8px;border:1px solid #2a313c;background:#161b22;color:#e6edf3;font:inherit">' +
      '<button id="zugang-senden" type="button" ' +
      'style="width:100%;margin-top:10px;padding:12px;border:0;border-radius:8px;background:#2fa4ff;color:#071018;font-weight:700;font-size:15px;cursor:pointer">' +
      "Anmelde-Link senden</button>" +
      '<p style="font-size:13px;margin-top:14px"><a id="zugang-kaufen" href="#" style="color:#2fa4ff">Noch kein Jahreszugang?</a></p>' +
      "</div></div>";
    document.body.prepend(sperre);
    return sperre;
  }

  async function starten(optionen) {
    const betreiberErforderlich = Boolean(optionen && optionen.betreiberErforderlich);
    const sperre = sperreAufbauen();
    const hinweis = sperre.querySelector("#zugang-hinweis");
    const anmeldung = sperre.querySelector("#zugang-anmeldung");
    sperre.querySelector("#zugang-kaufen").href = APP_CONFIG.bestellSeite;

    function zeigeAnmeldung(text) {
      hinweis.textContent = text;
      anmeldung.hidden = false;
    }

    let client;
    try {
      if (!window.supabase) {
        await new Promise((fertig, fehler) => {
          const skript = document.createElement("script");
          skript.src = BIBLIOTHEK;
          skript.onload = fertig;
          skript.onerror = fehler;
          document.head.appendChild(skript);
        });
      }
      client = window.supabase.createClient(APP_CONFIG.supabaseUrl, APP_CONFIG.supabaseAnonKey);
    } catch (e) {
      hinweis.textContent = TEXTE.netzfehler;
      return null;
    }

    sperre.querySelector("#zugang-senden").addEventListener("click", async () => {
      const email = sperre.querySelector("#zugang-email").value.trim();
      if (!email) {
        hinweis.textContent = "Bitte eine E-Mail-Adresse eingeben.";
        return;
      }
      const { error } = await client.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: location.origin + location.pathname },
      });
      hinweis.textContent = error
        ? "Der Anmelde-Link konnte nicht gesendet werden. Bitte später erneut versuchen."
        : "Anmelde-Link wurde versandt. Bitte das E-Mail-Postfach öffnen.";
    });

    async function pruefen() {
      const {
        data: { session },
      } = await client.auth.getSession();
      if (!session) {
        await zwischenspeicherLeeren();
        zeigeAnmeldung(TEXTE.nicht_angemeldet);
        return null;
      }

      let antwort;
      try {
        antwort = await fetch(
          APP_CONFIG.aboWorkerUrl + "/api/zugriff?geraet=" + encodeURIComponent(geraeteId()),
          { headers: { Authorization: "Bearer " + session.access_token }, cache: "no-store" }
        );
      } catch (e) {
        // Ohne Netz wird nicht freigegeben. Eine dauerhaft offline nutzbare
        // Vollversion liesse sich sonst nicht mehr sperren.
        hinweis.textContent = TEXTE.netzfehler;
        return null;
      }

      const ergebnis = await antwort.json().catch(() => ({}));
      if (!antwort.ok || !ergebnis.erlaubt) {
        await zwischenspeicherLeeren();
        zeigeAnmeldung(TEXTE[ergebnis.grund] || TEXTE.kein_abo);
        return null;
      }
      if (betreiberErforderlich && ergebnis.betreiber !== true) {
        await zwischenspeicherLeeren();
        hinweis.textContent = TEXTE.kein_betreiberkonto;
        anmeldung.hidden = true;
        return null;
      }

      sperre.remove();
      return { session, zugang: ergebnis };
    }

    client.auth.onAuthStateChange(() => {
      if (document.getElementById("zugang-sperre")) pruefen();
    });

    return pruefen();
  }

  // Laedt die Stellendaten. Bevorzugt ueber den geschuetzten Endpunkt; solange
  // der Betrieb die Daten noch als oeffentliche Datei ausliefert, wird diese
  // genutzt (siehe INTEGRATION_LOESCHBAERT.md, Abschnitt Datenschutzstrategie).
  async function stellenLaden(zugang, statischeAdresse) {
    if (zugang && zugang.session) {
      try {
        const antwort = await fetch(
          APP_CONFIG.aboWorkerUrl +
            "/api/stellen?geraet=" +
            encodeURIComponent(geraeteId()),
          {
            headers: { Authorization: "Bearer " + zugang.session.access_token },
            cache: "no-store",
          }
        );
        if (antwort.ok) return await antwort.text();
        if (antwort.status !== 503) throw new Error("Stellen nicht abrufbar: " + antwort.status);
        console.warn(
          "Geschützte Stellenquelle ist nicht eingerichtet; es wird die öffentliche Datei genutzt."
        );
      } catch (e) {
        console.warn("Geschützte Stellenquelle nicht erreichbar:", e);
      }
    }
    const antwort = await fetch(statischeAdresse, { cache: "no-store" });
    if (!antwort.ok) throw new Error("Stellendatei nicht abrufbar");
    return antwort.text();
  }

  window.LOESCHBAERT_ZUGANG = { starten, stellenLaden, geraeteId, zwischenspeicherLeeren };
})();
