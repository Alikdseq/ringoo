"""Celery: scheduled backup + offsite upload + retention."""

from __future__ import annotations

import logging

from django.conf import settings

from config.optional_task import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def create_and_upload_offsite_backup_task(self, archive_id: str | None = None):
    """
    Если archive_id задан — только upload.
    Иначе — создать scheduled архив (ключ env) и загрузить.
    """
    from apps.backups.models import BackupArchive
    from apps.backups.offsite import upload_archive_offsite
    from apps.backups.services import create_backup_archive

    try:
        if archive_id:
            return str(upload_archive_offsite(archive_id).pk)
        archive, _token = create_backup_archive(
            user=None,
            password=None,
            source=BackupArchive.SOURCE_SCHEDULED,
            encrypt_with_env_key=True,
        )
        uploaded = upload_archive_offsite(str(archive.pk))
        return str(uploaded.pk)
    except Exception as exc:
        logger.exception("create_and_upload_offsite_backup_task failed")
        try:
            raise self.retry(exc=exc)
        except Exception:
            raise


@shared_task
def apply_backup_retention_task():
    from apps.backups.offsite import apply_retention_policy

    if not getattr(settings, "BACKUP_OFFSITE_ENABLED", False):
        return {"skipped": True}
    return apply_retention_policy()
