param(
    [string]$DatabaseUrl = "",
    [string]$CloudApiUrl = "https://inventario-pos-api-pqju.onrender.com/api",
    [switch]$SkipFrontend,
    [switch]$SkipDeps
)

# --------------------------------------------------------------------------
#  Construye InventarioPOS.exe en modo hibrido:
#    - Frontend React compilado apuntando a Render como respaldo.
#    - Backend FastAPI con la cadena de Neon incrustada.
#
#  Uso:
#    powershell -ExecutionPolicy Bypass -File scripts\build_hybrid_exe.ps1
#    ... -DatabaseUrl "postgresql://..."
#    ... -SkipDeps -SkipFrontend
#
#  La cadena de Neon tambien se puede dejar en inventario-pos.env (raiz),
#  backend\.env o en la variable de entorno DATABASE_URL.
# --------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function Escribir-Paso([string]$texto) {
    Write-Host ""
    Write-Host "== $texto ==" -ForegroundColor Cyan
}

function Fallar([string]$texto) {
    Write-Host ""
    Write-Host "[ERROR] $texto" -ForegroundColor Red
    exit 1
}

function Leer-Env([string]$ruta) {
    if (-not (Test-Path -LiteralPath $ruta)) { return "" }
    foreach ($linea in Get-Content -LiteralPath $ruta -Encoding UTF8) {
        if ($linea -match '^\s*DATABASE_URL\s*=\s*(.+?)\s*$') {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

if (-not $DatabaseUrl) { $DatabaseUrl = $env:DATABASE_URL }

$candidatos = @(
    (Join-Path $Root "inventario-pos.env"),
    (Join-Path $Root "backend\.env"),
    (Join-Path $Root "neon_url.txt")
)
foreach ($candidato in $candidatos) {
    if ($DatabaseUrl) { break }
    if ($candidato -like "*neon_url.txt" -and (Test-Path -LiteralPath $candidato)) {
        $DatabaseUrl = (Get-Content -LiteralPath $candidato -Raw -Encoding UTF8).Trim()
    } else {
        $DatabaseUrl = Leer-Env $candidato
    }
}

if (-not $DatabaseUrl) {
    Fallar "Falta DATABASE_URL. Pasala con -DatabaseUrl, define la variable de entorno o crea inventario-pos.env junto al proyecto."
}

$DatabaseUrl = $DatabaseUrl.Trim().Trim('"').Trim("'")
if ($DatabaseUrl.StartsWith("postgres://")) {
    $DatabaseUrl = "postgresql://" + $DatabaseUrl.Substring("postgres://".Length)
}
if (-not $DatabaseUrl.StartsWith("postgresql://")) {
    Fallar "DATABASE_URL debe ser una cadena PostgreSQL de Neon (postgresql://...)."
}

Write-Host "=============================================================="
Write-Host "  INVENTARIO POS - COMPILACION HIBRIDA"
Write-Host "=============================================================="
Write-Host "  Proyecto : $Root"
Write-Host "  Nube     : $CloudApiUrl"
Write-Host "  Neon     : $($DatabaseUrl.Substring(0, [Math]::Min(38, $DatabaseUrl.Length)))..."

# 1) Frontend con la URL publica de Render como respaldo.
if (-not $SkipFrontend) {
    Escribir-Paso "1/4 Compilando frontend React"
    Push-Location -LiteralPath "frontend"
    try {
        $env:REACT_APP_CLOUD_API_URL = $CloudApiUrl
        Remove-Item Env:REACT_APP_API_URL -ErrorAction SilentlyContinue
        Remove-Item Env:REACT_APP_LOCAL_API_URL -ErrorAction SilentlyContinue
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build termino con codigo $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    if (-not (Test-Path -LiteralPath "frontend\build\index.html")) {
        Fallar "No se genero frontend\build\index.html."
    }
    Write-Host "Frontend compilado correctamente."
} else {
    Escribir-Paso "1/4 Frontend omitido (-SkipFrontend)"
    if (-not (Test-Path -LiteralPath "frontend\build\index.html")) {
        Fallar "No existe frontend\build. Compila sin -SkipFrontend."
    }
}

# 2) Entorno de Python para PyInstaller.
Escribir-Paso "2/4 Preparando entorno Python"
$venvPython = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creando backend\venv..."
    & python -m venv backend\venv
    if ($LASTEXITCODE -ne 0) { Fallar "No se pudo crear el entorno virtual (revisa Python 3.11+)." }
}
if (-not $SkipDeps) {
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r backend\requirements.txt pyinstaller
    if ($LASTEXITCODE -ne 0) { Fallar "Fallo la instalacion de dependencias." }
}
& $venvPython -c "import PyInstaller, psycopg, sqlalchemy, tzdata, dotenv"
if ($LASTEXITCODE -ne 0) { Fallar "Faltan dependencias en backend\venv. Ejecuta sin -SkipDeps." }

# 3) Cadena de Neon incrustada (archivo temporal, nunca se versiona).
$defaults = Join-Path $Root "backend\app\_build_defaults.py"
$jsonUrl = $DatabaseUrl | ConvertTo-Json -Compress
$contenido = @"
# Generado automaticamente por scripts/build_hybrid_exe.ps1.
# NO VERSIONAR: contiene la cadena de conexion de Neon.
DATABASE_URL = $jsonUrl
"@
$utf8SinBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($defaults, $contenido, $utf8SinBom)

try {
    Escribir-Paso "3/4 Generando InventarioPOS.exe"
    & $venvPython -m PyInstaller build_exe.spec --noconfirm --clean
    if ($LASTEXITCODE -ne 0) { Fallar "PyInstaller termino con codigo $LASTEXITCODE" }
} finally {
    if (Test-Path -LiteralPath $defaults) {
        Remove-Item -LiteralPath $defaults -Force
        Write-Host "Cadena temporal eliminada de backend\app\_build_defaults.py"
    }
}

# 4) Resultado.
Escribir-Paso "4/4 Resultado"
$exe = Join-Path $Root "dist\InventarioPOS.exe"
if (-not (Test-Path -LiteralPath $exe)) { Fallar "No se encontro dist\InventarioPOS.exe." }
$item = Get-Item -LiteralPath $exe
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash

Write-Host ""
Write-Host "=============================================================="
Write-Host "  LISTO: $($item.FullName)"
Write-Host "  Tamano: $([Math]::Round($item.Length / 1MB, 1)) MB"
Write-Host "  SHA256: $hash"
Write-Host "=============================================================="
Write-Host ""
Write-Host "  Copia InventarioPOS.exe al PC del negocio y ejecutalo."
Write-Host "  Si el PC no tiene la cadena incrustada, crea inventario-pos.env"
Write-Host "  junto al .exe con: DATABASE_URL=postgresql://..."
Write-Host ""
