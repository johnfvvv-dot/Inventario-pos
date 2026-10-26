"""Wrapper ADOMD para consultar motores tabulares (Power BI Desktop / SSAS).

Carga la DLL ADOMD que viene incluida con Power BI Desktop
(`Microsoft.PowerBI.AdomdClient.dll`) usando pythonnet.
"""

from __future__ import annotations

import datetime
import decimal
import json
import os
import sys

PBI_BIN = r"C:\Program Files\Microsoft Power BI Desktop\bin"
_DLL = os.path.join(PBI_BIN, "Microsoft.PowerBI.AdomdClient.dll")

_AdomdConnection = None
_AdomdCommand = None
_System = None
_Invariant = None


def _ensure_loaded() -> None:
    """Carga perezosa del ensamblado ADOMD (solo Windows)."""
    global _AdomdConnection, _AdomdCommand, _System, _Invariant
    if _AdomdConnection is not None:
        return

    if not os.path.exists(_DLL):
        raise RuntimeError(f"No se encontró la DLL ADOMD en: {_DLL}")

    if PBI_BIN not in sys.path:
        sys.path.append(PBI_BIN)

    import clr  # type: ignore

    clr.AddReference(_DLL)

    import System  # type: ignore

    _System = System

    # Resolver dependencias nativas dentro de la carpeta de Power BI Desktop
    def _resolver(_sender, args):  # pragma: no cover - depende de .NET
        simple = System.Reflection.AssemblyName(args.Name).Name
        candidato = os.path.join(PBI_BIN, simple + ".dll")
        if os.path.exists(candidato):
            return System.Reflection.Assembly.LoadFrom(candidato)
        return None

    System.AppDomain.CurrentDomain.AssemblyResolve += _resolver
    globals()["_resolver_ref"] = _resolver  # evitar GC del delegado

    from Microsoft.AnalysisServices.AdomdClient import (  # type: ignore
        AdomdCommand,
        AdomdConnection,
    )

    _AdomdConnection = AdomdConnection
    _AdomdCommand = AdomdCommand
    _Invariant = System.Globalization.CultureInfo.InvariantCulture


def connect(port: int, timeout_s: int = 10):
    """Abre una conexión ADOMD contra el motor local en `localhost:port`."""
    _ensure_loaded()
    conn = _AdomdConnection()
    conn.ConnectionString = (
        f"Provider=MSOLAP;Data Source=localhost:{port};"
        f"Connect Timeout={timeout_s};"
    )
    try:
        conn.Open()
    except Exception:
        try:
            conn.Close()
        except Exception:
            pass
        raise
    return conn


def _to_python(valor, tipo: str = ""):
    """Convierte valores .NET a tipos serializables en JSON.

    `tipo` es el nombre del tipo .NET reportado por ADOMD
    (p. ej. System.DateTime, System.Decimal), necesario porque pythonnet
    no siempre auto-convierte esos valores.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float, str)):
        return valor
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    if isinstance(valor, datetime.datetime):
        return valor.isoformat(sep=" ")
    if isinstance(valor, datetime.date):
        return valor.isoformat()
    if isinstance(valor, datetime.timedelta):
        return valor.total_seconds()
    if isinstance(valor, (bytes, bytearray)):
        return valor.decode("utf-8", errors="replace")

    # Objetos .NET sin convertir: usar el tipo de columna para decidir
    t = tipo or type(valor).__name__
    if "DateTime" in t or "Date" in t:
        try:
            return str(valor.ToString("yyyy-MM-dd HH:mm:ss", _Invariant))
        except Exception:
            return str(valor)
    if "Decimal" in t or "Double" in t or "Single" in t:
        try:
            return float(valor.ToString(_Invariant))
        except Exception:
            try:
                return float(str(valor).replace(",", "."))
            except (TypeError, ValueError):
                return str(valor)
    if "Int" in t or "Byte" in t:
        try:
            return int(valor.ToString(_Invariant))
        except Exception:
            return str(valor)
    if "TimeSpan" in t:
        try:
            return valor.TotalSeconds
        except Exception:
            return str(valor)
    return str(valor)


def query(conn, comando: str, max_rows: int | None = 200000) -> dict:
    """Ejecuta DAX / DMV / MDX y devuelve {columns, types, rows, rowCount}."""
    cmd = _AdomdCommand(comando, conn)
    reader = cmd.ExecuteReader()
    try:
        n = reader.FieldCount
        columnas = [reader.GetName(i) for i in range(n)]
        tipos = [reader.GetFieldType(i).ToString() for i in range(n)]
        filas = []
        while reader.Read():
            fila = []
            for i in range(n):
                if reader.IsDBNull(i):
                    fila.append(None)
                else:
                    fila.append(_to_python(reader.GetValue(i), tipos[i]))
            filas.append(fila)
            if max_rows is not None and len(filas) >= max_rows:
                break
    finally:
        reader.Close()

    return {
        "columns": columnas,
        "types": tipos,
        "rows": filas,
        "rowCount": len(filas),
    }


def probe(port: int, timeout_s: int = 5) -> str | None:
    """Devuelve el nombre del catálogo si el motor responde, o None."""
    try:
        conn = connect(port, timeout_s)
    except Exception:
        return None
    try:
        res = query(conn, "SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS", max_rows=1)
        if res["rows"]:
            return str(res["rows"][0][0])
        return ""
    except Exception:
        return None
    finally:
        conn.Close()


def main() -> None:
    """Uso directo: python adomd.py <puerto> "<consulta>" """
    import argparse

    p = argparse.ArgumentParser(description="Consulta ADOMD directa")
    p.add_argument("port", type=int)
    p.add_argument("consulta")
    p.add_argument("--max", type=int, default=200000)
    args = p.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    conn = connect(args.port)
    try:
        res = query(conn, args.consulta, max_rows=args.max)
    finally:
        conn.Close()
    json.dump(res, sys.stdout, ensure_ascii=False, default=str)
    print()


if __name__ == "__main__":
    main()
