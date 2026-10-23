"""Conexión a la base de datos SQLite (local) o PostgreSQL (nube).

Rutas portables:
  - En desarrollo : backend/inventario.db
  - Con PyInstaller: junto al ejecutable (portable) o en %LOCALAPPDATA%
"""

import os
import sys
from pathlib import Path

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


# SQLite local por defecto. Para PostgreSQL en la nube, definir DATABASE_URL.
DATABASE_URL_ENV = os.getenv("DATABASE_URL")
if DATABASE_URL_ENV:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL_ENV
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{(_data_dir() / 'inventario.db').as_posix()}"

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia FastAPI que entrega una sesión de BD por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
