"""Сборка Django на Vercel: миграции, если подключена внешняя Postgres."""

import os
import subprocess
import sys


def main() -> int:
    url = os.environ.get("DATABASE_URL", "").strip()
    host = os.environ.get("DB_HOST", "").strip()
    has_db = bool(url) or (host and host not in {"db", "localhost", "127.0.0.1"})
    if not has_db:
        print(
            "DATABASE_URL is not set. Skipping migrate. "
            "Add Vercel Postgres to the project and redeploy."
        )
        return 0
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
    return subprocess.call([sys.executable, "manage.py", "migrate", "--noinput"], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
