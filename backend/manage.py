#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Фикс UnicodeDecodeError в psycopg2/libpq на Windows при кириллице в путях (C:\Users\Имя\...).
# libpq по умолчанию строит пути через %APPDATA%\postgresql — при декодировании возникает ошибка.
# Перенаправляем все пути libpq в каталог проекта (только ASCII) и подменяем APPDATA.
if sys.platform == "win32":
    backend_dir = Path(__file__).resolve().parent
    pgconfig = backend_dir / "pgconfig"
    tmpdir = backend_dir / "tmp"
    pgconfig.mkdir(parents=True, exist_ok=True)
    tmpdir.mkdir(parents=True, exist_ok=True)
    # Пути только ASCII, прямые слэши (надёжнее для C-кода)
    pgpass_path = (backend_dir / ".pgpass").as_posix()
    pgconfig_path = pgconfig.as_posix()
    tmp_path = tmpdir.as_posix()
    os.environ.setdefault("PGCLIENTENCODING", "UTF8")
    os.environ["PGPASSFILE"] = pgpass_path
    os.environ["PGSYSCONFDIR"] = pgconfig_path
    os.environ["PGSERVICEFILE"] = (pgconfig / "pg_service.conf").as_posix()
    os.environ["TEMP"] = tmp_path
    os.environ["TMP"] = tmp_path
    # Критично: подмена APPDATA, чтобы libpq не строил путь %APPDATA%\postgresql с кириллицей
    os.environ["APPDATA"] = pgconfig_path


def main():
    """Run administrative tasks."""
    # Vercel вызывает manage.py collectstatic без DJANGO_SETTINGS_MODULE.
    # development.py подключает debug_toolbar, его нет в зависимостях деплоя.
    if os.environ.get("VERCEL") == "1":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
