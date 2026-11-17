"""
Импорт каталога из XML-выгрузки 1С или из HTTP API.

По умолчанию — dry-run без записи в БД; сохраняет plan_id.
APPLY только с --apply --plan-id --i-understand-apply (D.2.1).

snapshot_policy по умолчанию present_only (отсутствие в XML ≠ ноль).
full_snapshot только с --full-snapshot и --i-understand-full-snapshot.

APPLY всегда идёт через integrations.onec.catalog_sync.run_catalog_import
(общий Redis/cache lock + SyncLog) — CLI не обходит блокировку Celery/Admin.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Планирует (dry-run) или применяет сохранённый plan_id импорта "
        "категорий/товаров/остатков. По умолчанию ничего не пишет в БД. "
        "Default snapshot_policy=present_only. Apply использует тот же lock, что Admin и Celery."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--folders",
            default="",
            help="Путь к XML с папками (Иерархия Папок.xml). Не нужен с --from-api / --plan-id.",
        )
        parser.add_argument(
            "--products",
            default="",
            help="Путь к XML с товарами (Товары.xml). Не нужен с --from-api / --plan-id.",
        )
        parser.add_argument(
            "--from-api",
            action="store_true",
            help=(
                "Загрузить XML через GET CatalogFolders/folders и "
                "CatalogProducts/products. Требует ONE_C_API_ENABLED и учётные данные. "
                "Только для dry-run."
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
            help="Записать изменения в БД по --plan-id. Без флага — только dry-run.",
        )
        parser.add_argument(
            "--plan-id",
            default="",
            help="UUID сохранённого DRY-RUN плана. Обязателен для --apply.",
        )
        parser.add_argument(
            "--i-understand-apply",
            action="store_true",
            help="Обязательное подтверждение для --apply.",
        )
        parser.add_argument(
            "--full-snapshot",
            action="store_true",
            help=(
                "Явный выбор full_snapshot при dry-run: отсутствующие в XML остатки "
                "на confirmed складах планируются к обнулению. "
                "Требует --i-understand-full-snapshot."
            ),
        )
        parser.add_argument(
            "--i-understand-full-snapshot",
            action="store_true",
            help="Обязательное подтверждение для --full-snapshot.",
        )

    def handle(self, *args, **options):
        from integrations.onec.catalog_sync import run_catalog_import
        from integrations.onec.client import OneCClientError
        from integrations.onec.importer import SnapshotPolicy
        from integrations.onec.parser import OneCParseError

        apply = bool(options["apply"])
        from_api = bool(options["from_api"])
        full_snapshot = bool(options["full_snapshot"])
        ack_full = bool(options["i_understand_full_snapshot"])
        plan_id = (options.get("plan_id") or "").strip()

        if full_snapshot and not ack_full:
            raise CommandError(
                "Для full_snapshot укажите одновременно --full-snapshot "
                "и --i-understand-full-snapshot. Без подтверждения "
                "используется present_only (отсутствие в XML не обнуляет остатки)."
            )
        if ack_full and not full_snapshot:
            raise CommandError(
                "Флаг --i-understand-full-snapshot без --full-snapshot не включает "
                "полный снимок. Укажите оба флага или уберите подтверждение."
            )
        if apply and not options["i_understand_apply"]:
            raise CommandError(
                "Для записи в БД укажите одновременно --apply и --i-understand-apply. "
                "Сначала выполните dry-run и проверьте plan_id в JSON-отчёте."
            )
        if apply and not plan_id:
            raise CommandError(
                "APPLY требует --plan-id сохранённого DRY-RUN. "
                "Нельзя применить новый план, пересобранный из XML/API."
            )
        if apply and (from_api or options["folders"] or options["products"]):
            raise CommandError(
                "APPLY с --plan-id не принимает --from-api/--folders/--products. "
                "Источник данных — сохранённый план."
            )
        if apply and full_snapshot and not (ack_full and options["i_understand_apply"]):
            raise CommandError(
                "APPLY full_snapshot требует подтверждения: "
                "--full-snapshot --i-understand-full-snapshot "
                "--apply --i-understand-apply --plan-id ..."
            )

        # D.2.3: ack на APPLY не наследуется от dry-run; только явные флаги сессии.
        full_snapshot_acknowledged = bool(apply and full_snapshot and ack_full)

        snapshot_policy = (
            SnapshotPolicy.FULL_SNAPSHOT.value
            if full_snapshot
            else SnapshotPolicy.PRESENT_ONLY.value
        )

        folders = (options["folders"] or "").strip()
        products = (options["products"] or "").strip()
        if not apply and not from_api:
            if not folders or not Path(folders).is_file():
                raise CommandError(
                    "Укажите существующие --folders и --products или используйте --from-api"
                )
            if not products or not Path(products).is_file():
                raise CommandError(f"Файл товаров не найден: {products}")

        self.stdout.write(
            f"Режим: {'apply' if apply else 'dry_run'} "
            f"(lock={'да' if apply else 'нет'}; SyncLog=да; "
            f"snapshot_policy={snapshot_policy}"
            f"{f'; plan_id={plan_id}' if plan_id else ''})"
        )
        if not apply:
            self.stdout.write(
                f"Источник: {'HTTP API 1С' if from_api else f'{folders} + {products}'}"
            )

        try:
            data = run_catalog_import(
                dry_run=not apply,
                from_api=from_api if not apply else False,
                folders_path=folders if not apply else "",
                products_path=products if not apply else "",
                snapshot_policy=snapshot_policy if not apply else None,
                plan_id=plan_id if apply else None,
                full_snapshot_acknowledged=full_snapshot_acknowledged,
            )
        except OneCClientError as exc:
            raise CommandError(f"Ошибка HTTP 1С: {exc}") from exc
        except OneCParseError as exc:
            raise CommandError(f"XML не принят, БД не изменена: {exc}") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
        except PermissionError as exc:
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
        if data.get("plan_id"):
            self.stdout.write(self.style.SUCCESS(f"plan_id: {data.get('plan_id')}"))
            self.stdout.write(f"plan_checksum: {data.get('plan_checksum')}")
            self.stdout.write(f"plan_expires_at: {data.get('plan_expires_at')}")
        self.stdout.write(
            f"records_received: {data.get('records_received')} "
            f"stocks_upserted: {data.get('stocks_upserted')} "
            f"errors: {data.get('errors_count')}"
        )
        if summary:
            self.stdout.write(
                "plan: "
                f"snapshot_policy={summary.get('snapshot_policy', snapshot_policy)} "
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
            self.stdout.write(
                self.style.SUCCESS(
                    f"Применено: run_id={data.get('run_id')} plan_id={plan_id}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run завершён. База не изменена. "
                    "Для записи: --apply --plan-id <uuid> --i-understand-apply. "
                    "Для full_snapshot dry-run дополнительно: "
                    "--full-snapshot --i-understand-full-snapshot"
                )
            )
