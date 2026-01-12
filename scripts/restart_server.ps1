Param(
    [int]$Port = 8000,
    [string]$HostAddress = "0.0.0.0",
    [switch]$NoReload = $true,
    [int]$WaitSeconds = 10,
    [string]$EnvFile = ".env.development",
    [bool]$ForceUtf8 = $true,
    [bool]$UseNgrok = $true,
    [string]$NgrokDomain,
    [string]$PublicBaseUrl,
    [string]$NgrokPath,
    [int]$NgrokWaitSeconds = 15,
    [int]$NgrokApiPort = 4040,
    [bool]$OpenBrowser = $true,
    [string]$OpenPath = "/accounts/login/"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& (Join-Path $PSScriptRoot "stop_server.ps1") -Port $Port
& (Join-Path $PSScriptRoot "start_server.ps1") `
    -Port $Port `
    -HostAddress $HostAddress `
    -NoReload:$NoReload `
    -WaitSeconds $WaitSeconds `
    -EnvFile $EnvFile `
    -ForceUtf8:$ForceUtf8 `
    -UseNgrok:$UseNgrok `
    -NgrokDomain $NgrokDomain `
    -PublicBaseUrl $PublicBaseUrl `
    -NgrokPath $NgrokPath `
    -NgrokWaitSeconds $NgrokWaitSeconds `
    -NgrokApiPort $NgrokApiPort `
    -OpenBrowser:$OpenBrowser `
    -OpenPath $OpenPath

