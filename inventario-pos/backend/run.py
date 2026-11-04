"""Punto de entrada del ejecutable de escritorio (InventarioPOS.exe).

Arranca el backend FastAPI local (conectado a Neon), mantiene el servidor
activo y abre el frontend fijo de Cloudflare Pages en una ventana nueva de
Chrome o Edge. El frontend detecta este backend por localhost y, si no esta
disponible, usa Render como respaldo.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

# --- Rutas de importación (funciona en desarrollo y empaquetado) ---
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# La zona horaria debe quedar fijada antes de importar app.tiempo.
os.environ.setdefault("APP_TIMEZONE", "America/Bogota")

PUERTO = int(os.getenv("PUERTO", os.getenv("PORT", "8000")))
HOST = os.getenv("HOST", "0.0.0.0")
ABRIR_NAVEGADOR = os.getenv("ABRIR_NAVEGADOR", "1") == "1"
API_NUBE = os.getenv(
    "CLOUD_API_URL", "https://inventario-pos-api-pqju.onrender.com/api"
)
FRONTEND_URL = os.getenv(
    "FRONTEND_URL", "https://inventario-pos-bfw.pages.dev/admin/usuarios"
)

ES_EJECUTABLE = bool(getattr(sys, "frozen", False))


def puerto_en_uso(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def salud_local(puerto: int) -> bool:
    """True si en el puerto responde Inventario POS (y no otro programa)."""
    try:
        with urlopen(f"http://127.0.0.1:{puerto}/health", timeout=1.5) as r:
            datos = json.loads(r.read().decode("utf-8", errors="ignore"))
        return datos.get("status") == "healthy"
    except Exception:
        return False


def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _buscar_navegador() -> str:
    """Ruta de Chrome o Edge en Windows; cadena vacia si no se encuentra."""
    if os.name != "nt":
        return ""

    def unir(base: str, resto: str) -> Path:
        return Path(base) / resto if base else Path(resto)

    programas = os.getenv("PROGRAMFILES", r"C:\Program Files")
    programas_x86 = os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    local = os.getenv("LOCALAPPDATA", "")

    candidatos = [
        unir(programas, r"Google\Chrome\Application\chrome.exe"),
        unir(programas_x86, r"Google\Chrome\Application\chrome.exe"),
        unir(local, r"Google\Chrome\Application\chrome.exe"),
        unir(programas, r"Microsoft\Edge\Application\msedge.exe"),
        unir(programas_x86, r"Microsoft\Edge\Application\msedge.exe"),
        unir(local, r"Microsoft\Edge\Application\msedge.exe"),
    ]
    for ruta in candidatos:
        try:
            if ruta.is_file():
                return str(ruta)
        except OSError:
            continue
    return ""


def abrir_navegador() -> None:
    """Espera al backend y abre el frontend fijo en una ventana nueva.

    No se abre localhost: la aplicacion siempre se sirve desde Cloudflare
    Pages. El backend local solo responde a las llamadas /api y /health.
    """
    for _ in range(60):
        if salud_local(PUERTO):
            break
        time.sleep(0.5)

    navegador = _buscar_navegador()
    try:
        if navegador:
            # --new-window crea una ventana nueva con una sola pestaña en la URL.
            subprocess.Popen(
                [navegador, "--new-window", FRONTEND_URL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            webbrowser.open(FRONTEND_URL, new=1)
    except Exception:
        try:
            webbrowser.open(FRONTEND_URL, new=1)
        except Exception:
            pass


def pausar_si_error() -> None:
    """En el .exe la consola se cierra al terminar; dejamos leer el error."""
    if ES_EJECUTABLE:
        try:
            input("Presiona Enter para cerrar...")
        except Exception:
            pass


def mostrar_cabecera(ip: str, base_datos: str) -> None:
    print("=" * 64)
    print("            SISTEMA INVENTARIO - PUNTO DE VENTA")
    print("=" * 64)
    print(f"  Frontend fijo  : {FRONTEND_URL}")
    print(f"  API local      : http://localhost:{PUERTO}/api")
    print(f"  API en WiFi    : http://{ip}:{PUERTO}/api")
    print("-" * 64)
    print(f"  Base de datos  : {base_datos}")
    print(f"  Respaldo nube  : {API_NUBE.replace('/api', '')}")
    print("=" * 64)
    print("  El navegador se abre en Cloudflare Pages y usa este backend")
    print("  local cuando responde; si no, usa Render automaticamente.")
    print("  Para detener el servidor: presiona Ctrl+C")
    print("  Mientras esta ventana siga abierta, el backend local sigue activo.")
    print("=" * 64)


def main() -> None:
    if os.name == "nt":
        try:
            os.system("title Inventario POS - Servidor local")
        except Exception:
            pass

    # La consola del .exe tambien puede redirigirse a un archivo: forzamos
    # line-buffering para que las URLs y el diagnostico aparezcan al instante.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    from app.database import descripcion_database, tipo_database

    base_datos = descripcion_database()

    if puerto_en_uso(PUERTO):
        if salud_local(PUERTO):
            print("=" * 64)
            print(f"  Inventario POS ya esta corriendo en el puerto {PUERTO}")
            print(f"  Frontend: {FRONTEND_URL}")
            print(f"  API local: http://localhost:{PUERTO}/api")
            print(f"  API en WiFi: http://{ip_local()}:{PUERTO}/api")
            print("=" * 64)
            if ABRIR_NAVEGADOR:
                abrir_navegador()
        else:
            print("=" * 64)
            print(f"  [ERROR] El puerto {PUERTO} esta ocupado por otro programa.")
            print("  Cierra ese programa o cambia el puerto con: set PUERTO=8010")
            print("=" * 64)
            pausar_si_error()
        return

    if ES_EJECUTABLE and tipo_database() != "postgresql":
        print("=" * 64)
        print("  [AVISO IMPORTANTE] El ejecutable esta usando SQLite local.")
        print("  Los datos NO se sincronizaran con Neon ni con Render.")
        print("  Vuelve a compilar con scripts\\build_hybrid_exe.bat.")
        print("=" * 64)

    # La importación de app.main prepara rutas, routers y migraciones.
    from app.main import app
    import uvicorn

    mostrar_cabecera(ip_local(), base_datos)

    if ABRIR_NAVEGADOR:
        threading.Thread(target=abrir_navegador, daemon=True).start()

    try:
        uvicorn.run(app, host=HOST, port=PUERTO, log_level="info")
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"\n[ERROR] No se pudo iniciar el servidor: {exc}")
        pausar_si_error()


if __name__ == "__main__":
    main()
