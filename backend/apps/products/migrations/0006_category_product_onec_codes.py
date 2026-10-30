from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_product_brand_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="onec_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Внешний идентификатор категории из 1С (Папка.code). Не путать со slug сайта.",
                max_length=64,
                null=True,
                unique=True,
                verbose_name="Код папки в 1С",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="onec_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Внешний идентификатор товара из 1С (Товар.code). Один код — одна карточка.",
                max_length=64,
                null=True,
                unique=True,
                verbose_name="Код номенклатуры в 1С",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="onec_type",
            field=models.CharField(
                blank=True,
                help_text="Значение Товар.type из выгрузки (Телефоны, Аксессуары и т.д.).",
                max_length=64,
                null=True,
                verbose_name="Вид номенклатуры 1С",
            ),
        ),
    ]
