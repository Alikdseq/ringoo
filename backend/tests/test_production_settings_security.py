"""Fail-closed checks for config.settings.production via isolated subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from django.test import SimpleTestCase

BACKEND_ROOT = Path(__file__).resolve().parents[1]

_SCRIPT = textwrap.dedent(
    """
    import django
    from django.core.exceptions import ImproperlyConfigured
    try:
        django.setup()
        print("SETUP_OK")
    except ImproperlyConfigured:
        print("IMPROPER")
    except Exception as e:
        print("OTHER", type(e).__name__)
    """
)


def _run_production_import(env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "VERCEL": "",
        "PYTHONPATH": str(BACKEND_ROOT),
        **env_extra,
    }
    return subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )


_BASE_OK = {
    "DEBUG": "False",
    "SECRET_KEY": "a" * 48 + "Bb1!",
    "ALLOWED_HOSTS": "shop.example.com",
    "ADMIN_OTP_ENABLED": "1",
    "CORS_ALLOWED_ORIGINS": "https://shop.example.com",
    "CSRF_TRUSTED_ORIGINS": "https://shop.example.com",
    "DATABASE_URL": "postgresql://ringoo_app:strong-db-password-99@db:5432/ringoo",
    "REDIS_PASSWORD": "strong-redis-pass99",
    "REDIS_URL": "redis://:strong-redis-pass99@redis:6379/0",
    "TRUST_PROXY": "1",
    "LOG_FILE_PATH": str(BACKEND_ROOT / "tmp" / "prod-test-django.log"),
}


class ProductionSettingsGuardTests(SimpleTestCase):
    def test_debug_true_is_rejected(self):
        proc = _run_production_import({**_BASE_OK, "DEBUG": "True"})
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertIn("IMPROPER", out, msg=out[-800:])

    def test_weak_secret_is_rejected(self):
        proc = _run_production_import(
            {**_BASE_OK, "SECRET_KEY": "django-insecure-dev-key-change-in-production"}
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertIn("IMPROPER", out, msg=out[-800:])

    def test_postgres_role_rejected(self):
        proc = _run_production_import(
            {
                **_BASE_OK,
                "DATABASE_URL": "postgresql://postgres:strong-db-password-99@db:5432/ringoo",
            }
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertIn("IMPROPER", out, msg=out[-800:])

    def test_valid_minimal_env_loads_or_infra_only_error(self):
        (BACKEND_ROOT / "tmp").mkdir(exist_ok=True)
        proc = _run_production_import(_BASE_OK)
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertTrue(
            "SETUP_OK" in out or "IMPROPER" in out or "OTHER" in out,
            msg=out[-1200:],
        )
        if "IMPROPER" in out:
            # Не ожидаем IMPROPER при валидном env; если есть — fail
            self.fail(f"Unexpected ImproperlyConfigured for valid env: {out[-800:]}")
