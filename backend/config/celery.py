"""
Celery configuration for Ringoo project.
"""

import os
from celery import Celery, Task

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')


class RingooTask(Task):
    """
    Базовый класс задач: экспоненциальный backoff при сетевых сбоях брокера/бэкенда и т.п.
    Не подменяет логику конкретных задач (SMTP внутри функций — по-прежнему локально).
    """

    abstract = True
    autoretry_for = (
        ConnectionError,
        OSError,
        TimeoutError,
        BrokenPipeError,
    )
    retry_kwargs = {"max_retries": 5}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


app = Celery('ringoo', task_cls=RingooTask)

# Load task modules from all registered Django apps
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
