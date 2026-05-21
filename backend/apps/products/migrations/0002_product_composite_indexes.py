# Составные индексы для списка каталога (highload, IMPROVEMENT_PLAN шаг 6)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_catalog_models"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["is_active", "category"],
                name="products_prod_active_cat_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["is_active", "-created_at"],
                name="products_prod_act_created_idx",
            ),
        ),
    ]
