"""
Публичные абсолютные URL для медиа/API.

SSR Next.js в Docker ходит на http://web:8000 — request.build_absolute_uri() иначе
отдаёт http://web:8000/media/..., недоступный из браузера пользователя.
"""

from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse

# Hostname из docker-compose, которые не резолвятся в браузере на хосте
_INTERNAL_HOST_SUFFIXES = (
    "web",
    "web:8000",
    "ringoo_backend",
    "ringoo_backend:8000",
    "host.docker.internal",
    "host.docker.internal:8000",
)


def get_public_api_origin() -> str:
    """Origin API для ссылок в JSON (браузер / Next на хосте)."""
    origin = (
        os.getenv("PUBLIC_API_ORIGIN", "").strip()
        or os.getenv("RINGOO_PUBLIC_API_ORIGIN", "").strip()
        or "http://localhost:8000"
    )
    return origin.rstrip("/")


def _is_internal_host(netloc: str) -> bool:
    if not netloc:
        return False
    host = netloc.lower()
    if host in _INTERNAL_HOST_SUFFIXES:
        return True
    return host.startswith("web:") or host.startswith("ringoo_backend:")


def absolute_media_url(request, url: str | None) -> str | None:
    """
    Абсолютный URL файла: всегда с публичным origin (localhost:8000 в dev),
    даже если request пришёл с Host: web:8000.
    """
    if not url:
        return None
    raw = str(url).strip()
    if not raw:
        return None

    public = get_public_api_origin()

    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        if _is_internal_host(parsed.netloc):
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            return urljoin(public + "/", path.lstrip("/"))
        return raw

    if request is not None:
        built = request.build_absolute_uri(raw)
        parsed = urlparse(built)
        if _is_internal_host(parsed.netloc):
            return urljoin(public + "/", raw.lstrip("/"))
        return built

    return urljoin(public + "/", raw.lstrip("/"))
