from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_consentrecord"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="onec_partner_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="UUID partnerId из 1С. При наличии повторная регистрация в 1С не выполняется.",
                max_length=64,
                null=True,
                unique=True,
                verbose_name="ID партнёра в 1С",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="onec_partner_status",
            field=models.CharField(
                choices=[
                    ("none", "Не регистрировался"),
                    ("synced", "Синхронизирован"),
                    ("pending_review", "Требует сверки с 1С"),
                    ("error", "Ошибка интеграции"),
                ],
                db_index=True,
                default="none",
                max_length=32,
                verbose_name="Статус партнёра 1С",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="onec_partner_synced_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Дата синхронизации партнёра 1С",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="onec_partner_last_error",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Техническое сообщение для админов; пользователю не показывается.",
                max_length=500,
                verbose_name="Последняя ошибка регистрации в 1С",
            ),
        ),
    ]
