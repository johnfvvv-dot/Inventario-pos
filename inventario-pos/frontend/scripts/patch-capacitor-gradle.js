/**
 * Parche post-instalación para Capacitor + AGP 9.
 *
 * AGP 9 ya no permite 'proguard-android.txt' (incluye -dontoptimize).
 * Sustituye por 'proguard-android-optimize.txt' en los build.gradle
 * de Capacitor para que el APK compile con Gradle 9 / Java 25.
 *
 * Se ejecuta automáticamente con "npm install" (script postinstall).
 */
const fs = require("fs");
const path = require("path");

const objetivos = [
  path.join(__dirname, "..", "node_modules", "@capacitor", "android", "capacitor", "build.gradle"),
  path.join(__dirname, "..", "node_modules", "@capacitor", "android", "template", "app", "build.gradle"),
];

let applied = 0;

for (const archivo of objetivos) {
  try {
    if (!fs.existsSync(archivo)) continue;
    let contenido = fs.readFileSync(archivo, "utf-8");
    if (contenido.includes("proguard-android.txt")) {
      contenido = contenido.replace(
        /proguard-android\.txt/g,
        "proguard-android-optimize.txt"
      );
      fs.writeFileSync(archivo, contenido, "utf-8");
      console.log("[patch] proguard actualizado en:", archivo);
      applied++;
    }
  } catch (e) {
    console.warn("[patch] no se pudo parchear", archivo, e.message);
  }
}

if (applied === 0) {
  console.log("[patch] no fue necesario ningún cambio");
}
