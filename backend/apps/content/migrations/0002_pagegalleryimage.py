# Generated manually for PageGalleryImage

import uuid

import apps.content.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0001_content_tag_article_news_review"),
    ]

    operations = [
        migrations.CreateModel(
            name="PageGalleryImage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "placement",
                    models.CharField(
                        choices=[
                            ("stores_hero", "Магазины — hero"),
                            ("about_hero", "О нас — hero"),
                        ],
                        max_length=32,
                        verbose_name="Размещение",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        upload_to=apps.content.models.page_gallery_upload_to,
                        verbose_name="Изображение",
                    ),
                ),
                ("alt_text", models.CharField(blank=True, max_length=255, verbose_name="Alt-текст")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активно")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
            ],
            options={
                "verbose_name": "Изображение галереи страницы",
                "verbose_name_plural": "Галереи страниц",
                "db_table": "content_pagegalleryimage",
                "ordering": ["placement", "sort_order", "id"],
                "indexes": [
                    models.Index(
                        fields=["placement", "is_active", "sort_order"],
                        name="content_pag_placeme_idx",
                    )
                ],
            },
        ),
    ]
