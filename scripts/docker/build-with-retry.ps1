# docker compose build с повторами при TLS timeout.
param(
  [string[]]$Services = @("frontend", "web"),
  [int]$MaxAttempts = 3,
  [int]$DelaySeconds = 20,
  [switch]$Ngrok
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $RepoRoot

$compose = @("compose", "-f", "docker-compose.yml")
if ($Ngrok) { $compose += @("-f", "docker-compose.ngrok.yml") }

Write-Host "=== docker compose build (Ngrok=$Ngrok) ===" -ForegroundColor Cyan

for ($i = 1; $i -le $MaxAttempts; $i++) {
  Write-Host "Attempt $i of $MaxAttempts - docker $($compose -join ' ') build $($Services -join ' ')"
  docker @compose build @Services 2>&1 | Out-Host
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Build OK." -ForegroundColor Green
    exit 0
  }
  if ($i -lt $MaxAttempts) {
    Write-Host "Build failed. Retry in ${DelaySeconds}s..." -ForegroundColor Yellow
    Start-Sleep -Seconds $DelaySeconds
  }
}

Write-Host "Build failed after $MaxAttempts attempts." -ForegroundColor Red
Write-Host "Try: scripts\docker\pull-base-images.ps1"
Write-Host "Or set RINGOO_USE_PIP_ONLY=1 in .env if backend deps fail"
exit 1
