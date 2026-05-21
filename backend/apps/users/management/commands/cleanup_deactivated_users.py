"""
Удаление из БД записей пользователей, уже деактивированных давно (3.1.4, 152-ФЗ — лишние ПДн).

По умолчанию только отчёт (dry run). Реальное удаление: --execute.

Критерий: is_active=False, не staff/superuser, updated_at старше --min-days.
Типичный сценарий — аккаунты после self-service удаления (анонимизация + is_active=False).

Запуск по cron (раз в месяц), например:
  python manage.py cleanup_deactivated_users --min-days=730 --execute
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import CustomUser


class Command(BaseCommand):
    help = (
        "Удалить из БД давно деактивированных обычных пользователей "
        "(без --execute только показывает количество)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-days",
            type=int,
            default=365,
            help="Минимум дней с момента updated_at деактивированного пользователя (по умолчанию 365).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Выполнить удаление (без флага — только dry run).",
        )

    def handle(self, *args, **options):
        days = max(30, int(options["min_days"]))
        execute = options["execute"]
        verbosity = options.get("verbosity", 1)
        cutoff = timezone.now() - timedelta(days=days)

        qs = CustomUser.objects.filter(
            is_active=False,
            is_staff=False,
            is_superuser=False,
            updated_at__lt=cutoff,
        )
        n = qs.count()
        self.stdout.write(
            f"Кандидатов на удаление: {n} (is_active=False, не персонал, updated_at < {cutoff.date()})."
        )
        if n and verbosity >= 1:
            for u in qs[:10]:
                self.stdout.write(f"  … id={u.pk} phone={u.phone!r}")
            if n > 10:
                self.stdout.write(f"  … и ещё {n - 10}")
        if not execute:
            self.stdout.write(
                self.style.WARNING("Dry run. Добавьте --execute для физического удаления.")
            )
            return

        deleted, details = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Удалено объектов (каскадом): {deleted}"))
        if details and verbosity >= 2:
            self.stdout.write(str(details))
