@echo off
:: ==========================================================================
::  Crea un acceso directo en el ESCRITORIO para InventarioPOS.exe
::  Ejecutar:  scripts\crear_acceso_directo.bat
::  (puedes indicarle otra ruta: scripts\crear_acceso_directo.bat "D:\Apps\POS.exe")
:: ==========================================================================
setlocal

set "EXE=%~dp0..\dist\InventarioPOS.exe"
if not "%~1"=="" set "EXE=%~1"

if not exist "%EXE%" (
    echo [ERROR] No se encontro el ejecutable:
    echo         %EXE%
    echo.
    echo Primero construye el .exe con:  scripts\build_exe.bat
    pause
    exit /b 1
)

:: Resolver ruta absoluta
for %%i in ("%EXE%") do set "EXE=%%~fi"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$shell=New-Object -ComObject WScript.Shell;" ^
  "$sc=$shell.CreateShortcut((Join-Path $desktop 'Inventario POS.lnk'));" ^
  "$sc.TargetPath='%EXE%';" ^
  "$sc.WorkingDirectory=(Split-Path '%EXE%');" ^
  "$sc.Description='Sistema de Inventario y Punto de Venta';" ^
  "$sc.IconLocation='%EXE%,0';" ^
  "$sc.Save();" ^
  "Write-Host '';" ^
  "Write-Host 'Acceso directo creado en el escritorio: Inventario POS.lnk';"

pause
endlocal
