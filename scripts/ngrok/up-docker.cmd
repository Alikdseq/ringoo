@echo off
REM Ringoo: Docker для ngrok (production Next.js, без HMR). Запускать из cmd.
cd /d "%~dp0..\.."
echo === Ringoo ngrok Docker (production build, no dev/HMR) ===
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d --build --force-recreate frontend web
if errorlevel 1 exit /b 1
echo.
echo Wait for build in logs: docker logs -f ringoo_frontend
echo Must see: "next start" or "Ready" — NOT "next dev"
echo.
echo Then sync env and ngrok:
echo   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ngrok\sync-ngrok-env.ps1
echo   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ngrok\start-ringoo.ps1 -NoSync
echo   docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d --force-recreate frontend web
pause
