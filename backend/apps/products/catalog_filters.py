"""
Общие фильтры каталога (список товаров, product-models).
"""

from __future__ import annotations

import re
from collections import defaultdict

from django.db.models import Exists, F, OuterRef, Q, QuerySet

from apps.stores.models import Stock

from .search_synonyms import get_search_terms
from .utils import model_key_from_title, normalize_model_label

_STORAGE_RE = re.compile(
    r"\s+\d+\s*(?:GB|TB|ГБ|ТБ)\b",
    re.IGNORECASE,
)


def apply_catalog_filters(qs: QuerySet, params, *, exclude_model: bool = False) -> QuerySet:
    """Применяет query-параметры каталога к queryset товаров."""
    category_slug = (params.get("category") or "").strip()
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    brand = (params.get("brand") or "").strip()
    if brand:
        brand_terms = get_search_terms(brand)
        if brand_terms:
            qs = qs.filter(Q(*(Q(brand__iexact=t) for t in brand_terms), _connector=Q.OR))

    min_price = params.get("min_price")
    if min_price is not None and str(min_price).strip() != "":
        try:
            qs = qs.filter(price__gte=float(min_price))
        except (TypeError, ValueError):
            pass

    max_price = params.get("max_price")
    if max_price is not None and str(max_price).strip() != "":
        try:
            qs = qs.filter(price__lte=float(max_price))
        except (TypeError, ValueError):
            pass

    search = (params.get("search") or "").strip()
    if search:
        terms = get_search_terms(search)
        if terms:
            search_q = Q()
            for term in terms:
                search_q |= (
                    Q(title__icontains=term)
                    | Q(sku__icontains=term)
                    | Q(description__icontains=term)
                )
            qs = qs.filter(search_q)

    if not exclude_model:
        model_key = (params.get("model") or "").strip()
        if model_key:
            qs = filter_queryset_by_model_key(qs, model_key)

    in_stock = (params.get("in_stock") or "").strip().lower()
    if in_stock in ("true", "1", "yes"):
        has_stock = Stock.objects.filter(product_id=OuterRef("pk")).filter(
            quantity__gt=F("reserved_quantity"),
        )
        qs = qs.filter(Exists(has_stock))

    rating_min = params.get("rating_min")
    if rating_min is not None and str(rating_min).strip() != "":
        try:
            qs = qs.filter(rating__gte=float(rating_min))
        except (TypeError, ValueError):
            pass

    store_slug = (params.get("store") or "").strip()
    if store_slug:
        has_stock_in_store = Stock.objects.filter(
            product_id=OuterRef("pk"),
            store__slug=store_slug,
            store__is_active=True,
        ).filter(quantity__gt=F("reserved_quantity"))
        qs = qs.filter(Exists(has_stock_in_store))

    return qs


def filter_queryset_by_model_key(qs: QuerySet, model_key: str) -> QuerySet:
    """Фильтр по ключу модели: все значимые части ключа есть в title или slug."""
    parts = [p for p in model_key.lower().split("-") if len(p) >= 2]
    if not parts:
        return qs.filter(Q(slug__icontains=model_key))
    q = Q(slug__icontains=model_key)
    title_q = Q()
    for part in parts:
        title_q &= Q(title__icontains=part)
    return qs.filter(q | title_q)


def aggregate_product_models(qs: QuerySet) -> list[dict]:
    """
    Уникальные «линейки» из title товаров в текущей выборке.
    results: [{ key, label, count }]
    """
    buckets: dict[str, dict] = {}
    for title, slug in qs.values_list("title", "slug"):
        label = normalize_model_label(title or "")
        if not label:
            continue
        key = model_key_from_title(title or "", slug or "")
        entry = buckets.get(key)
        if not entry:
            buckets[key] = {"key": key, "label": label, "count": 1}
        else:
            entry["count"] += 1
            if len(label) < len(entry["label"]):
                entry["label"] = label
    results = sorted(buckets.values(), key=lambda x: (-x["count"], x["label"]))
    return results
