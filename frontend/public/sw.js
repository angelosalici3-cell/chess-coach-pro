/* Service worker: rende l'app installabile e mostra una pagina offline.
   Non mette mai in cache le chiamate API, il login o i dati personali. */
const VERSION = "v3";
const STATIC = `static-${VERSION}`;
const OFFLINE = "/offline.html";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(STATIC).then((c) => c.addAll([OFFLINE, "/icon-192.png", "/logo.svg"])));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== STATIC).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;           // API e Supabase sono su altri domini: mai toccati
  if (req.mode === "navigate") {                                                // pagine: sempre dalla rete, offline solo come ripiego
    e.respondWith(fetch(req).catch(() => caches.match(OFFLINE)));
    return;
  }
  if (url.pathname.startsWith("/_next/static/")) {                              // file con hash nel nome: cache-first
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(STATIC).then((c) => c.put(req, copy)); }
      return res;
    })));
  } else if (/\.(png|svg|woff2?)$/.test(url.pathname)) {                         // icone e logo: prima la rete, così non restano mai quelle vecchie
    e.respondWith(fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(STATIC).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req)));
  }
});

self.addEventListener("message", (e) => { if (e.data === "SKIP_WAITING") self.skipWaiting(); });
