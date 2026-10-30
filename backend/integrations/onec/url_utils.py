"""Нормализация и проверка ONE_C_API_BASE_URL (без сетевых запросов)."""

from __future__ import annotations

from urllib.parse import urlparse


class OneCBaseUrlError(ValueError):
    """Некорректный базовый URL публикации 1С."""


REQUIRED_PUBLICATION_SUFFIX = "/razrab/hs"
FORBIDDEN_PUBLICATION = "/ut11_test/hs"


def normalize_onec_base_url(raw: str | None) -> str:
    """
    Возвращает base URL со завершающим «/».
    Требует путь, оканчивающийся на /razrab/hs (без дублей и без ut11_test).
    """
    text = (raw or "").strip()
    if not text:
        raise OneCBaseUrlError("ONE_C_API_BASE_URL не задан")

    # Без схемы — отклоняем (не выдумываем хост)
    parsed = urlparse(text if "://" in text else f"//{text}", allow_fragments=False)
    if "://" not in text:
        raise OneCBaseUrlError(
            "ONE_C_API_BASE_URL должен содержать схему (http:// или https://)"
        )
    if not parsed.netloc:
        raise OneCBaseUrlError("ONE_C_API_BASE_URL не содержит хост")

    path = (parsed.path or "").rstrip("/")
    if FORBIDDEN_PUBLICATION in path or path.endswith(FORBIDDEN_PUBLICATION.rstrip("/")):
        raise OneCBaseUrlError(
            "Запрещена старая публикация /ut11_test/hs/ — используйте /razrab/hs/"
        )
    if path.count("razrab/hs") > 1 or "/razrab/hs/razrab/hs" in path:
        raise OneCBaseUrlError(
            "Повторение /razrab/hs в ONE_C_API_BASE_URL недопустимо"
        )
    if not path.endswith("/razrab/hs"):
        raise OneCBaseUrlError(
            "ONE_C_API_BASE_URL должен заканчиваться на /razrab/hs "
            f"(сейчас path={path!r})"
        )

    # Собираем без лишнего слэша в середине
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}/"
    return normalized
