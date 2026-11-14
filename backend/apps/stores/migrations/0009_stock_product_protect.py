# ONEC-023: Product deletion must not cascade-wipe Stock / reserves.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0008_map_confirmed_onec_warehouses"),
        ("products", "0009_block10_state_sync"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stock",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stock_items",
                to="products.product",
                verbose_name="Товар",
            ),
        ),
    ]
