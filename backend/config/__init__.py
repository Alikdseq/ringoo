# Celery нужен воркерам. На Vercel пакета нет — сайт должен стартовать без него.
try:
    from .celery import app as celery_app
except ImportError:
    celery_app = None

__all__ = ("celery_app",)
