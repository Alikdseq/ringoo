# Full ngrok demo: Docker production frontend FIRST, then ngrok (avoids 503 while building).
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $RepoRoot

Write-Host "=== Ringoo ngrok demo ===" -ForegroundColor Cyan
Write-Host ""

# 1) Env for same-origin API (no need for ngrok yet)
if (Get-Process -Name ngrok -ErrorAction SilentlyContinue) {
  Write-Host "Stopping old ngrok..."
  Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
  Start-Sleep -Seconds 1
}

# Pre-fill env if 4040 not ready yet
$fe = "https://demanding-most-caramel.ngrok-free.dev"
$frontendEnv = Join-Path $RepoRoot "frontend\.env.local"
function Set-Line($f,$k,$v) {
  $lines = if (Test-Path $f) { Get-Content $f -Encoding UTF8 } else { @() }
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($k))\s*=") { $found = $true; "$k=$v" } else { $line }
  }
  if (-not $found) { $out += "$k=$v" }
  Set-Content $f $out -Encoding UTF8
}
Set-Line $frontendEnv "NEXT_PUBLIC_SITE_URL" $fe
Set-Line $frontendEnv "NEXT_PUBLIC_APP_URL" $fe
Set-Line $frontendEnv "NEXT_PUBLIC_API_URL" $fe
Set-Line $frontendEnv "NEXT_PUBLIC_API_V1_URL" "$fe/api/v1"
Set-Line (Join-Path $RepoRoot ".env") "NEXT_PUBLIC_SITE_URL" $fe
Set-Line (Join-Path $RepoRoot ".env") "NEXT_PUBLIC_API_V1_URL" "$fe/api/v1"
Set-Line (Join-Path $RepoRoot ".env") "RINGOO_NGROK_DEMO" "1"
Set-Line (Join-Path $RepoRoot ".env") "RINGOO_DISABLE_HMR" "1"

Write-Host "=== Step 1/3: Docker build + start (~3-8 min first time). Do NOT open ngrok URL yet. ===" -ForegroundColor Yellow
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d --build web frontend

Write-Host "Seeding demo promotions..."
docker compose exec -T web python manage.py seed_demo_promotions 2>&1 | Out-Host

Write-Host "Waiting for http://127.0.0.1:3000 ..."
$ok = $false
foreach ($i in 1..90) {
  Start-Sleep -Seconds 5
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:3000/api/v1/products/categories/" -UseBasicParsing -TimeoutSec 15
    if ($r.StatusCode -eq 200 -and $r.Content -match 'results|"count"') {
      $ok = $true
      Write-Host "Frontend + API proxy OK (attempt $i)" -ForegroundColor Green
      break
    }
  } catch {
    Write-Host "  ... building/starting ($($i * 5)s)"
  }
}

if (-not $ok) {
  Write-Host "Frontend not ready. Logs: docker compose logs -f frontend" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "=== Step 2/3: Start ngrok (only when site is ready) ===" -ForegroundColor Cyan
$null = Start-Process -FilePath "ngrok" -ArgumentList @(
  "start", "--config", "$env:LOCALAPPDATA\ngrok\ngrok.yml",
  "--config", (Join-Path $RepoRoot "scripts\ngrok\ngrok.ringoo.yml"),
  "--all"
) -PassThru -WindowStyle Normal

Start-Sleep -Seconds 3
& (Join-Path $PSScriptRoot "sync-ngrok-env.ps1") -RepoRoot $RepoRoot -MaxWaitSeconds 30

Write-Host ""
Write-Host "=== Step 3/3: Done ===" -ForegroundColor Green
Write-Host "Client link: $fe"
Write-Host ""
Write-Host "503 from ngrok means you opened the link BEFORE step 1 finished."
Write-Host "If 503 now: wait 30s and hard-refresh (Ctrl+Shift+R)."
