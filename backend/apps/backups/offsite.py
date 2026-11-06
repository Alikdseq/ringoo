"""Загрузка зашифрованного архива во внешнее S3-хранилище + verify + retention."""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.backups.crypto_keys import (
    decrypt_with_configured_keys,
    encrypt_with_configured_key,
    encryption_configured,
)
from apps.backups.models import BackupArchive
from apps.backups.s3 import (
    OffsiteNotConfigured,
    delete_object,
    get_object_bytes,
    is_offsite_configured,
    list_backup_keys,
    object_key_for,
    offsite_settings,
    probe_connection,
    put_object,
)
from apps.backups.services import resolve_archive_path, _sha256_file

logger = logging.getLogger(__name__)

MAX_UPLOAD_ATTEMPTS = 3


def offsite_status_snapshot() -> dict:
    cfg = offsite_settings()
    probe = probe_connection()
    latest_ok = (
        BackupArchive.objects.filter(offsite_status=BackupArchive.OFFSITE_SUCCESS)
        .order_by("-offsite_uploaded_at")
        .first()
    )
    count = BackupArchive.objects.filter(
        offsite_status=BackupArchive.OFFSITE_SUCCESS
    ).count()
    last_fail = (
        BackupArchive.objects.filter(offsite_status=BackupArchive.OFFSITE_FAILED)
        .order_by("-updated_at")
        .first()
    )
    return {
        "configured": is_offsite_configured() and encryption_configured(),
        "s3_configured": is_offsite_configured(),
        "encryption_configured": encryption_configured(),
        "provider": cfg["provider_label"],
        "connection_status": probe.get("status"),
        "bucket": cfg["bucket"] or None,
        "prefix": cfg["prefix"] or None,
        "last_success_at": latest_ok.offsite_uploaded_at if latest_ok else None,
        "last_success_size": latest_ok.offsite_size_bytes if latest_ok else None,
        "last_verified_at": latest_ok.offsite_verified_at if latest_ok else None,
        "last_success_filename": latest_ok.filename if latest_ok else None,
        "stored_count": count,
        "last_error": (last_fail.offsite_error if last_fail else "") or "",
    }


def prepare_encrypted_payload(archive: BackupArchive) -> tuple[bytes, str, str]:
    """
    Возвращает (encrypted_bytes, sha256_hex, encryption_key_id).
    Если файл уже RINGOO2 — использует его; иначе шифрует ключом окружения.
    """
    path = resolve_archive_path(archive)
    if path is None:
        raise FileNotFoundError("Локальный архив не найден")
    raw = path.read_bytes()
    if raw.startswith(b"RINGOO2"):
        digest = hashlib.sha256(raw).hexdigest()
        return raw, digest, archive.encryption_key_id or "embedded"
    if raw.startswith(b"RINGOO1"):
        # парольный архив — для offsite перешифруем ключом сервера нельзя без пароля;
        # создаём обёртку: шифруем весь RINGOO1-блоб ключом окружения
        enc, kid = encrypt_with_configured_key(raw)
        return enc, hashlib.sha256(enc).hexdigest(), kid
    # plain zip → encrypt with env key
    enc, kid = encrypt_with_configured_key(raw)
    return enc, hashlib.sha256(enc).hexdigest(), kid


def upload_archive_offsite(archive_id, *, force: bool = False) -> BackupArchive:
    with transaction.atomic():
        archive = BackupArchive.objects.select_for_update().get(pk=archive_id)
        if archive.status != BackupArchive.STATUS_READY:
            raise RuntimeError("Архив ещё не готов к загрузке")
        if archive.offsite_status == BackupArchive.OFFSITE_SUCCESS and not force:
            return archive
        if not is_offsite_configured():
            archive.offsite_status = BackupArchive.OFFSITE_NOT_CONFIGURED
            archive.offsite_error = "S3 не настроен"
            archive.save(update_fields=["offsite_status", "offsite_error", "updated_at"])
            raise OffsiteNotConfigured(archive.offsite_error)
        if not encryption_configured():
            archive.offsite_status = BackupArchive.OFFSITE_FAILED
            archive.offsite_error = "Ключ шифрования не настроен"
            archive.save(update_fields=["offsite_status", "offsite_error", "updated_at"])
            raise RuntimeError(archive.offsite_error)
        if archive.offsite_attempts >= MAX_UPLOAD_ATTEMPTS and not force:
            raise RuntimeError("Превышен лимит попыток загрузки")

        archive.offsite_status = BackupArchive.OFFSITE_RUNNING
        archive.offsite_attempts = int(archive.offsite_attempts) + 1
        archive.offsite_error = ""
        archive.save(
            update_fields=[
                "offsite_status",
                "offsite_attempts",
                "offsite_error",
                "updated_at",
            ]
        )

    try:
        archive = BackupArchive.objects.get(pk=archive_id)
        payload, digest, kid = prepare_encrypted_payload(archive)
        filename = archive.filename or f"{archive.pk}.zip.enc"
        if not filename.endswith(".enc"):
            filename = filename + ".enc"
        key = object_key_for(f"{archive.pk}_{filename}")
        meta = put_object(key=key, body=payload)

        archive.offsite_status = BackupArchive.OFFSITE_VERIFYING
        archive.offsite_key = meta.key
        archive.offsite_etag = meta.etag
        archive.offsite_size_bytes = meta.size
        archive.encryption_key_id = kid
        archive.encrypted = True
        archive.save(
            update_fields=[
                "offsite_status",
                "offsite_key",
                "offsite_etag",
                "offsite_size_bytes",
                "encryption_key_id",
                "encrypted",
                "updated_at",
            ]
        )

        remote = get_object_bytes(meta.key)
        if len(remote) != meta.size:
            raise RuntimeError("Verify size mismatch after download")
        remote_digest = hashlib.sha256(remote).hexdigest()
        if remote_digest != digest:
            raise RuntimeError("Verify checksum mismatch after download")
        decrypt_with_configured_keys(remote)

        archive.offsite_status = BackupArchive.OFFSITE_SUCCESS
        archive.offsite_uploaded_at = timezone.now()
        archive.offsite_verified_at = timezone.now()
        archive.offsite_error = ""
        archive.sha256 = digest
        archive.size_bytes = meta.size
        archive.save()
        return archive
    except Exception as exc:
        logger.exception("offsite upload failed archive=%s", archive_id)
        BackupArchive.objects.filter(pk=archive_id).update(
            offsite_status=BackupArchive.OFFSITE_FAILED,
            offsite_error=str(exc)[:512],
            updated_at=timezone.now(),
        )
        raise


def verify_latest_offsite() -> dict:
    archive = (
        BackupArchive.objects.filter(offsite_status=BackupArchive.OFFSITE_SUCCESS)
        .order_by("-offsite_uploaded_at")
        .first()
    )
    if not archive or not archive.offsite_key:
        return {"status": "FAILED", "detail": "Нет успешной внешней копии"}
    remote = get_object_bytes(archive.offsite_key)
    digest = hashlib.sha256(remote).hexdigest()
    if archive.sha256 and digest != archive.sha256:
        return {"status": "FAILED", "detail": "checksum mismatch", "archive_id": str(archive.pk)}
    decrypt_with_configured_keys(remote)
    archive.offsite_verified_at = timezone.now()
    archive.save(update_fields=["offsite_verified_at", "updated_at"])
    return {
        "status": "SUCCESS",
        "archive_id": str(archive.pk),
        "size": len(remote),
        "sha256": digest,
        "verified_at": archive.offsite_verified_at,
    }


def apply_retention_policy() -> dict:
    """
    Удаляет только SUCCESS offsite-объекты вне окон retention.
    Не удаляет FAILED / неподтверждённые.
    """
    daily_keep = int(getattr(settings, "BACKUP_RETENTION_DAILY_DAYS", 14))
    weekly_keep = int(getattr(settings, "BACKUP_RETENTION_WEEKLY_WEEKS", 8))
    monthly_keep = int(getattr(settings, "BACKUP_RETENTION_MONTHLY_MONTHS", 12))
    now = timezone.now()
    keep_ids: set = set()

    qs = BackupArchive.objects.filter(
        offsite_status=BackupArchive.OFFSITE_SUCCESS
    ).order_by("-offsite_uploaded_at")

    # daily window
    daily_cut = now - timedelta(days=daily_keep)
    for a in qs.filter(offsite_uploaded_at__gte=daily_cut):
        keep_ids.add(a.pk)

    # weekly: one per ISO week for weekly_keep weeks
    if weekly_keep > 0:
        week_seen: set[str] = set()
        for a in qs:
            if not a.offsite_uploaded_at:
                continue
            week = a.offsite_uploaded_at.strftime("%G-W%V")
            if week in week_seen:
                continue
            if len(week_seen) >= weekly_keep:
                break
            week_seen.add(week)
            keep_ids.add(a.pk)

    # monthly: one per month
    if monthly_keep > 0:
        month_seen: set[str] = set()
        for a in qs:
            if not a.offsite_uploaded_at:
                continue
            month = a.offsite_uploaded_at.strftime("%Y-%m")
            if month in month_seen:
                continue
            if len(month_seen) >= monthly_keep:
                break
            month_seen.add(month)
            keep_ids.add(a.pk)

    deleted = 0
    errors = 0
    for a in qs:
        if a.pk in keep_ids:
            continue
        if not a.offsite_key:
            continue
        try:
            delete_object(a.offsite_key)
            a.offsite_status = BackupArchive.OFFSITE_FAILED
            a.offsite_error = "removed_by_retention"
            a.offsite_key = ""
            a.save(
                update_fields=[
                    "offsite_status",
                    "offsite_error",
                    "offsite_key",
                    "updated_at",
                ]
            )
            deleted += 1
        except Exception:
            errors += 1
            logger.exception("retention delete failed archive=%s", a.pk)
    return {"kept": len(keep_ids), "deleted": deleted, "errors": errors}


def download_offsite_to_path(archive: BackupArchive, dest: Path) -> Path:
    if archive.offsite_status != BackupArchive.OFFSITE_SUCCESS or not archive.offsite_key:
        raise RuntimeError("Архив не загружен во внешнее хранилище")
    blob = get_object_bytes(archive.offsite_key)
    if archive.sha256:
        digest = hashlib.sha256(blob).hexdigest()
        if digest != archive.sha256:
            raise RuntimeError("Checksum внешнего объекта не совпал")
    plain = decrypt_with_configured_keys(blob)
    dest.write_bytes(plain)
    return dest
