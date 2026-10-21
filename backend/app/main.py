"""Punto de entrada principal de la aplicación FastAPI."""

import hashlib
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import Base, SessionLocal, engine, _data_dir
from app.models import Division, Mesa, Producto, TurnoCaja, Usuario
from app.routes.caja import router as caja_router
from app.routes.categorias import router as categorias_router
from app.routes.cuentas import router as cuentas_router
from app.routes.inventario import router as inventario_router
from app.routes.mesas import router as mesas_router
from app.routes.pedidos import router as pedidos_router
from app.routes.usuarios import router as usuarios_router

VERSION = "1.1.0"

app = FastAPI(
    title="Sistema Inventario y Punto de Venta",
    description="Aplicación multiplataforma para gestión de inventario, mesas y ventas",
    version=VERSION,
)

# CORS: permite que el frontend React (localhost:3000 o IP de la red) consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(usuarios_router, prefix="/api/usuarios", tags=["usuarios"])
app.include_router(mesas_router, prefix="/api/mesas", tags=["mesas"])
app.include_router(inventario_router, prefix="/api/inventario", tags=["inventario"])
app.include_router(pedidos_router, prefix="/api/pedidos", tags=["pedidos"])
app.include_router(cuentas_router, prefix="/api/cuentas", tags=["cuentas"])
app.include_router(caja_router, prefix="/api/caja", tags=["caja"])
app.include_router(categorias_router, prefix="/api/categorias", tags=["categorias"])


# ------------------------------------------------------------------
# Rutas portables (funcionan en desarrollo y en el .exe compilado)
# ------------------------------------------------------------------

def _build_dir() -> Path:
    """Carpeta con el build de producción del frontend."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "frontend" / "build"


def _ip_local() -> str:
    """IP local de la PC (para que el móvil/la APK la descubran)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _migrar_columnas_faltantes() -> None:
    """Añade columnas nuevas a tablas existentes (migración ligera para SQLite).

    create_all() solo crea tablas nuevas, no columnas nuevas en tablas que ya
    existen. Aquí se detectan y agregan las que falten.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tablas_existentes = set(inspector.get_table_names())

    for tabla in Base.metadata.sorted_tables:
        if tabla.name not in tablas_existentes:
            continue
        columnas_existentes = {c["name"] for c in inspector.get_columns(tabla.name)}
        for columna in tabla.columns:
            if columna.name in columnas_existentes:
                continue
            tipo = columna.type.compile(engine.dialect)
            default = ""
            if columna.default is not None and getattr(columna.default, "is_scalar", False):
                default = f" DEFAULT {columna.default.arg!r}"
            elif not columna.nullable and columna.default is None:
                default = " DEFAULT ''"
            sql = (
                f'ALTER TABLE {tabla.name} ADD COLUMN "{columna.name}" {tipo}{default}'
            )
            with engine.begin() as conexion:
                conexion.execute(text(sql))
            print(f"[migracion] columna {tabla.name}.{columna.name} agregada")


def crear_datos_iniciales() -> None:
    """Crea tablas y siembra usuarios, productos y mesas de ejemplo."""
    Base.metadata.create_all(bind=engine)
    _migrar_columnas_faltantes()

    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            db.add_all(
                [
                    Usuario(
                        nombre="Administrador",
                        rol="admin",
                        email="admin@localpos.com",
                        password_hash=hash_password("admin123"),
                    ),
                    Usuario(
                        nombre="Mesero Demo",
                        rol="mesero",
                        email="mesero@localpos.com",
                        password_hash=hash_password("mesero123"),
                    ),
                ]
            )

        if db.query(Producto).count() == 0:
            db.add_all(
                [
                    Producto(nombre="Hamburguesa", descripcion="Con papas", precio=9.00, stock=50),
                    Producto(nombre="Papas fritas", descripcion="Porcion grande", precio=3.00, stock=50),
                    Producto(nombre="Refresco", descripcion="Botella 500 ml", precio=2.00, stock=100),
                    Producto(nombre="Cafe", descripcion="Taza caliente", precio=1.50, stock=100),
                ]
            )

        if db.query(Mesa).count() == 0:
            db.add_all([Mesa(numero=n, capacidad=4, estado="disponible") for n in range(1, 7)])

        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    crear_datos_iniciales()


@app.get("/")
def read_root():
    build = _build_dir()
    if (build / "index.html").exists():
        return FileResponse(build / "index.html")
    return {"message": "Sistema Inventario y Punto de Venta API", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": VERSION}


@app.get("/api/config")
def config():
    """Información de la instalación (la usan el móvil y la APK)."""
    build = _build_dir()
    return {
        "version": VERSION,
        "ip": _ip_local(),
        "puerto": int(os.getenv("PORT", "8000")),
        "modo": "ejecutable" if getattr(sys, "frozen", False) else "desarrollo",
        "frontend_incorporado": (build / "index.html").exists(),
        "datos": str(_data_dir()),
    }


# ------------------------------------------------------------------
# Frontend compilado (SPA). Se registra al final para no tapar la API.
# ------------------------------------------------------------------

BUILD = _build_dir()


@app.get("/{ruta:path}", include_in_schema=False)
def spa(ruta: str):
    """Sirve el build de React con fallback a index.html (enrutado SPA)."""
    if ruta.startswith("api/") or ruta in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")

    if not (BUILD / "index.html").exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend no compilado. Ejecuta 'npm run build' en frontend/ o usa npm start.",
        )

    candidato = (BUILD / ruta).resolve()
    try:
        dentro = str(candidato).startswith(str(BUILD.resolve()))
    except Exception:
        dentro = False
    if dentro and candidato.is_file():
        return FileResponse(candidato)

    return FileResponse(BUILD / "index.html")
