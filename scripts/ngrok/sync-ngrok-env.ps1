# Sync ngrok tunnel URLs (http://127.0.0.1:4040) into frontend/.env.local and backend/.env
param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
  [int]$ApiPort = 4040,
  [int]$MaxWaitSeconds = 90,
  [string]$RingooConfig = (Join-Path $PSScriptRoot "ngrok.ringoo.yml")
)

$ErrorActionPreference = "Stop"

function Get-HostnameFrom-PublicUrl([string]$Url) {
  if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
  try {
    return ([Uri]$Url).Host
  } catch {
    return $null
  }
}

function Set-EnvLine {
  param(
    [string]$FilePath,
    [string]$Key,
    [string]$Value
  )
  $lines = @()
  if (Test-Path $FilePath) {
    $lines = Get-Content $FilePath -Encoding UTF8
  }
  $found = $false
  $newLines = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
      $found = $true
      "$Key=$Value"
    } else {
      $line
    }
  }
  if (-not $found) {
    if ($newLines.Count -gt 0 -and $newLines[-1] -ne "") { $newLines += "" }
    $newLines += "$Key=$Value"
  }
  $dir = Split-Path $FilePath -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  Set-Content -Path $FilePath -Value $newLines -Encoding UTF8
}

function Get-EnvValueFromFile {
  param(
    [string]$FilePath,
    [string]$Key
  )
  if (-not (Test-Path $FilePath)) { return "" }
  $line = Get-Content $FilePath -Encoding UTF8 | Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" } | Select-Object -First 1
  if ($line) { return ($line -split '=', 2)[1].Trim() }
  return ""
}

function Merge-CommaHosts {
  param(
    [string]$Existing,
    [string[]]$Add
  )
  $set = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach ($p in ($Existing -split ',')) {
    $t = $p.Trim()
    if ($t) { [void]$set.Add($t) }
  }
  foreach ($a in $Add) {
    $t = $a.Trim()
    if ($t) { [void]$set.Add($t) }
  }
  return ($set | Sort-Object) -join ','
}

function Normalize-PublicUrl([string]$Url) {
  if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
  if ($Url -notmatch '^https?://') { $Url = "https://$Url" }
  return $Url.TrimEnd('/')
}

function Get-UpstreamAddr($item) {
  if ($item.config -and $item.config.addr) {
    return [string]$item.config.addr
  }
  if ($item.upstream -and $item.upstream.url) {
    return [string]$item.upstream.url
  }
  return ""
}

function Get-PublicUrl($item) {
  if ($item.public_url) { return Normalize-PublicUrl $item.public_url }
  if ($item.url) { return Normalize-PublicUrl $item.url }
  return $null
}

function Get-FrontendUrlFrom-RingooConfig {
  param([string]$ConfigPath)
  if (-not (Test-Path $ConfigPath)) { return $null }
  $text = Get-Content $ConfigPath -Raw -Encoding UTF8
  if ($text -match '(?ms)name:\s*ringoo-frontend\s+url:\s*(https://\S+)') {
    return (Normalize-PublicUrl $Matches[1])
  }
  if ($text -match 'url:\s*(https://[a-z0-9.-]+\.ngrok-free\.dev)') {
    return (Normalize-PublicUrl $Matches[1])
  }
  return $null
}

function Fetch-NgrokItems {
  $items = @()
  $base = "http://127.0.0.1:$ApiPort/api"
  foreach ($path in @('/endpoints', '/tunnels')) {
    try {
      $resp = Invoke-RestMethod -Uri "$base$path" -Method Get -TimeoutSec 3
      if ($resp.endpoints) { $items += @($resp.endpoints) }
      if ($resp.tunnels) { $items += @($resp.tunnels) }
    } catch {
      # try next
    }
  }
  return $items
}

function Resolve-NgrokUrls {
  $frontendUrl = $null
  $backendUrl = $null

  foreach ($t in (Fetch-NgrokItems)) {
    $public = Get-PublicUrl $t
    if (-not $public) { continue }
    $addr = Get-UpstreamAddr $t
    $name = [string]$t.name

    if ($name -match 'frontend' -or $addr -match '(^|:|\/)3000(\/|$)') {
      if (-not $frontendUrl) { $frontendUrl = $public }
    }
    if ($name -match 'backend' -or $addr -match '(^|:|\/)8000(\/|$)') {
      if (-not $backendUrl) { $backendUrl = $public }
    }
  }

  # Single tunnel on 3000 only (demo mode)
  if ($frontendUrl -and -not $backendUrl) {
    return @{ Frontend = $frontendUrl; Backend = $null }
  }

  return @{ Frontend = $frontendUrl; Backend = $backendUrl }
}

$frontendUrl = $null
$backendUrl = $null
$deadline = (Get-Date).AddSeconds($MaxWaitSeconds)

while ((Get-Date) -lt $deadline) {
  $resolved = Resolve-NgrokUrls
  $frontendUrl = $resolved.Frontend
  $backendUrl = $resolved.Backend
  if ($frontendUrl -or $backendUrl) { break }
  Start-Sleep -Seconds 2
}

if (-not $frontendUrl -and -not $backendUrl) {
  $fallback = Get-FrontendUrlFrom-RingooConfig -ConfigPath $RingooConfig
  if ($fallback) {
    Write-Warning "Ngrok API had no tunnels yet; using URL from $RingooConfig"
    $frontendUrl = $fallback
  } else {
    Write-Error @"
No ngrok endpoints found for ports 3000/8000 within ${MaxWaitSeconds}s.
1) Docker must listen on http://127.0.0.1:3000 (frontend)
2) In ngrok window: no errors; endpoint ringoo-frontend online
3) Open http://127.0.0.1:4040 — check Forwarding
4) Retry: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ngrok\sync-ngrok-env.ps1
"@
  }
}

$frontendEnv = Join-Path $RepoRoot "frontend\.env.local"
$backendEnvFiles = @(
  (Join-Path $RepoRoot "backend\.env.development"),
  (Join-Path $RepoRoot "backend\.env")
)
$rootEnv = Join-Path $RepoRoot ".env"
$useSameOrigin = $false

if ($frontendUrl -and (-not $backendUrl -or ($frontendUrl -eq $backendUrl))) {
  $useSameOrigin = $true
  Write-Host "[mode] Same-origin: API and /media via Next.js proxy (recommended for demo)"
}

if ($useSameOrigin -and $frontendUrl) {
  $apiV1 = "$frontendUrl/api/v1"
  Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_API_V1_URL" -Value $apiV1
  Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_API_URL" -Value $frontendUrl
  Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_SITE_URL" -Value $frontendUrl
  Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_APP_URL" -Value $frontendUrl
  Set-EnvLine -FilePath $rootEnv -Key "NEXT_PUBLIC_API_V1_URL" -Value $apiV1
  Set-EnvLine -FilePath $rootEnv -Key "NEXT_PUBLIC_API_URL" -Value $frontendUrl
  Set-EnvLine -FilePath $rootEnv -Key "NEXT_PUBLIC_SITE_URL" -Value $frontendUrl
  Set-EnvLine -FilePath $rootEnv -Key "RINGOO_DISABLE_HMR" -Value "1"
  Set-EnvLine -FilePath $rootEnv -Key "RINGOO_NGROK_DEMO" -Value "1"
  Write-Host "[ok] NEXT_PUBLIC_SITE_URL=$frontendUrl"
  Write-Host "[ok] NEXT_PUBLIC_API_V1_URL=$apiV1 (proxied to Django)"
} else {
  if ($backendUrl) {
    $apiV1 = "$backendUrl/api/v1"
    Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_API_V1_URL" -Value $apiV1
    Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_API_URL" -Value $backendUrl
    Set-EnvLine -FilePath $rootEnv -Key "NEXT_PUBLIC_API_V1_URL" -Value $apiV1
    Set-EnvLine -FilePath $rootEnv -Key "NEXT_PUBLIC_API_URL" -Value $backendUrl
    Write-Host "[ok] NEXT_PUBLIC_API_V1_URL=$apiV1"
  }
  if ($frontendUrl) {
    Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_SITE_URL" -Value $frontendUrl
    Set-EnvLine -FilePath $frontendEnv -Key "NEXT_PUBLIC_APP_URL" -Value $frontendUrl
    Set-EnvLine -FilePath $rootEnv -Key "NEXT_PUBLIC_SITE_URL" -Value $frontendUrl
    Write-Host "[ok] NEXT_PUBLIC_SITE_URL=$frontendUrl"
  }
  if ($frontendUrl -or $backendUrl) {
    Set-EnvLine -FilePath $rootEnv -Key "RINGOO_DISABLE_HMR" -Value "1"
    Set-EnvLine -FilePath $rootEnv -Key "RINGOO_NGROK_DEMO" -Value "1"
  }
}

$feHost = Get-HostnameFrom-PublicUrl $frontendUrl
$beHost = Get-HostnameFrom-PublicUrl $backendUrl
$hostsToAdd = @($feHost, $beHost) | Where-Object { $_ }

$csrfOrigins = @()
if ($frontendUrl) { $csrfOrigins += $frontendUrl }
if ($backendUrl) { $csrfOrigins += $backendUrl }

foreach ($backendEnv in $backendEnvFiles) {
  if (-not (Test-Path $backendEnv)) { continue }
  if ($hostsToAdd.Count -gt 0) {
    $hosts = Merge-CommaHosts -Existing (Get-EnvValueFromFile -FilePath $backendEnv -Key "ALLOWED_HOSTS") -Add $hostsToAdd
    Set-EnvLine -FilePath $backendEnv -Key "ALLOWED_HOSTS" -Value $hosts
  }
  if ($csrfOrigins.Count -gt 0) {
    $existingCsrf = Get-EnvValueFromFile -FilePath $backendEnv -Key "CSRF_TRUSTED_ORIGINS"
    $csrf = Merge-CommaHosts -Existing $existingCsrf -Add $csrfOrigins
    Set-EnvLine -FilePath $backendEnv -Key "CSRF_TRUSTED_ORIGINS" -Value $csrf
  }
  if ($backendUrl) {
    Set-EnvLine -FilePath $backendEnv -Key "PUBLIC_API_ORIGIN" -Value $backendUrl
  }
  Write-Host "[ok] updated $backendEnv"
}

Write-Host ""
Write-Host "Demo link for client:"
if ($frontendUrl) { Write-Host "  $frontendUrl" }
if ($backendUrl -and $backendUrl -ne $frontendUrl) {
  Write-Host "  API: $backendUrl/api/v1"
}
Write-Host ""
Write-Host "Then recreate Docker (required):"
Write-Host "  docker compose up -d --force-recreate frontend web"
