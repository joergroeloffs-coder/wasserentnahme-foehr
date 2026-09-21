const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const BASE = 'http://127.0.0.1:8795';
const OUT = '/tmp/claude-0/-home-user-vereinsmanager/0d10283b-e0b1-544c-9b74-1390cffcad4f/scratchpad/shots';

let fehlgeschlagen = 0;
function pruefe(name, ok, zusatz = '') {
  if (!ok) fehlgeschlagen++;
  console.log(`  ${ok ? 'BESTANDEN' : 'FEHLGESCHLAGEN'}  ${name}${zusatz ? ' — ' + zusatz : ''}`);
}

// Antwort des Worker steuerbar machen, ohne echte Zugangsdaten.
function stub({ session = true, antwort = { erlaubt: true, status: 'aktiv', betreiber: false } } = {}) {
  return `(${((s, a) => {
    const sitzung = s
      ? { access_token: 'test-token', user: { id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', email: 'kunde@example.test' } }
      : null;
    window.supabase = {
      createClient: () => ({
        auth: {
          getSession: async () => ({ data: { session: sitzung } }),
          signInWithOtp: async () => ({ error: null }),
          onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
        },
      }),
    };
    const echtesFetch = window.fetch;
    window.fetch = async (url, optionen) => {
      const adresse = String(url);
      if (adresse.includes('/api/zugriff')) {
        return new Response(JSON.stringify(a), {
          status: a.erlaubt ? 200 : 403,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (adresse.includes('/api/stellen')) {
        // Noch nicht eingerichtet -> Rueckfall auf die oeffentliche Datei
        return new Response(JSON.stringify({ fehler: 'stellenquelle_nicht_konfiguriert' }), { status: 503 });
      }
      return echtesFetch(url, optionen);
    };
  }).toString()})(${JSON.stringify(session)}, ${JSON.stringify(antwort)})`;
}

async function seite(browser, pfad, optionen, name) {
  const page = await browser.newPage({ viewport: { width: 420, height: 880 } });
  await page.addInitScript({ content: stub(optionen) });
  await page.goto(BASE + pfad, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  if (name) await page.screenshot({ path: `${OUT}/app-${name}.png` });
  const zustand = await page.evaluate(() => ({
    gesperrt: Boolean(document.getElementById('zugang-sperre')),
    hinweis: document.getElementById('zugang-hinweis')?.textContent?.trim() || '',
    stellen: document.querySelectorAll('#v-liste .treffer, #v-liste li, #liste > *').length,
    marker: document.querySelectorAll('.leaflet-marker-icon').length,
  }));
  return { page, zustand };
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });

  console.log('Nutzerversion (nutzer/)');
  let r = await seite(browser, '/nutzer/', { session: false }, 'gesperrt');
  pruefe('ohne Anmeldung gesperrt', r.zustand.gesperrt, r.zustand.hinweis);
  await r.page.close();

  r = await seite(browser, '/nutzer/', { session: true, antwort: { erlaubt: false, grund: 'bezahlter_zeitraum_beendet' } });
  pruefe('abgelaufenes Abo gesperrt', r.zustand.gesperrt, r.zustand.hinweis);
  await r.page.close();

  r = await seite(browser, '/nutzer/', { session: true, antwort: { erlaubt: false, grund: 'geraetelimit_erreicht' } });
  pruefe('drittes Gerät gesperrt', r.zustand.gesperrt, r.zustand.hinweis);
  await r.page.close();

  r = await seite(browser, '/nutzer/', { session: true, antwort: { erlaubt: true, status: 'aktiv', betreiber: false } }, 'frei');
  pruefe('aktives Abo gibt frei', !r.zustand.gesperrt);
  pruefe('Kartendaten geladen', r.zustand.stellen > 0, `${r.zustand.stellen} Listeneinträge`);
  // Kartenansicht: PMTiles-Grundkarte und Marker muessen erscheinen.
  await r.page.locator('button[data-view="v-karte"]').click();
  await r.page.waitForTimeout(3000);
  const karte = await r.page.evaluate(() => ({
    leinwand: document.querySelectorAll('canvas').length,
    marker: document.querySelectorAll('.leaflet-marker-icon').length,
  }));
  pruefe('Kartenansicht zeichnet die Grundkarte', karte.leinwand > 0, `${karte.leinwand} Zeichenflächen`);
  pruefe('Marker auf der Karte', karte.marker > 0, `${karte.marker} Marker`);
  await r.page.screenshot({ path: `${OUT}/app-karte.png` });
  await r.page.close();

  console.log('\nInterne Bereiche');
  r = await seite(browser, '/nutzer-admin/', { session: true, antwort: { erlaubt: true, status: 'aktiv', betreiber: false } });
  pruefe('nutzer-admin für Kunden gesperrt', r.zustand.gesperrt, r.zustand.hinweis);
  await r.page.close();

  r = await seite(browser, '/index.html', { session: true, antwort: { erlaubt: true, status: 'aktiv', betreiber: false } });
  pruefe('Datenpflege für Kunden gesperrt', r.zustand.gesperrt, r.zustand.hinweis);
  await r.page.close();

  r = await seite(browser, '/index.html', { session: true, antwort: { erlaubt: true, status: 'betreiber', betreiber: true } }, 'betrieb');
  pruefe('Datenpflege für Betreiber frei', !r.zustand.gesperrt);
  await r.page.close();

  console.log('\nUmgehungsversuche');
  for (const versuch of ['/nutzer/?freigabe=1', '/nutzer/?zugang=12345678', '/nutzer/index.html?test=1']) {
    r = await seite(browser, versuch, { session: false });
    pruefe(`URL-Parameter hilft nicht: ${versuch}`, r.zustand.gesperrt);
    await r.page.close();
  }

  // localStorage-Manipulation darf nichts bringen
  const p = await browser.newPage({ viewport: { width: 420, height: 880 } });
  await p.addInitScript({ content: stub({ session: false }) });
  await p.addInitScript(() => {
    try {
      localStorage.setItem('wasserentnahme.foehr.nutzer.trialstart', '1');
      localStorage.setItem('wasserentnahme.foehr.nutzer.freigabestart', String(Date.now()));
      localStorage.setItem('loeschmeier_abo_zugriff_bis', new Date(Date.now() + 9e8).toISOString());
    } catch (e) {}
  });
  await p.goto(BASE + '/nutzer/', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(2000);
  pruefe('manipuliertes localStorage hilft nicht',
    await p.evaluate(() => Boolean(document.getElementById('zugang-sperre'))));
  await p.close();

  await browser.close();
  console.log(fehlgeschlagen === 0 ? '\nAlle Prüfungen bestanden.' : `\n${fehlgeschlagen} Prüfung(en) fehlgeschlagen.`);
  process.exit(fehlgeschlagen === 0 ? 0 : 1);
})();
