"""
Фискализация / онлайн-касса.

Схема не выбрана (через Сбер orderBundle или отдельный провайдер).
После решения владельца/бухгалтера — клиент чеков, модель Receipt, retry.
См. docs/integrations/EXTERNAL_REQUESTS_CHECKLIST.md
"""

from __future__ import annotations

from typing import Any


class FiscalNotConfigured(Exception):
    """Онлайн-касса ещё не выбрана и не настроена."""


def issue_receipt_for_payment(payment: Any) -> dict[str, Any]:
    """Placeholder до выбора схемы фискализации (фаза C)."""
    raise FiscalNotConfigured(
        "Фискализация не настроена: выберите схему (Сбер orderBundle или отдельная касса). "
        "См. docs/integrations/EXTERNAL_REQUESTS_CHECKLIST.md"
    )
