"""Метаданные скачиваемых и offsite резервных копий."""

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

    OFFSITE_NOT_CONFIGURED = "NOT_CONFIGURED"
    OFFSITE_PENDING = "PENDING"
    OFFSITE_RUNNING = "RUNNING"
    OFFSITE_VERIFYING = "VERIFYING"
    OFFSITE_SUCCESS = "SUCCESS"
    OFFSITE_FAILED = "FAILED"
    OFFSITE_CHOICES = [
        (OFFSITE_NOT_CONFIGURED, "Не настроено"),
        (OFFSITE_PENDING, "Ожидает загрузки"),
        (OFFSITE_RUNNING, "Загрузка"),
        (OFFSITE_VERIFYING, "Проверка"),
        (OFFSITE_SUCCESS, "Успех"),
        (OFFSITE_FAILED, "Ошибка"),
    ]

    SOURCE_MANUAL = "manual"
    SOURCE_SCHEDULED = "scheduled"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Вручную"),
        (SOURCE_SCHEDULED, "По расписанию"),
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
    source = models.CharField(
        max_length=16, choices=SOURCE_CHOICES, default=SOURCE_MANUAL, db_index=True
    )
    filename = models.CharField(max_length=255, blank=True, default="")
    relative_path = models.CharField(max_length=512, blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default="")
    encrypted = models.BooleanField(default=False)
    encryption_key_id = models.CharField(max_length=64, blank=True, default="")
    manifest = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=512, blank=True, default="")
    download_token_hash = models.CharField(max_length=64, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    offsite_status = models.CharField(
        max_length=32,
        choices=OFFSITE_CHOICES,
        default=OFFSITE_NOT_CONFIGURED,
        db_index=True,
    )
    offsite_key = models.CharField(max_length=512, blank=True, default="")
    offsite_etag = models.CharField(max_length=128, blank=True, default="")
    offsite_size_bytes = models.BigIntegerField(default=0)
    offsite_uploaded_at = models.DateTimeField(null=True, blank=True)
    offsite_verified_at = models.DateTimeField(null=True, blank=True)
    offsite_error = models.CharField(max_length=512, blank=True, default="")
    offsite_attempts = models.PositiveSmallIntegerField(default=0)

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

    @property
    def offsite_ok(self) -> bool:
        return self.offsite_status == self.OFFSITE_SUCCESS
