# Generated manually for 152-ФЗ / GDPR-style consent tracking.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_last_login_ip"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="privacy_policy_accepted_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Согласие с политикой конфиденциальности (дата)",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="marketing_opt_in",
            field=models.BooleanField(
                default=False,
                verbose_name="Согласие на маркетинговые уведомления",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="marketing_opt_in_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Дата согласия на маркетинг",
            ),
        ),
    ]
