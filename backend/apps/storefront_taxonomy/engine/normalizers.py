"""
Нормализация признаков классификации (S1.2.2).

Чистые функции без I/O и без обращения к ORM.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

NORMALIZER_VERSION = 1


@dataclass(frozen=True, slots=True)
class ProductFeatures:
    """
    ORM-независимые входные признаки товара.

    Пути — последовательности сегментов от корня к листу.
    """

    title: str = ""
    brand: str | None = None
    category_slug: str = ""
    category_onec_code: str | None = None
    category_title_path: tuple[str, ...] = ()
    category_slug_path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedFeatures:
    """Нормализованные признаки для детерминированного сопоставления."""

    title: str
    brand: str
    category_slug: str
    category_onec_code: str
    category_title_path: tuple[str, ...]
    category_slug_path: tuple[str, ...]
    normalizer_version: int = NORMALIZER_VERSION


def normalize_text(value: str | None) -> str:
    """
    Нормализация title / названий категорий:
    NFKC → trim → collapse whitespace → casefold.
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = " ".join(text.split())
    return text.casefold()


def normalize_brand(value: str | None) -> str:
    """Нормализация бренда: trim, collapse spaces, casefold; None/пусто → \"\"."""
    return normalize_text(value)


def normalize_slug(value: str | None) -> str:
    """
    Нормализация slug: trim + lower.
    Семантика исходного slug не меняется (без NFKC-переписывания символов).
    """
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_path_segments(segments: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Нормализует каждый сегмент пути как текст (для title_path)."""
    if not segments:
        return ()
    return tuple(normalize_text(seg) for seg in segments)


def normalize_slug_path(segments: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Нормализует каждый сегмент пути как slug."""
    if not segments:
        return ()
    return tuple(normalize_slug(seg) for seg in segments)


def normalize_features(features: ProductFeatures) -> NormalizedFeatures:
    """Строит NormalizedFeatures из сырых ProductFeatures."""
    return NormalizedFeatures(
        title=normalize_text(features.title),
        brand=normalize_brand(features.brand),
        category_slug=normalize_slug(features.category_slug),
        category_onec_code=(features.category_onec_code or "").strip(),
        category_title_path=normalize_path_segments(features.category_title_path),
        category_slug_path=normalize_slug_path(features.category_slug_path),
        normalizer_version=NORMALIZER_VERSION,
    )
