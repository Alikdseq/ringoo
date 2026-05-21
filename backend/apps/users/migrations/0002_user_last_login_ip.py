# Добавление last_login_ip для уведомления о входе с нового IP.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial_user_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="last_login_ip",
            field=models.CharField(
                blank=True,
                help_text="Для уведомления о входе с нового адреса (если указан email).",
                max_length=45,
                null=True,
                verbose_name="IP последнего успешного входа",
            ),
        ),
    ]
