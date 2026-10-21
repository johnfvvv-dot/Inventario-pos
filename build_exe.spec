# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para generar InventarioPOS.exe (un solo archivo).

Uso:  pyinstaller build_exe.spec --noconfirm
"""

import os
from pathlib import Path

ROOT = Path(os.path.abspath(SPECPATH))
BUILD_FRONTEND = ROOT / "frontend" / "build"

# --- Datos que se empaquetan dentro del ejecutable ---
datas = []
if (BUILD_FRONTEND / "index.html").exists():
    datas.append((str(BUILD_FRONTEND), "frontend/build"))
else:
    print("[AVISO] No existe frontend/build. Ejecuta 'npm run build' en frontend/")

# --- Módulos que PyInstaller no detecta solo ---
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "websockets",
    "wsproto",
    "sqlalchemy.dialects.sqlite",
    "pydantic",
    "email_validator",
    "anyio",
]

a = Analysis(
    [str(ROOT / "backend" / "run.py")],
    pathex=[str(ROOT / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "notebook",
        "IPython",
        "jupyter",
        "pytest",
        "PyQt5",
        "PySide2",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="InventarioPOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # False para ocultar la consola; True muestra el log de arranque
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icono.ico") if (ROOT / "assets" / "icono.ico").exists() else None,
)
