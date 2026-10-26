#!/usr/bin/env python3
"""Demo de la tubería prompt -> consulta DAX -> dashboard HTML.

Genera dos tableros con datos reales del modelo abierto:
  1. "KPIs de ventas por región" (prima/contratos por sucursal)
  2. "Distribución de planes Petamigo vs Petfiel"

Ejecutar con el python3 de WSL (o cualquier Python local):
    python3 demos/generar_dashboards.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLKIT))

from dashboard import renderizar  # noqa: E402

DASHBOARDS = TOOLKIT / "dashboards"
QUERY_PY = TOOLKIT / "query.py"


def q(dax: str) -> list[dict]:
    """Ejecuta DAX contra el modelo y devuelve filas como lista de dicts."""
    proc = subprocess.run(
        [sys.executable, str(QUERY_PY), "query", "--stdin"],
        input=dax,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"Error ejecutando DAX:\n{proc.stderr}\n{proc.stdout}")
    res = json.loads(proc.stdout)

    def norm(nombre: str) -> str:
        """[Mascotas] -> Mascotas ; Cttes[Sucursal] -> Cttes[Sucursal]"""
        return nombre[1:-1] if nombre.startswith("[") and nombre.endswith("]") else nombre

    columnas = [norm(c) for c in res["columns"]]
    return [dict(zip(columnas, fila)) for fila in res["rows"]]


def familia(proteccion: str | None) -> str:
    texto = (proteccion or "").strip()
    if texto.lower().startswith("petamigo"):
        return "Petamigo"
    if texto.lower().startswith("petfiel") or texto.lower().startswith("petplan"):
        return "Petfiel"
    return "Otras"


# --------------------------------------------------------------------------- #
# Consultas (una sola pasada por el motor)
# --------------------------------------------------------------------------- #
Q_GLOBAL = """
EVALUATE ROW(
    "Contratos", COUNTROWS('Cttes'),
    "Activos", COALESCE(CALCULATE(COUNTROWS('Cttes'), 'Cttes'[Estado del Contrato] = "ACT"), 0),
    "PrimaActiva", COALESCE(CALCULATE(SUM('Cttes'[Valor Mensual]), 'Cttes'[Estado del Contrato] = "ACT"), 0),
    "PrimaPromedioActiva", COALESCE(DIVIDE(
        CALCULATE(SUM('Cttes'[Valor Mensual]), 'Cttes'[Estado del Contrato] = "ACT"),
        CALCULATE(COUNTROWS('Cttes'), 'Cttes'[Estado del Contrato] = "ACT")
    ), 0),
    "Mascotas", COUNTROWS('Beneficiarios'),
    "Perros", COALESCE(CALCULATE(COUNTROWS('Beneficiarios'), 'Beneficiarios'[Tipo de Beneficiario] = "PERRO"), 0),
    "Gatos", COALESCE(CALCULATE(COUNTROWS('Beneficiarios'), 'Beneficiarios'[Tipo de Beneficiario] = "GATO"), 0)
)
"""

Q_SUCURSAL = """
EVALUATE
SUMMARIZECOLUMNS(
    'Cttes'[Sucursal],
    "Contratos", COUNTROWS('Cttes'),
    "Activos", COALESCE(CALCULATE(COUNTROWS('Cttes'), 'Cttes'[Estado del Contrato] = "ACT"), 0),
    "PrimaActiva", COALESCE(CALCULATE(SUM('Cttes'[Valor Mensual]), 'Cttes'[Estado del Contrato] = "ACT"), 0)
)
ORDER BY [PrimaActiva] DESC
"""

Q_ESTADO = """
EVALUATE
SUMMARIZECOLUMNS(
    'Estados'[Nombre],
    "Contratos", COUNTROWS('Cttes')
)
ORDER BY [Contratos] DESC
"""

Q_MASCOTAS_SUC = """
EVALUATE
SUMMARIZECOLUMNS('Beneficiarios'[Sucursal], "Mascotas", COUNTROWS('Beneficiarios'))
ORDER BY [Mascotas] DESC
"""

Q_PROT = """
EVALUATE
SUMMARIZECOLUMNS(
    'Cttes'[Proteccion],
    "Contratos", COUNTROWS('Cttes'),
    "Activos", COALESCE(CALCULATE(COUNTROWS('Cttes'), 'Cttes'[Estado del Contrato] = "ACT"), 0),
    "PrimaActiva", COALESCE(CALCULATE(SUM('Cttes'[Valor Mensual]), 'Cttes'[Estado del Contrato] = "ACT"), 0)
)
ORDER BY [Contratos] DESC
"""

Q_PROT_MASC = """
EVALUATE
SUMMARIZECOLUMNS('Beneficiarios'[Proteccion], "Mascotas", COUNTROWS('Beneficiarios'))
ORDER BY [Mascotas] DESC
"""

Q_PLAN = """
EVALUATE
SUMMARIZECOLUMNS(
    'Cttes'[Proteccion],
    'Cttes'[Nombre Plan],
    "Contratos", COUNTROWS('Cttes'),
    "Activos", COALESCE(CALCULATE(COUNTROWS('Cttes'), 'Cttes'[Estado del Contrato] = "ACT"), 0),
    "PrimaActiva", COALESCE(CALCULATE(SUM('Cttes'[Valor Mensual]), 'Cttes'[Estado del Contrato] = "ACT"), 0)
)
ORDER BY [Contratos] DESC
"""


def tablero_kpis_sucursal() -> Path:
    print("· Consultando KPIs globales, sucursal, estados y mascotas...")
    glob = q(Q_GLOBAL)[0]
    suc = q(Q_SUCURSAL)
    estados = q(Q_ESTADO)
    mascotas_suc = q(Q_MASCOTAS_SUC)

    masc_por_suc = {r["Beneficiarios[Sucursal]"]: r["Mascotas"] for r in mascotas_suc}
    sucursales = [r["Cttes[Sucursal]"] for r in suc]

    total = glob["Contratos"]
    pct_activos = round(100 * glob["Activos"] / total) if total else 0

    filas_tabla = []
    for r in suc:
        nombre = r["Cttes[Sucursal]"]
        filas_tabla.append(
            [
                nombre,
                r["Contratos"],
                r["Activos"],
                round(100 * r["Activos"] / r["Contratos"]) if r["Contratos"] else 0,
                r["PrimaActiva"],
                masc_por_suc.get(nombre),
            ]
        )

    spec = {
        "title": "KPIs de ventas por región — Portafolio de Mascotas",
        "subtitle": "Prima mensual, contratos y mascotas aseguradas por sucursal",
        "meta": "Prompt: «Genera un tablero de KPIs de ventas por región» · Datos: Cttes / Beneficiarios / Estados",
        "kpis": [
            {"label": "Contratos totales", "value": total, "format": "int"},
            {"label": "Contratos activos", "value": glob["Activos"], "format": "int",
             "hint": f"{pct_activos}% del portafolio"},
            {"label": "Prima mensual activa", "value": glob["PrimaActiva"], "format": "money",
             "hint": "contratos en estado Activo"},
            {"label": "Prima promedio / contrato", "value": glob["PrimaPromedioActiva"], "format": "money"},
            {"label": "Mascotas aseguradas", "value": glob["Mascotas"], "format": "int",
             "hint": f"{glob['Perros']} perros · {glob['Gatos']} gatos"},
        ],
        "charts": [
            {
                "type": "bar", "horizontal": True, "format": "money",
                "title": "Prima mensual activa por sucursal",
                "categories": sucursales,
                "series": [{"name": "Prima activa", "data": [r["PrimaActiva"] for r in suc]}],
            },
            {
                "type": "bar", "format": "int",
                "title": "Contratos por sucursal (activos vs resto)",
                "categories": sucursales,
                "series": [
                    {"name": "Activos", "data": [r["Activos"] for r in suc], "stack": True},
                    {"name": "No activos", "data": [r["Contratos"] - r["Activos"] for r in suc], "stack": True},
                ],
            },
            {
                "type": "pie", "donut": True, "format": "int",
                "title": "Contratos por estado",
                "data": [{"name": r["Estados[Nombre]"], "value": r["Contratos"]} for r in estados],
            },
            {
                "type": "bar", "horizontal": True, "format": "int",
                "title": "Mascotas aseguradas por sucursal",
                "categories": [r["Beneficiarios[Sucursal]"] for r in mascotas_suc],
                "series": [{"name": "Mascotas", "data": [r["Mascotas"] for r in mascotas_suc]}],
            },
            {
                "type": "table",
                "title": "Detalle por sucursal",
                "columns": ["Sucursal", "Contratos", "Activos", "% Activos", "Prima mensual activa", "Mascotas"],
                "formats": [None, "int", "int", "int", "money", "int"],
                "rows": filas_tabla,
            },
        ],
    }

    spec_path = DASHBOARDS / "spec_kpis_sucursal.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return renderizar(spec, DASHBOARDS / "tablero_kpis_sucursal.html")


def tablero_planes() -> Path:
    print("· Consultando contratos y mascotas por plan / protección...")
    prot = q(Q_PROT)
    prot_masc = q(Q_PROT_MASC)
    planes = q(Q_PLAN)

    def agregar(filas, llave, columna) -> dict[str, float]:
        acc: dict[str, float] = {}
        for r in filas:
            f = familia(r[llave])
            acc[f] = acc.get(f, 0) + (r[columna] or 0)
        return acc

    c_fam = agregar(prot, "Cttes[Proteccion]", "Contratos")
    c_act = agregar(prot, "Cttes[Proteccion]", "Activos")
    p_fam = agregar(prot, "Cttes[Proteccion]", "PrimaActiva")
    m_fam = agregar(prot_masc, "Beneficiarios[Proteccion]", "Mascotas")

    planes_orden = sorted(planes, key=lambda r: r["Contratos"] or 0, reverse=True)
    top_planes = planes_orden[:10]

    filas_tabla = [
        [
            familia(r["Cttes[Proteccion]"]),
            r["Cttes[Nombre Plan]"],
            r["Contratos"],
            r["Activos"],
            r["PrimaActiva"],
        ]
        for r in planes_orden
    ]

    spec = {
        "title": "Distribución de planes — Petamigo vs Petfiel",
        "subtitle": "Contratos, mascotas y prima por familia de plan",
        "meta": "Prompt: «Muestra la distribución de planes Petamigo vs Petfiel» · Datos: Cttes / Beneficiarios",
        "kpis": [
            {"label": "Contratos Petamigo", "value": c_fam.get("Petamigo", 0), "format": "int"},
            {"label": "Contratos Petfiel", "value": c_fam.get("Petfiel", 0), "format": "int"},
            {"label": "Mascotas Petamigo", "value": m_fam.get("Petamigo", 0), "format": "int"},
            {"label": "Mascotas Petfiel", "value": m_fam.get("Petfiel", 0), "format": "int"},
            {"label": "Prima activa Petamigo", "value": p_fam.get("Petamigo", 0), "format": "money",
             "hint": f"{c_act.get('Petamigo', 0)} contratos activos"},
            {"label": "Prima activa Petfiel", "value": p_fam.get("Petfiel", 0), "format": "money",
             "hint": f"{c_act.get('Petfiel', 0)} contratos activos"},
        ],
        "charts": [
            {
                "type": "pie", "donut": True, "format": "int",
                "title": "Contratos por familia de plan",
                "data": [{"name": k, "value": v} for k, v in sorted(c_fam.items(), key=lambda kv: -kv[1])],
            },
            {
                "type": "pie", "donut": True, "format": "int",
                "title": "Mascotas aseguradas por familia",
                "data": [{"name": k, "value": v} for k, v in sorted(m_fam.items(), key=lambda kv: -kv[1])],
            },
            {
                "type": "bar", "horizontal": True, "format": "int",
                "title": "Contratos por plan (top 10)",
                "categories": [r["Cttes[Nombre Plan]"] for r in top_planes],
                "series": [{"name": "Contratos", "data": [r["Contratos"] for r in top_planes]}],
            },
            {
                "type": "bar", "horizontal": True, "format": "money",
                "title": "Prima mensual activa por plan (top 10)",
                "categories": [r["Cttes[Nombre Plan]"] for r in top_planes],
                "series": [{"name": "Prima activa", "data": [r["PrimaActiva"] for r in top_planes]}],
            },
            {
                "type": "table",
                "title": "Detalle por plan",
                "columns": ["Familia", "Plan", "Contratos", "Activos", "Prima mensual activa"],
                "formats": [None, None, "int", "int", "money"],
                "rows": filas_tabla,
            },
        ],
    }

    spec_path = DASHBOARDS / "spec_planes.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return renderizar(spec, DASHBOARDS / "tablero_planes_petamigo_petfiel.html")


def main() -> None:
    hechos = [tablero_kpis_sucursal(), tablero_planes()]
    print()
    for h in hechos:
        print(f"✓ Dashboard generado: {h}")


if __name__ == "__main__":
    main()
