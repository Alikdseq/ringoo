"""
Отмена неоплаченных online-заказов старше ONLINE_PAYMENT_TIMEOUT_MINUTES.

Запуск (cron / celery):
  python manage.py expire_unpaid_online_orders
"""

from django.core.management.base import BaseCommand

from apps.payments.services import expire_unpaid_online_orders


class Command(BaseCommand):
    help = "Cancel unpaid online orders past timeout and release stock."

    def handle(self, *args, **options):
        result = expire_unpaid_online_orders()
        self.stdout.write(self.style.SUCCESS(str(result)))
