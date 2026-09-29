# Pull base images with retries (TLS timeout to Docker Hub).
param(
  [int]$MaxAttempts = 5,
  [int]$DelaySeconds = 15
)

$ErrorActionPreference = "Continue"
$images = @(
  "node:20-bookworm-slim",
  "python:3.11-slim-bookworm"
)

Write-Host "=== Pull base images (max $MaxAttempts attempts each) ===" -ForegroundColor Cyan

$failed = @()
foreach ($img in $images) {
  $ok = $false
  for ($i = 1; $i -le $MaxAttempts; $i++) {
    Write-Host "[$i/$MaxAttempts] docker pull $img"
    docker pull $img 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
      $ok = $true
      Write-Host "OK: $img" -ForegroundColor Green
      break
    }
    if ($i -lt $MaxAttempts) {
      Write-Host "Retry in ${DelaySeconds}s..." -ForegroundColor Yellow
      Start-Sleep -Seconds $DelaySeconds
    }
  }
  if (-not $ok) { $failed += $img }
}

if ($failed.Count -gt 0) {
  Write-Host ""
  Write-Host "Failed to pull:" -ForegroundColor Red
  $failed | ForEach-Object { Write-Host "  $_" }
  Write-Host ""
  Write-Host "Tips:" -ForegroundColor Yellow
  Write-Host "  - VPN or stable network, then run this script again"
  Write-Host "  - Docker Desktop -> Docker Engine -> registry-mirrors (scripts/docker/registry-mirror.example.json)"
  Write-Host "  - If ringoo images exist: compose-ngrok-up.ps1 -SkipPull"
  exit 1
}

Write-Host "All base images ready." -ForegroundColor Green
exit 0
