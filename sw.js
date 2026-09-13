"use strict";
const SHELL_CACHE = "shell-v7-openfreemap";
const TILE_CACHE = "openfreemap-assets-v1";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon.svg",
  "./icon-180.png",
  "./icon-192.png",
  "./icon-512.png",
  "./vendor/leaflet.js",
  "./vendor/leaflet.css",
  "https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js",
  "https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css",
  "https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js",
  "./vendor/images/marker-icon.png",
  "./vendor/images/marker-icon-2x.png",
  "./vendor/images/marker-shadow.png",
  "./vendor/images/layers.png",
  "./vendor/images/layers-2x.png",
  "./daten/stellen.geojson",
  "./anleitung/index.html",
  "./anleitung/bilder/suchen.png",
  "./anleitung/bilder/filter.png",
  "./anleitung/bilder/navigation.png",
  "./anleitung/bilder/karte.png",
  "./anleitung/bilder/erfassen.png",
  "./anleitung/bilder/daten.png"
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

function isMapAsset(url){
  return url.hostname === "tiles.openfreemap.org";
}

function isMapLibrary(url){
  return url.hostname === "unpkg.com" &&
    (url.pathname.startsWith("/maplibre-gl@5.24.0/") ||
     url.pathname.startsWith("/@maplibre/maplibre-gl-leaflet@0.1.4/"));
}

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  if(isMapAsset(url)){
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

  if(isMapLibrary(url)){
    event.respondWith(
      caches.open(SHELL_CACHE).then(cache =>
        cache.match(event.request).then(hit => hit || fetch(event.request).then(res => {
          if(res.ok) cache.put(event.request, res.clone());
          return res;
        }))
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
