# Ngrok demo: pull bases -> build (retry) -> up. Skip build if images exist.
param(
  [switch]$ForceBuild,
  [switch]$SkipPull,
  [switch]$StartNgrok
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $RepoRoot

$composeArgs = @("-f", "docker-compose.yml", "-f", "docker-compose.ngrok.yml")

function Test-LocalImage([string]$Name) {
  docker image inspect $Name 2>$null | Out-Null
  return $LASTEXITCODE -eq 0
}

$hasFrontend = Test-LocalImage "ringoo-frontend:latest"
$hasWeb = Test-LocalImage "ringoo-web:latest"

if (-not $SkipPull -and (-not $hasFrontend -or -not $hasWeb -or $ForceBuild)) {
  & (Join-Path $PSScriptRoot "pull-base-images.ps1")
  if ($LASTEXITCODE -ne 0) {
    if ($hasFrontend -and $hasWeb) {
      Write-Warning "Base pull failed; using existing ringoo images without rebuild."
    } else {
      exit 1
    }
  }
}

if ($ForceBuild -or -not ($hasFrontend -and $hasWeb)) {
  & (Join-Path $PSScriptRoot "build-with-retry.ps1") -Ngrok -Services @("frontend", "web")
  if ($LASTEXITCODE -ne 0) { exit 1 }
  docker compose @composeArgs up -d frontend web
} else {
  Write-Host "Using existing ringoo-frontend and ringoo-web images. Skip build." -ForegroundColor Green
  docker compose @composeArgs up -d --no-build frontend web
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Frontend may build 3-8 min on first start. Logs: docker logs -f ringoo_frontend" -ForegroundColor Yellow

if ($StartNgrok) {
  & (Join-Path $RepoRoot "scripts\ngrok\start-ringoo.ps1")
  docker compose @composeArgs up -d --force-recreate frontend web
}

Write-Host "Done. Local http://127.0.0.1:3000" -ForegroundColor Green
