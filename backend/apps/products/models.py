"""
Модели каталога: Category, Product, ProductImage, ProductSpec (задачи 1.2.1–1.2.4).
"""

import os
import re
import uuid

from django.db import models
from django.db.models.signals import post_save


def product_image_upload_to(instance, filename):
    """Путь загрузки изображения товара: products/YYYY/MM/uuid.ext. Безопасное имя (без кириллицы) для отображения на всех устройствах."""
    from django.utils import timezone

    ext = os.path.splitext(filename)[1] or ".jpg"
    ext = ext.lower() if ext else ".jpg"
    safe_ext = re.sub(r"[^a-z0-9.]", "", ext)[:10] or ".jpg"
    now = timezone.now()
    return "products/{:%Y/%m}/{}{}".format(now, uuid.uuid4().hex, safe_ext)


class Category(models.Model):
    """Категория товаров (древовидная через parent)."""

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
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    image = models.ImageField(
        upload_to="categories/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Изображение",
    )
    sort_order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
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
        db_table = "products_category"
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/catalog/category/{self.slug}/"


class Product(models.Model):
    """Товар."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Артикул",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Может содержать HTML",
    )
    short_description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Краткое описание",
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена",
    )
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Старая цена",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Категория",
    )
    brand = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Бренд",
    )
    rating = models.FloatField(default=0.0, verbose_name="Рейтинг")
    reviews_count = models.IntegerField(default=0, verbose_name="Количество отзывов")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_featured = models.BooleanField(default=False, verbose_name="Рекомендуемый")
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
        db_table = "products_product"
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
            models.Index(
                fields=["is_active", "category"],
                name="products_prod_active_cat_idx",
            ),
            models.Index(
                fields=["is_active", "-created_at"],
                name="products_prod_act_created_idx",
            ),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/catalog/product/{self.slug}/"

    @property
    def discount_percent(self):
        """Процент скидки (0 если нет old_price или old_price <= price)."""
        if not self.old_price or self.old_price <= self.price:
            return 0
        return round(
            (float(self.old_price) - float(self.price)) / float(self.old_price) * 100,
            1,
        )


class ProductColor(models.Model):
    """Вариант цвета товара (для галереи по цвету и кружков на PDP)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="colors",
        verbose_name="Товар",
    )
    slug = models.SlugField(max_length=100, verbose_name="Slug цвета")
    label = models.CharField(max_length=255, verbose_name="Подпись")
    hex = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        verbose_name="HEX для кружка",
        help_text="Например #1C1C1E",
    )
    sort_order = models.IntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена варианта",
        help_text="Пусто — используется цена товара.",
    )
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Старая цена варианта",
    )

    class Meta:
        db_table = "products_productcolor"
        verbose_name = "Цвет товара"
        verbose_name_plural = "Цвета товаров"
        ordering = ["sort_order", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "slug"],
                name="products_productcolor_product_slug_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "sort_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} / {self.label}"

    def effective_price(self):
        if self.price is not None:
            return self.price
        return self.product.price

    def effective_old_price(self):
        if self.old_price is not None:
            return self.old_price
        return self.product.old_price


class ProductImage(models.Model):
    """Изображение товара."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Товар",
    )
    color = models.ForeignKey(
        ProductColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
        verbose_name="Цвет",
        help_text="Пусто — общее фото (комплект, коробка и т.д.).",
    )
    image = models.ImageField(
        upload_to=product_image_upload_to,
        verbose_name="Изображение",
    )
    is_main = models.BooleanField(default=False, verbose_name="Главное")
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Alt-текст",
    )
    sort_order = models.IntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "products_productimage"
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.product.title} — {self.image.name}"


class ProductSpec(models.Model):
    """Характеристика товара (название — значение)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specs",
        verbose_name="Товар",
    )
    name = models.CharField(max_length=255, verbose_name="Название характеристики")
    value = models.CharField(max_length=500, verbose_name="Значение")
    sort_order = models.IntegerField(default=0, verbose_name="Порядок")

    class Meta:
        db_table = "products_productspec"
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товаров"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name}: {self.value}"


def _product_image_ensure_single_main(sender, instance, created, **kwargs):
    """Оставляем только одно главное изображение у товара (is_main=True)."""
    if not instance.is_main:
        return
    ProductImage.objects.filter(product=instance.product).exclude(pk=instance.pk).update(
        is_main=False
    )


post_save.connect(
    _product_image_ensure_single_main,
    sender=ProductImage,
    dispatch_uid="products.productimage.ensure_single_main",
)
