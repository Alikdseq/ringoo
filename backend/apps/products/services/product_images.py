"""
Упорядочивание изображений товара для API (карточка каталога, PDP).
Все фото сохраняются; порядок: по sort_order цвета → внутри цвета (main, full/front/back).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.products.models import Product, ProductImage


def _image_sort_key(img: ProductImage, color_order: dict) -> tuple:
    c_ord = color_order.get(img.color_id, 10_000)
    return (c_ord, not img.is_main, img.sort_order or 0, img.created_at)


def ordered_product_images(product: Product) -> list:
    """Все изображения товара, сгруппированные по активным цветам."""
    qs = list(product.images.select_related("color").order_by("sort_order", "created_at"))
    if not qs:
        return []

    colors = list(product.colors.filter(is_active=True).order_by("sort_order", "label"))
    color_order = {c.id: idx for idx, c in enumerate(colors)}

    if colors:
        qs.sort(key=lambda img: _image_sort_key(img, color_order))
        return qs

    qs.sort(key=lambda img: (not img.is_main, img.sort_order or 0, img.created_at))
    return qs
