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

& (Join-Path $PSScriptRoot "stop_server.ps1") -Port $Port
& (Join-Path $PSScriptRoot "start_server.ps1") `
    -Environment $Environment `
    -RunMode $RunMode `
    -Port $Port `
    -HostAddress $HostAddress `
    -NoReload:$NoReload `
    -WaitSeconds $WaitSeconds `
    -HealthTimeoutSeconds $HealthTimeoutSeconds `
    -HealthPath $HealthPath `
    -EnvFile $EnvFile `
    -ForceUtf8:$ForceUtf8

