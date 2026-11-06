from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0009_order_guest_access_token"),
        ("products", "0004_productcolor_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="color",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="order_items",
                to="products.productcolor",
                verbose_name="Цвет (ссылка)",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="color_label",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Название цвета (снимок)",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="color_slug",
            field=models.SlugField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="Slug цвета (снимок)",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="color_hex",
            field=models.CharField(
                blank=True,
                default="",
                max_length=12,
                verbose_name="HEX цвета (снимок)",
            ),
        ),
    ]
