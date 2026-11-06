"""S3-compatible object storage adapter (AWS / Yandex / Selectel / MinIO)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class OffsiteObjectMeta:
    key: str
    size: int
    etag: str


class OffsiteNotConfigured(RuntimeError):
    pass


def offsite_settings() -> dict[str, Any]:
    return {
        "enabled": bool(getattr(settings, "BACKUP_OFFSITE_ENABLED", False)),
        "endpoint_url": str(getattr(settings, "BACKUP_S3_ENDPOINT_URL", "") or "").strip()
        or None,
        "region": str(getattr(settings, "BACKUP_S3_REGION", "") or "ru-central1").strip(),
        "bucket": str(getattr(settings, "BACKUP_S3_BUCKET", "") or "").strip(),
        "access_key": str(getattr(settings, "BACKUP_S3_ACCESS_KEY", "") or "").strip(),
        "secret_key": str(getattr(settings, "BACKUP_S3_SECRET_KEY", "") or "").strip(),
        "prefix": str(getattr(settings, "BACKUP_S3_PREFIX", "ringoo/backups") or "")
        .strip()
        .strip("/"),
        "provider_label": str(
            getattr(settings, "BACKUP_S3_PROVIDER_LABEL", "s3-compatible") or "s3-compatible"
        ).strip(),
    }


def is_offsite_configured() -> bool:
    cfg = offsite_settings()
    return bool(
        cfg["enabled"]
        and cfg["bucket"]
        and cfg["access_key"]
        and cfg["secret_key"]
    )


def _client():
    import boto3
    from botocore.config import Config

    cfg = offsite_settings()
    if not is_offsite_configured():
        raise OffsiteNotConfigured("Внешнее хранилище не настроено")
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint_url"],
        region_name=cfg["region"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )


def object_key_for(filename: str) -> str:
    cfg = offsite_settings()
    prefix = cfg["prefix"]
    name = filename.lstrip("/")
    return f"{prefix}/{name}" if prefix else name


def put_object(*, key: str, body: bytes, content_type: str = "application/octet-stream") -> OffsiteObjectMeta:
    client = _client()
    cfg = offsite_settings()
    resp = client.put_object(
        Bucket=cfg["bucket"],
        Key=key,
        Body=body,
        ContentType=content_type,
        ACL="private",
    )
    head = client.head_object(Bucket=cfg["bucket"], Key=key)
    size = int(head.get("ContentLength") or len(body))
    etag = str(resp.get("ETag") or head.get("ETag") or "").strip('"')
    if size != len(body):
        raise RuntimeError(
            f"Размер объекта в S3 ({size}) не совпал с локальным ({len(body)})"
        )
    return OffsiteObjectMeta(key=key, size=size, etag=etag)


def get_object_bytes(key: str) -> bytes:
    client = _client()
    cfg = offsite_settings()
    resp = client.get_object(Bucket=cfg["bucket"], Key=key)
    return resp["Body"].read()


def head_object(key: str) -> dict[str, Any]:
    client = _client()
    cfg = offsite_settings()
    return client.head_object(Bucket=cfg["bucket"], Key=key)


def delete_object(key: str) -> None:
    client = _client()
    cfg = offsite_settings()
    client.delete_object(Bucket=cfg["bucket"], Key=key)


def list_backup_keys(max_keys: int = 1000) -> list[dict[str, Any]]:
    client = _client()
    cfg = offsite_settings()
    prefix = cfg["prefix"]
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"
    paginator = client.get_paginator("list_objects_v2")
    items: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=cfg["bucket"], Prefix=prefix):
        for obj in page.get("Contents") or []:
            items.append(
                {
                    "key": obj["Key"],
                    "size": int(obj.get("Size") or 0),
                    "last_modified": obj.get("LastModified"),
                }
            )
            if len(items) >= max_keys:
                return items
    return items


def probe_connection() -> dict[str, Any]:
    """Проверка credentials без вывода секретов."""
    cfg = offsite_settings()
    if not is_offsite_configured():
        return {
            "status": "NOT_CONFIGURED",
            "provider": cfg["provider_label"],
            "bucket": cfg["bucket"] or None,
        }
    try:
        client = _client()
        client.head_bucket(Bucket=cfg["bucket"])
        return {
            "status": "SUCCESS",
            "provider": cfg["provider_label"],
            "bucket": cfg["bucket"],
            "endpoint": cfg["endpoint_url"],
            "prefix": cfg["prefix"],
            "region": cfg["region"],
        }
    except Exception as exc:
        logger.warning("offsite probe failed: %s", type(exc).__name__)
        return {
            "status": "FAILED",
            "provider": cfg["provider_label"],
            "bucket": cfg["bucket"],
            "error": type(exc).__name__,
        }
