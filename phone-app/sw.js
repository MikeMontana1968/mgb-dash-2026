/**
 * MGB Dash 2026 — Service worker (cache-first offline).
 * Bump CACHE_NAME to force update.
 */

const CACHE_NAME = "mgb-diag-v1";
const ASSETS = [
    "./",
    "./index.html",
    "./manifest.json",
    "./css/style.css",
    "./js/app.js",
    "./js/vehicle-state.js",
    "./js/can-decoder.js",
    "./js/demo-source.js",
    "./js/ble-source.js",
    "./js/ui.js",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    event.respondWith(
        caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
});
