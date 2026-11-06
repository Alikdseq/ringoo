from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="provider",
            field=models.CharField(
                choices=[("sber", "Сбербанк ecom"), ("yookassa", "ЮKassa")],
                default="sber",
                max_length=32,
                verbose_name="Провайдер",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="yookassa_payment_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                unique=True,
                verbose_name="payment_id ЮKassa",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="is_test",
            field=models.BooleanField(
                default=False,
                help_text="True для тестового магазина ЮKassa / тестового контура",
                verbose_name="Тестовый платёж",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="merchant_order_number",
            field=models.CharField(
                db_index=True,
                max_length=36,
                unique=True,
                verbose_name="Внутренний номер платежа (idempotence)",
            ),
        ),
    ]
