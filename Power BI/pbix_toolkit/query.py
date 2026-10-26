#!/usr/bin/env python3
"""Puente WSL -> Windows para consultar el modelo .pbix abierto.

Ejecuta `engine.py` con el Python de Windows y devuelve su salida (JSON).

Uso:
    python3 query.py open "Ruta\\Archivo.pbix"    # abre el modelo (copia segura)
    python3 query.py status                       # estado de la sesión
    python3 query.py schema [--refresh]           # esquema del modelo
    python3 query.py query "EVALUATE ..."         # consulta DAX -> JSON
    python3 query.py query --file consulta.dax    # consulta desde archivo
    python3 query.py query "EVALUATE ..." --table # salida tabular legible
    python3 query.py close                        # cierra Power BI Desktop
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

# Rutas (ajustables por variables de entorno)
WIN_PYTHON_WSL = os.environ.get(
    "PBI_WIN_PYTHON",
    "/mnt/c/Users/XR-18/AppData/Local/Programs/Python/Python313/python.exe",
)
ENGINE_WIN = os.environ.get(
    "PBI_ENGINE",
    r"C:\Users\XR-18\Desktop\Python\Power BI\pbix_toolkit\engine.py",
)


def ejecutar_engine(args: list[str], stdin_data: str | None = None) -> tuple[int, str, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [WIN_PYTHON_WSL, ENGINE_WIN, *args],
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def imprimir_tabla(res: dict) -> None:
    columnas = [str(c) for c in res.get("columns", [])]
    filas = res.get("rows", [])
    if not columnas:
        print("(sin columnas)")
        return

    def celda(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:,.2f}".rstrip("0").rstrip(".")
        return str(v)

    datos = [[celda(v) for v in fila] for fila in filas]
    anchos = [len(c) for c in columnas]
    for fila in datos:
        for i, v in enumerate(fila):
            anchos[i] = max(anchos[i], len(v))

    sep = "  "
    encabezado = sep.join(c.ljust(anchos[i]) for i, c in enumerate(columnas))
    print(encabezado)
    print("-" * len(encabezado))
    for fila in datos:
        print(sep.join(v.ljust(anchos[i]) for i, v in enumerate(fila)))
    print(f"\n({res.get('rowCount', len(filas))} filas)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Puente de consulta .pbix -> Power BI Desktop")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_open = sub.add_parser("open")
    p_open.add_argument("pbix")
    p_open.add_argument("--timeout", type=int, default=240)

    sub.add_parser("status")
    sub.add_parser("close")

    p_schema = sub.add_parser("schema")
    p_schema.add_argument("--refresh", action="store_true")
    p_schema.add_argument("--summary", action="store_true", help="Solo el resumen de texto")

    p_query = sub.add_parser("query")
    p_query.add_argument("consulta", nargs="?", default=None)
    p_query.add_argument("--stdin", action="store_true", help="Leer la consulta de stdin")
    p_query.add_argument("--file", default=None, help="Leer la consulta desde un archivo")
    p_query.add_argument("--table", action="store_true", help="Salida tabular legible")
    p_query.add_argument("--max", type=int, default=200000)

    args = parser.parse_args()

    if args.cmd == "open":
        rc, out, err = ejecutar_engine(["open", args.pbix, "--timeout", str(args.timeout)])
    elif args.cmd == "status":
        rc, out, err = ejecutar_engine(["status"])
    elif args.cmd == "close":
        rc, out, err = ejecutar_engine(["close"])
    elif args.cmd == "schema":
        cmd = ["schema"] + (["--refresh"] if args.refresh else [])
        rc, out, err = ejecutar_engine(cmd)
    elif args.cmd == "query":
        if args.file:
            consulta = open(args.file, encoding="utf-8").read()
        elif args.consulta:
            consulta = args.consulta
        else:
            consulta = sys.stdin.read()
        rc, out, err = ejecutar_engine(["query", "--stdin", "--max", str(args.max)], stdin_data=consulta)
    else:  # pragma: no cover
        parser.error("comando desconocido")

    if err.strip() and (rc != 0 or not out.strip()):
        sys.stderr.write(err)
    if rc != 0:
        sys.exit(rc)
    if not out.strip():
        sys.exit(0)

    if args.cmd == "schema" and args.summary:
        datos = json.loads(out)
        print(datos.get("summary", ""))
        return

    if args.cmd == "query" and getattr(args, "table", False):
        datos = json.loads(out)
        if not datos.get("ok", True):
            print(json.dumps(datos, ensure_ascii=False, indent=2))
            return
        imprimir_tabla(datos)
        return

    print(out, end="")


if __name__ == "__main__":
    main()
