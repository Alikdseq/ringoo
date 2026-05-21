"""
Модели контента: Tag, Article, News, Review (задачи 2.2.1–2.2.4).
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


def page_gallery_upload_to(instance, filename):
    return f"page-gallery/{timezone.now():%Y/%m}/{filename}"


class Tag(models.Model):
    """Тег для статей и новостей."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")

    class Meta:
        db_table = "content_tag"
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Article(models.Model):
    """Статья блога."""

    CATEGORY_CHOICES = [
        ("news", "Новости"),
        ("guide", "Гайды"),
        ("review", "Обзоры"),
        ("other", "Другое"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    content = models.TextField(verbose_name="Содержание", help_text="HTML допускается")
    excerpt = models.TextField(blank=True, null=True, verbose_name="Краткое описание")
    image = models.ImageField(
        upload_to="content/articles/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Изображение",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_articles",
        verbose_name="Автор",
    )
    category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        blank=True,
        null=True,
        verbose_name="Категория",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="articles",
        blank=True,
        verbose_name="Теги",
    )
    is_published = models.BooleanField(default=False, verbose_name="Опубликовано")
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата публикации",
    )
    views_count = models.IntegerField(default=0, verbose_name="Просмотры")
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
        db_table = "content_article"
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/blog/{self.slug}/"


class News(models.Model):
    """Новость (упрощённая версия статьи)."""

    CATEGORY_CHOICES = Article.CATEGORY_CHOICES

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    content = models.TextField(verbose_name="Содержание")
    excerpt = models.TextField(blank=True, null=True, verbose_name="Краткое описание")
    image = models.ImageField(
        upload_to="content/news/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Изображение",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_news",
        verbose_name="Автор",
    )
    category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        blank=True,
        null=True,
        verbose_name="Категория",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="news",
        blank=True,
        verbose_name="Теги",
    )
    is_published = models.BooleanField(default=False, verbose_name="Опубликовано")
    is_featured = models.BooleanField(default=False, verbose_name="В избранном")
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата публикации",
    )
    views_count = models.IntegerField(default=0, verbose_name="Просмотры")
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
        db_table = "content_news"
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["is_featured"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/news/{self.slug}/"


class Review(models.Model):
    """Отзыв на товар."""

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Товар",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        verbose_name="Пользователь",
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Имя (для гостя)",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email (для гостя)",
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Оценка",
    )
    comment = models.TextField(verbose_name="Текст отзыва")
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")
    is_verified_purchase = models.BooleanField(
        default=False,
        verbose_name="Покупка подтверждена",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "content_review"
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["is_approved"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                condition=Q(user__isnull=False),
                name="content_review_unique_product_user",
            ),
            models.UniqueConstraint(
                fields=["product", "email"],
                condition=Q(user__isnull=True) & Q(email__isnull=False),
                name="content_review_unique_product_email",
            ),
        ]

    def __str__(self):
        return f"{self.product_id} — {self.rating}"


class PageGalleryImage(models.Model):
    """Изображения для hero-блоков страниц «Магазины» и «О нас»."""

    PLACEMENT_STORES_HERO = "stores_hero"
    PLACEMENT_ABOUT_HERO = "about_hero"
    PLACEMENT_CHOICES = [
        (PLACEMENT_STORES_HERO, "Магазины — hero"),
        (PLACEMENT_ABOUT_HERO, "О нас — hero"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    placement = models.CharField(
        max_length=32,
        choices=PLACEMENT_CHOICES,
        verbose_name="Размещение",
    )
    image = models.ImageField(upload_to=page_gallery_upload_to, verbose_name="Изображение")
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="Alt-текст")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "content_pagegalleryimage"
        verbose_name = "Изображение галереи страницы"
        verbose_name_plural = "Галереи страниц"
        ordering = ["placement", "sort_order", "id"]
        indexes = [
            models.Index(fields=["placement", "is_active", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.placement} — {self.pk}"
