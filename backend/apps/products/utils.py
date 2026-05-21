"""Утилиты каталога: slug товаров, разбор slug iPhone."""

from django.utils.text import slugify

from apps.products.models import Product

IPHONE_PREFIX = "iphone-"


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
