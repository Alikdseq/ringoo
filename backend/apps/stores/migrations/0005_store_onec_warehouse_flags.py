from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0004_store_page_and_manager_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="store",
            name="onec_warehouse_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Внешний идентификатор склада (Товар.skladID).",
                max_length=64,
                null=True,
                unique=True,
                verbose_name="ID склада в 1С",
            ),
        ),
        migrations.AddField(
            model_name="store",
            name="onec_warehouse_name",
            field=models.CharField(
                blank=True,
                help_text="Как в выгрузке (Товар.sklad), например Apple Room.",
                max_length=255,
                null=True,
                verbose_name="Название склада в 1С",
            ),
        ),
        migrations.AddField(
            model_name="store",
            name="is_warehouse",
            field=models.BooleanField(
                default=False,
                help_text="True для складов вроде Apple Room: остаток учитывается, самовывоз не предлагается.",
                verbose_name="Склад (не точка самовывоза)",
            ),
        ),
    ]
