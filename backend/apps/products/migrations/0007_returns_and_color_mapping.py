# ProductColor external identity fields for 1C mapping

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0006_category_product_onec_codes"),
    ]

    operations = [
        migrations.AddField(
            model_name="productcolor",
            name="barcode",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
                verbose_name="Штрихкод варианта",
            ),
        ),
        migrations.AddField(
            model_name="productcolor",
            name="mapping_status",
            field=models.CharField(
                choices=[
                    ("unmatched", "Не сопоставлено"),
                    ("matched", "Сопоставлено"),
                    ("ambiguous", "Неоднозначно"),
                    ("conflict", "Конфликт"),
                    ("inactive", "Неактивно"),
                ],
                db_index=True,
                default="unmatched",
                max_length=16,
                verbose_name="Статус сопоставления с 1С",
            ),
        ),
        migrations.AddField(
            model_name="productcolor",
            name="onec_characteristic_ref",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
                verbose_name="GUID/ссылка характеристики 1С",
            ),
        ),
        migrations.AddField(
            model_name="productcolor",
            name="onec_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Если в 1С у цвета отдельный code — указывайте здесь. Не путать с seriesId.",
                max_length=64,
                verbose_name="Код номенклатуры 1С для варианта",
            ),
        ),
        migrations.AddField(
            model_name="productcolor",
            name="sku",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
                verbose_name="Артикул варианта",
            ),
        ),
    ]
