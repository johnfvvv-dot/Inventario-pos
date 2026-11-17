"""Configuración compartida de la base de datos temporal para las pruebas.

Todos los módulos de prueba se ejecutan en el mismo proceso con
``unittest discover``. La URL de la base se define una sola vez, antes de
importar ``app.database``, y la limpieza se hace al finalizar el proceso.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    _TEMP_DIR = tempfile.mkdtemp(prefix="inventario_pos_test_")
    _DB_PATH = Path(_TEMP_DIR) / "inventario_pos_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"
    os.environ.setdefault("APP_TIMEZONE", "America/Bogota")

    def _limpiar_entorno() -> None:
        try:
            from app.database import engine

            engine.dispose()
        except Exception:
            pass
        shutil.rmtree(_TEMP_DIR, ignore_errors=True)

    atexit.register(_limpiar_entorno)
