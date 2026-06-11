Param(
    [ValidateSet("development", "production")]
    [string]$Environment = "development",
    [ValidateSet("background", "foreground")]
    [string]$RunMode = "foreground",
    [int]$Port = 8000,
    [string]$HostAddress = "0.0.0.0",
    [switch]$NoReload = $true,
    [int]$WaitSeconds = 15,
    [int]$HealthTimeoutSeconds = 5,
    [string]$HealthPath = "/health/live/",
    [string]$EnvFile = "",
    [bool]$ForceUtf8 = $true
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pidFile = Join-Path $repoRoot ".server.pid"
$stdoutLog = Join-Path $repoRoot "server.log"
$stderrLog = Join-Path $repoRoot "server_err.log"

function Resolve-DefaultEnvFile([string]$mode) {
    if ($mode -eq "production") {
        return ".env.production"
    }
    return ".env.development"
}

function Resolve-AppEnv([string]$mode) {
    if ($mode -eq "production") {
        return "aws-prod"
    }
    return "local"
}

function Resolve-EnvFilePath([string]$path) {
    if (-not $path) { return $null }
    if ([System.IO.Path]::IsPathRooted($path)) { return $path }
    return (Join-Path $repoRoot $path)
}

function Resolve-PythonPath() {
    $venvPython = Join-Path $repoRoot "venv\\Scripts\\python.exe"
    if (Test-Path $venvPython) { return $venvPython }
    return "python"
}

function Get-ListeningPid([int]$p) {
    $portPattern = ":{0}\s+" -f $p
    $lines = netstat -ano | Select-String -Pattern $portPattern | Where-Object { $_.Line -match "LISTENING" }
    foreach ($line in $lines) {
        if ($line.Line -match "LISTENING\s+(\d+)\s*$") {
            return [int]$matches[1]
        }
    }
    return $null
}

function Test-HttpReady([string]$uri, [int]$timeoutSec) {
    try {
        $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec $timeoutSec
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            return $true
        }
    } catch {
        if ($_.Exception.Response) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
                if ($statusCode -ge 200 -and $statusCode -lt 500) {
                    return $true
                }
            } catch {}
        }
    }
    return $false
}

$effectiveEnvFile = $EnvFile
if (-not $effectiveEnvFile) {
    $effectiveEnvFile = Resolve-DefaultEnvFile -mode $Environment
}

$resolvedEnvFile = Resolve-EnvFilePath -path $effectiveEnvFile
if (-not (Test-Path $resolvedEnvFile)) {
    Write-Host "Env file not found: $resolvedEnvFile"
    exit 1
}

$env:ENV_FILE = $effectiveEnvFile
$env:APP_ENV = Resolve-AppEnv -mode $Environment
$env:ENVIRONMENT = $(if ($Environment -eq "development") { "development" } else { "production" })
$env:DEBUG = $(if ($Environment -eq "development") { "true" } else { "false" })
Remove-Item Env:DJANGO_SETTINGS_MODULE -ErrorAction SilentlyContinue

if ($ForceUtf8 -and -not $env:PYTHONUTF8) {
    $env:PYTHONUTF8 = "1"
}

$normalizedHealthPath = $HealthPath
if (-not $normalizedHealthPath.StartsWith("/")) {
    $normalizedHealthPath = "/$normalizedHealthPath"
}
$healthUrl = "http://127.0.0.1:$Port$normalizedHealthPath"

$existingListenPid = Get-ListeningPid -p $Port
if ($existingListenPid) {
    if (Test-HttpReady -uri $healthUrl -timeoutSec $HealthTimeoutSeconds) {
        Write-Host "Already listening on $($HostAddress):$Port (PID: $existingListenPid)"
        $existingListenPid | Out-File -FilePath $pidFile -Encoding ascii
        exit 0
    }
    Write-Host "Port $Port is already in use by PID $existingListenPid, but health check failed."
    Write-Host "Run scripts\\stop_server.ps1 -Port $Port, then retry."
    exit 1
}

$python = Resolve-PythonPath
$args = @("manage.py", "runserver", "$HostAddress`:$Port")
if ($NoReload) { $args += "--noreload" }

if ($RunMode -eq "foreground") {
    Write-Host "Starting Django server in foreground ($Environment): $python $($args -join ' ')"
    Write-Host "Press Ctrl+C to stop."
    & $python @args
    exit $LASTEXITCODE
}

Write-Host "Starting Django server in background ($Environment): $python $($args -join ' ')"
$proc = Start-Process `
    -FilePath $python `
    -ArgumentList $args `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru
$proc.Id | Out-File -FilePath $pidFile -Encoding ascii

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 300
    if (Test-HttpReady -uri $healthUrl -timeoutSec $HealthTimeoutSeconds) {
        Write-Host "Server is ready: http://127.0.0.1:$Port/ (PID: $($proc.Id), env: $Environment)"
        exit 0
    }

    try {
        if ($proc.HasExited) {
            Write-Host "Server process exited early with code: $($proc.ExitCode)"
            break
        }
    } catch {}
}

Write-Host "Server did not become ready within $WaitSeconds seconds."
Write-Host "Health URL: $healthUrl"
Write-Host "See logs: $stdoutLog / $stderrLog"
exit 1
