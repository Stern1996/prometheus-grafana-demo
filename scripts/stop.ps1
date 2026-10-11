<#
    stop.ps1 -- shuts the demo stack down.

    Tries the PIDs recorded by start.ps1 first, then falls back to whatever is
    listening on the ports (in case a process was restarted by hand).

    Usage:  powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
#>
param(
    [int]$AppPort     = 8080,
    [int]$PromPort    = 9090,
    [int]$GrafanaPort = 3000
)

$ROOT = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $ROOT 'run\pids.txt'
$killed = @()

if (Test-Path $pidFile) {
    Get-Content $pidFile | ForEach-Object {
        $parts = $_ -split '='
        if ($parts.Count -eq 2) {
            $procId = [int]$parts[1]
            $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host "stopping $($parts[0]) (pid $procId)"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                $killed += $procId
            }
        }
    }
}

# Fallback: anything still holding the ports
Start-Sleep -Seconds 2
foreach ($port in @($AppPort, $PromPort, $GrafanaPort)) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            if ($killed -notcontains $_) {
                $p = Get-Process -Id $_ -ErrorAction SilentlyContinue
                if ($p) {
                    Write-Host "stopping $($p.ProcessName) on port $port (pid $_)"
                    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
                }
            }
        }
}

Start-Sleep -Seconds 2
Write-Host ""
$still = @()
foreach ($port in @($AppPort, $PromPort, $GrafanaPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        $still += $port
    }
}
if ($still.Count -eq 0) {
    Write-Host "all demo services stopped"
} else {
    Write-Host "still listening on: $($still -join ', ')"
    exit 1
}
