from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_payment_yookassa_refund_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentRefund",
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
                    "provider_refund_id",
                    models.CharField(
                        db_index=True,
                        max_length=64,
                        unique=True,
                        verbose_name="refund_id провайдера",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="Сумма"
                    ),
                ),
                ("currency", models.CharField(default="RUB", max_length=3)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="refund_lines",
                        to="payments.payment",
                        verbose_name="Платёж",
                    ),
                ),
            ],
            options={
                "verbose_name": "Строка возврата",
                "verbose_name_plural": "Строки возврата",
                "db_table": "payments_payment_refund",
                "ordering": ["created_at"],
            },
        ),
    ]
