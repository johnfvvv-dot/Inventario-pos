# Devuelve el PID del proceso PBIDesktop.exe que tiene abierto runtime\model.pbix
$pids = Get-CimInstance Win32_Process -Filter "Name='PBIDesktop.exe'" |
    Where-Object { $_.CommandLine -like "*pbix_toolkit\runtime\model.pbix*" } |
    Select-Object -ExpandProperty ProcessId
if ($pids) { $pids -join ',' } else { '' }
