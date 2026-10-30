"""Punto de entrada principal de la aplicación FastAPI."""

import hashlib
import os
import socket
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import Base, SessionLocal, engine, _data_dir
from app.models import (
    Division,
    Mesa,
    MigracionSistema,
    Pedido,
    Producto,
    TurnoCaja,
    Usuario,
    etiqueta_desde_numero_historico,
)
from app.routes.caja import router as caja_router
from app.routes.categorias import router as categorias_router
from app.routes.cuentas import router as cuentas_router
from app.routes.inventario import router as inventario_router
from app.routes.mesas import router as mesas_router
from app.routes.pedidos import router as pedidos_router
from app.routes.usuarios import router as usuarios_router
from app.schemas import CLAVE_INICIAL
from app.tiempo import ahora_local, utc_a_local

VERSION = "1.1.0"

CLAVE_MIGRACION_FECHAS = "fechas_locales_v1"

app = FastAPI(
    title="Sistema Inventario y Punto de Venta",
    description="Aplicación multiplataforma para gestión de inventario, mesas y ventas",
    version=VERSION,
)

def _cors_origins() -> list[str]:
    """Orígenes permitidos, configurables en el despliegue público.

    Sin ``CORS_ORIGINS`` se mantiene el comportamiento local permisivo. En
    producción se recomienda una lista separada por comas con la URL del
    frontend, por ejemplo:
    ``CORS_ORIGINS=https://inventario-pos.pages.dev``.
    """
    origenes = os.getenv("CORS_ORIGINS", "*").strip()
    if not origenes or origenes == "*":
        return ["*"]
    return [origen.strip().rstrip("/") for origen in origenes.split(",") if origen.strip()]


# CORS: permite que el frontend React (localhost:3000, IP de la red o el
# dominio público de Cloudflare Pages) consuma la API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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


def _migrar_alias_usuarios() -> None:
    """En bases antiguas el identificador era 'email'; ahora es 'alias'."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "usuarios" not in inspector.get_table_names():
        return
    columnas = {c["name"] for c in inspector.get_columns("usuarios")}
    if "alias" not in columnas:
        return

    with engine.begin() as conexion:
        # Detecta si la base es "legacy" (aún tiene la columna email con datos)
        legacy = 0
        if "email" in columnas:
            legacy = (
                conexion.execute(
                    text(
                        "SELECT COUNT(*) FROM usuarios "
                        "WHERE email IS NOT NULL AND email != ''"
                    )
                ).scalar()
                or 0
            )

        if "email" in columnas:
            conexion.execute(
                text(
                    "UPDATE usuarios SET alias = email "
                    "WHERE (alias IS NULL OR alias = '') AND email IS NOT NULL"
                )
            )
        conexion.execute(
            text("UPDATE usuarios SET alias = 'Admin' WHERE alias IS NULL OR alias = ''")
        )
        # El rol antiguo era 'mesero', ahora es 'bartender'
        conexion.execute(
            text("UPDATE usuarios SET rol = 'bartender' WHERE rol = 'mesero'")
        )

        if legacy:
            # El admin migrado usa la clave inicial
            conexion.execute(
                text(
                    "UPDATE usuarios SET password_hash = :hash "
                    "WHERE rol = 'admin' AND (alias = 'Admin' OR alias LIKE '%@%')"
                ),
                {"hash": hash_password(CLAVE_INICIAL)},
            )
            # Solo se conserva el admin (el primero)
            conexion.execute(
                text(
                    "UPDATE usuarios SET alias = 'Admin' "
                    "WHERE alias LIKE '%@%' AND rol = 'admin' "
                    "AND NOT EXISTS (SELECT 1 FROM usuarios u2 WHERE u2.alias = 'Admin')"
                )
            )
            # Los bartenders de prueba quedan desactivados
            conexion.execute(
                text(
                    "UPDATE usuarios SET activo = 0 "
                    "WHERE alias LIKE '%@%' AND rol = 'bartender'"
                )
            )

        # Pedidos Antiguos: guardar el numero de mesa historico
        try:
            conexion.execute(
                text(
                    "UPDATE pedidos SET mesa_numero_historico = "
                    "(SELECT numero FROM mesas WHERE mesas.id = pedidos.mesa_id) "
                    "WHERE mesa_id IS NOT NULL AND mesa_numero_historico IS NULL"
                )
            )
        except Exception:
            pass

        # Mesas antiguas: completar tipo/grupo/posicion
        try:
            conexion.execute(
                text("UPDATE mesas SET tipo = 'mesa' WHERE tipo IS NULL OR tipo = ''")
            )
            conexion.execute(
                text("UPDATE mesas SET posicion = 1 WHERE posicion IS NULL")
            )
        except Exception:
            pass

        # Usuarios antiguos sin fecha de creacion
        try:
            if engine.dialect.name == "sqlite":
                conexion.execute(
                    text(
                        "UPDATE usuarios SET creado_en = datetime('now', 'localtime') "
                        "WHERE creado_en IS NULL"
                    )
                )
            else:
                conexion.execute(
                    text(
                        "UPDATE usuarios SET creado_en = :ahora "
                        "WHERE creado_en IS NULL"
                    ),
                    {"ahora": ahora_local()},
                )
        except Exception:
            pass

        # La columna 'email' ya no se usa: se elimina (SQLite 3.35+)
        if "email" in columnas:
            try:
                conexion.execute(text("DROP INDEX IF EXISTS ix_usuarios_email"))
                conexion.execute(text("ALTER TABLE usuarios DROP COLUMN email"))
            except Exception as exc:  # pragma: no cover
                print(f"[migracion] no se pudo eliminar usuarios.email: {exc}")


def _migrar_fechas_a_hora_local() -> None:
    """Convierte a hora local las fechas que versiones anteriores guardaron en UTC.

    Se ejecuta una sola vez por base de datos. El marcador en
    ``migraciones_sistema`` evita desplazar de nuevo fechas ya convertidas.
    """
    db = SessionLocal()
    try:
        aplicada = (
            db.query(MigracionSistema)
            .filter(MigracionSistema.clave == CLAVE_MIGRACION_FECHAS)
            .first()
        )
        if aplicada:
            return

        cambios = 0

        for usuario in db.query(Usuario).all():
            if usuario.creado_en is not None:
                usuario.creado_en = utc_a_local(usuario.creado_en)
                cambios += 1

        for pedido in db.query(Pedido).all():
            if pedido.fecha is not None:
                pedido.fecha = utc_a_local(pedido.fecha)
                cambios += 1
            if pedido.fecha_cierre is not None:
                pedido.fecha_cierre = utc_a_local(pedido.fecha_cierre)
                cambios += 1

        for division in db.query(Division).all():
            if division.fecha is not None:
                division.fecha = utc_a_local(division.fecha)
                cambios += 1

        for turno in db.query(TurnoCaja).all():
            if turno.fecha_apertura is not None:
                turno.fecha_apertura = utc_a_local(turno.fecha_apertura)
                cambios += 1
            if turno.fecha_cierre is not None:
                turno.fecha_cierre = utc_a_local(turno.fecha_cierre)
                cambios += 1

        db.add(MigracionSistema(clave=CLAVE_MIGRACION_FECHAS))
        db.commit()
        print(f"[migracion] {cambios} fechas convertidas de UTC a hora local")
    finally:
        db.close()


def _migrar_etiquetas_historial() -> None:
    """Completa el origen histórico (número y etiqueta) de pedidos anteriores.

    - Si el pedido conserva su mesa/plaza, toma los datos actuales.
    - Si la mesa fue eliminada, conserva el número histórico y reconstruye
      la etiqueta ("Mesa N" o "Barra N") cuando falte.
    """
    db = SessionLocal()
    try:
        pedidos = db.query(Pedido).all()
        if not pedidos:
            return

        mesas = {m.id: m for m in db.query(Mesa).all()}
        cambiados = 0
        for pedido in pedidos:
            numero_antes = pedido.mesa_numero_historico
            etiqueta_antes = pedido.mesa_etiqueta_historica
            if pedido.mesa_id and pedido.mesa_id in mesas:
                mesa = mesas[pedido.mesa_id]
                pedido.mesa_numero_historico = mesa.numero
                pedido.mesa_etiqueta_historica = mesa.etiqueta_historial()
            elif (
                pedido.mesa_numero_historico is not None
                and not pedido.mesa_etiqueta_historica
            ):
                pedido.mesa_etiqueta_historica = etiqueta_desde_numero_historico(
                    pedido.mesa_numero_historico
                )
            if (
                pedido.mesa_numero_historico != numero_antes
                or pedido.mesa_etiqueta_historica != etiqueta_antes
            ):
                cambiados += 1

        if cambiados:
            db.commit()
            print(f"[migracion] {cambiados} pedidos con origen histórico actualizado")
    finally:
        db.close()


def crear_datos_iniciales() -> None:
    """Crea tablas y siembra usuarios, productos y mesas de ejemplo."""
    Base.metadata.create_all(bind=engine)
    _migrar_columnas_faltantes()
    # Antes de completar fechas nulas: así las que se rellenen ya quedan locales.
    _migrar_fechas_a_hora_local()
    _migrar_alias_usuarios()
    _migrar_etiquetas_historial()

    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            # Unico usuario inicial: alias "Admin" con la clave inicial
            db.add(
                Usuario(
                    alias="Admin",
                    nombre="Administrador",
                    rol="admin",
                    password_hash=hash_password(CLAVE_INICIAL),
                    activo=1,
                )
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


@app.api_route(
    "/api/{ruta:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
def api_no_encontrada(ruta: str):
    """Responde 404 claro para una ruta de API inexistente.

    Sin esta ruta, un POST a una dirección no registrada cae en el fallback
    del frontend (que solo acepta GET) y el cliente recibe un confuso
    "Method Not Allowed" en lugar de un 404 con el detalle.
    """
    raise HTTPException(
        status_code=404,
        detail=f"Ruta de API no encontrada: /api/{ruta}",
    )


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
