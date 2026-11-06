"""
Health check endpoint for monitoring.
"""
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger('ringoo.security')


def health_check(request):
    """
    Health check for Docker / load balancers.
    Does not expose exception text to clients (SEC remediation).
    """
    health_status = {
        'status': 'healthy',
        'database': 'ok',
        'cache': 'ok',
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception('health_check database failure')
        health_status['database'] = 'error'
        health_status['status'] = 'unhealthy'

    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise RuntimeError('Cache read failed')
    except Exception:
        logger.exception('health_check cache failure')
        health_status['cache'] = 'error'
        health_status['status'] = 'unhealthy'

    # Опциональные ops-метрики (только при OPS_HEALTH_DETAILS=1) — для внутреннего мониторинга.
    if bool(getattr(settings, 'OPS_HEALTH_DETAILS', False)):
        try:
            from datetime import timedelta

            from apps.orders.models import Order
            from apps.payments.models import Payment

            ops = {
                'payments_needs_review': Payment.objects.filter(
                    status=Payment.STATUS_NEEDS_REVIEW
                ).count(),
                'orders_onec_error': Order.objects.filter(
                    onec_sync_status=Order.ONEC_SYNC_ERROR
                ).count(),
                'orders_stale_new_online_30m': Order.objects.filter(
                    payment_type=Order.PAYMENT_ONLINE,
                    status=Order.STATUS_NEW,
                    created_at__lt=timezone.now() - timedelta(minutes=30),
                ).count(),
            }
            try:
                from apps.backups.models import BackupArchive

                latest_backup = (
                    BackupArchive.objects.filter(status=BackupArchive.STATUS_READY)
                    .order_by('-created_at')
                    .first()
                )
                ops['backup_latest_ready_at'] = (
                    latest_backup.created_at.isoformat() if latest_backup else None
                )
                ops['backup_failed_24h'] = BackupArchive.objects.filter(
                    status=BackupArchive.STATUS_FAILED,
                    created_at__gte=timezone.now() - timedelta(hours=24),
                ).count()
            except Exception:
                ops['backup_error'] = True
            health_status['ops'] = ops
        except Exception:
            logger.exception('health_check ops metrics failure')
            health_status['ops'] = {'error': True}

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
