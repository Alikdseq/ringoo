"""
Витринная таксономия и артефакты классификации.

Независимо от 1С Category / Product.category.
S1.1: только модели (без сигналов, Celery, seed, публичного API).
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# Ключи condition_payload, которые запрещены для универсальных правил
# (нельзя привязывать правило к конкретному Product UUID).
_FORBIDDEN_CONDITION_PAYLOAD_KEYS = frozenset(
    {
        "product_id",
        "product_ids",
        "product_uuid",
        "product_uuids",
        "products",
    }
)


def _find_forbidden_condition_keys(value) -> set[str]:
    """Рекурсивно ищет запрещённые ключи в dict/list структурах payload."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in _FORBIDDEN_CONDITION_PAYLOAD_KEYS:
                found.add(key)
            found.update(_find_forbidden_condition_keys(nested))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_forbidden_condition_keys(item))
    return found


class StorefrontCategory(models.Model):
    """Витринная категория (независима от Category / 1С)."""

    SECTION_PRIMARY = "primary"
    SECTION_ADDITIONAL = "additional"
    SECTION_TYPE_CHOICES = [
        (SECTION_PRIMARY, "Основной каталог"),
        (SECTION_ADDITIONAL, "Дополнительный раздел"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родительская категория",
    )
    section_type = models.CharField(
        max_length=20,
        choices=SECTION_TYPE_CHOICES,
        default=SECTION_PRIMARY,
        db_index=True,
        verbose_name="Тип раздела",
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    image = models.ImageField(
        upload_to="storefront_categories/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Изображение",
    )
    sort_order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Активна")
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Meta title (SEO)",
    )
    meta_description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Meta description (SEO)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "storefront_category"
        verbose_name = "Витринная категория"
        verbose_name_plural = "Витринные категории"
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["parent", "is_active"], name="sf_cat_parent_active_idx"),
            models.Index(fields=["section_type", "is_active"], name="sf_cat_section_active_idx"),
            models.Index(fields=["is_active", "sort_order"], name="sf_cat_active_sort_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class ClassificationRule(models.Model):
    """Универсальное правило автоматической классификации."""

    CONDITION_TITLE_CONTAINS = "title_contains"
    CONDITION_TITLE_REGEX = "title_regex"
    CONDITION_ONEC_CATEGORY_SLUG = "onec_category_slug"
    CONDITION_ONEC_CATEGORY_PATH = "onec_category_path"
    CONDITION_BRAND_EQUALS = "brand_equals"
    CONDITION_COMPOSITE = "composite"
    CONDITION_TYPE_CHOICES = [
        (CONDITION_TITLE_CONTAINS, "Название содержит"),
        (CONDITION_TITLE_REGEX, "Название по regex"),
        (CONDITION_ONEC_CATEGORY_SLUG, "Slug категории 1С"),
        (CONDITION_ONEC_CATEGORY_PATH, "Путь категории 1С"),
        (CONDITION_BRAND_EQUALS, "Бренд равен"),
        (CONDITION_COMPOSITE, "Составное условие"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.SlugField(max_length=100, unique=True, verbose_name="Код правила")
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    priority = models.IntegerField(
        default=100,
        db_index=True,
        verbose_name="Приоритет",
        help_text="Меньше значение — выше приоритет.",
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Активно")
    storefront_category = models.ForeignKey(
        StorefrontCategory,
        on_delete=models.PROTECT,
        related_name="classification_rules",
        verbose_name="Витринная категория",
    )
    condition_type = models.CharField(
        max_length=40,
        choices=CONDITION_TYPE_CHOICES,
        db_index=True,
        verbose_name="Тип условия",
    )
    condition_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Параметры условия",
        help_text="Универсальные параметры. Product UUID запрещены.",
    )
    schema_version = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Версия схемы payload",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "storefront_classification_rule"
        verbose_name = "Правило классификации"
        verbose_name_plural = "Правила классификации"
        ordering = ["priority", "code"]
        indexes = [
            models.Index(
                fields=["is_active", "priority"],
                name="sf_rule_active_prio_idx",
            ),
            models.Index(
                fields=["storefront_category", "is_active"],
                name="sf_rule_cat_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.title}"

    def clean(self) -> None:
        super().clean()
        payload = self.condition_payload
        if not isinstance(payload, dict):
            raise ValidationError(
                {"condition_payload": "condition_payload должен быть объектом JSON."}
            )
        forbidden = _find_forbidden_condition_keys(payload)
        if forbidden:
            raise ValidationError(
                {
                    "condition_payload": (
                        "Универсальное правило не может ссылаться на Product UUID. "
                        f"Запрещённые ключи: {', '.join(sorted(forbidden))}."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ProductClassificationOverride(models.Model):
    """Ручное назначение витринной категории (независимо от правил)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="storefront_override",
        verbose_name="Товар",
    )
    storefront_category = models.ForeignKey(
        StorefrontCategory,
        on_delete=models.PROTECT,
        related_name="manual_overrides",
        verbose_name="Витринная категория",
    )
    is_locked = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Заблокировано",
        help_text="Если True — автоклассификация не перезаписывает назначение.",
    )
    reason = models.TextField(blank=True, null=True, verbose_name="Причина")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storefront_overrides_created",
        verbose_name="Кем создано",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "storefront_product_override"
        verbose_name = "Ручной override классификации"
        verbose_name_plural = "Ручные override классификации"
        indexes = [
            models.Index(
                fields=["storefront_category", "is_locked"],
                name="sf_ovr_cat_locked_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Override {self.product_id} → {self.storefront_category_id}"


class ProductStorefrontAssignment(models.Model):
    """
    Текущее назначение основной витринной категории товару.
    Не более одной записи на Product (OneToOne).
    """

    SOURCE_RULE = "rule"
    SOURCE_OVERRIDE = "override"
    SOURCE_MANUAL = "manual"
    SOURCE_IMPORT = "import"
    SOURCE_SYSTEM = "system"
    SOURCE_CHOICES = [
        (SOURCE_RULE, "Правило"),
        (SOURCE_OVERRIDE, "Override"),
        (SOURCE_MANUAL, "Вручную"),
        (SOURCE_IMPORT, "Импорт"),
        (SOURCE_SYSTEM, "Система"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="storefront_assignment",
        verbose_name="Товар",
    )
    storefront_category = models.ForeignKey(
        StorefrontCategory,
        on_delete=models.PROTECT,
        related_name="assignments",
        verbose_name="Витринная категория",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        db_index=True,
        verbose_name="Источник",
    )
    rule = models.ForeignKey(
        ClassificationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
        verbose_name="Правило",
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Уверенность",
    )
    fingerprint = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Fingerprint входных признаков",
    )
    classified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время классификации",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "storefront_product_assignment"
        verbose_name = "Назначение витринной категории"
        verbose_name_plural = "Назначения витринных категорий"
        indexes = [
            models.Index(
                fields=["storefront_category", "source"],
                name="sf_asg_cat_source_idx",
            ),
            models.Index(
                fields=["classified_at"],
                name="sf_asg_classified_at_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Assignment {self.product_id} → {self.storefront_category_id}"


class ClassificationRun(models.Model):
    """Прогон классификатора (аудит / статистика)."""

    TRIGGER_MANUAL = "manual"
    TRIGGER_SCHEDULED = "scheduled"
    TRIGGER_POST_IMPORT = "post_import"
    TRIGGER_API = "api"
    TRIGGER_CHOICES = [
        (TRIGGER_MANUAL, "Вручную"),
        (TRIGGER_SCHEDULED, "По расписанию"),
        (TRIGGER_POST_IMPORT, "После импорта"),
        (TRIGGER_API, "API"),
    ]

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает"),
        (STATUS_RUNNING, "Выполняется"),
        (STATUS_COMPLETED, "Завершён"),
        (STATUS_FAILED, "Ошибка"),
        (STATUS_CANCELLED, "Отменён"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    run_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Идентификатор прогона",
    )
    trigger = models.CharField(
        max_length=20,
        choices=TRIGGER_CHOICES,
        db_index=True,
        verbose_name="Триггер",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="Статус",
    )
    stats = models.JSONField(default=dict, blank=True, verbose_name="Статистика")
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Начало",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Окончание",
    )

    class Meta:
        db_table = "storefront_classification_run"
        verbose_name = "Прогон классификации"
        verbose_name_plural = "Прогоны классификации"
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["status", "started_at"], name="sf_run_status_started_idx"),
            models.Index(fields=["trigger", "status"], name="sf_run_trigger_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Run {self.run_id} ({self.status})"


class ClassificationEvent(models.Model):
    """Событие изменения назначения в рамках прогона (история)."""

    STATUS_ASSIGNED = "assigned"
    STATUS_UPDATED = "updated"
    STATUS_SKIPPED = "skipped"
    STATUS_UNMATCHED = "unmatched"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_ASSIGNED, "Назначено"),
        (STATUS_UPDATED, "Обновлено"),
        (STATUS_SKIPPED, "Пропущено"),
        (STATUS_UNMATCHED, "Без совпадения"),
        (STATUS_ERROR, "Ошибка"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    run = models.ForeignKey(
        ClassificationRun,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="Прогон",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storefront_classification_events",
        verbose_name="Товар",
    )
    old_category = models.ForeignKey(
        StorefrontCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events_as_old",
        verbose_name="Старая категория",
    )
    new_category = models.ForeignKey(
        StorefrontCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events_as_new",
        verbose_name="Новая категория",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
        verbose_name="Статус",
    )
    message = models.TextField(blank=True, null=True, verbose_name="Сообщение")
    snapshot = models.JSONField(default=dict, blank=True, verbose_name="Снимок признаков")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Создано")

    class Meta:
        db_table = "storefront_classification_event"
        verbose_name = "Событие классификации"
        verbose_name_plural = "События классификации"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["run", "status"], name="sf_evt_run_status_idx"),
            models.Index(fields=["product", "created_at"], name="sf_evt_product_created_idx"),
            models.Index(fields=["status", "created_at"], name="sf_evt_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Event {self.id} ({self.status})"


class UnmatchedProductQueue(models.Model):
    """Очередь товаров без автоматического совпадения."""

    STATUS_OPEN = "open"
    STATUS_REVIEWING = "reviewing"
    STATUS_RESOLVED = "resolved"
    STATUS_IGNORED = "ignored"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Открыт"),
        (STATUS_REVIEWING, "На проверке"),
        (STATUS_RESOLVED, "Решён"),
        (STATUS_IGNORED, "Игнорируется"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="storefront_unmatched",
        verbose_name="Товар",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True,
        verbose_name="Статус",
    )
    reason = models.TextField(blank=True, null=True, verbose_name="Причина")
    attempts = models.PositiveIntegerField(default=0, verbose_name="Попыток")
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Последняя попытка",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "storefront_unmatched_queue"
        verbose_name = "Неклассифицированный товар"
        verbose_name_plural = "Очередь неклассифицированных"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "updated_at"], name="sf_umq_status_updated_idx"),
            models.Index(fields=["status", "attempts"], name="sf_umq_status_attempts_idx"),
        ]

    def __str__(self) -> str:
        return f"Unmatched {self.product_id} ({self.status})"
