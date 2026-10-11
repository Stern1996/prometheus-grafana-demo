<#
    screenshot.ps1 -- captures the provisioned Grafana dashboard to PNG.

    Uses headless Chrome/Edge. Grafana is a single-page app, so we give the
    renderer a virtual time budget big enough for every panel to finish its
    query, otherwise you get a half-drawn dashboard.

    Usage:
      powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1
      powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1 -Height 1500 -From now-1h
#>
param(
    [string]$DashboardUid = 'service-overview',
    [int]$GrafanaPort     = 3000,
    [string]$From         = 'now-30m',
    [string]$To           = 'now',
    [int]$Width           = 1920,
    [int]$Height          = 1220,
    [string]$OutDir       = '',
    [string]$Name         = 'dashboard'
)

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $ROOT 'gallery' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Find-Browser {
    $candidates = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw "no Chrome or Edge found"
}

$browser = Find-Browser
$url = "http://127.0.0.1:$GrafanaPort/d/$DashboardUid" +
       "?kiosk&from=$([uri]::EscapeDataString($From))&to=$([uri]::EscapeDataString($To))"

$out = Join-Path $OutDir "$Name.png"
if (Test-Path $out) { Remove-Item $out -Force }

Write-Host "capturing $url"
Write-Host "  viewport ${Width}x${Height} -> $out"

$args = @(
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-sandbox',
    '--disable-crash-reporter',
    '--force-device-scale-factor=1',
    '--virtual-time-budget=25000',
    "--window-size=$Width,$Height",
    "--screenshot=$out",
    $url
)
& $browser @args 2>&1 | Out-Null
Start-Sleep -Seconds 2

if (Test-Path $out) {
    Write-Host "  ok: $((Get-Item $out).Length) bytes"
} else {
    throw "screenshot was not produced"
}
