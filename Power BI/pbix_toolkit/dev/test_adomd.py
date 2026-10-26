"""Prueba de carga de la DLL ADOMD que viene con Power BI Desktop."""
import os
import sys
import traceback

BIN = r"C:\Program Files\Microsoft Power BI Desktop\bin"
sys.path.append(BIN)

import clr  # noqa: E402

DLL = os.path.join(BIN, "Microsoft.PowerBI.AdomdClient.dll")

# 1) Probar AddReference con ruta directa
loaded = None
try:
    ref = clr.AddReference(DLL)
    print("[OK] clr.AddReference(ruta) ->", ref)
    loaded = True
except Exception:
    print("[FAIL] clr.AddReference(ruta)")
    traceback.print_exc()

# 2) Fallback: AddReference por nombre de ensamblado
if not loaded:
    try:
        ref = clr.AddReference("Microsoft.PowerBI.AdomdClient")
        print("[OK] clr.AddReference(nombre) ->", ref)
        loaded = True
    except Exception:
        print("[FAIL] clr.AddReference(nombre)")
        traceback.print_exc()

# 3) Inspeccionar nombre completo del ensamblado y sus dependencias
try:
    import System  # noqa: E402

    asm = System.Reflection.Assembly.LoadFile(DLL)
    print("Assembly FullName:", asm.FullName)
    print("Dependencias:")
    for d in asm.GetReferencedAssemblies():
        print("   -", d.Name, d.Version)
except Exception:
    traceback.print_exc()

# 4) Probar import del namespace e instanciar conexión
try:
    from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
        AdomdCommand,
        AdomdConnection,
    )

    print("[OK] import namespace Microsoft.AnalysisServices.AdomdClient")
    conn = AdomdConnection()
    print("[OK] AdomdConnection instanciada:", conn)
    cmd_cls = AdomdCommand
    print("[OK] AdomdCommand disponible:", cmd_cls)
except Exception:
    print("[FAIL] import namespace / instanciación")
    traceback.print_exc()
