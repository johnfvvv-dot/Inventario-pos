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

// Permite que el service worker intercepta peticiones en desarrollo
export function unregister() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => registration.unregister())
      .catch((error) => console.log(error.message));
  }
}
