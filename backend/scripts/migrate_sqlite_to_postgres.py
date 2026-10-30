#!/usr/bin/env python3
"""Migra la base SQLite local a PostgreSQL (Neon u otro PostgreSQL).

Uso recomendado (desde ``backend/``):

    export DATABASE_URL="postgresql://usuario:clave@host/db?sslmode=require"
    export ADMIN_PASSWORD="una-clave-segura"
    python scripts/migrate_sqlite_to_postgres.py --reset

El script:
  1. Crea las tablas que falten con el esquema actual de SQLAlchemy.
  2. Copia todas las filas conservando sus IDs.
  3. Ajusta las secuencias de PostgreSQL para futuros INSERT.
  4. Opcionalmente cambia la clave del administrador indicado.

No modifica la base SQLite: la abre en modo solo lectura.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _parse_datetime(valor):
    """Convierte las fechas de texto de SQLite a ``datetime`` de Python."""
    if valor is None or isinstance(valor, datetime):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(texto).replace(tzinfo=None)
        except ValueError:
            for formato in (
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ):
                try:
                    return datetime.strptime(texto, formato)
                except ValueError:
                    continue
    return valor


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _normalizar_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra inventario.db (SQLite) a PostgreSQL."
    )
    parser.add_argument(
        "--sqlite",
        default=str(BASE_DIR / "data" / "inventario.db"),
        help="Ruta a la base SQLite de origen.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Vacía las tablas del destino antes de copiar (recomendado).",
    )
    parser.add_argument(
        "--admin-alias",
        default="Admin",
        help="Alias del administrador cuya clave se actualizará.",
    )
    parser.add_argument(
        "--admin-password",
        default=None,
        help="Clave nueva del administrador (mejor usar la variable ADMIN_PASSWORD).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    url = _normalizar_url(os.getenv("DATABASE_URL", ""))
    if not url.startswith(
        ("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")
    ):
        print(
            "ERROR: define DATABASE_URL con una cadena de PostgreSQL.\n"
            "Ejemplo: postgresql://usuario:clave@host/db?sslmode=require"
        )
        return 2
    os.environ["DATABASE_URL"] = url

    sqlite_path = Path(args.sqlite).expanduser().resolve()
    if not sqlite_path.is_file():
        print(f"ERROR: no existe la base SQLite: {sqlite_path}")
        return 2

    admin_password = args.admin_password or os.getenv("ADMIN_PASSWORD") or ""

    # Se importan después de fijar DATABASE_URL para que SQLAlchemy use el
    # motor PostgreSQL y no cree el archivo SQLite local.
    from sqlalchemy import DateTime, text
    from app import models  # noqa: F401  (registra las tablas en Base.metadata)
    from app.database import Base, engine

    Base.metadata.create_all(bind=engine)

    tablas = list(Base.metadata.sorted_tables)
    sqlite = sqlite3.connect(sqlite_path.as_uri() + "?mode=ro", uri=True)
    sqlite.row_factory = sqlite3.Row

    try:
        tablas_sqlite = {
            fila["name"]
            for fila in sqlite.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        if admin_password:
            existe_admin = sqlite.execute(
                "SELECT 1 FROM usuarios WHERE alias = ?", (args.admin_alias,)
            ).fetchone()
            if not existe_admin:
                print(
                    f"ERROR: no existe el usuario '{args.admin_alias}' en la "
                    "base SQLite; no se puede cambiar su clave."
                )
                return 2

        with engine.begin() as conexion:
            total_destino = sum(
                conexion.execute(text(f'SELECT COUNT(*) FROM "{tabla.name}"')).scalar()
                or 0
                for tabla in tablas
            )
            if total_destino and not args.reset:
                print(
                    "ERROR: la base destino ya contiene datos. "
                    "Ejecuta de nuevo con --reset para reemplazarlos."
                )
                return 3

            if args.reset:
                nombres = ", ".join(f'"{tabla.name}"' for tabla in reversed(tablas))
                conexion.execute(
                    text(f"TRUNCATE TABLE {nombres} RESTART IDENTITY CASCADE")
                )
                print("Tablas del destino vaciadas.")

            for tabla in tablas:
                if tabla.name not in tablas_sqlite:
                    print(f"OMITIDA {tabla.name}: no existe en SQLite")
                    continue

                columnas_sqlite = {
                    fila["name"]
                    for fila in sqlite.execute(f'PRAGMA table_info("{tabla.name}")')
                }
                columnas = [
                    columna
                    for columna in tabla.columns
                    if columna.name in columnas_sqlite
                ]
                faltantes = [
                    columna.name
                    for columna in tabla.columns
                    if columna.name not in columnas_sqlite
                    and not columna.nullable
                    and columna.default is None
                    and not columna.primary_key
                ]
                if faltantes:
                    print(
                        f"AVISO {tabla.name}: columnas nuevas sin valor en "
                        f"SQLite: {', '.join(faltantes)}"
                    )

                if not columnas:
                    continue

                lista_columnas = ", ".join(
                    f'"{columna.name}"' for columna in columnas
                )
                filas = []
                for fila in sqlite.execute(
                    f'SELECT {lista_columnas} FROM "{tabla.name}"'
                ):
                    datos = {}
                    for columna in columnas:
                        valor = fila[columna.name]
                        if isinstance(columna.type, DateTime):
                            valor = _parse_datetime(valor)
                        datos[columna.name] = valor
                    filas.append(datos)

                if filas:
                    conexion.execute(tabla.insert(), filas)
                print(f"COPIADA {tabla.name}: {len(filas)} fila(s)")

                if "id" in tabla.c:
                    max_id = (
                        conexion.execute(
                            text(f'SELECT COALESCE(MAX(id), 0) FROM "{tabla.name}"')
                        ).scalar()
                        or 0
                    )
                    conexion.execute(
                        text(
                            "SELECT setval("
                            "pg_get_serial_sequence(:tabla, 'id'), "
                            ":valor, :llamado)"
                        ),
                        {
                            "tabla": tabla.name,
                            "valor": max_id or 1,
                            "llamado": max_id > 0,
                        },
                    )

            if admin_password:
                resultado = conexion.execute(
                    text(
                        "UPDATE usuarios "
                        "SET password_hash = :hash, activo = 1 "
                        "WHERE alias = :alias"
                    ),
                    {
                        "hash": _hash_password(admin_password),
                        "alias": args.admin_alias,
                    },
                )
                print(
                    f"CLAVE ACTUALIZADA: {args.admin_alias} "
                    f"({resultado.rowcount} usuario)"
                )

            errores = []
            for tabla in tablas:
                if tabla.name not in tablas_sqlite:
                    continue
                origen = sqlite.execute(
                    f'SELECT COUNT(*) FROM "{tabla.name}"'
                ).fetchone()[0]
                destino = (
                    conexion.execute(
                        text(f'SELECT COUNT(*) FROM "{tabla.name}"')
                    ).scalar()
                    or 0
                )
                estado = "OK " if origen == destino else "DIF"
                print(f"{estado} {tabla.name:24} {origen:6} -> {destino}")
                if origen != destino:
                    errores.append(tabla.name)

            if errores:
                print(f"ERROR: conteos distintos en: {', '.join(errores)}")
                return 1

        print("\nMigración completada correctamente.")
        return 0
    finally:
        sqlite.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
