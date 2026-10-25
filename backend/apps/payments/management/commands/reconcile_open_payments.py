"""Сверка незавершённых платежей с банком (пропущенный callback / сбой сайта)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.payments.services import reconcile_open_payments


class Command(BaseCommand):
    help = (
        "Запросить getOrderStatusExtended для pending/registered платежей "
        "старше N минут и обновить статусы."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-minutes",
            type=int,
            default=2,
            help="Минимальный возраст платежа (минуты), по умолчанию 2",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Максимум платежей за один прогон",
        )

    def handle(self, *args, **options):
        result = reconcile_open_payments(
            older_than_minutes=options["older_than_minutes"],
            limit=options["limit"],
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
