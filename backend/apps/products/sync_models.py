"""Журнал синхронизации каталога с 1С (SyncLog)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class OneCCatalogSyncLog(models.Model):
    """Один запуск импорта/проверки каталога (dry-run или apply)."""

    TYPE_CATALOG = "catalog"
    TYPE_PROBE = "probe"
    TYPE_CHOICES = [
        (TYPE_CATALOG, "Каталог (категории/товары/остатки)"),
        (TYPE_PROBE, "Проверка подключения"),
    ]

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_PARTIAL = "partial_success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает"),
        (STATUS_RUNNING, "Выполняется"),
        (STATUS_SUCCESS, "Успех"),
        (STATUS_PARTIAL, "Частичный успех"),
        (STATUS_FAILED, "Ошибка"),
    ]

    SOURCE_API = "api"
    SOURCE_FILE = "file"
    SOURCE_FIXTURE = "fixture"
    SOURCE_CHOICES = [
        (SOURCE_API, "HTTP API 1С"),
        (SOURCE_FILE, "XML-файлы"),
        (SOURCE_FIXTURE, "Фикстуры/тесты"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run_id = models.CharField(max_length=64, unique=True, db_index=True)
    sync_type = models.CharField(
        max_length=32, choices=TYPE_CHOICES, default=TYPE_CATALOG, db_index=True
    )
    source = models.CharField(
        max_length=16, choices=SOURCE_CHOICES, default=SOURCE_API
    )
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    dry_run = models.BooleanField(default=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    records_received = models.PositiveIntegerField(default=0)
    categories_created = models.PositiveIntegerField(default=0)
    categories_updated = models.PositiveIntegerField(default=0)
    categories_skipped = models.PositiveIntegerField(default=0)
    products_created = models.PositiveIntegerField(default=0)
    products_updated = models.PositiveIntegerField(default=0)
    products_skipped = models.PositiveIntegerField(default=0)
    stocks_upserted = models.PositiveIntegerField(default=0)
    stocks_skipped = models.PositiveIntegerField(default=0)
    errors_count = models.PositiveIntegerField(default=0)

    summary = models.JSONField(default=dict, blank=True)
    # Человекочитаемые ошибки без секретов (список строк / dict).
    error_messages = models.JSONField(default=list, blank=True)
    celery_task_id = models.CharField(max_length=64, blank=True, default="")

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onec_catalog_sync_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "products_onec_catalog_synclog"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sync_type", "-started_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["dry_run", "-created_at"]),
        ]
        verbose_name = "Журнал синхронизации 1С"
        verbose_name_plural = "Журнал синхронизации 1С"

    def __str__(self) -> str:
        return f"{self.run_id} {self.status} dry_run={self.dry_run}"
