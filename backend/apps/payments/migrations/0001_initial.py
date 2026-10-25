import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0006_order_anonymized_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
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
                    "provider",
                    models.CharField(
                        choices=[("sber", "Сбербанк ecom")],
                        default="sber",
                        max_length=32,
                        verbose_name="Провайдер",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Создан"),
                            ("registered", "Зарегистрирован в банке"),
                            ("pending", "Ожидает оплаты"),
                            ("paid", "Оплачен"),
                            ("failed", "Ошибка / отказ"),
                            ("expired", "Истёк"),
                            ("reversed", "Отменён (reverse)"),
                            ("refunded", "Возврат"),
                            ("needs_review", "Требует сверки"),
                        ],
                        db_index=True,
                        default="created",
                        max_length=20,
                        verbose_name="Статус платежа",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="Сумма (руб.)"
                    ),
                ),
                (
                    "amount_kopecks",
                    models.PositiveBigIntegerField(verbose_name="Сумма (копейки)"),
                ),
                (
                    "currency",
                    models.CharField(
                        default="643", max_length=3, verbose_name="Валюта ISO"
                    ),
                ),
                (
                    "merchant_order_number",
                    models.CharField(
                        db_index=True,
                        max_length=36,
                        unique=True,
                        verbose_name="Номер заказа для Сбера",
                    ),
                ),
                (
                    "sber_order_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=64,
                        null=True,
                        unique=True,
                        verbose_name="orderId Сбера",
                    ),
                ),
                (
                    "form_url",
                    models.URLField(
                        blank=True,
                        default="",
                        max_length=2048,
                        verbose_name="URL платёжной страницы",
                    ),
                ),
                (
                    "sber_order_status",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="orderStatus из шлюза"
                    ),
                ),
                (
                    "action_code",
                    models.IntegerField(blank=True, null=True, verbose_name="actionCode"),
                ),
                ("error_code", models.CharField(blank=True, default="", max_length=32)),
                (
                    "error_message",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("callback_received_at", models.DateTimeField(blank=True, null=True)),
                ("last_status_checked_at", models.DateTimeField(blank=True, null=True)),
                ("register_response", models.JSONField(blank=True, default=dict)),
                ("last_status_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Платёж",
                "verbose_name_plural": "Платежи",
                "db_table": "payments_payment",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["order", "status"], name="payments_pa_order_i_7e0e0e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["created_at"], name="payments_pa_created_e4e6f7_idx"),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "paid")),
                fields=("order",),
                name="payments_one_paid_per_order",
            ),
        ),
    ]
