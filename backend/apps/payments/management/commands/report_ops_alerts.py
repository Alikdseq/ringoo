"""
Периодический отчёт по критичным ops-ситуациям (мониторинг / cron).

Пример:
  python manage.py report_ops_alerts
  python manage.py report_ops_alerts --json

Не инициирует платежи и не пишет во внешние системы.
"""

from __future__ import annotations

import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.locks import EXPIRE_LOCK_KEY, RECONCILE_LOCK_KEY


class Command(BaseCommand):
    help = "Report payments needs_review, 1C errors, stale online orders, lock presence"

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="JSON output")
        parser.add_argument(
            "--stale-minutes",
            type=int,
            default=30,
            help="Online NEW older than N minutes",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        stale_minutes = int(options["stale_minutes"])
        cutoff = timezone.now() - timedelta(minutes=stale_minutes)
        backup_failed = 0
        backup_stale = False
        try:
            from apps.backups.models import BackupArchive

            backup_failed = BackupArchive.objects.filter(
                status=BackupArchive.STATUS_FAILED,
                created_at__gte=timezone.now() - timedelta(hours=24),
            ).count()
            stale_h = int(getattr(settings, "BACKUP_STALE_ALERT_HOURS", 48) or 48)
            latest = (
                BackupArchive.objects.filter(status=BackupArchive.STATUS_READY)
                .order_by("-created_at")
                .first()
            )
            if latest is None:
                backup_stale = True
            elif latest.created_at < timezone.now() - timedelta(hours=stale_h):
                backup_stale = True
        except Exception:
            backup_failed = -1

        report = {
            "generated_at": timezone.now().isoformat(),
            "payments_needs_review": Payment.objects.filter(
                status=Payment.STATUS_NEEDS_REVIEW
            ).count(),
            "orders_onec_error": Order.objects.filter(
                onec_sync_status=Order.ONEC_SYNC_ERROR
            ).count(),
            "orders_onec_pending_review": Order.objects.filter(
                onec_sync_status=Order.ONEC_SYNC_PENDING_REVIEW
            ).count(),
            "orders_stale_new_online": Order.objects.filter(
                payment_type=Order.PAYMENT_ONLINE,
                status=Order.STATUS_NEW,
                created_at__lt=cutoff,
            ).count(),
            "expire_lock_held": bool(cache.get(EXPIRE_LOCK_KEY)),
            "reconcile_lock_held": bool(cache.get(RECONCILE_LOCK_KEY)),
            "backup_failed_24h": backup_failed,
            "backup_stale": backup_stale,
        }
        alert = any(
            [
                report["payments_needs_review"] > 0,
                report["orders_onec_error"] > 0,
                report["orders_stale_new_online"] > 0,
                backup_failed > 0,
                backup_stale,
            ]
        )
        report["alert"] = alert

        if options["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for k, v in report.items():
                self.stdout.write(f"{k}: {v}")
            if alert:
                self.stderr.write(self.style.WARNING("OPS_ALERT=1"))
            else:
                self.stdout.write(self.style.SUCCESS("OPS_ALERT=0"))
