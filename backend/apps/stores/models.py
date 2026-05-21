"""
Модели магазинов и наличия: Store, Stock (задачи 1.3.1, 1.3.2).
Атомарное резервирование (reserve_atomic) для защиты от гонок при создании заказов.
"""

import uuid

from django.db import models
from django.db.models import F
from django.utils import timezone

from .utils import generate_unique_manager_slug


def store_image_upload_to(instance, filename):
    return f"stores/{timezone.now():%Y/%m}/{filename}"


def manager_photo_upload_to(instance, filename):
    return f"managers/{timezone.now():%Y/%m}/{filename}"


class Store(models.Model):
    """Магазин."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    address = models.CharField(max_length=500, verbose_name="Адрес")
    city = models.CharField(max_length=255, verbose_name="Город")
    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Телефон",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Широта",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Долгота",
    )
    working_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Часы работы",
        help_text='Например: {"monday": "9:00-21:00", "tuesday": "9:00-21:00"}',
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    meta_title = models.CharField(max_length=255, blank=True, verbose_name="Meta title")
    meta_description = models.CharField(max_length=500, blank=True, verbose_name="Meta description")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "stores_store"
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ["city", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["city"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"

    def get_absolute_url(self):
        return f"/stores/{self.slug}/"


class StoreImage(models.Model):
    """Изображение для страницы магазина (галерея, баннеры)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Магазин",
    )
    image = models.ImageField(upload_to=store_image_upload_to, verbose_name="Изображение")
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="Alt-текст")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        db_table = "stores_storeimage"
        verbose_name = "Изображение магазина"
        verbose_name_plural = "Изображения магазинов"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.store.name} — image {self.pk}"


class Manager(models.Model):
    """Менеджер магазина (для привязки оценки к конкретному человеку)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255, verbose_name="ФИО")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    job_title = models.CharField(max_length=255, blank=True, verbose_name="Должность")
    bio = models.TextField(blank=True, verbose_name="О себе")
    photo = models.ImageField(
        upload_to=manager_photo_upload_to,
        blank=True,
        null=True,
        verbose_name="Фото",
    )
    photo_2 = models.ImageField(
        upload_to=manager_photo_upload_to,
        blank=True,
        null=True,
        verbose_name="Фото 2",
    )
    photo_alt = models.CharField(max_length=255, blank=True, verbose_name="Alt фото 1")
    photo_2_alt = models.CharField(max_length=255, blank=True, verbose_name="Alt фото 2")
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="managers",
        verbose_name="Магазин",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Порядок вывода",
    )

    class Meta:
        db_table = "stores_manager"
        verbose_name = "Менеджер"
        verbose_name_plural = "Менеджеры"
        ordering = ["store", "order", "name"]

    def __str__(self):
        return f"{self.name} — {self.store.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_manager_slug(self.name, exclude_pk=self.pk)
        super().save(*args, **kwargs)


class Stock(models.Model):
    """Наличие товара в магазине."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="stock_items",
        verbose_name="Товар",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="stock_items",
        verbose_name="Магазин",
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество",
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Зарезервировано",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "stores_stock"
        verbose_name = "Остаток"
        verbose_name_plural = "Остатки"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "store"],
                name="stores_stock_product_store_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["store"]),
        ]

    def __str__(self):
        return f"{self.product} — {self.store}: {self.available_quantity}"

    @property
    def available_quantity(self):
        """Доступно: quantity - reserved_quantity."""
        return max(0, self.quantity - self.reserved_quantity)

    def reserve(self, amount):
        """Резервирование количества. Не проверяет доступность — вызывающий должен проверить.
        Для создания заказов используйте reserve_atomic() внутри transaction.atomic()."""
        if amount <= 0:
            return
        self.reserved_quantity += amount
        self.save(update_fields=["reserved_quantity", "updated_at"])

    @classmethod
    def reserve_atomic(cls, product_id, store_id, amount):
        """
        Атомарно зарезервировать количество на складе.
        Использовать только внутри transaction.atomic() при создании заказа.
        Возвращает True при успехе, False если недостаточно остатка (без гонок).
        """
        if amount <= 0:
            return True
        updated = cls.objects.filter(
            product_id=product_id,
            store_id=store_id,
        ).filter(
            quantity__gte=F("reserved_quantity") + amount,
        ).update(
            reserved_quantity=F("reserved_quantity") + amount,
            updated_at=timezone.now(),
        )
        return updated == 1

    @classmethod
    def reserve_for_delivery(cls, product_id, amount):
        """
        Зарезервировать quantity для доставки по сети магазинов (жадно по складам).
        Все строки Stock по товару блокируются через select_for_update; при нехватке
        суммарного остатка резерв **не** создаётся (без частичного успеха).
        Только внутри transaction.atomic().
        """
        if amount <= 0:
            return True
        need = int(amount)
        rows = list(
            cls.objects.select_for_update()
            .filter(product_id=product_id)
            .order_by("store_id", "pk")
        )
        plan = []
        remaining = need
        for row in rows:
            if remaining <= 0:
                break
            available = int(row.quantity) - int(row.reserved_quantity)
            if available <= 0:
                continue
            take = min(available, remaining)
            plan.append((row.pk, take))
            remaining -= take
        if remaining > 0:
            return False
        for pk, take in plan:
            updated = cls.objects.filter(
                pk=pk,
                quantity__gte=F("reserved_quantity") + take,
            ).update(
                reserved_quantity=F("reserved_quantity") + take,
                updated_at=timezone.now(),
            )
            if updated != 1:
                return False
        return True

    def release(self, amount):
        """Освобождение резерва."""
        if amount <= 0:
            return
        self.reserved_quantity = max(0, self.reserved_quantity - amount)
        self.save(update_fields=["reserved_quantity", "updated_at"])
