# Inspecciona procesos de Power BI Desktop / msmdsrv y los archivos que tienen abiertos
Get-CimInstance Win32_Process -Filter "Name='PBIDesktop.exe' or Name='msmdsrv.exe'" |
    ForEach-Object {
        $cl = $_.CommandLine
        if ($cl -and $cl.Length -gt 240) { $cl = $cl.Substring(0, 240) }
        [PSCustomObject]@{
            Id      = $_.ProcessId
            Nombre  = $_.Name
            Padre   = $_.ParentProcessId
            CmdLine = $cl
        }
    } | Format-List
