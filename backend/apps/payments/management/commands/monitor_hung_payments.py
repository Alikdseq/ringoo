"""Мониторинг зависших и needs_review платежей (без вызова банка)."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.payments.services import find_hung_payments


class Command(BaseCommand):
    help = (
        "Вывести снимок pending старше N минут и платежей needs_review. "
        "Exit code 1, если есть needs_review или pending (удобно для cron/алертов)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pending-minutes",
            type=int,
            default=30,
            help="Порог «зависшего» pending (минуты)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Вывод в JSON",
        )
        parser.add_argument(
            "--fail-on-findings",
            action="store_true",
            help="Exit 1 при наличии pending или needs_review",
        )

    def handle(self, *args, **options):
        snapshot = find_hung_payments(pending_minutes=options["pending_minutes"])
        if options["json"]:
            self.stdout.write(json.dumps(snapshot, default=str, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(
                f"pending>{options['pending_minutes']}m: {snapshot['pending_count']}; "
                f"needs_review: {snapshot['needs_review_count']}"
            )
            for row in snapshot["needs_review"][:20]:
                self.stdout.write(
                    f"  REVIEW {row['id']} order={row['order_id']} "
                    f"{row.get('error_message', '')[:80]}"
                )
            for row in snapshot["pending"][:20]:
                self.stdout.write(
                    f"  PENDING {row['id']} status={row['status']} "
                    f"sber={row.get('sber_order_id')}"
                )

        if options["fail_on_findings"] and (
            snapshot["pending_count"] or snapshot["needs_review_count"]
        ):
            raise SystemExit(1)
