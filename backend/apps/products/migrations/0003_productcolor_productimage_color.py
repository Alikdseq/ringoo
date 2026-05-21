# Generated manually for ProductColor + ProductImage.color

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_product_composite_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductColor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slug", models.SlugField(max_length=100, verbose_name="Slug цвета")),
                ("label", models.CharField(max_length=255, verbose_name="Подпись")),
                (
                    "hex",
                    models.CharField(
                        blank=True,
                        help_text="Например #1C1C1E",
                        max_length=12,
                        null=True,
                        verbose_name="HEX для кружка",
                    ),
                ),
                ("sort_order", models.IntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="colors",
                        to="products.product",
                        verbose_name="Товар",
                    ),
                ),
            ],
            options={
                "verbose_name": "Цвет товара",
                "verbose_name_plural": "Цвета товаров",
                "db_table": "products_productcolor",
                "ordering": ["sort_order", "label"],
            },
        ),
        migrations.AddField(
            model_name="productimage",
            name="color",
            field=models.ForeignKey(
                blank=True,
                help_text="Пусто — общее фото (комплект, коробка и т.д.).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="images",
                to="products.productcolor",
                verbose_name="Цвет",
            ),
        ),
        migrations.AddIndex(
            model_name="productcolor",
            index=models.Index(fields=["product", "sort_order"], name="products_pr_product_6b2f0a_idx"),
        ),
        migrations.AddConstraint(
            model_name="productcolor",
            constraint=models.UniqueConstraint(fields=("product", "slug"), name="products_productcolor_product_slug_uniq"),
        ),
    ]
