/** Registro del Service Worker (PWA) + iconos generados por defecto. */

const isLocalhost = Boolean(
  window.location.hostname === "localhost" ||
    window.location.hostname === "[::1]" ||
    window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d?\d)){3}$/)
);

export function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      const url = `${process.env.PUBLIC_URL}/service-worker.js`;
      navigator.serviceWorker.register(url).catch((error) => {
        console.log("No se pudo registrar el service worker:", error);
      });
    });
  }
}

// En desarrollo se elimina el service worker y su caché para no servir
// una versión anterior del frontend.
export function unregister() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) =>
        Promise.all(
          registrations.map((registration) => registration.unregister())
        )
      )
      .catch((error) => console.log(error.message));
  }

  if ("caches" in window) {
    caches
      .keys()
      .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
      .catch((error) => console.log(error.message));
  }
}
