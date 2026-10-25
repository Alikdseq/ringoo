"""
Преflight staging для Сбер ecom без вызова шлюза и без вывода секретов.
"""

from __future__ import annotations

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.urls import reverse

from integrations.sber.client import SberEcomClient, _is_production_sber_base


class Command(BaseCommand):
    help = (
        "Проверить готовность staging к тесту Сбера (миграции, env, URL, Celery). "
        "Секреты не печатает. Exit 1 при критичных пробелах."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-enabled",
            action="store_true",
            help="Требовать SBER_ECOM_ENABLED=true (для дня реального теста)",
        )
        parser.add_argument(
            "--require-credentials",
            action="store_true",
            help="Требовать наличие username/password (факт наличия, не значения)",
        )

    def handle(self, *args, **options):
        errors: list[str] = []
        warnings: list[str] = []
        ok: list[str] = []

        # App + migration table
        if not apps.is_installed("apps.payments"):
            errors.append("apps.payments не в INSTALLED_APPS")
        else:
            ok.append("apps.payments установлен")

        try:
            Payment = apps.get_model("payments", "Payment")
            table = Payment._meta.db_table
            connection.ensure_connection()
            tables = connection.introspection.table_names()
            if table in tables:
                ok.append(f"таблица {table} существует")
            else:
                errors.append(
                    f"таблица {table} отсутствует — выполните: "
                    "python manage.py migrate payments"
                )
        except Exception as exc:  # noqa: BLE001
            # Локально без Docker host `db` часто недоступен — не путать с staging
            warnings.append(
                f"БД недоступна для проверки таблицы Payment ({exc}). "
                "На staging выполните migrate и повторите check."
            )

        enabled = bool(getattr(settings, "SBER_ECOM_ENABLED", False))
        base = str(getattr(settings, "SBER_ECOM_BASE_URL", "") or "")
        allow_prod = bool(getattr(settings, "SBER_ECOM_ALLOW_PRODUCTION", False))
        callback = str(getattr(settings, "SBER_ECOM_CALLBACK_URL", "") or "").strip()
        frontend = str(getattr(settings, "FRONTEND_URL", "") or "").strip()
        username = str(getattr(settings, "SBER_ECOM_USERNAME", "") or "").strip()
        password = str(getattr(settings, "SBER_ECOM_PASSWORD", "") or "").strip()

        if enabled:
            ok.append("SBER_ECOM_ENABLED=true")
        else:
            msg = "SBER_ECOM_ENABLED выключен (норма до дня теста)"
            if options["require_enabled"]:
                errors.append("SBER_ECOM_ENABLED должен быть true")
            else:
                warnings.append(msg)

        if _is_production_sber_base(base):
            if allow_prod:
                warnings.append(
                    "SBER_ECOM_BASE_URL указывает на боевой epay + ALLOW_PRODUCTION"
                )
            else:
                errors.append(
                    "SBER_ECOM_BASE_URL=epay без SBER_ECOM_ALLOW_PRODUCTION — "
                    "клиент откажет; для staging нужен ecomtest"
                )
        else:
            if "ecomtest.sberbank.ru" in base.lower() or not base:
                ok.append(f"BASE_URL тест: {base or '(default ecomtest)'}")
            else:
                warnings.append(f"нестандартный SBER_ECOM_BASE_URL={base}")

        if allow_prod and not _is_production_sber_base(base):
            warnings.append(
                "SBER_ECOM_ALLOW_PRODUCTION=true при тестовом BASE_URL (лишнее)"
            )

        if callback.startswith("https://"):
            ok.append("SBER_ECOM_CALLBACK_URL задан (https)")
            if "payments/sber/callback" not in callback:
                warnings.append(
                    "callback URL не содержит /payments/sber/callback/ — проверьте путь"
                )
        elif callback:
            errors.append("SBER_ECOM_CALLBACK_URL должен быть https://…")
        else:
            warnings.append(
                "SBER_ECOM_CALLBACK_URL пуст — dynamicCallbackUrl не уйдёт; "
                "нужен публичный HTTPS перед реальным тестом"
            )

        if frontend.startswith("http://localhost") or frontend.startswith(
            "http://127."
        ):
            warnings.append(
                "FRONTEND_URL локальный — return/fail URL не достучатся с ПШ Сбера "
                "без публичного HTTPS фронта или явных SBER_ECOM_RETURN/FAIL_URL"
            )
        elif frontend.startswith("https://"):
            ok.append("FRONTEND_URL https")
        elif frontend:
            warnings.append(f"FRONTEND_URL={frontend} — предпочтителен https")
        else:
            errors.append("FRONTEND_URL пуст")

        if username and password:
            ok.append("учётные данные Сбера заданы (значения скрыты)")
        elif options["require_credentials"]:
            errors.append("нет SBER_ECOM_USERNAME и/или SBER_ECOM_PASSWORD")
        else:
            warnings.append("учётные данные Сбера ещё не заданы")

        beat = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}
        for key in ("expire-unpaid-online-orders", "reconcile-open-payments"):
            if key in beat:
                ok.append(f"CELERY_BEAT_SCHEDULE[{key}]")
            else:
                errors.append(f"нет задачи beat: {key}")

        try:
            from uuid import UUID

            sample_pk = UUID("00000000-0000-0000-0000-000000000000")
            pay_path = None
            for name in (
                "api_v1:orders:order-pay",
                "orders:order-pay",
                "order-pay",
            ):
                try:
                    pay_path = reverse(name, kwargs={"pk": sample_pk})
                    break
                except Exception:  # noqa: BLE001
                    continue
            if pay_path:
                ok.append(f"маршрут pay: {pay_path}")
            else:
                warnings.append("не удалось reverse order-pay")

            cb_path = None
            for name in (
                "api_v1:payments:sber-callback",
                "payments:sber-callback",
                "sber-callback",
            ):
                try:
                    cb_path = reverse(name)
                    break
                except Exception:  # noqa: BLE001
                    continue
            if cb_path:
                ok.append(f"маршрут callback: {cb_path}")
            else:
                warnings.append("не удалось reverse sber-callback")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"проверка URL: {exc}")

        # Клиент не падает на default test URL
        try:
            client = SberEcomClient(
                enabled=False,
                base_url=base or "https://ecomtest.sberbank.ru",
                allow_production=allow_prod,
            )
            ok.append(f"SberEcomClient init OK (enabled={client.enabled})")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"SberEcomClient: {exc}")

        self.stdout.write("=== check_sber_staging ===")
        for line in ok:
            self.stdout.write(self.style.SUCCESS(f"OK  {line}"))
        for line in warnings:
            self.stdout.write(self.style.WARNING(f"WARN {line}"))
        for line in errors:
            self.stdout.write(self.style.ERROR(f"ERR  {line}"))

        if errors:
            raise CommandError(
                f"Staging не готов: {len(errors)} ошибок, {len(warnings)} предупреждений"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Критических ошибок нет ({len(warnings)} предупреждений). "
                "Реальный шлюз не вызывался."
            )
        )
