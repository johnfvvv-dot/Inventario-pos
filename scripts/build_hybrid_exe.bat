@echo off
:: ==========================================================================
::  Compila InventarioPOS.exe en modo hibrido (frontend + Neon + Render).
::  Uso normal:  scripts\build_hybrid_exe.bat
::  Con cadena:  scripts\build_hybrid_exe.bat -DatabaseUrl "postgresql://..."
:: ==========================================================================
setlocal
cd /d "%~dp0.."

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_hybrid_exe.ps1" %*
set "CODIGO=%ERRORLEVEL%"

if not "%CODIGO%"=="0" (
    echo.
    echo [ERROR] La compilacion fallo. Revisa los mensajes anteriores.
)

pause
exit /b %CODIGO%
