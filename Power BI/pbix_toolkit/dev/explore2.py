"""Exploración #2: IDs, tipos de dato, relaciones resueltas y datos de muestra."""
import sys

sys.path.insert(0, r"C:\Users\XR-18\Desktop\Python\Power BI\pbix_toolkit")
sys.stdout.reconfigure(encoding="utf-8")

import adomd  # noqa: E402
import engine  # noqa: E402

estado = engine.cargar_estado()
conn = engine._conectar_estado(estado)


def dmv(tabla):
    res = adomd.query(conn, f"SELECT * FROM $SYSTEM.{tabla}", max_rows=None)
    return [dict(zip(res["columns"], fila)) for fila in res["rows"]]


tablas = dmv("TMSCHEMA_TABLES")
cols = dmv("TMSCHEMA_COLUMNS")
rels = dmv("TMSCHEMA_RELATIONSHIPS")

tname = {t["ID"]: t["Name"] for t in tablas}
colname = {}
for c in cols:
    colname[(c["TableID"], c["ID"])] = c.get("ExplicitName") or c.get("InferredName")

print("### ID -> TABLA ###")
for t in tablas:
    print(f"  {t['ID']} -> {t['Name']}")
print()

print("### TIPOS DE DATO (columnas clave) ###")
clave = {"Valor Mensual", "Fecha creacion SAP", "Estado del Contrato", "Edad", "DocEntry", "Date", "Año", "Proteccion", "Nombre Plan", "Sucursal"}
vistos = set()
for c in cols:
    nm = c.get("ExplicitName") or c.get("InferredName")
    tabla = tname.get(c["TableID"])
    if nm in clave and (tabla, nm) not in vistos:
        vistos.add((tabla, nm))
        print(f"  {tabla} :: {nm}")
        print(f"      ExplicitDataType={c.get('ExplicitDataType')} InferredDataType={c.get('InferredDataType')} Type={c.get('Type')}")
        print(f"      SourceProviderType={c.get('SourceProviderType')} SummarizeBy={c.get('SummarizeBy')} FormatString={c.get('FormatString')}")
print()

print("### RELACIONES RESUELTAS ###")
for r in rels:
    ft, tt = r.get("FromTableID"), r.get("ToTableID")
    fc, tc = r.get("FromColumnID"), r.get("ToColumnID")
    print(f"- {tname.get(ft)}[{colname.get((ft, fc), fc)}] -> {tname.get(tt)}[{colname.get((tt, tc), tc)}]")
    print(f"    Type={r.get('Type')} FromCard={r.get('FromCardinality')} ToCard={r.get('ToCardinality')} "
          f"Filtro={r.get('CrossFilteringBehavior')} Activa={r.get('IsActive')} Security={r.get('SecurityFilteringBehavior')}")
print()

print("### CONTEO DE FILAS ###")
for t in ("Cttes", "Beneficiarios", "Estados"):
    res = adomd.query(conn, f"EVALUATE ROW(\"n\", COUNTROWS('{t}'))")
    print(f"  {t}: {res['rows'][0][0]} filas")
print()

for t in ("Cttes", "Beneficiarios", "Estados"):
    res = adomd.query(conn, f"EVALUATE TOPN(3, '{t}')")
    visibles = [c for c in res["columns"] if not c.startswith("RowNumber")]
    idx = [i for i, c in enumerate(res["columns"]) if not c.startswith("RowNumber")]
    print(f"### MUESTRA {t} ###")
    print("  cols:", ", ".join(visibles))
    for fila in res["rows"]:
        print("  ", [fila[i] for i in idx])
    print()

conn.Close()
print("OK")
