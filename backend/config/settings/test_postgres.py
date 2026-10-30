"""
PostgreSQL test settings for concurrency proofs.

Usage (НЕ production):

  set RINGOO_TEST_POSTGRES=1
  set DATABASE_URL=postgres://USER:PASS@127.0.0.1:5432/ringoo_test
  set DJANGO_SETTINGS_MODULE=config.settings.test_postgres
  pytest tests/test_concurrency_postgres.py -q --no-cov

Требует пустую/тестовую БД с правами CREATE. Миграции применяются.
"""

from __future__ import annotations

import os
import urllib.parse

from django.core.exceptions import ImproperlyConfigured

from .test import *  # noqa: F403

# Override in-memory SQLite from test.py
_database_url = os.getenv("DATABASE_URL", "").strip()
if not _database_url:
    raise ImproperlyConfigured(
        "config.settings.test_postgres requires DATABASE_URL "
        "(postgres://.../ringoo_test). Do not point at production."
    )

_parsed = urllib.parse.urlparse(_database_url)
if _parsed.scheme not in ("postgres", "postgresql"):
    raise ImproperlyConfigured("DATABASE_URL must be postgres/postgresql for concurrency tests")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _parsed.path.lstrip("/"),
        "USER": urllib.parse.unquote(_parsed.username or ""),
        "PASSWORD": urllib.parse.unquote(_parsed.password or ""),
        "HOST": _parsed.hostname or "127.0.0.1",
        "PORT": str(_parsed.port or 5432),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 10},
        "TEST": {
            "NAME": os.getenv(
                "RINGOO_TEST_POSTGRES_NAME",
                f"{_parsed.path.lstrip('/')}_pytest",
            ),
        },
    }
}

# Нужны реальные миграции для constraints (unique paid-per-order и т.д.)
MIGRATION_MODULES = {}
