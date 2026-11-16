"""
Импорт каталога из XML-выгрузки 1С или из HTTP API.

По умолчанию — dry-run без записи в БД. Запись только с --apply
и --i-understand-apply. HTTP только при --from-api и ONE_C_API_ENABLED.

APPLY всегда идёт через integrations.onec.catalog_sync.run_catalog_import
(общий Redis/cache lock + SyncLog) — CLI не обходит блокировку Celery/Admin.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Планирует (dry-run) или применяет импорт категорий/товаров/остатков "
        "из XML выгрузки 1С или HTTP API. По умолчанию ничего не пишет в БД. "
        "Apply использует тот же lock, что Admin и Celery."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--folders",
            default="",
            help="Путь к XML с папками (Иерархия Папок.xml). Не нужен с --from-api.",
        )
        parser.add_argument(
            "--products",
            default="",
            help="Путь к XML с товарами (Товары.xml). Не нужен с --from-api.",
        )
        parser.add_argument(
            "--from-api",
            action="store_true",
            help=(
                "Загрузить XML через GET CatalogFolders/folders и "
                "CatalogProducts/products. Требует ONE_C_API_ENABLED и учётные данные."
            ),
        )
        parser.add_argument(
            "--report",
            default="",
            help="Куда сохранить JSON-отчёт (SyncLog serialize)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Записать изменения в БД. Без флага — только dry-run.",
        )
        parser.add_argument(
            "--i-understand-apply",
            action="store_true",
            help="Обязательное подтверждение для --apply.",
        )

    def handle(self, *args, **options):
        from integrations.onec.catalog_sync import run_catalog_import
        from integrations.onec.client import OneCClientError
        from integrations.onec.parser import OneCParseError

        apply = bool(options["apply"])
        from_api = bool(options["from_api"])
        if apply and not options["i_understand_apply"]:
            raise CommandError(
                "Для записи в БД укажите одновременно --apply и --i-understand-apply. "
                "Сначала выполните dry-run и проверьте JSON-отчёт."
            )

        folders = (options["folders"] or "").strip()
        products = (options["products"] or "").strip()
        if not from_api:
            if not folders or not Path(folders).is_file():
                raise CommandError("Укажите существующие --folders и --products или используйте --from-api")
            if not products or not Path(products).is_file():
                raise CommandError(f"Файл товаров не найден: {products}")

        self.stdout.write(f"Режим: {'apply' if apply else 'dry_run'} " f"(lock={'да' if apply else 'нет'}; SyncLog=да)")
        self.stdout.write(f"Источник: {'HTTP API 1С' if from_api else f'{folders} + {products}'}")

        try:
            data = run_catalog_import(
                dry_run=not apply,
                from_api=from_api,
                folders_path=folders,
                products_path=products,
            )
        except OneCClientError as exc:
            raise CommandError(f"Ошибка HTTP 1С: {exc}") from exc
        except OneCParseError as exc:
            raise CommandError(f"XML не принят, БД не изменена: {exc}") from exc
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        report_path = options["report"]
        if not report_path:
            mode = "apply" if apply else "dry_run"
            report_path = str(Path.cwd() / f"onec_import_report_{mode}.json")
        Path(report_path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        summary = data.get("summary") or {}
        self.stdout.write(self.style.NOTICE("— Краткий отчёт —"))
        self.stdout.write(f"run_id: {data.get('run_id')}")
        self.stdout.write(f"status: {data.get('status')}")
        self.stdout.write(
            f"records_received: {data.get('records_received')} "
            f"stocks_upserted: {data.get('stocks_upserted')} "
            f"errors: {data.get('errors_count')}"
        )
        if summary:
            self.stdout.write(
                "plan: "
                f"products_create={summary.get('products_create')} "
                f"products_update={summary.get('products_update')} "
                f"stocks_upsert={summary.get('stocks_upsert')} "
                f"stocks_to_zero={summary.get('stocks_to_zero')} "
                f"apply_allowed={summary.get('apply_allowed')}"
            )
        self.stdout.write(self.style.SUCCESS(f"JSON-отчёт: {report_path}"))

        if data.get("status") == "failed":
            errs = data.get("error_messages") or []
            hint = errs[-1] if errs else "см. SyncLog"
            raise CommandError(f"Импорт завершился со статусом failed: {hint}")

        if apply:
            self.stdout.write(self.style.SUCCESS(f"Применено: run_id={data.get('run_id')}"))
        else:
            self.stdout.write(
                self.style.WARNING("Dry-run завершён. База не изменена. " "Для записи: --apply --i-understand-apply")
            )
