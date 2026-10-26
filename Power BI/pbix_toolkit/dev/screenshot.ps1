param(
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$FocusTitle = ""
)

# Captura de pantalla completa (escritorio virtual).
# Opcionalmente trae al frente la ventana de Power BI Desktop.

if ($FocusTitle) {
    $sig = @"
using System;
using System.Runtime.InteropServices;
public class Win32Foco {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
    Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue
    $p = Get-Process PBIDesktop -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowTitle -like "*$FocusTitle*" } |
         Select-Object -First 1
    if ($p -and $p.MainWindowHandle -ne 0) {
        [Win32Foco]::ShowWindow($p.MainWindowHandle, 9) | Out-Null   # SW_RESTORE
        [Win32Foco]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
        Start-Sleep -Milliseconds 900
    }
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$vs = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap($vs.Width, $vs.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($vs.Left, $vs.Top, 0, 0, $bmp.Size)

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output "OK $Out"
