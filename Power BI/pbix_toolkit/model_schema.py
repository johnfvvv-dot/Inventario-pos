"""Construye un esquema legible del modelo tabular del .pbix.

Usa las DMV `$SYSTEM.TMSCHEMA_*` del motor local de Power BI Desktop
para extraer tablas, columnas, medidas y relaciones, manteniendo la
integridad referencial del modelo original.
"""

from __future__ import annotations

import adomd

# --------------------------------------------------------------------------- #
# Enumeraciones del motor tabular (TOM/TMSL) - valores observados en el motor
# --------------------------------------------------------------------------- #
TIPO_DATO = {
    1: "Automatic",
    2: "String",
    3: "Variant",       # poco frecuente
    6: "Int64",
    8: "Double",
    9: "DateTime",
    10: "Decimal",
    11: "Boolean",
    17: "Binary",
    19: "inferido",     # sin tipo explícito (lo infiere el motor)
}

CARDINALIDAD = {1: "One", 2: "Many"}

FILTRO = {0: "Automatic", 1: "OneDirection", 2: "BothDirections"}

AGREGACION = {
    1: "Default",
    2: "None",
    3: "Sum",
    4: "Min",
    5: "Max",
    6: "Count",
    7: "Average",
    8: "DistinctCount",
}

TIPO_RELACION = {1: "SingleColumn", 2: "MultipleColumns", 3: "ManyToMany"}


def _dmv(conn, tabla_dmv: str) -> list[dict]:
    """Consulta una DMV y la devuelve como lista de diccionarios."""
    res = adomd.query(conn, f"SELECT * FROM $SYSTEM.{tabla_dmv}", max_rows=None)
    cols = res["columns"]
    return [dict(zip(cols, fila)) for fila in res["rows"]]


def _nombre_columna(c: dict) -> str:
    return str(c.get("ExplicitName") or c.get("InferredName") or c.get("Name") or "")


def _mapa(valor, tabla: dict):
    return tabla.get(valor, valor)


def build(conn) -> dict:
    """Devuelve el esquema completo del modelo conectado."""
    catalogos = _dmv(conn, "DBSCHEMA_CATALOGS")
    catalogo = str(catalogos[0].get("CATALOG_NAME", "")) if catalogos else ""

    tablas = _dmv(conn, "TMSCHEMA_TABLES")
    columnas = _dmv(conn, "TMSCHEMA_COLUMNS")
    medidas = _dmv(conn, "TMSCHEMA_MEASURES")
    relaciones = _dmv(conn, "TMSCHEMA_RELATIONSHIPS")

    nombre_tabla = {t.get("ID"): str(t.get("Name", "")) for t in tablas}

    columnas_por_tabla: dict = {}
    col_index = {}
    for c in columnas:
        tid = c.get("TableID")
        nombre = _nombre_columna(c)
        col_index[(tid, c.get("ID"))] = nombre
        tipo = c.get("ExplicitDataType")
        if tipo in (None, 19):
            tipo = c.get("InferredDataType", tipo)
        columnas_por_tabla.setdefault(tid, []).append(
            {
                "name": nombre,
                "dataType": _mapa(tipo, TIPO_DATO),
                "isHidden": bool(c.get("IsHidden", False)),
                "formatString": c.get("FormatString"),
                "summarizeBy": _mapa(c.get("SummarizeBy"), AGREGACION),
                "displayFolder": c.get("DisplayFolder") or "",
                "description": c.get("Description") or "",
            }
        )

    medidas_por_tabla: dict = {}
    for m in medidas:
        tid = m.get("TableID")
        medidas_por_tabla.setdefault(tid, []).append(
            {
                "name": str(m.get("Name", "")),
                "expression": m.get("Expression") or "",
                "formatString": m.get("FormatString"),
                "dataType": _mapa(m.get("DataType"), TIPO_DATO),
                "description": m.get("Description") or "",
                "displayFolder": m.get("DisplayFolder") or "",
                "isHidden": bool(m.get("IsHidden", False)),
            }
        )

    esquema_tablas = []
    for t in tablas:
        tid = t.get("ID")
        filas = None
        if not t.get("IsHidden", False):
            try:
                res = adomd.query(conn, f"EVALUATE ROW(\"n\", COUNTROWS('{t.get('Name')}'))", max_rows=1)
                filas = res["rows"][0][0]
            except Exception:
                filas = None
        esquema_tablas.append(
            {
                "name": str(t.get("Name", "")),
                "isHidden": bool(t.get("IsHidden", False)),
                "description": t.get("Description") or "",
                "rowCount": filas,
                "columns": columnas_por_tabla.get(tid, []),
                "measures": medidas_por_tabla.get(tid, []),
            }
        )

    esquema_relaciones = []
    for r in relaciones:
        ft, tt = r.get("FromTableID"), r.get("ToTableID")
        fc, tc = r.get("FromColumnID"), r.get("ToColumnID")
        c_from = _mapa(r.get("FromCardinality"), CARDINALIDAD)
        c_to = _mapa(r.get("ToCardinality"), CARDINALIDAD)
        esquema_relaciones.append(
            {
                "name": r.get("Name") or "",
                "fromTable": nombre_tabla.get(ft, str(ft)),
                "fromColumn": col_index.get((ft, fc), str(fc)),
                "toTable": nombre_tabla.get(tt, str(tt)),
                "toColumn": col_index.get((tt, tc), str(tc)),
                "cardinality": f"{c_from}->{c_to}",
                "type": _mapa(r.get("Type"), TIPO_RELACION),
                "crossFilteringBehavior": _mapa(r.get("CrossFilteringBehavior"), FILTRO),
                "securityFilteringBehavior": _mapa(r.get("SecurityFilteringBehavior"), FILTRO),
                "isActive": bool(r.get("IsActive", True)),
            }
        )

    return {
        "catalog": catalogo,
        "tables": esquema_tablas,
        "relationships": esquema_relaciones,
    }


def resumen_texto(esquema: dict) -> str:
    """Resumen compacto del esquema (ideal para prompts/LLM)."""
    partes = [f"Catálogo: {esquema.get('catalog') or '(modelo local)'}", ""]

    partes.append("TABLAS:")
    for t in esquema["tables"]:
        if t["isHidden"]:
            continue
        filas = f" ({t['rowCount']} filas)" if t.get("rowCount") is not None else ""
        partes.append(f"- {t['name']}{filas}")
        cols = [c["name"] for c in t["columns"] if not c["isHidden"]]
        if cols:
            partes.append(f"    columnas: {', '.join(cols)}")
        meds = [m["name"] for m in t["measures"] if not m["isHidden"]]
        if meds:
            partes.append(f"    medidas: {', '.join(meds)}")
        else:
            partes.append("    medidas: (ninguna definida en el modelo)")

    partes.append("")
    partes.append("RELACIONES:")
    for r in esquema["relationships"]:
        activa = "" if r["isActive"] else " (INACTIVA)"
        partes.append(
            f"- {r['fromTable']}[{r['fromColumn']}] -> {r['toTable']}[{r['toColumn']}]"
            f" [{r['cardinality']}, {r['crossFilteringBehavior']}]{activa}"
        )

    return "\n".join(partes)
