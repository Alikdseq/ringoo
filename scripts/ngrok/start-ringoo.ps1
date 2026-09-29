# Ringoo: ngrok tunnel to localhost:3000 (Next proxies API/media to Django).
param(
  [switch]$NoKill,
  [switch]$NoSync,
  [switch]$UseV2,
  [switch]$Dual
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$RingooConfig = if ($UseV2) {
  Join-Path $PSScriptRoot "ngrok.ringoo.v2.yml"
} elseif ($Dual) {
  Join-Path $PSScriptRoot "ngrok.ringoo.dual.yml"
} else {
  Join-Path $PSScriptRoot "ngrok.ringoo.yml"
}

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
  Write-Error "ngrok not found in PATH. Install from https://ngrok.com/download"
}

$userConfigs = @(
  (Join-Path $env:LOCALAPPDATA "ngrok\ngrok.yml"),
  (Join-Path $env:USERPROFILE ".ngrok2\ngrok.yml"),
  (Join-Path $env:APPDATA "ngrok\ngrok.yml")
)
$userConfig = $userConfigs | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $userConfig) {
  Write-Host "User ngrok.yml not found. Run once:"
  Write-Host "  ngrok config add-authtoken YOUR_TOKEN_FROM_dashboard.ngrok.com"
  Write-Host ""
}

if (-not $NoKill) {
  $procs = Get-Process -Name ngrok -ErrorAction SilentlyContinue
  if ($procs) {
    Write-Host "Stopping existing ngrok processes..."
    $procs | Stop-Process -Force
    Start-Sleep -Seconds 2
  }
}

$ngrokArgs = @("start")
if ($userConfig) {
  $ngrokArgs += @("--config", $userConfig)
}
$ngrokArgs += @("--config", $RingooConfig)

if ($UseV2) {
  if ($Dual) {
    $ngrokArgs += @("ringoo-frontend", "ringoo-backend")
  } else {
    $ngrokArgs += @("ringoo-frontend")
  }
} else {
  # ngrok v3 (ngrok.ringoo.yml с endpoints:) — имя endpoint, не --all
  $ngrokArgs += @("ringoo-frontend")
}

Write-Host "Command: ngrok $($ngrokArgs -join ' ')"
Write-Host "Ringoo config: $RingooConfig"
Write-Host ""

$null = Start-Process -FilePath "ngrok" -ArgumentList $ngrokArgs -PassThru -WindowStyle Normal

if (-not $NoSync) {
  Write-Host "Waiting for ngrok agent (5s)..."
  Start-Sleep -Seconds 5
  Write-Host "Syncing env from ngrok API (up to 90s)..."
  try {
    & (Join-Path $PSScriptRoot "sync-ngrok-env.ps1") -RepoRoot $RepoRoot -MaxWaitSeconds 90 -RingooConfig $RingooConfig
  } catch {
    Write-Warning $_.Exception.Message
    Write-Warning "Ngrok is running but sync failed. When ready, run: scripts\ngrok\sync-ngrok-env.ps1"
  }
}

Write-Host ""
Write-Host "ngrok dashboard: http://127.0.0.1:4040"
Write-Host "Stop: Ctrl+C in ngrok window, or taskkill /IM ngrok.exe /F"
Write-Host "Docker (ngrok = production, BOTH compose files):"
Write-Host "  scripts\ngrok\up-docker.cmd"
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d --build --force-recreate frontend web"
