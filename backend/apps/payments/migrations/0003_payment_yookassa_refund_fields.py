from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_payment_yookassa_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="yookassa_refund_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Последний подтверждённый полный возврат (INT-004)",
                max_length=64,
                null=True,
                unique=True,
                verbose_name="refund_id ЮKassa",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="refunded_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Сумма возврата (руб.)",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="refunded_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Время подтверждённого возврата",
            ),
        ),
    ]
