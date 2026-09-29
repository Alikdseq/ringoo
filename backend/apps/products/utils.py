"""Утилиты каталога: slug товаров, разбор slug iPhone, линейки моделей."""

import re

from django.utils.text import slugify

from apps.products.models import Product

IPHONE_PREFIX = "iphone-"

_STORAGE_SUFFIX_RE = re.compile(
    r"\s+\d+\s*(?:GB|TB|ГБ|ТБ)\b",
    re.IGNORECASE,
)


def normalize_model_label(title: str) -> str:
    """Убирает объём памяти и лишние хвосты из названия для группировки «модель»."""
    t = (title or "").strip()
    if not t:
        return ""
    t = _STORAGE_SUFFIX_RE.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def model_key_from_title(title: str, slug: str = "") -> str:
    """Стабильный ключ модели для URL (?model=)."""
    label = normalize_model_label(title)
    key = slugify(label) if label else ""
    if not key and slug:
        key = slugify(slug.split("-")[-6:])  # fallback
    return key or slugify(slug) or "model"


def extract_model_label(title: str, slug: str = "") -> str:
    """Человекочитаемая подпись модели для фильтра."""
    label = normalize_model_label(title)
    return label or (title or "").strip() or slug


def iphone_product_model_tail(slug: str) -> str | None:
    """
    Импорт: product_slug = f"{brand}-{model_slug}", у Apple model_slug часто уже
    iphone-17-pro → в БД iphone-iphone-17-pro. Снимаем все ведущие iphone-.
    """
    s = (slug or "").strip().lower()
    if not s.startswith(IPHONE_PREFIX):
        return None
    while s.startswith(IPHONE_PREFIX):
        s = s[len(IPHONE_PREFIX) :]
    return s or None


def slugify_product_title(title: str) -> str:
    base = slugify((title or "").strip(), allow_unicode=False)
    return base or "product"


def unique_product_slug(base: str, *, exclude_pk=None) -> str:
    slug = base
    n = 1
    qs = Product.objects.all()
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug
