from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_productcolor_price"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["brand"], name="products_product_brand_idx"),
        ),
    ]
