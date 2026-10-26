"""Exploración de las DMV del modelo conectado (herramienta de desarrollo)."""
import sys

sys.path.insert(0, r"C:\Users\XR-18\Desktop\Python\Power BI\pbix_toolkit")
sys.stdout.reconfigure(encoding="utf-8")

import adomd  # noqa: E402
import engine  # noqa: E402

estado = engine.cargar_estado()
conn = engine._conectar_estado(estado)

DMVS = [
    "DBSCHEMA_CATALOGS",
    "TMSCHEMA_TABLES",
    "TMSCHEMA_COLUMNS",
    "TMSCHEMA_MEASURES",
    "TMSCHEMA_RELATIONSHIPS",
]

resultados = {}
for dmv in DMVS:
    try:
        res = adomd.query(conn, f"SELECT * FROM $SYSTEM.{dmv}", max_rows=None)
        resultados[dmv] = res
        print(f"== {dmv}: {res['rowCount']} filas | columnas:")
        print("   " + " | ".join(res["columns"]))
        print()
    except Exception as exc:
        print(f"== {dmv}: ERROR {exc}")
        print()

if "TMSCHEMA_TABLES" in resultados:
    r = resultados["TMSCHEMA_TABLES"]
    print("### TABLAS ###")
    for fila in r["rows"]:
        d = dict(zip(r["columns"], fila))
        print(f"- {d.get('Name')}  (hidden={d.get('IsHidden')})")
    print()

if "TMSCHEMA_COLUMNS" in resultados:
    r = resultados["TMSCHEMA_COLUMNS"]
    t = resultados["TMSCHEMA_TABLES"]
    nombre_tabla = {d.get("ID"): d.get("Name") for d in (dict(zip(t["columns"], f)) for f in t["rows"])}
    print("### COLUMNAS ###")
    actual = None
    for fila in r["rows"]:
        d = dict(zip(r["columns"], fila))
        tabla = nombre_tabla.get(d.get("TableID"))
        if tabla != actual:
            actual = tabla
            print(f"-- {tabla}:")
        nombre = d.get("ExplicitName") or d.get("Name") or d.get("InferredName")
        print(f"   {nombre}  [{d.get('DataType')}]  hidden={d.get('IsHidden')}")
    print()

if "TMSCHEMA_MEASURES" in resultados:
    r = resultados["TMSCHEMA_MEASURES"]
    t = resultados["TMSCHEMA_TABLES"]
    nombre_tabla = {d.get("ID"): d.get("Name") for d in (dict(zip(t["columns"], f)) for f in t["rows"])}
    print("### MEDIDAS ###")
    for fila in r["rows"]:
        d = dict(zip(r["columns"], fila))
        expr = (d.get("Expression") or "").replace("\n", " ")[:110]
        print(f"- {nombre_tabla.get(d.get('TableID'))} :: {d.get('Name')}  =  {expr}")
    print()

if "TMSCHEMA_RELATIONSHIPS" in resultados:
    r = resultados["TMSCHEMA_RELATIONSHIPS"]
    print(f"### RELACIONES ({r['rowCount']}) ###")
    for fila in r["rows"]:
        d = dict(zip(r["columns"], fila))
        print(f"- T{d.get('FromTableID')}[{d.get('FromColumnID')}] -> T{d.get('ToTableID')}[{d.get('ToColumnID')}] "
              f"card={d.get('Cardinality')} filtro={d.get('CrossFilteringBehavior')} activa={d.get('IsActive')}")
    print()

conn.Close()
print("OK")
