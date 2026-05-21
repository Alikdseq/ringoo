from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_confirmation_email_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="anonymized_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Обезличен (удаление аккаунта)",
            ),
        ),
    ]
