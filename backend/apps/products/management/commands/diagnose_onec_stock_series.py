"""
Диагностика потенциально устаревших остатков без seriesId.
Только отчёт — без удаления и без сетевых запросов к 1С.
"""

from django.core.management.base import BaseCommand

from integrations.onec.importer import diagnose_stale_blank_series_stocks


class Command(BaseCommand):
    help = (
        "Показать Stock с пустым onec_series_id там, где уже есть серийные "
        "остатки того же товара в магазине (без автоисправления)."
    )

    def handle(self, *args, **options):
        report = diagnose_stale_blank_series_stocks()
        self.stdout.write(
            self.style.NOTICE(
                f"Подозрительных строк: {report['suspect_count']} "
                f"({report['action']})"
            )
        )
        for row in report["suspects"][:100]:
            self.stdout.write(
                f"- product={row['product_onec_code'] or row['product_id']} "
                f"store={row['store_slug']} qty={row['quantity']} "
                f"reserved={row['reserved_quantity']}"
            )
        if report["suspect_count"] > 100:
            self.stdout.write(f"... и ещё {report['suspect_count'] - 100}")
        self.stdout.write(report["message"])
