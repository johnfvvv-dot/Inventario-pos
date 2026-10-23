@echo off
:: ==========================================================================
::  Compila el APK de Android (Capacitor) para Inventario POS
::  Uso:  scripts\build_apk.bat
::  Salida: frontend\android\app\build\outputs\apk\debug\app-debug.apk
:: ==========================================================================
setlocal

set "PROJECT=%~dp0.."
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "ANDROID_HOME=%USERPROFILE%\AppData\Local\Android\Sdk"
set "ANDROID_SDK_ROOT=%ANDROID_HOME%"
set "PATH=%JAVA_HOME%\bin;%PATH%"

echo ==========================================
echo   COMPILANDO APK DE ANDROID
echo ==========================================
echo.

if not exist "%JAVA_HOME%\bin\java.exe" (
    echo [ERROR] No se encontro Java en "%JAVA_HOME%"
    echo         Abre Android Studio una vez para que instale su JDK.
    pause
    exit /b 1
)

cd /d "%PROJECT%\frontend"

:: 1) Verificar que el frontend esta compilado
if not exist "build\index.html" (
    echo [1/3] Compilando el frontend...
    call npm run build
)

:: 2) Sincronizar los assets con Android
echo [2/3] Sincronizando con Capacitor...
call npx cap sync android
if errorlevel 1 (
    echo [ERROR] Fallo la sincronizacion de Capacitor
    pause
    exit /b 1
)

:: 3) Compilar el APK
echo [3/3] Compilando el APK con Gradle...
cd android
call gradlew.bat assembleDebug --no-daemon
if errorlevel 1 (
    echo [ERROR] Gradle fallo. Revisa que el SDK de Android este instalado.
    pause
    exit /b 1
)

cd /d "%PROJECT%"

if exist "frontend\android\app\build\outputs\apk\debug\app-debug.apk" (
    echo.
    echo ==========================================
    echo   APK LISTO
    echo ==========================================
    echo   Ubicacion: frontend\android\app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo   Para instalarlo en el celular conectado:
    echo     adb install -r frontend\android\app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo   O copia el .apk al celular y abrilo (activa "instalar apps desconocidas").
    echo.
) else (
    echo [ERROR] No se genero el APK
)

pause
endlocal
