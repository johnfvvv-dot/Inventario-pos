#!/usr/bin/env python3
"""Construye los dos tableros interactivos (con filtros) con datos del modelo.

Extrae el detalle (contratos y mascotas) desde la sesión activa del .pbix
vía query.py, lo enriquece y renderiza los HTML autocontenidos:

    dashboards/tablero_kpis_sucursal.html
    dashboards/tablero_planes_petamigo_petfiel.html

Uso (con el modelo ya abierto con `python3 query.py open ...`):
    python3 demos/generar_tableros.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT))

from dashboard_interactivo import renderizar  # noqa: E402

DASHBOARDS = TOOLKIT / "dashboards"

CONSULTA_CONTRATOS = """
EVALUATE
SELECTCOLUMNS('Cttes',
  "c", 'Cttes'[Numero Contrato],
  "de", 'Cttes'[Doc entry actual],
  "s", 'Cttes'[Sucursal],
  "e", 'Cttes'[Estado del Contrato],
  "pr", 'Cttes'[Proteccion],
  "pl", 'Cttes'[Nombre Plan],
  "v", 'Cttes'[Valor Mensual])
"""

CONSULTA_MASCOTAS = """
EVALUATE
SELECTCOLUMNS('Beneficiarios',
  "de", 'Beneficiarios'[DocEntry],
  "t", 'Beneficiarios'[Tipo de Beneficiario],
  "s", 'Beneficiarios'[Sucursal],
  "pr", 'Beneficiarios'[Proteccion])
"""

CONSULTA_ESTADOS = """
EVALUATE
SELECTCOLUMNS('Estados',
  "e", 'Estados'[Estado del Contrato],
  "n", 'Estados'[Nombre])
"""


def consultar(dax: str) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, str(TOOLKIT / "query.py"), "query", "--stdin"],
        input=dax,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(TOOLKIT),
    )
    if proc.returncode != 0:
        raise SystemExit("La consulta DAX falló:\n" + proc.stderr[:900])
    datos = json.loads(proc.stdout)
    if isinstance(datos, dict) and datos.get("ok") is False:
        raise SystemExit("Error del motor: " + json.dumps(datos, ensure_ascii=False)[:700])
    cols = [str(c).strip("[]") for c in datos.get("columns", [])]
    return [dict(zip(cols, fila)) for fila in datos.get("rows", [])]


def familia(proteccion) -> str:
    return "Petamigo" if str(proteccion or "").startswith("Petamigo") else "Petfiel"


def cargar_datos() -> tuple[list[dict], list[dict], list[str]]:
    brutos = consultar(CONSULTA_CONTRATOS)
    mascotas_brutas = consultar(CONSULTA_MASCOTAS)
    estados = {r["e"]: r["n"] for r in consultar(CONSULTA_ESTADOS)}

    contratos = []
    por_de: dict[str, dict] = {}
    for r in brutos:
        c = {
            "c": r["c"],
            "de": str(r["de"]),
            "s": r["s"],
            "e": r["e"],
            "enomb": estados.get(r["e"], r["e"]),
            "fam": familia(r["pr"]),
            "pl": r["pl"],
            "v": float(r["v"] or 0),
            "tipos": [],
        }
        contratos.append(c)
        por_de[c["de"]] = c

    mascotas = []
    for r in mascotas_brutas:
        contrato = por_de.get(str(r["de"]))
        m = {
            "de": str(r["de"]),
            "t": r["t"],
            "s": contrato["s"] if contrato else r["s"],
            "fam": contrato["fam"] if contrato else familia(r["pr"]),
            "c": contrato["c"] if contrato else None,
        }
        mascotas.append(m)

    for m in mascotas:
        if m["c"] is None:
            continue
        for c in contratos:
            if c["c"] == m["c"]:
                c["tipos"].append(m["t"])
                break
    for c in contratos:
        c["tipos"] = sorted(set(c["tipos"]))

    sucursales = sorted({c["s"] for c in contratos})
    return contratos, mascotas, sucursales


COLORES = {
    "Activo": "#2563eb",
    "Cancelado": "#f59e0b",
    "Suspendido": "#10b981",
    "Petamigo": "#2563eb",
    "Petfiel": "#f59e0b",
}


def spec_kpis_sucursal(contratos, mascotas, sucursales) -> dict:
    return {
        "titulo": "KPIs de ventas por región — Portafolio de Mascotas",
        "subtitulo": "Prima mensual, contratos y mascotas aseguradas por sucursal",
        "meta": "Filtros interactivos: sucursal y tipo de mascota · Datos: modelo del .pbix (Cttes / Beneficiarios / Estados)",
        "colores": COLORES,
        "filtros": [
            {"id": "sucursal", "etiqueta": "Sucursal", "valores": sucursales, "todos": "Todas"},
            {
                "id": "tipo",
                "etiqueta": "Tipo de mascota",
                "valores": ["PERRO", "GATO"],
                "etiquetas": {"PERRO": "Perro", "GATO": "Gato"},
                "todos": "Todos",
            },
        ],
        "kpis": [
            {"etiqueta": "Contratos totales", "base": "contratos", "agg": "count", "formato": "int"},
            {"etiqueta": "Contratos activos", "base": "contratos", "agg": "count",
             "filtro": {"e": ["ACT"]}, "formato": "int", "pista": "auto:pctActivos"},
            {"etiqueta": "Prima mensual activa", "base": "contratos", "agg": "sum", "medida": "v",
             "filtro": {"e": ["ACT"]}, "formato": "money0"},
            {"etiqueta": "Prima promedio activa", "base": "contratos", "agg": "avg", "medida": "v",
             "filtro": {"e": ["ACT"]}, "formato": "money"},
            {"etiqueta": "Mascotas aseguradas", "base": "mascotas", "agg": "count",
             "formato": "int", "pista": "auto:perrosGatos"},
        ],
        "graficos": [
            {"tipo": "barras-h", "titulo": "Prima mensual activa por sucursal", "dim": "s",
             "series": [{"nombre": "Prima activa", "base": "contratos", "agg": "sum", "medida": "v",
                         "filtro": {"e": ["ACT"]}, "formato": "money0"}]},
            {"tipo": "barras-apiladas", "titulo": "Contratos por sucursal (activos vs resto)",
             "dim": "s", "rotar": 18,
             "series": [
                 {"nombre": "Activos", "base": "contratos", "agg": "count",
                  "filtro": {"e": ["ACT"]}, "formato": "int"},
                 {"nombre": "No activos", "base": "contratos", "agg": "count",
                  "filtro": {"e": ["!ACT"]}, "formato": "int"},
             ]},
            {"tipo": "dona", "titulo": "Contratos por estado", "dim": "enomb",
             "series": [{"nombre": "Contratos", "base": "contratos", "agg": "count", "formato": "int"}]},
            {"tipo": "barras-h", "titulo": "Mascotas aseguradas por sucursal", "dim": "s",
             "series": [{"nombre": "Mascotas", "base": "mascotas", "agg": "count", "formato": "int"}]},
            {"tipo": "tabla", "titulo": "Detalle por sucursal", "dim": "s",
             "columnas": [
                 {"titulo": "Sucursal", "campo": "dim"},
                 {"titulo": "Contratos", "base": "contratos", "agg": "count", "formato": "int", "id": "total"},
                 {"titulo": "Activos", "base": "contratos", "agg": "count",
                  "filtro": {"e": ["ACT"]}, "formato": "int", "id": "activos"},
                 {"titulo": "% Activos", "calculo": "pctActivos", "formato": "pct"},
                 {"titulo": "Prima mensual activa", "base": "contratos", "agg": "sum", "medida": "v",
                  "filtro": {"e": ["ACT"]}, "formato": "money0"},
                 {"titulo": "Mascotas", "base": "mascotas", "agg": "count", "formato": "int"},
             ]},
        ],
        "datos": {"contratos": contratos, "mascotas": mascotas},
    }


def spec_planes(contratos, mascotas, sucursales) -> dict:
    return {
        "titulo": "Distribución de planes — Petamigo vs Petfiel",
        "subtitulo": "Contratos, mascotas y prima por familia de plan",
        "meta": "Filtros interactivos: familia, sucursal y tipo de mascota · Datos: modelo del .pbix (Cttes / Beneficiarios)",
        "colores": COLORES,
        "filtros": [
            {"id": "familia", "etiqueta": "Familia de plan",
             "valores": ["Petamigo", "Petfiel"], "todos": "Todas"},
            {"id": "sucursal", "etiqueta": "Sucursal", "valores": sucursales, "todos": "Todas"},
            {
                "id": "tipo",
                "etiqueta": "Tipo de mascota",
                "valores": ["PERRO", "GATO"],
                "etiquetas": {"PERRO": "Perro", "GATO": "Gato"},
                "todos": "Todos",
            },
        ],
        "kpis": [
            {"etiqueta": "Contratos Petamigo", "base": "contratos", "agg": "count",
             "filtro": {"fam": ["Petamigo"]}, "formato": "int", "pista": "auto:activos"},
            {"etiqueta": "Contratos Petfiel", "base": "contratos", "agg": "count",
             "filtro": {"fam": ["Petfiel"]}, "formato": "int", "pista": "auto:activos"},
            {"etiqueta": "Mascotas Petamigo", "base": "mascotas", "agg": "count",
             "filtro": {"fam": ["Petamigo"]}, "formato": "int"},
            {"etiqueta": "Mascotas Petfiel", "base": "mascotas", "agg": "count",
             "filtro": {"fam": ["Petfiel"]}, "formato": "int"},
            {"etiqueta": "Prima activa Petamigo", "base": "contratos", "agg": "sum", "medida": "v",
             "filtro": {"fam": ["Petamigo"], "e": ["ACT"]}, "formato": "money0"},
            {"etiqueta": "Prima activa Petfiel", "base": "contratos", "agg": "sum", "medida": "v",
             "filtro": {"fam": ["Petfiel"], "e": ["ACT"]}, "formato": "money0"},
        ],
        "graficos": [
            {"tipo": "dona", "titulo": "Contratos por familia de plan", "dim": "fam",
             "series": [{"nombre": "Contratos", "base": "contratos", "agg": "count", "formato": "int"}]},
            {"tipo": "dona", "titulo": "Mascotas aseguradas por familia", "dim": "fam",
             "series": [{"nombre": "Mascotas", "base": "mascotas", "agg": "count", "formato": "int"}]},
            {"tipo": "barras-h", "titulo": "Contratos por plan (top 10)", "dim": "pl", "limite": 10,
             "series": [{"nombre": "Contratos", "base": "contratos", "agg": "count", "formato": "int"}]},
            {"tipo": "barras-h", "titulo": "Prima mensual activa por plan (top 10)", "dim": "pl",
             "limite": 10,
             "series": [{"nombre": "Prima activa", "base": "contratos", "agg": "sum", "medida": "v",
                         "filtro": {"e": ["ACT"]}, "formato": "money0"}]},
            {"tipo": "tabla", "titulo": "Detalle por plan", "dim": "fam", "dim2": "pl",
             "columnas": [
                 {"titulo": "Familia", "campo": "dim"},
                 {"titulo": "Plan", "campo": "dim2"},
                 {"titulo": "Contratos", "base": "contratos", "agg": "count", "formato": "int", "id": "total"},
                 {"titulo": "Activos", "base": "contratos", "agg": "count",
                  "filtro": {"e": ["ACT"]}, "formato": "int", "id": "activos"},
                 {"titulo": "Prima mensual activa", "base": "contratos", "agg": "sum", "medida": "v",
                  "filtro": {"e": ["ACT"]}, "formato": "money0"},
             ]},
        ],
        "datos": {"contratos": contratos, "mascotas": mascotas},
    }


def main() -> None:
    contratos, mascotas, sucursales = cargar_datos()
    print(f"Datos: {len(contratos)} contratos · {len(mascotas)} mascotas · {len(sucursales)} sucursales")

    especificaciones = [
        (spec_kpis_sucursal(contratos, mascotas, sucursales),
         "spec_kpis_sucursal_v2.json", "tablero_kpis_sucursal.html"),
        (spec_planes(contratos, mascotas, sucursales),
         "spec_planes_v2.json", "tablero_planes_petamigo_petfiel.html"),
    ]
    for spec, ruta_spec, ruta_html in especificaciones:
        destino_spec = DASHBOARDS / ruta_spec
        destino_spec.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        destino_html = renderizar(spec, DASHBOARDS / ruta_html)
        peso = destino_html.stat().st_size / 1024
        print(f"OK  {destino_html.name}  ({peso:,.0f} KB)  spec: {destino_spec.name}")


if __name__ == "__main__":
    main()
