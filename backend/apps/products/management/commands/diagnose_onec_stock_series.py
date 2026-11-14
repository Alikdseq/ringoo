"""
Диагностика остатков 1С: stale blank-series и reserved > quantity.
Только отчёт — без удаления, без сетевых запросов к 1С.
"""

from django.core.management.base import BaseCommand

from integrations.onec.importer import (
    diagnose_reserved_over_quantity,
    diagnose_stale_blank_series_stocks,
)


class Command(BaseCommand):
    help = (
        "Показать подозрительные Stock: пустой seriesId рядом с сериями "
        "и reserved_quantity > quantity (без автоисправления)."
    )

    def handle(self, *args, **options):
        stale = diagnose_stale_blank_series_stocks()
        self.stdout.write(
            self.style.NOTICE(
                f"[blank+serial] подозрительных строк: {stale['suspect_count']} "
                f"({stale['action']})"
            )
        )
        for row in stale["suspects"][:100]:
            self.stdout.write(
                f"- product={row['product_onec_code'] or row['product_id']} "
                f"store={row['store_slug']} qty={row['quantity']} "
                f"reserved={row['reserved_quantity']}"
            )
        if stale["suspect_count"] > 100:
            self.stdout.write(f"... и ещё {stale['suspect_count'] - 100}")
        self.stdout.write(stale["message"])

        over = diagnose_reserved_over_quantity()
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                f"[reserved>qty] аномалий: {over['anomaly_count']} "
                f"({over['action']})"
            )
        )
        for row in over["anomalies"][:100]:
            self.stdout.write(
                f"- product={row['product_onec_code'] or row['product_id']} "
                f"store={row['store_slug']} series={row['onec_series_id']!r} "
                f"qty={row['quantity']} reserved={row['reserved_quantity']} "
                f"deficit={row['deficit']}"
            )
        if over["anomaly_count"] > 100:
            self.stdout.write(f"... и ещё {over['anomaly_count'] - 100}")
        self.stdout.write(over["message"])
