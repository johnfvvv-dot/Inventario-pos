@echo off
:: Script para iniciar Inventario POS en Windows
:: Levanta tanto el backend como el frontend

echo ==========================================
echo     SISTEMA INVENTARIO POS - INICIANDO
echo ==========================================
echo.

:: Verificar que el entorno virtual existe
if not exist "backend\venv" (
    echo ⚠ Entorno virtual no encontrado.
    echo Ejecuta primero scripts\install.bat o scripts\install.sh
    echo.
    pause
    exit /b 1
)

:: Activar entorno virtual backend y empezar uvicorn
call backend\venv\Scripts\activate
cd /d backend
echo Iniciando Backend FastAPI...
start /b uvicorn app.main:app --host 0.0.0.0 --port 8000
echo Backend corriendo en http://localhost:8000

:: Cambiar al directorio frontend
cd /d ..\frontend

echo Iniciando Frontend React...
npm start

echo.
echo ==========================================
echo     SISTEMA EN EJECUCIÓN
echo ==========================================
echo.
echo Backend (API):     http://localhost:8000
echo Docs API:          http://localhost:8000/docs
echo Frontend:          http://localhost:3000
echo.
echo Para detener: Cierra las ventanas de terminal abiertas.
echo.

:: Mantener la terminal abierta
timeout -1 >nul