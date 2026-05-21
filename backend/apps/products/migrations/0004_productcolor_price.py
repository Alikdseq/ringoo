from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_productcolor_productimage_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="productcolor",
            name="price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Пусто — используется цена товара.",
                max_digits=12,
                null=True,
                verbose_name="Цена варианта",
            ),
        ),
        migrations.AddField(
            model_name="productcolor",
            name="old_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Старая цена варианта",
            ),
        ),
    ]
