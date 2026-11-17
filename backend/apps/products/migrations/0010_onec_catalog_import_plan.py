# RELEASE 46.1 Stage D.2.1: OneCCatalogImportPlan storage for dry-run → plan_id → APPLY.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0009_block10_state_sync"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OneCCatalogImportPlan",
            fields=[
                (
                    "plan_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("checksum", models.CharField(db_index=True, max_length=64)),
                ("schema_version", models.PositiveSmallIntegerField()),
                ("storage_version", models.PositiveSmallIntegerField(default=1)),
                ("canonical_payload", models.JSONField()),
                ("snapshot_policy", models.CharField(db_index=True, max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ready", "Готов"),
                            ("applying", "Применяется"),
                            ("applied", "Применён"),
                            ("expired", "Истёк"),
                            ("rejected", "Отклонён"),
                        ],
                        db_index=True,
                        default="ready",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("error_detail", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="onec_catalog_import_plans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dry_run_sync_log",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="saved_import_plans",
                        to="products.onecatalogsynclog",
                    ),
                ),
            ],
            options={
                "verbose_name": "Сохранённый план импорта 1С",
                "verbose_name_plural": "Сохранённые планы импорта 1С",
                "db_table": "products_onec_catalog_import_plan",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="onecatalogimportplan",
            index=models.Index(
                fields=["status", "expires_at"],
                name="products_on_status_exp_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="onecatalogimportplan",
            index=models.Index(
                fields=["-created_at"],
                name="products_on_created_desc_idx",
            ),
        ),
    ]
