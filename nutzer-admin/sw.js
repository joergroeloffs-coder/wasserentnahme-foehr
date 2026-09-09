"use strict";
const SHELL_CACHE = "nutzer-admin-shell-v1";
const TILE_CACHE = "osm-tiles-v1";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.json",
  "../icon.svg",
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

function isTile(url){
  return url.hostname.endsWith("tile.openstreetmap.org");
}

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  if(isTile(url)){
    event.respondWith(
      caches.open(TILE_CACHE).then(cache =>
        cache.match(event.request).then(hit => hit || fetch(event.request).then(res => {
          if(res.ok) cache.put(event.request, res.clone());
          return res;
        }).catch(() => hit))
      )
    );
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
