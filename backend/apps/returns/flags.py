"""Feature flag для временного отключения API/UI возвратов."""

from __future__ import annotations

from django.conf import settings


def returns_enabled() -> bool:
    """True только при явном RETURNS_ENABLED=1|true|yes."""
    return bool(getattr(settings, "RETURNS_ENABLED", False))
