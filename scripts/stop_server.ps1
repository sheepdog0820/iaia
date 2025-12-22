Param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pidFile = Join-Path $repoRoot ".server.pid"

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
    if ($serverPid) { [void](Stop-Pid -pidToStop ([int]$serverPid)) }
}

# Then ensure the port is free (kill any remaining listener/holders).
try {
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { [void](Stop-Pid -pidToStop $_) }
} catch {}

exit 0

