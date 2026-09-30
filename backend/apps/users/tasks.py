"""
Celery tasks for users app.
"""

from config.optional_task import shared_task


@shared_task
def test_celery_task():
    """
    Тестовая задача для проверки работы Celery.
    """
    return "Celery is working correctly!"


