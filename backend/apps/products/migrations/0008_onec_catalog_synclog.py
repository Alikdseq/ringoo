# Generated manually for OneCCatalogSyncLog only (no unrelated schema churn).

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0007_returns_and_color_mapping"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OneCCatalogSyncLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("run_id", models.CharField(db_index=True, max_length=64, unique=True)),
                (
                    "sync_type",
                    models.CharField(
                        choices=[
                            ("catalog", "Каталог (категории/товары/остатки)"),
                            ("probe", "Проверка подключения"),
                        ],
                        db_index=True,
                        default="catalog",
                        max_length=32,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("api", "HTTP API 1С"),
                            ("file", "XML-файлы"),
                            ("fixture", "Фикстуры/тесты"),
                        ],
                        default="api",
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает"),
                            ("running", "Выполняется"),
                            ("success", "Успех"),
                            ("partial_success", "Частичный успех"),
                            ("failed", "Ошибка"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("dry_run", models.BooleanField(default=True)),
                ("started_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("records_received", models.PositiveIntegerField(default=0)),
                ("categories_created", models.PositiveIntegerField(default=0)),
                ("categories_updated", models.PositiveIntegerField(default=0)),
                ("categories_skipped", models.PositiveIntegerField(default=0)),
                ("products_created", models.PositiveIntegerField(default=0)),
                ("products_updated", models.PositiveIntegerField(default=0)),
                ("products_skipped", models.PositiveIntegerField(default=0)),
                ("stocks_upserted", models.PositiveIntegerField(default=0)),
                ("stocks_skipped", models.PositiveIntegerField(default=0)),
                ("errors_count", models.PositiveIntegerField(default=0)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("error_messages", models.JSONField(blank=True, default=list)),
                ("celery_task_id", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "triggered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="onec_catalog_sync_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Журнал синхронизации 1С",
                "verbose_name_plural": "Журнал синхронизации 1С",
                "db_table": "products_onec_catalog_synclog",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="oneccatalogsynclog",
            index=models.Index(fields=["sync_type", "-started_at"], name="products_on_sync_ty_4ad8b8_idx"),
        ),
        migrations.AddIndex(
            model_name="oneccatalogsynclog",
            index=models.Index(fields=["status", "-created_at"], name="products_on_status_f06af9_idx"),
        ),
        migrations.AddIndex(
            model_name="oneccatalogsynclog",
            index=models.Index(fields=["dry_run", "-created_at"], name="products_on_dry_run_cd2da0_idx"),
        ),
    ]
