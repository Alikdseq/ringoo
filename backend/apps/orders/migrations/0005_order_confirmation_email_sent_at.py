from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_add_manager_fk_to_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="confirmation_email_sent_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Письмо подтверждения заказа отправлено",
                help_text="Идемпотентность Celery: повторная доставка задачи не шлёт письмо снова.",
            ),
        ),
    ]
