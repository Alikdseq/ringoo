"""
Нормализация и ограничение delivery_address (JSON) при создании заказа.
Защита от лишних ключей, вложенных структур и чрезмерной длины (2.2.2 чек-листа).
"""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import ValidationError

ALLOWED_DELIVERY_ADDRESS_KEYS = frozenset(
    {"city", "street", "house", "apartment", "postal_code"}
)

DELIVERY_ADDRESS_MAX_LEN: dict[str, int] = {
    "city": 255,
    "street": 255,
    "house": 50,
    "apartment": 50,
    "postal_code": 20,
}


def normalize_delivery_address(value: Any) -> dict[str, str]:
    """
    Разрешены только известные строковые поля; не dict/list в значениях.
    Возвращает словарь только с непустыми строками после strip.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValidationError("Адрес доставки должен быть объектом JSON.")
    unknown = set(value) - ALLOWED_DELIVERY_ADDRESS_KEYS
    if unknown:
        raise ValidationError(
            f"Недопустимые поля в адресе: {', '.join(sorted(unknown))}."
        )

    out: dict[str, str] = {}
    for key in ALLOWED_DELIVERY_ADDRESS_KEYS:
        if key not in value:
            continue
        raw = value[key]
        if raw is None:
            continue
        if isinstance(raw, (dict, list, tuple)):
            raise ValidationError(f"Поле «{key}» должно быть строкой.")
        if isinstance(raw, bool):
            raise ValidationError(f"Поле «{key}» должно быть строкой.")
        if not isinstance(raw, str):
            raw = str(raw)
        s = raw.strip()
        if not s:
            continue
        max_len = DELIVERY_ADDRESS_MAX_LEN[key]
        if len(s) > max_len:
            raise ValidationError(f"Поле «{key}» слишком длинное (максимум {max_len} символов).")
        out[key] = s
    return out
