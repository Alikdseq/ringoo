"""Метаданные скачиваемых резервных копий (INT final / ops)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BackupArchive(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает"),
        (STATUS_RUNNING, "Создаётся"),
        (STATUS_READY, "Готов"),
        (STATUS_FAILED, "Ошибка"),
        (STATUS_EXPIRED, "Истёк"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backup_archives",
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    filename = models.CharField(max_length=255, blank=True, default="")
    # Относительный путь внутри BACKUP_STORAGE_ROOT (без traversal)
    relative_path = models.CharField(max_length=512, blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default="")
    encrypted = models.BooleanField(default=False)
    manifest = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=512, blank=True, default="")
    download_token_hash = models.CharField(max_length=64, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backups_backuparchive"
        ordering = ["-created_at"]
        verbose_name = "Резервная копия"
        verbose_name_plural = "Резервные копии"

    def __str__(self) -> str:
        return self.filename or str(self.pk)

    @property
    def is_downloadable(self) -> bool:
        if self.status != self.STATUS_READY:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return bool(self.relative_path)
