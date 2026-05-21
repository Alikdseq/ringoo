"""
Celery tasks for users app.
"""

from celery import shared_task


@shared_task
def test_celery_task():
    """
    Тестовая задача для проверки работы Celery.
    """
    return "Celery is working correctly!"


