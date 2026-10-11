<#
    start.ps1 -- brings up the whole demo stack.

    Order matters a little: the demo app first (so Prometheus has something to
    scrape), then Prometheus, then Grafana, then the load generator.

    Usage:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#>
param(
    [int]$AppPort     = 8080,
    [int]$PromPort    = 9090,
    [int]$GrafanaPort = 3000,
    [double]$Rps      = 18
)

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent $PSScriptRoot

function Find-Exe($pattern) {
    $hit = Get-ChildItem -Path (Join-Path $ROOT 'bin') -Recurse -Filter $pattern -ErrorAction SilentlyContinue |
           Select-Object -First 1
    if (-not $hit) { throw "could not find $pattern under $ROOT\bin" }
    return $hit.FullName
}

$PROM_EXE = Find-Exe 'prometheus.exe'
$GRAF_EXE = Find-Exe 'grafana.exe'
$GRAF_HOME = Split-Path -Parent (Split-Path -Parent $GRAF_EXE)
$PY = (Get-Command python).Source

$RUN   = Join-Path $ROOT 'run'
$LOGS  = Join-Path $ROOT 'logs'
$DATA  = Join-Path $ROOT 'data'
New-Item -ItemType Directory -Force -Path $RUN, $LOGS, (Join-Path $DATA 'prometheus'), (Join-Path $DATA 'grafana') | Out-Null

$pids = @{}

Write-Host "starting demo app on :$AppPort"
$pids.app = (Start-Process -FilePath $PY `
    -ArgumentList @('app.py', '--port', $AppPort) `
    -WorkingDirectory (Join-Path $ROOT 'demo-app') `
    -RedirectStandardOutput (Join-Path $LOGS 'app.out.log') `
    -RedirectStandardError  (Join-Path $LOGS 'app.err.log') `
    -PassThru -NoNewWindow).Id

Start-Sleep -Seconds 2

Write-Host "starting prometheus on :$PromPort"
$pids.prometheus = (Start-Process -FilePath $PROM_EXE `
    -ArgumentList @(
        "--config.file=$(Join-Path $ROOT 'prometheus\prometheus.yml')",
        "--storage.tsdb.path=$(Join-Path $DATA 'prometheus')",
        "--storage.tsdb.retention.time=7d",
        "--web.listen-address=127.0.0.1:$PromPort",
        "--web.enable-lifecycle"
    ) `
    -WorkingDirectory (Join-Path $ROOT 'prometheus') `
    -RedirectStandardOutput (Join-Path $LOGS 'prometheus.out.log') `
    -RedirectStandardError  (Join-Path $LOGS 'prometheus.err.log') `
    -PassThru -NoNewWindow).Id

# --- Grafana: anonymous admin so screenshots work without a login step -----
$env:GF_SERVER_HTTP_ADDR          = '127.0.0.1'
$env:GF_SERVER_HTTP_PORT          = "$GrafanaPort"
$env:GF_AUTH_ANONYMOUS_ENABLED    = 'true'
$env:GF_AUTH_ANONYMOUS_ORG_ROLE   = 'Admin'
$env:GF_AUTH_ANONYMOUS_ORG_NAME   = 'Main Org.'
$env:GF_SECURITY_ALLOW_EMBEDDING  = 'true'
$env:GF_PATHS_PROVISIONING        = (Join-Path $ROOT 'provisioning')
$env:GF_PATHS_DATA                = (Join-Path $DATA 'grafana')
$env:GF_PATHS_LOGS                = (Join-Path $LOGS 'grafana')
$env:GF_PATHS_PLUGINS             = (Join-Path $DATA 'grafana-plugins')
$env:GF_ANALYTICS_REPORTING_ENABLED   = 'false'
$env:GF_ANALYTICS_CHECK_FOR_UPDATES   = 'false'
$env:GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES = 'false'
$env:GF_NEWS_NEWS_FEED_ENABLED    = 'false'
$env:GF_LOG_LEVEL                 = 'warn'
New-Item -ItemType Directory -Force -Path (Join-Path $LOGS 'grafana'), $env:GF_PATHS_PLUGINS | Out-Null

Write-Host "starting grafana on :$GrafanaPort"
$pids.grafana = (Start-Process -FilePath $GRAF_EXE `
    -ArgumentList @('server', "--homepath=$GRAF_HOME") `
    -WorkingDirectory $GRAF_HOME `
    -RedirectStandardOutput (Join-Path $LOGS 'grafana.out.log') `
    -RedirectStandardError  (Join-Path $LOGS 'grafana.err.log') `
    -PassThru -NoNewWindow).Id

Start-Sleep -Seconds 3

Write-Host "starting load generator (target $Rps req/s)"
$pids.loadgen = (Start-Process -FilePath $PY `
    -ArgumentList @('loadgen.py', '--url', "http://127.0.0.1:$AppPort", '--rps', "$Rps") `
    -WorkingDirectory (Join-Path $ROOT 'demo-app') `
    -RedirectStandardOutput (Join-Path $LOGS 'loadgen.out.log') `
    -RedirectStandardError  (Join-Path $LOGS 'loadgen.err.log') `
    -PassThru -NoNewWindow).Id

$pids.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } |
    Set-Content -Path (Join-Path $RUN 'pids.txt')

Write-Host ""
Write-Host "waiting for services to become ready ..."
$ok = $true
foreach ($svc in @(
    @{ name='demo app';   url="http://127.0.0.1:$AppPort/metrics" },
    @{ name='prometheus'; url="http://127.0.0.1:$PromPort/-/ready" },
    @{ name='grafana';    url="http://127.0.0.1:$GrafanaPort/api/health" }
)) {
    $ready = $false
    for ($i = 1; $i -le 40; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $svc.url -TimeoutSec 3 -UseBasicParsing
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 1500 }
    }
    if ($ready) { Write-Host "  [ok]   $($svc.name)  $($svc.url)" }
    else        { Write-Host "  [FAIL] $($svc.name)  $($svc.url)"; $ok = $false }
}

Write-Host ""
if ($ok) {
    Write-Host "dashboard: http://127.0.0.1:$GrafanaPort/d/service-overview"
    Write-Host "targets  : http://127.0.0.1:$PromPort/targets"
    Write-Host "alerts   : http://127.0.0.1:$PromPort/alerts"
    Write-Host ""
    Write-Host "let it run ~10 minutes before screenshotting so the charts have history."
} else {
    Write-Host "one or more services failed to start -- see logs\"
    exit 1
}
