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
    sync_type = models.CharField(max_length=32, choices=TYPE_CHOICES, default=TYPE_CATALOG, db_index=True)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_API)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
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


class OneCCatalogImportPlan(models.Model):
    """
    Сохранённый CatalogImportPlan после DRY-RUN (RELEASE 46.1 D.2).
    APPLY только через plan_id + verify checksum / TTL / status.
    """

    STATUS_READY = "ready"
    STATUS_APPLYING = "applying"
    STATUS_APPLIED = "applied"
    STATUS_EXPIRED = "expired"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_READY, "Готов"),
        (STATUS_APPLYING, "Применяется"),
        (STATUS_APPLIED, "Применён"),
        (STATUS_EXPIRED, "Истёк"),
        (STATUS_REJECTED, "Отклонён"),
    ]

    plan_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checksum = models.CharField(max_length=64, db_index=True)
    schema_version = models.PositiveSmallIntegerField()
    storage_version = models.PositiveSmallIntegerField(default=1)
    canonical_payload = models.JSONField()
    snapshot_policy = models.CharField(max_length=32, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_READY,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onec_catalog_import_plans",
    )
    dry_run_sync_log = models.ForeignKey(
        OneCCatalogSyncLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saved_import_plans",
    )
    error_detail = models.TextField(blank=True, default="")
    # D.2.3: server-side one-time execution right + stuck applying diagnostics
    applying_at = models.DateTimeField(null=True, blank=True)
    execution_token = models.CharField(max_length=64, blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onec_catalog_plan_resolutions",
    )

    class Meta:
        db_table = "products_onec_catalog_import_plan"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["-created_at"]),
        ]
        verbose_name = "Сохранённый план импорта 1С"
        verbose_name_plural = "Сохранённые планы импорта 1С"

    def __str__(self) -> str:
        return f"{self.plan_id} {self.status} checksum={self.checksum[:12]}"
