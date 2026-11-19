"""
Dry-run витринной классификации (S1.2.5).

  python manage.py storefront_dry_run
  python manage.py storefront_dry_run --output /tmp/report.json --pretty
  python manage.py storefront_dry_run --summary-only
  python manage.py storefront_dry_run --limit 100

READ-ONLY относительно БД: не создаёт Run/Event/Assignment/Queue.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.storefront_taxonomy.services.dry_run import (
    DryRunError,
    format_summary_text,
    run_storefront_dry_run,
)
from apps.storefront_taxonomy.services.report import (
    ReportSerializationError,
    dump_dry_run_report,
    serialize_dry_run_report,
)


class Command(BaseCommand):
    help = (
        "Dry-run классификации storefront taxonomy по актуальной БД "
        "(без записи результатов)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Путь для сохранения JSON-отчёта (обязателен для файла).",
        )
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="Форматированный JSON (indent=2).",
        )
        parser.add_argument(
            "--summary-only",
            action="store_true",
            help="Вывести только текстовую сводку (без полного JSON в stdout).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Ограничить число товаров (только диагностика/тесты).",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        output = options.get("output")
        pretty = bool(options.get("pretty"))
        summary_only = bool(options.get("summary_only"))

        try:
            report = run_storefront_dry_run(limit=limit)
        except DryRunError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(
                f"Неожиданная ошибка Dry-run: {type(exc).__name__}: {exc}"
            ) from exc

        self.stdout.write(format_summary_text(report))
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDry-run завершён за {report['summary']['execution_time_ms']} ms"
            )
        )

        if output:
            try:
                path = dump_dry_run_report(report, output, pretty=pretty or True)
            except ReportSerializationError as exc:
                raise CommandError(f"Ошибка сериализации отчёта: {exc}") from exc
            except OSError as exc:
                raise CommandError(f"Не удалось записать отчёт: {exc}") from exc
            self.stdout.write(self.style.SUCCESS(f"Отчёт сохранён: {path}"))
            return

        if summary_only:
            return

        # Без --output и без --summary-only: полный JSON в stdout после сводки.
        try:
            payload = serialize_dry_run_report(report, pretty=pretty)
        except ReportSerializationError as exc:
            raise CommandError(f"Ошибка сериализации отчёта: {exc}") from exc
        self.stdout.write("\n--- JSON report ---\n")
        self.stdout.write(payload)
