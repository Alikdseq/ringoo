from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0005_store_onec_warehouse_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="stock",
            name="onec_series_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="UUID серии; пустая строка — товар без серии на этом складе",
                max_length=64,
                verbose_name="seriesId 1С",
            ),
        ),
        migrations.AddField(
            model_name="stock",
            name="onec_series_name",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Название серии 1С",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="stock",
            name="stores_stock_product_store_uniq",
        ),
        migrations.AddConstraint(
            model_name="stock",
            constraint=models.UniqueConstraint(
                fields=("product", "store", "onec_series_id"),
                name="stores_stock_product_store_series_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="stock",
            index=models.Index(
                fields=["onec_series_id"],
                name="stores_stoc_onec_se_4b8e1a_idx",
            ),
        ),
    ]
