# Generated manually for catalog main-section flags on existing 1C Category nodes.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0011_onec_plan_execution_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="is_catalog_main",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "Если True — существующий узел 1С показывается на главной странице "
                    "каталога. Не создаёт новую иерархию и не меняет parent/товары."
                ),
                verbose_name="Главный раздел каталога",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="catalog_main_sort",
            field=models.IntegerField(
                default=0,
                help_text="Сортировка среди is_catalog_main (меньше — выше).",
                verbose_name="Порядок главного раздела",
            ),
        ),
        migrations.AddIndex(
            model_name="category",
            index=models.Index(
                fields=["is_catalog_main", "catalog_main_sort"],
                name="products_cat_main_sort_idx",
            ),
        ),
    ]
