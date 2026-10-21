@echo off
:: ==========================================================================
::  Construye InventarioPOS.exe (archivo unico) a partir del proyecto
::  Ejecutar desde la raiz del proyecto:  scripts\build_exe.bat
:: ==========================================================================
setlocal
cd /d "%~dp0.."

echo ==========================================
echo   CONSTRUYENDO InventarioPOS.exe
echo ==========================================
echo.

:: 1) Verificar Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado. Instalalo desde https://nodejs.org
    pause
    exit /b 1
)

:: 2) Compilar el frontend
echo [1/4] Compilando el frontend React...
pushd frontend
call npm run build
if errorlevel 1 (
    echo [ERROR] Fallo la compilacion del frontend
    popd
    pause
    exit /b 1
)
popd
if not exist "frontend\build\index.html" (
    echo [ERROR] No se genero frontend\build\index.html
    pause
    exit /b 1
)
echo       Frontend compilado OK
echo.

:: 3) Preparar el entorno virtual del backend
echo [2/4] Preparando entorno virtual del backend...
if not exist "backend\venv\Scripts\python.exe" (
    echo       Creando venv...
    python -m venv backend\venv
)
call backend\venv\Scripts\activate
python -m pip install --upgrade pip >nul
echo       Instalando dependencias...
pip install -r backend\requirements.txt
pip install pyinstaller
echo       Dependencias OK
echo.

:: 4) Compilar el ejecutable
echo [3/4] Generando el ejecutable (PyInstaller onefile)...
pyinstaller build_exe.spec --noconfirm --clean
if errorlevel 1 (
    echo [ERROR] PyInstaller fallo
    pause
    exit /b 1
)
echo       Ejecutable generado
echo.

:: 5) Resultado
echo [4/4] Finalizando...
if exist "dist\InventarioPOS.exe" (
    echo.
    echo ==========================================
    echo   LISTO: dist\InventarioPOS.exe
    echo ==========================================
    for %%f in ("dist\InventarioPOS.exe") do echo   Tamano: %%~zf bytes
    echo.
    echo   Copia el .exe a la carpeta donde lo quieras usar.
    echo   Para crear el acceso directo: scripts\crear_acceso_directo.bat
    echo.
) else (
    echo [ERROR] No se encontro dist\InventarioPOS.exe
)

pause
endlocal
