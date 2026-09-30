"""Декоратор задачи: настоящий Celery, если пакет установлен, иначе вызов сразу."""

try:
    from celery import shared_task
except ImportError:  # Vercel: Celery не входит в функцию

    def shared_task(func=None, **_kwargs):
        def decorate(fn):
            def delay(*args, **kwargs):
                return fn(*args, **kwargs)

            def apply_async(args=None, kwargs=None, **_kw):
                return fn(*(args or ()), **(kwargs or {}))

            fn.delay = delay
            fn.apply_async = apply_async
            return fn

        if callable(func):
            return decorate(func)
        return decorate
