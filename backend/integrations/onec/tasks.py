"""
Совместимость: задачи живут в apps.orders.tasks (Celery autodiscover по INSTALLED_APPS).
"""

from apps.orders.tasks import (  # noqa: F401
    cancel_order_in_onec_task,
    enqueue_order_cancel,
    enqueue_order_sync,
    sync_order_to_onec_task,
)
