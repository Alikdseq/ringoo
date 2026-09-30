"""Сборка Django на Vercel: миграции и витрина из 5 товаров с фото."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
    env["VERCEL"] = "1"
    url = os.environ.get("DATABASE_URL", "").strip()
    host = os.environ.get("DB_HOST", "").strip()
    has_external_db = bool(url) or (host and host not in {"db", "localhost", "127.0.0.1"})
    if not has_external_db:
        env["RINGOO_VERCEL_BUILD"] = "1"
        data_dir = Path(__file__).resolve().parent.parent / "vercel_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        print("DATABASE_URL is not set. Using bundled SQLite catalog for the storefront.")
    else:
        print("Applying migrations to the external database.")

    migrate = subprocess.call([sys.executable, "manage.py", "migrate", "--noinput"], env=env)
    if migrate != 0:
        return migrate
    return subprocess.call(
        [sys.executable, "manage.py", "seed_vercel_showcase"],
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
