# Generated manually for wishlist app (ТЗ EPIC 3 — избранные товары)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("products", "0001_catalog_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WishlistItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата добавления"
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wishlist_items",
                        to="products.product",
                        verbose_name="Товар",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wishlist_items",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Избранный товар",
                "verbose_name_plural": "Избранные товары",
                "db_table": "wishlist_wishlistitem",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="wishlistitem",
            index=models.Index(fields=["user"], name="wishlist_wi_user_id_7a8c2a_idx"),
        ),
        migrations.AddIndex(
            model_name="wishlistitem",
            index=models.Index(fields=["product"], name="wishlist_wi_product_2b9f3c_idx"),
        ),
        migrations.AddConstraint(
            model_name="wishlistitem",
            constraint=models.UniqueConstraint(
                fields=("user", "product"), name="wishlist_user_product_uniq"
            ),
        ),
    ]
