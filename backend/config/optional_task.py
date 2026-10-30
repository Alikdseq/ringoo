"""Декоратор задачи: настоящий Celery, если пакет установлен, иначе вызов сразу."""

from __future__ import annotations

import threading

try:
    from celery import shared_task as _celery_shared_task

    CELERY_AVAILABLE = True
except ImportError:  # Vercel: Celery не входит в функцию
    _celery_shared_task = None
    CELERY_AVAILABLE = False


_stub_depth = threading.local()


def is_celery_available() -> bool:
    return bool(CELERY_AVAILABLE)


if CELERY_AVAILABLE:

    def shared_task(func=None, **kwargs):
        return _celery_shared_task(func, **kwargs) if func is not None else _celery_shared_task(**kwargs)

else:

    def shared_task(func=None, **_kwargs):
        def decorate(fn):
            def delay(*args, **kwargs):
                depth = getattr(_stub_depth, "n", 0)
                if depth >= 1:
                    # Запрет синхронной рекурсии .delay() → .delay()
                    raise RuntimeError(
                        "optional_task stub: nested delay() forbidden "
                        "(no recursive retries in sync mode)"
                    )
                _stub_depth.n = depth + 1
                try:
                    return fn(*args, **kwargs)
                finally:
                    _stub_depth.n = depth

            def apply_async(args=None, kwargs=None, **_kw):
                return delay(*(args or ()), **(kwargs or {}))

            fn.delay = delay
            fn.apply_async = apply_async
            return fn

        if callable(func):
            return decorate(func)
        return decorate
