param(
    [string]$CloudApiUrl = "https://inventario-pos-api-pqju.onrender.com/api",
    [string]$LocalApiUrl = "",
    [switch]$Deploy
)

# --------------------------------------------------------------------------
#  Compila el frontend para Cloudflare Pages.
#    - Render queda como respaldo.
#    - La IP LAN activa del PC se incluye como candidato local.
#    - REACT_APP_API_URL se elimina: nunca puede forzar un endpoint.
#
#  Uso:
#    powershell -ExecutionPolicy Bypass -File scripts\build_pages.ps1
#    powershell -ExecutionPolicy Bypass -File scripts\build_pages.ps1 -Deploy
#    ... -LocalApiUrl "https://mi-tunel-https.example.com/api"
# --------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function IpLanActiva() {
    try {
        $cfg = Get-NetIPConfiguration |
            Where-Object {
                $_.IPv4DefaultGateway -ne $null -and
                $_.NetAdapter.Status -eq "Up" -and
                $_.IPv4Address.IPAddress
            } |
            Select-Object -First 1
        if ($cfg) { return $cfg.IPv4Address.IPAddress }
    } catch {
        # Sin cmdlets de red: se usa el metodo de socket mas abajo.
    }

    try {
        $socket = [System.Net.Sockets.Socket]::new(
            [System.Net.Sockets.AddressFamily]::InterNetwork,
            [System.Net.Sockets.SocketType]::Dgram,
            [System.Net.Sockets.ProtocolType]::Udp
        )
        $socket.Connect("8.8.8.8", 80)
        $ip = $socket.LocalEndPoint.Address.ToString()
        $socket.Dispose()
        return $ip
    } catch {
        return "127.0.0.1"
    }
}

if (-not $LocalApiUrl) {
    $ip = IpLanActiva
    if ($ip -and $ip -ne "127.0.0.1") {
        $LocalApiUrl = "http://${ip}:8000/api"
    }
}

$env:REACT_APP_CLOUD_API_URL = $CloudApiUrl
$env:REACT_APP_LOCAL_API_URL = $LocalApiUrl
Remove-Item Env:REACT_APP_API_URL -ErrorAction SilentlyContinue

Write-Host "=============================================================="
Write-Host "  INVENTARIO POS - BUILD CLOUDFLARE PAGES"
Write-Host "=============================================================="
Write-Host "  Nube : $CloudApiUrl"
Write-Host "  Local: $LocalApiUrl"
Write-Host "=============================================================="

Push-Location -LiteralPath "frontend"
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build termino con codigo $LASTEXITCODE" }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath "frontend\build\index.html")) {
    throw "No se genero frontend\build\index.html"
}

Write-Host ""
Write-Host "Build listo en frontend\build" -ForegroundColor Green

if ($Deploy) {
    Push-Location -LiteralPath "frontend"
    try {
        & npx.cmd wrangler pages deploy build --project-name inventario-pos --branch main --commit-dirty=true
        if ($LASTEXITCODE -ne 0) { throw "wrangler pages deploy termino con codigo $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
}
