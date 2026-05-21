from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_productcolor_price"),
        ("cart", "0001_cart_and_cartitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="color",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cart_items",
                to="products.productcolor",
                verbose_name="Цвет",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="cartitem",
            name="cart_cartitem_cart_product_store_uniq",
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                fields=("cart", "product", "store", "color"),
                name="cart_cartitem_cart_product_store_color_uniq",
            ),
        ),
    ]
