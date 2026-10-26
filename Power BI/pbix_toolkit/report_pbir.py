#!/usr/bin/env python3
"""Inyecta páginas con visuales NATIVOS (formato PBIR) en una copia del .pbix.

- Lee el .pbix ORIGINAL (nunca lo modifica).
- Reemplaza `Report/Layout` por `Report/definition/...` (PBIR v2),
  el formato de reporte moderno que Power BI Desktop lee y edita.
- Conserva intacto el DataModel (datos, relaciones, medidas).

Uso:
    python3 report_pbir.py pbix_origen pbix_destino
"""

from __future__ import annotations

import json
import sys
import uuid
import zipfile
from pathlib import Path

# --------------------------------------------------------------------------- #
# Utilidades de serialización (expresiones de Power BI)
# --------------------------------------------------------------------------- #
_LIT = lambda v: {"expr": {"Literal": {"Value": v}}}          # noqa: E731
_LIT_TEXTO = lambda s: _LIT("'" + str(s).replace("'", "''") + "'")  # noqa: E731
_LIT_BOOL = lambda b: _LIT("true" if b else "false")          # noqa: E731

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
SCHEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/2.0.0/schema.json"
SCHEMA_VERSION = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"

FUNC = {"Sum": 0, "Avg": 1, "Count": 2, "Min": 3, "Max": 4}


def nombre_visual() -> str:
    return uuid.uuid4().hex[:20]


def posicion(x, y, w, h, z, tab):
    return {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": tab}


def columna(entidad: str, prop: str, activo: bool | None = None):
    d = {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": entidad}},
                "Property": prop,
            }
        },
        "queryRef": f"{entidad}.{prop}",
        "nativeQueryRef": prop,
    }
    if activo is not None:
        d["active"] = activo
    return d


def agregado(entidad: str, prop: str, funcion: str, etiqueta: str):
    return {
        "field": {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": entidad}},
                        "Property": prop,
                    }
                },
                "Function": FUNC[funcion],
            }
        },
        "queryRef": f"{funcion}({entidad}.{prop})",
        "nativeQueryRef": etiqueta,
    }


def filtro_in(entidad: str, prop: str, valores: list[str]) -> dict:
    return {
        "name": "Filter" + uuid.uuid4().hex[:20],
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": entidad}},
                "Property": prop,
            }
        },
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "f", "Entity": entidad, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": "f"}},
                                        "Property": prop,
                                    }
                                }
                            ],
                            "Values": [[{"Literal": {"Value": f"'{v}'"}}] for v in valores],
                        }
                    }
                }
            ],
        },
        "howCreated": "User",
    }


def titulo(texto: str) -> dict:
    return {
        "title": [
            {
                "properties": {
                    "show": _LIT_BOOL(True),
                    "text": _LIT_TEXTO(texto),
                }
            }
        ]
    }


def visual(visual_type: str, pos: dict, query_state: dict, *, filtros=None, tit=None) -> dict:
    v = {
        "$schema": SCHEMA_VISUAL,
        "name": None,  # se rellena al asignar carpeta
        "position": pos,
        "visual": {
            "visualType": visual_type,
            "query": {"queryState": query_state},
            "drillFilterOtherVisuals": True,
        },
    }
    if tit:
        v["visual"]["visualContainerObjects"] = titulo(tit)
    if filtros:
        v["filterConfig"] = {"filters": filtros}
    return v


# --------------------------------------------------------------------------- #
# Definición de las páginas y visuales
# --------------------------------------------------------------------------- #
def pagina_kpis_sucursal() -> tuple[str, str, list[dict]]:
    nombre = "PagKpisSucursal"
    display = "KPIs por Sucursal"
    z, tab = 1000, 0
    visuals = []

    def add(v):
        nonlocal z, tab
        v["name"] = nombre_visual()
        visuals.append(v)
        z += 100
        tab += 1

    # Fila 1: tarjetas KPI
    add(visual(
        "cardVisual", posicion(16, 16, 616, 130, z, tab),
        {"Data": {"projections": [
            agregado("Cttes", "Valor Mensual", "Sum", "Prima mensual total"),
            agregado("Cttes", "Numero Contrato", "Count", "Contratos"),
            agregado("Beneficiarios", "DocEntry", "Count", "Mascotas"),
        ]}},
    ))
    filtro_act = filtro_in("Cttes", "Estado del Contrato", ["ACT"])
    add(visual(
        "cardVisual", posicion(648, 16, 616, 130, z, tab),
        {"Data": {"projections": [
            agregado("Cttes", "Numero Contrato", "Count", "Contratos activos"),
            agregado("Cttes", "Valor Mensual", "Sum", "Prima mensual activa"),
            agregado("Cttes", "Valor Mensual", "Avg", "Prima promedio activa"),
        ]}},
        filtros=[filtro_act],
    ))

    # Fila 2: barras + dona
    add(visual(
        "clusteredBarChart", posicion(16, 156, 616, 250, z, tab),
        {"Category": {"projections": [columna("Cttes", "Sucursal", activo=True)]},
         "Y": {"projections": [agregado("Cttes", "Valor Mensual", "Sum", "Prima activa")]}},
        filtros=[filtro_act],
        tit="Prima mensual activa por sucursal",
    ))
    add(visual(
        "donutChart", posicion(648, 156, 616, 250, z, tab),
        {"Category": {"projections": [columna("Estados", "Nombre", activo=True)]},
         "Y": {"projections": [agregado("Cttes", "Numero Contrato", "Count", "Contratos")]}},
        tit="Contratos por estado",
    ))

    # Fila 3: columnas + tabla
    add(visual(
        "clusteredColumnChart", posicion(16, 416, 616, 288, z, tab),
        {"Category": {"projections": [columna("Cttes", "Sucursal", activo=True)]},
         "Y": {"projections": [agregado("Cttes", "Numero Contrato", "Count", "Contratos")]}},
        tit="Contratos por sucursal",
    ))
    add(visual(
        "pivotTable", posicion(648, 416, 616, 288, z, tab),
        {"Rows": {"projections": [columna("Cttes", "Sucursal", activo=True)]},
         "Values": {"projections": [
             agregado("Cttes", "Numero Contrato", "Count", "Contratos"),
             agregado("Cttes", "Valor Mensual", "Sum", "Prima mensual total"),
         ]}},
        tit="Detalle por sucursal",
    ))
    return nombre, display, visuals


def pagina_planes() -> tuple[str, str, list[dict]]:
    nombre = "PagPlanes"
    display = "Planes Petamigo vs Petfiel"
    z, tab = 1000, 0
    visuals = []

    def add(v):
        nonlocal z, tab
        v["name"] = nombre_visual()
        visuals.append(v)
        z += 100
        tab += 1

    filtro_petamigo = filtro_in("Cttes", "Proteccion", ["Petamigo", "Petamigo Tradicional"])
    filtro_petfiel = filtro_in("Cttes", "Proteccion", ["Petfiel", "Petfiel Superior", "Petfiel VIP"])

    # Tarjetas
    add(visual(
        "cardVisual", posicion(16, 16, 410, 130, z, tab),
        {"Data": {"projections": [
            agregado("Cttes", "Numero Contrato", "Count", "Contratos totales"),
            agregado("Beneficiarios", "DocEntry", "Count", "Mascotas totales"),
        ]}},
    ))
    add(visual(
        "cardVisual", posicion(435, 16, 410, 130, z, tab),
        {"Data": {"projections": [
            agregado("Cttes", "Numero Contrato", "Count", "Contratos Petamigo"),
            agregado("Beneficiarios", "DocEntry", "Count", "Mascotas Petamigo"),
        ]}},
        filtros=[filtro_petamigo],
    ))
    add(visual(
        "cardVisual", posicion(854, 16, 410, 130, z, tab),
        {"Data": {"projections": [
            agregado("Cttes", "Numero Contrato", "Count", "Contratos Petfiel"),
            agregado("Beneficiarios", "DocEntry", "Count", "Mascotas Petfiel"),
        ]}},
        filtros=[filtro_petfiel],
    ))

    # Dona + dona + barras
    add(visual(
        "donutChart", posicion(16, 156, 410, 250, z, tab),
        {"Category": {"projections": [columna("Cttes", "Proteccion", activo=True)]},
         "Y": {"projections": [agregado("Cttes", "Numero Contrato", "Count", "Contratos")]}},
        tit="Contratos por plan (protección)",
    ))
    add(visual(
        "donutChart", posicion(435, 156, 410, 250, z, tab),
        {"Category": {"projections": [columna("Beneficiarios", "Proteccion", activo=True)]},
         "Y": {"projections": [agregado("Beneficiarios", "DocEntry", "Count", "Mascotas")]}},
        tit="Mascotas por plan (protección)",
    ))
    add(visual(
        "clusteredBarChart", posicion(854, 156, 410, 250, z, tab),
        {"Category": {"projections": [columna("Cttes", "Nombre Plan", activo=True)]},
         "Y": {"projections": [agregado("Cttes", "Numero Contrato", "Count", "Contratos")]}},
        tit="Contratos por plan comercial",
    ))

    # Tabla
    add(visual(
        "pivotTable", posicion(16, 416, 1248, 288, z, tab),
        {"Rows": {"projections": [
            columna("Cttes", "Proteccion", activo=True),
            columna("Cttes", "Nombre Plan", activo=False),
        ]},
         "Values": {"projections": [
             agregado("Cttes", "Numero Contrato", "Count", "Contratos"),
             agregado("Cttes", "Valor Mensual", "Sum", "Prima mensual total"),
         ]}},
        tit="Detalle por plan",
    ))
    return nombre, display, visuals


def pagina_vacia() -> tuple[str, str, list[dict]]:
    return "PagOriginal", "Página 2", []


# --------------------------------------------------------------------------- #
# Ensamblado del paquete .pbix
# --------------------------------------------------------------------------- #
def construir(origen: Path, destino: Path) -> dict:
    paginas = [pagina_kpis_sucursal(), pagina_planes(), pagina_vacia()]

    version_json = {"$schema": SCHEMA_VERSION, "version": "2.0.0"}

    report_json = {
        "$schema": SCHEMA_REPORT,
        "themeCollection": {
            "baseTheme": {"name": "CY25SU11", "type": "SharedResources"}
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {"name": "CY25SU11", "path": "BaseThemes/CY25SU11.json", "type": "BaseTheme"}
                ],
            }
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultFilterActionIsDataFilter": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": False,
            "queryLimitOption": "None",
        },
    }

    nombres_pagina = [p[0] for p in paginas]
    pages_json = {
        "$schema": SCHEMA_PAGES,
        "pageOrder": nombres_pagina,
        "activePageName": nombres_pagina[0],
        "landingPageName": nombres_pagina[0],
    }

    nuevos: dict[str, str] = {}
    nuevos["Report/definition/version.json"] = json.dumps(version_json, ensure_ascii=False)
    nuevos["Report/definition/report.json"] = json.dumps(report_json, ensure_ascii=False)
    nuevos["Report/definition/pages/pages.json"] = json.dumps(pages_json, ensure_ascii=False)

    resumen = {"paginas": [], "visuales": 0}
    for nombre, display, visuals in paginas:
        page_json = {
            "$schema": SCHEMA_PAGE,
            "name": nombre,
            "displayName": display,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        }
        nuevos[f"Report/definition/pages/{nombre}/page.json"] = json.dumps(page_json, ensure_ascii=False)
        for v in visuals:
            v_con_nombre = {
                "$schema": SCHEMA_VISUAL,
                "name": v["name"],
                "position": v["position"],
                "visual": v["visual"],
            }
            if "filterConfig" in v:
                v_con_nombre["filterConfig"] = v["filterConfig"]
            nuevos[f"Report/definition/pages/{nombre}/visuals/{v['name']}/visual.json"] = json.dumps(
                v_con_nombre, ensure_ascii=False
            )
        resumen["paginas"].append({"nombre": nombre, "display": display, "visuales": len(visuals)})
        resumen["visuales"] += len(visuals)

    # Re-empaquetar el .pbix
    z_in = zipfile.ZipFile(origen)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            if item.filename == "Report/Layout":
                # el formato antiguo se sustituye por PBIR; se agregan los nuevos aquí
                for ruta, contenido in nuevos.items():
                    z_out.writestr(ruta, contenido.encode("utf-8"))
                continue
            datos = z_in.read(item.filename)
            if item.filename == "[Content_Types].xml":
                xml = datos.decode("utf-8-sig")
                xml = xml.replace('<Override PartName="/Report/Layout" ContentType="" />', "")
                datos = xml.encode("utf-8-sig")
            z_out.writestr(item, datos)

    resumen["origen"] = str(origen)
    resumen["destino"] = str(destino)
    return resumen


def validar(pbix: Path) -> None:
    """Relee el paquete generado y valida todos los JSON e integridad."""
    z = zipfile.ZipFile(pbix)
    malos = z.testzip()
    if malos:
        raise RuntimeError(f"ZIP corrupto en {malos}")
    assert "Report/Layout" not in z.namelist(), "Report/Layout no fue eliminado"
    assert "DataModel" in z.namelist(), "Falta el DataModel"
    definidos = [n for n in z.namelist() if n.startswith("Report/definition/")]
    assert definidos, "No se generaron archivos PBIR"
    for n in definidos:
        if n.endswith(".json"):
            json.loads(z.read(n).decode("utf-8"))
    print(f"Validación OK: {len(definidos)} archivos PBIR, DataModel intacto.")


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    origen, destino = Path(sys.argv[1]), Path(sys.argv[2])
    resumen = construir(origen, destino)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    validar(destino)


if __name__ == "__main__":
    main()
