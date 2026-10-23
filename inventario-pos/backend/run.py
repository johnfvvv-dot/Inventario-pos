"""Punto de entrada del ejecutable de escritorio (InventarioPOS.exe).

Arranca el servidor FastAPI (que sirve también el frontend compilado) y abre
el navegador apuntando a la aplicación. Pensado para uso en el mostrador:
doble clic -> la app queda lista para usar en el PC, tablet y celular.
"""

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# --- Rutas de importación (funciona en desarrollo y empaquetado) ---
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PUERTO = int(os.getenv("PUERTO", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
ABRIR_NAVEGADOR = os.getenv("ABRIR_NAVEGADOR", "1") == "1"


def puerto_en_uso(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def abrir_navegador() -> None:
    time.sleep(2.5)
    try:
        webbrowser.open(f"http://localhost:{PUERTO}")
    except Exception:
        pass


def main() -> None:
    import uvicorn

    from app.main import app

    if puerto_en_uso(PUERTO):
        print("=" * 62)
        print(f"  Inventario POS ya esta corriendo en el puerto {PUERTO}")
        print(f"  Abre: http://localhost:{PUERTO}")
        print("=" * 62)
        if ABRIR_NAVEGADOR:
            webbrowser.open(f"http://localhost:{PUERTO}")
        return

    ip = ip_local()
    print("=" * 62)
    print("            SISTEMA INVENTARIO - PUNTO DE VENTA")
    print("=" * 62)
    print(f"  En esta PC     : http://localhost:{PUERTO}")
    print(f"  En el celular  : http://{ip}:{PUERTO}")
    print("  (el celular debe estar en la misma red WiFi)")
    print("=" * 62)
    print("  Para detener el servidor: presiona Ctrl+C")
    print("=" * 62)

    if ABRIR_NAVEGADOR:
        threading.Thread(target=abrir_navegador, daemon=True).start()

    uvicorn.run(app, host=HOST, port=PUERTO, log_level="info")


if __name__ == "__main__":
    main()
