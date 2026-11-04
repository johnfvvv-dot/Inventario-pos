"""Conexión a la base de datos SQLite (local) o PostgreSQL (nube).

Rutas portables:
  - En desarrollo : backend/data/inventario.db (o backend/.env)
  - Con PyInstaller: junto al ejecutable (portable) o en %LOCALAPPDATA%

El ejecutable híbrido lee la cadena de Neon, en este orden:
  1. Variable de entorno DATABASE_URL.
  2. Archivo inventario-pos.env junto al .exe (o backend/.env en desarrollo).
  3. Valor compilado en app/_build_defaults.py (solo en el .exe de entrega).
"""

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


def _base_dir() -> Path:
    """Directorio base de datos de la aplicación."""
    if getattr(sys, "frozen", False):  # ejecutable compilado con PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent  # backend/


def _data_dir() -> Path:
    """Carpeta donde se guardan los datos (BD y copias de seguridad)."""
    if getattr(sys, "frozen", False):
        carpeta = Path(os.getenv("LOCALAPPDATA", Path.home())) / "InventarioPOS"
    else:
        carpeta = _base_dir() / "data"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _normalizar_url(url: str) -> str:
    """Acepta el formato ``postgres://`` que usan algunos proveedores."""
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _leer_env_archivo(ruta: Path) -> None:
    """Carga un .env sin sobrescribir variables ya definidas."""
    if not ruta.is_file():
        return

    valores = {}
    try:
        from dotenv import dotenv_values

        valores = dotenv_values(ruta)
    except Exception:
        # Respaldo mínimo por si python-dotenv no está disponible.
        for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
            texto = linea.strip()
            if not texto or texto.startswith("#") or "=" not in texto:
                continue
            clave, valor = texto.split("=", 1)
            clave = clave.strip()
            if clave.startswith("export "):
                clave = clave[len("export ") :].strip()
            valores[clave] = valor.strip().strip('"').strip("'")

    for clave, valor in valores.items():
        if clave and valor is not None:
            os.environ.setdefault(clave, str(valor))


def _cargar_env_local() -> None:
    """Busca configuración junto al ejecutable o en backend/.env."""
    candidatos = []
    ruta_explicita = os.getenv("INVENTARIO_POS_ENV", "").strip()
    if ruta_explicita:
        candidatos.append(Path(ruta_explicita).expanduser())

    if getattr(sys, "frozen", False):
        candidatos.append(Path(sys.executable).resolve().parent / "inventario-pos.env")
    else:
        candidatos.append(Path(__file__).resolve().parent.parent / ".env")

    for ruta in candidatos:
        _leer_env_archivo(ruta)


# Valor embebido solo en el .exe híbrido. El archivo no se versiona.
try:
    from app._build_defaults import DATABASE_URL as _DATABASE_URL_COMPILADA
except Exception:
    _DATABASE_URL_COMPILADA = ""

_cargar_env_local()

# SQLite local por defecto. En el .exe híbrido se usa la cadena compilada.
DATABASE_URL_ENV = os.getenv("DATABASE_URL") or _DATABASE_URL_COMPILADA
if DATABASE_URL_ENV:
    SQLALCHEMY_DATABASE_URL = _normalizar_url(DATABASE_URL_ENV)
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{(_data_dir() / 'inventario.db').as_posix()}"

connect_args = {}
engine_options = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL gestionado (Neon): valida la conexión antes de usarla y
    # recíclala antes de que el proveedor cierre las conexiones ociosas.
    connect_args = {"connect_timeout": 10}
    engine_options = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 5,
    }

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args, **engine_options
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def tipo_database() -> str:
    """Devuelve 'sqlite' o 'postgresql' sin exponer credenciales."""
    return "sqlite" if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else "postgresql"


def descripcion_database() -> str:
    """Texto corto para el arranque del ejecutable, sin usuario ni clave."""
    if tipo_database() == "sqlite":
        return f"SQLite local ({_data_dir() / 'inventario.db'})"
    host = urlparse(SQLALCHEMY_DATABASE_URL).hostname or "host desconocido"
    return f"PostgreSQL en {host}"


def huella_database() -> str:
    """Identificador no sensible de la base configurada (host + nombre).

    Permite comparar si el ejecutable y Render apuntan a la misma base sin
    exponer usuario, clave ni la cadena de conexion completa.
    """
    if tipo_database() == "sqlite":
        return "sqlite-local"
    partes = urlparse(SQLALCHEMY_DATABASE_URL)
    base = f"{partes.hostname or ''}/{partes.path.lstrip('/')}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


def get_db():
    """Dependencia FastAPI que entrega una sesión de BD por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
