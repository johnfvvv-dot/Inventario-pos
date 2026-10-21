/* Service Worker de Inventario POS
 * Estrategia:
 *  - Recursos estáticos (JS/CSS/imágenes): cache-first
 *  - Peticiones a la API: network-only (nunca cachear datos de ventas)
 */

const CACHE_NAME = "inventario-pos-v1";
const ASSETS_TO_CACHE = ["./", "./index.html", "./manifest.json"];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE)).catch(() => {})
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Las llamadas a la API siempre van a la red (datos en vivo)
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Navegación: red primero con respaldo al index cacheado
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copia = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put("./index.html", copia));
          return response;
        })
        .catch(() => caches.match("./index.html"))
    );
    return;
  }

  // Resto de recursos: cache primero
  event.respondWith(
    caches.match(event.request).then((cacheada) => {
      if (cacheada) return cacheada;
      return fetch(event.request).then((respuesta) => {
        if (respuesta.ok && respuesta.type === "basic") {
          const copia = respuesta.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copia));
        }
        return respuesta;
      });
    })
  );
});
