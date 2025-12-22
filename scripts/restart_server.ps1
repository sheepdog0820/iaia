Param(
    [int]$Port = 8000,
    [string]$HostAddress = "0.0.0.0",
    [switch]$NoReload = $true,
    [int]$WaitSeconds = 10
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& (Join-Path $PSScriptRoot "stop_server.ps1") -Port $Port
& (Join-Path $PSScriptRoot "start_server.ps1") -Port $Port -HostAddress $HostAddress -NoReload:$NoReload -WaitSeconds $WaitSeconds

