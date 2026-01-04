Param(
    [int]$Port = 8000,
    [string]$HostAddress = "0.0.0.0",
    [switch]$NoReload = $true,
    [int]$WaitSeconds = 10,
    [int]$HealthTimeoutSeconds = 5,
    [string]$EnvFile = ".env.development",
    [bool]$ForceUtf8 = $true
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pidFile = Join-Path $repoRoot ".server.pid"
$stdoutLog = Join-Path $repoRoot "server.log"
$stderrLog = Join-Path $repoRoot "server_err.log"

function Resolve-EnvFilePath([string]$path) {
    if (-not $path) { return $null }
    if ([System.IO.Path]::IsPathRooted($path)) { return $path }
    return (Join-Path $repoRoot $path)
}

function Get-ListeningPid([int]$p) {
    try {
        return (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess)
    } catch {
        return $null
    }
}

function Resolve-PythonPath() {
    $venvPython = Join-Path $repoRoot "venv\\Scripts\\python.exe"
    if (Test-Path $venvPython) { return $venvPython }
    return "python"
}

$resolvedEnvFile = Resolve-EnvFilePath -path $EnvFile
if ($EnvFile) {
    if (-not (Test-Path $resolvedEnvFile)) {
        Write-Host "Env file not found: $resolvedEnvFile"
        exit 1
    }
    $env:ENV_FILE = $EnvFile
}

if ($ForceUtf8 -and -not $env:PYTHONUTF8) {
    $env:PYTHONUTF8 = "1"
}

$existingListenPid = Get-ListeningPid -p $Port
if ($existingListenPid) {
    Write-Host "Already listening on $($HostAddress):$Port (PID: $existingListenPid)"
    $existingListenPid | Out-File -FilePath $pidFile -Encoding ascii
    exit 0
}

$python = Resolve-PythonPath
$args = @("manage.py", "runserver", "$HostAddress`:$Port")
if ($NoReload) { $args += "--noreload" }

$env:DJANGO_SETTINGS_MODULE = "tableno.settings"

Write-Host "Starting Django dev server: $python $($args -join ' ')"
$proc = Start-Process -FilePath $python -ArgumentList $args -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

# Prefer the actual listening PID (in case the launching process differs).
$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    Start-Sleep -Milliseconds 250
    $listenPid = Get-ListeningPid -p $Port
} while (-not $listenPid -and (Get-Date) -lt $deadline)

if ($listenPid) {
    $listenPid | Out-File -FilePath $pidFile -Encoding ascii
    # Optional health check: make sure the loopback URL answers.
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec $HealthTimeoutSeconds
        Write-Host "Server is ready: http://127.0.0.1:$Port/ (PID: $listenPid)"
        exit 0
    } catch {
        Write-Host "Server is listening but health check failed: http://127.0.0.1:$Port/"
        Write-Host "See logs: $stdoutLog / $stderrLog"
        exit 1
    }
}

try {
    if (-not $proc.HasExited) {
        $proc.Id | Out-File -FilePath $pidFile -Encoding ascii
    }
} catch {}

Write-Host "Server did not start listening within $WaitSeconds seconds."
Write-Host "See logs: $stdoutLog / $stderrLog"
exit 1
