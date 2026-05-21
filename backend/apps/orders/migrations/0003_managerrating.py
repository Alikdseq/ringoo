# Оценки менеджеров по заказу (ТЗ EPIC 2, IMPROVEMENT_PLAN шаг 8)

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_order_consent_personal_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManagerRating",
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
                    "rating",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "1"),
                            (2, "2"),
                            (3, "3"),
                            (4, "4"),
                            (5, "5"),
                        ],
                        verbose_name="Оценка (1–5)",
                    ),
                ),
                (
                    "comment",
                    models.TextField(
                        blank=True, null=True, verbose_name="Комментарий"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата оценки"
                    ),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="manager_rating",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Оценка менеджера",
                "verbose_name_plural": "Оценки менеджеров",
                "db_table": "orders_managerrating",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="managerrating",
            index=models.Index(
                fields=["rating"], name="orders_mana_rating_8a1f2b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="managerrating",
            index=models.Index(
                fields=["created_at"], name="orders_mana_created_9c3d4e_idx"
            ),
        ),
    ]
