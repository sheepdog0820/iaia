Param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pidFile = Join-Path $repoRoot ".server.pid"
$ngrokPidFile = Join-Path $repoRoot ".ngrok.pid"

function Get-ListeningPid([int]$p) {
    try {
        return (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess)
    } catch {
        return $null
    }
}

function Stop-Pid([int]$pidToStop) {
    try {
        Stop-Process -Id $pidToStop -Force -ErrorAction Stop | Out-Null
        Write-Host "Stopped PID $pidToStop"
        return $true
    } catch {
        return $false
    }
}

# Stop by pidfile first
if (Test-Path $pidFile) {
    $serverPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($serverPid -match '^\d+$') { [void](Stop-Pid -pidToStop ([int]$serverPid)) }
}

# Stop ngrok if started by our scripts
if (Test-Path $ngrokPidFile) {
    $ngrokPid = (Get-Content $ngrokPidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($ngrokPid -match '^\d+$') { [void](Stop-Pid -pidToStop ([int]$ngrokPid)) }
    Remove-Item -Path $ngrokPidFile -Force -ErrorAction SilentlyContinue
}

# Then ensure the port is free (kill any remaining listener/holders).
try {
    $listenPid = Get-ListeningPid -p $Port
    if ($listenPid) { [void](Stop-Pid -pidToStop $listenPid) }
} catch {}

if (Get-ListeningPid -p $Port) {
    Write-Host "Port $Port is still in use. Stop failed."
    exit 1
}

if (Test-Path $pidFile) {
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
}

exit 0

