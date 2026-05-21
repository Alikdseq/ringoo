"""Кэш каталога и HTTP Cache-Control для публичных GET."""

import hashlib

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response


def bump_products_list_version() -> None:
    try:
        version = cache.get("products_list_version") or 0
        cache.set("products_list_version", version + 1, timeout=None)
    except Exception:
        pass


def product_detail_cache_key(slug: str) -> str:
    version = cache.get("products_list_version") or 0
    return f"product_detail:v{version}:{slug}"


def product_list_cache_key(request) -> str:
    version = cache.get("products_list_version") or 0
    params = [
        ("category", request.query_params.get("category") or ""),
        ("brand", request.query_params.get("brand") or ""),
        ("min_price", request.query_params.get("min_price") or ""),
        ("max_price", request.query_params.get("max_price") or ""),
        ("search", request.query_params.get("search") or ""),
        ("ordering", request.query_params.get("ordering") or "created_at"),
        ("page", request.query_params.get("page") or "1"),
        ("page_size", request.query_params.get("page_size") or ""),
        ("in_stock", request.query_params.get("in_stock") or ""),
        ("rating_min", request.query_params.get("rating_min") or ""),
        ("store", request.query_params.get("store") or ""),
    ]
    raw = "&".join(f"{k}={v}" for k, v in params)
    h = hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"products_list:v{version}:{h}"


def brands_cache_key() -> str:
    version = cache.get("products_list_version") or 0
    return f"products_brands:v{version}"


def autocomplete_cache_key(q: str) -> str:
    version = cache.get("products_list_version") or 0
    h = hashlib.md5(q.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"products_autocomplete:v{version}:{h}"


def apply_public_cache_headers(response: Response, *, max_age: int = 60, swr: int = 300) -> Response:
    response["Cache-Control"] = f"public, max-age={max_age}, stale-while-revalidate={swr}"
    return response
