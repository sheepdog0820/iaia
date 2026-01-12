Param(
    [string]$EnvFile = ".env.development",
    [string]$ClientId,
    [string]$ClientSecret,
    [string]$RedirectUri,
    [string]$PublicBaseUrl,
    [switch]$RunSetup
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

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

function Read-Secret([string]$prompt) {
    $secure = Read-Host $prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringUni($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Parse-EnvValues([System.Collections.Generic.List[string]]$lines) {
    $values = @{}
    foreach ($line in $lines) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2]
        }
    }
    return $values
}

function Set-EnvValue([System.Collections.Generic.List[string]]$lines, [string]$key, [string]$value) {
    $escaped = [regex]::Escape($key)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match ('^\s*' + $escaped + '=')) {
            $lines[$i] = "$key=$value"
            return
        }
    }
    $lines.Add("$key=$value")
}

function Get-EnvValue([System.Collections.Generic.List[string]]$lines, [string]$key) {
    $escaped = [regex]::Escape($key)
    foreach ($line in $lines) {
        if ($line -match ('^\s*' + $escaped + '=(.*)$')) {
            return $Matches[1]
        }
    }
    return $null
}

function Remove-DuplicateEnvKeys([System.Collections.Generic.List[string]]$lines, [string[]]$keysToDedupe) {
    $keySet = @{}
    foreach ($key in $keysToDedupe) { $keySet[$key] = $true }

    $seen = @{}
    $indexesToRemove = New-Object System.Collections.Generic.List[int]

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=') {
            $key = $Matches[1]
            if ($keySet.ContainsKey($key)) {
                if ($seen.ContainsKey($key)) {
                    $indexesToRemove.Add($i)
                } else {
                    $seen[$key] = $true
                }
            }
        }
    }

    for ($j = $indexesToRemove.Count - 1; $j -ge 0; $j--) {
        $lines.RemoveAt($indexesToRemove[$j])
    }
}

function Add-EnvCsvValue([System.Collections.Generic.List[string]]$lines, [string]$key, [string]$value) {
    if ($null -eq $value) { $value = "" }
    $value = $value.Trim()
    if (-not $value) { return }

    $existing = Get-EnvValue -lines $lines -key $key
    if (-not $existing) {
        Set-EnvValue -lines $lines -key $key -value $value
        return
    }

    $parts = @($existing.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($parts -notcontains $value) {
        $parts += $value
        Set-EnvValue -lines $lines -key $key -value ($parts -join ",")
    }
}

function Resolve-Uri([string]$url) {
    $candidate = $url
    if ($null -eq $candidate) { $candidate = "" }
    $candidate = $candidate.Trim()
    if (-not $candidate) { return $null }
    if ($candidate -notmatch '^[a-zA-Z][a-zA-Z0-9+.-]*://') {
        $candidate = "https://$candidate"
    }
    try {
        return [Uri]$candidate
    } catch {
        return $null
    }
}

function Get-Origin([Uri]$uri) {
    if (-not $uri) { return $null }
    $origin = "$($uri.Scheme)://$($uri.Host)"
    if (-not $uri.IsDefaultPort) {
        $origin += ":$($uri.Port)"
    }
    return $origin
}

function Get-SiteDomain([Uri]$uri) {
    if (-not $uri) { return $null }
    $domain = "$($uri.Host)"
    if (-not $uri.IsDefaultPort) {
        $domain += ":$($uri.Port)"
    }
    return $domain
}

$resolvedEnvFile = Resolve-EnvFilePath -path $EnvFile
if (-not (Test-Path $resolvedEnvFile)) {
    Write-Host "Env file not found: $resolvedEnvFile"
    exit 1
}

$lines = [System.Collections.Generic.List[string]](Get-Content $resolvedEnvFile -Encoding UTF8)
$existing = Parse-EnvValues -lines $lines

$publicUri = Resolve-Uri -url $PublicBaseUrl
if (-not $publicUri) {
    $publicUri = Resolve-Uri -url $RedirectUri
}
$publicOrigin = Get-Origin -uri $publicUri
$publicHost = if ($publicUri) { $publicUri.Host } else { $null }
$publicSiteDomain = Get-SiteDomain -uri $publicUri

if (-not $RedirectUri -and $publicOrigin) {
    $RedirectUri = "$publicOrigin/accounts/twitter_oauth2/login/callback/"
}

$placeholders = @("your-twitter-client-id", "your-twitter-client-secret")
if (-not $ClientId) {
    $fromEnv = $existing["TWITTER_CLIENT_ID"]
    if ($null -eq $fromEnv) { $fromEnv = "" }
    $fromEnv = $fromEnv.Trim()
    if ($fromEnv -and ($placeholders -notcontains $fromEnv)) {
        $ClientId = $fromEnv
    } else {
        $ClientId = (Read-Host "X (Twitter) Client ID").Trim()
    }
}
if (-not $ClientSecret) {
    $fromEnv = $existing["TWITTER_CLIENT_SECRET"]
    if ($null -eq $fromEnv) { $fromEnv = "" }
    $fromEnv = $fromEnv.Trim()
    if ($fromEnv -and ($placeholders -notcontains $fromEnv)) {
        $ClientSecret = $fromEnv
    } else {
        $ClientSecret = (Read-Secret "X (Twitter) Client Secret").Trim()
    }
}

if (-not $ClientId) {
    Write-Host "Client ID is required."
    exit 1
}
if (-not $ClientSecret) {
    Write-Host "Client Secret is required."
    exit 1
}

Set-EnvValue -lines $lines -key "TWITTER_CLIENT_ID" -value $ClientId
Set-EnvValue -lines $lines -key "TWITTER_CLIENT_SECRET" -value $ClientSecret
if ($RedirectUri) {
    Set-EnvValue -lines $lines -key "TWITTER_REDIRECT_URI" -value $RedirectUri.Trim()
}
if ($publicHost) {
    Add-EnvCsvValue -lines $lines -key "ALLOWED_HOSTS" -value $publicHost
}
if ($publicOrigin) {
    Add-EnvCsvValue -lines $lines -key "CSRF_TRUSTED_ORIGINS" -value $publicOrigin
}
if ($publicSiteDomain) {
    Set-EnvValue -lines $lines -key "SITE_DOMAIN" -value $publicSiteDomain
}

Remove-DuplicateEnvKeys -lines $lines -keysToDedupe @(
    "TWITTER_CLIENT_ID",
    "TWITTER_CLIENT_SECRET",
    "TWITTER_REDIRECT_URI",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "SITE_DOMAIN"
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($resolvedEnvFile, $lines.ToArray(), $utf8NoBom)

Write-Host "Updated X OAuth env vars in: $EnvFile"
Write-Host "  - TWITTER_CLIENT_ID"
Write-Host "  - TWITTER_CLIENT_SECRET"
if ($RedirectUri) {
    Write-Host "  - TWITTER_REDIRECT_URI"
}
if ($publicHost) {
    Write-Host "  - ALLOWED_HOSTS (+ $publicHost)"
}
if ($publicOrigin) {
    Write-Host "  - CSRF_TRUSTED_ORIGINS (+ $publicOrigin)"
}
if ($publicSiteDomain) {
    Write-Host "  - SITE_DOMAIN (= $publicSiteDomain)"
}

if ($RunSetup) {
    $python = Resolve-PythonPath
    $env:ENV_FILE = $EnvFile
    $setupScript = Join-Path $repoRoot "setup_twitter_oauth.py"
    if ($publicSiteDomain) {
        & $python $setupScript "--domain" $publicSiteDomain "--scheme" ($publicUri.Scheme)
    } else {
        & $python $setupScript
    }
}
