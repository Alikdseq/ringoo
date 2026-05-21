@echo off
cd /d "%~dp0"
REM Обход UnicodeDecodeError: переменные задаём ДО запуска Python, чтобы libpq не видел путь с кириллицей
set PGCLIENTENCODING=UTF8
set PYTHONUTF8=1
set APPDATA=%~dp0pgconfig
set PGPASSFILE=%~dp0.pgpass
set PGSYSCONFDIR=%~dp0pgconfig
set PGSERVICEFILE=%~dp0pgconfig\pg_service.conf
set TEMP=%~dp0tmp
set TMP=%~dp0tmp
if not exist "%~dp0pgconfig" mkdir "%~dp0pgconfig"
if not exist "%~dp0tmp" mkdir "%~dp0tmp"
python manage.py migrate %*
pause
