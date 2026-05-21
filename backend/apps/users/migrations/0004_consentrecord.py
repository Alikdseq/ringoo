import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_order_anonymized_at"),
        ("users", "0003_user_privacy_marketing_consent"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsentRecord",
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
                    "consent_type",
                    models.CharField(
                        choices=[
                            ("privacy", "Политика конфиденциальности"),
                            ("marketing", "Маркетинг"),
                            ("order_pdn", "ПДн при оформлении заказа"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "accepted_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата согласия"),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True, null=True, verbose_name="IP"
                    ),
                ),
                (
                    "policy_version",
                    models.CharField(max_length=64, verbose_name="Версия политики"),
                ),
                (
                    "user_agent",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                (
                    "order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="consent_records",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="consent_records",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Запись согласия",
                "verbose_name_plural": "Записи согласий",
                "db_table": "users_consent_record",
                "ordering": ["-accepted_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "consent_type"],
                        name="users_conse_user_id_6e0f0a_idx",
                    ),
                    models.Index(fields=["order"], name="users_conse_order_i_8c8f8b_idx"),
                ],
            },
        ),
    ]
