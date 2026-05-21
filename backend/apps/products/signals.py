"""
Сигналы приложения products: инвалидация кэша списка товаров и категорий (задача 2.5.2, 2.5.3).
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save


def _invalidate_products_list_cache(**kwargs):
    """Инвалидировать кэш списка товаров при изменении Product или Category."""
    from .cache_utils import bump_products_list_version

    bump_products_list_version()


def _invalidate_categories_list_cache(**kwargs):
    """Инвалидировать кэш списка категорий при изменении Category (см. docstring выше про версии)."""
    try:
        version = cache.get("category_list_version") or 0
        cache.set("category_list_version", version + 1, timeout=None)
    except Exception:
        pass


def _connect_cache_invalidation():
    from apps.stores.models import Stock

    from .models import Category, Product, ProductColor, ProductImage  # noqa: I001

    for signal in (post_save, post_delete):
        signal.connect(
            _invalidate_products_list_cache,
            sender=Stock,
            dispatch_uid="products.cache_invalidate.stock",
        )
        signal.connect(
            _invalidate_products_list_cache,
            sender=Product,
            dispatch_uid="products.cache_invalidate.product",
        )
        signal.connect(
            _invalidate_products_list_cache,
            sender=Category,
            dispatch_uid="products.cache_invalidate.category_products",
        )
        signal.connect(
            _invalidate_products_list_cache,
            sender=ProductColor,
            dispatch_uid="products.cache_invalidate.productcolor",
        )
        signal.connect(
            _invalidate_products_list_cache,
            sender=ProductImage,
            dispatch_uid="products.cache_invalidate.productimage",
        )
        signal.connect(
            _invalidate_categories_list_cache,
            sender=Category,
            dispatch_uid="products.cache_invalidate.category_list",
        )
