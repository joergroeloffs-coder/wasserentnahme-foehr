"use strict";
importScripts("../config.js");
const SHELL_CACHE = "nutzer-shell-v17-config";
const TILE_CACHE = "osm-kacheln-v1";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.json",
  "../config.js",
  "../icon.svg",
  "../icon-180.png",
  "../icon-192.png",
  "../icon-512.png",
  "../vendor/leaflet.js",
  "../vendor/leaflet.css",
  "../vendor/images/marker-icon.png",
  "../vendor/images/marker-icon-2x.png",
  "../vendor/images/marker-shadow.png",
  "../vendor/images/layers.png",
  "../vendor/images/layers-2x.png",
  "../daten/stellen.geojson",
  "../anleitung/index.html"
];
/* Die PMTiles/MapLibre-Dateien nur cachen, wenn diese Gemeinde eine eigene
   Offlinekarte hat (APP_CONFIG.pmtilesDatei gesetzt) - cache.addAll() ist
   atomar, eine fehlende Datei würde sonst die GESAMTE Installation kippen. */
if(self.APP_CONFIG && self.APP_CONFIG.pmtilesDatei){
  SHELL_FILES.push(
    "../vendor/maplibre-gl.js",
    "../vendor/maplibre-gl.css",
    "../vendor/pmtiles.js",
    "../vendor/leaflet-maplibre-gl.js",
    "../vendor/protomaps-light-de.json",
    "../vendor/protomaps-assets/fonts/Noto Sans Italic/0-255.pbf",
    "../vendor/protomaps-assets/fonts/Noto Sans Regular/0-255.pbf",
    "../vendor/protomaps-assets/fonts/Noto Sans Medium/0-255.pbf",
    "../vendor/protomaps-assets/sprites/v4/light.json",
    "../vendor/protomaps-assets/sprites/v4/light.png",
    "../vendor/protomaps-assets/sprites/v4/light@2x.json",
    "../vendor/protomaps-assets/sprites/v4/light@2x.png",
    "../daten/" + self.APP_CONFIG.pmtilesDatei
  );
}

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== SHELL_CACHE && k !== TILE_CACHE).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

function istOsmKachel(url){
  return url.hostname === "tile.openstreetmap.org";
}

async function kachelAusCache(request){
  const cache = await caches.open(TILE_CACHE);
  const vorhanden = await cache.match(request);
  if(vorhanden) return vorhanden;
  try {
    const res = await fetch(request);
    if(res.ok) cache.put(request, res.clone());
    return res;
  } catch(e){
    return new Response("", { status: 504 });
  }
}

function istPmtilesDatei(url){
  if(!self.APP_CONFIG || !self.APP_CONFIG.pmtilesDatei) return false;
  return url.origin === self.location.origin && url.pathname.endsWith("/daten/" + self.APP_CONFIG.pmtilesDatei);
}

async function pmtilesAusCache(request){
  const cache = await caches.open(SHELL_CACHE);
  const dateiUrl = new URL(request.url);
  const vollAnfrage = new Request(dateiUrl.href, { credentials:"same-origin" });
  let vollAntwort = await cache.match(vollAnfrage);

  if(!vollAntwort){
    vollAntwort = await fetch(vollAnfrage);
    if(!vollAntwort.ok) return vollAntwort;
    await cache.put(vollAnfrage, vollAntwort.clone());
  }

  const bereich = request.headers.get("range");
  if(!bereich) return vollAntwort;

  const treffer = /^bytes=(\d+)-(\d*)$/.exec(bereich);
  const daten = await vollAntwort.arrayBuffer();
  const gesamt = daten.byteLength;
  if(!treffer) return new Response(null, { status:416, headers:{ "Content-Range":"bytes */" + gesamt } });

  const start = Number(treffer[1]);
  const ende = treffer[2] ? Math.min(Number(treffer[2]), gesamt - 1) : gesamt - 1;
  if(start >= gesamt || start > ende){
    return new Response(null, { status:416, headers:{ "Content-Range":"bytes */" + gesamt } });
  }

  const teil = daten.slice(start, ende + 1);
  return new Response(teil, {
    status:206,
    headers:{
      "Accept-Ranges":"bytes",
      "Content-Length":String(teil.byteLength),
      "Content-Range":"bytes " + start + "-" + ende + "/" + gesamt,
      "Content-Type":"application/vnd.pmtiles"
    }
  });
}

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  if(istPmtilesDatei(url)){
    event.respondWith(pmtilesAusCache(event.request));
    return;
  }

  if(istOsmKachel(url)){
    event.respondWith(kachelAusCache(event.request));
    return;
  }

  if(url.origin === self.location.origin){
    event.respondWith(
      fetch(event.request).then(res => {
        if(res.ok){
          const copy = res.clone();
          caches.open(SHELL_CACHE).then(c => c.put(event.request, copy));
        }
        return res;
      }).catch(() => caches.match(event.request).then(hit => hit || caches.match("./index.html")))
    );
  }
});
