import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_orderitem_color_snapshot"),
        ("products", "0006_category_product_onec_codes"),
        ("stores", "0006_stock_onec_series"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockMovement",
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
                    "operation",
                    models.CharField(
                        choices=[
                            ("reserve", "Резерв"),
                            ("release", "Снятие резерва"),
                            ("deduction", "Списание"),
                            ("restock", "Возврат на склад"),
                            ("reconciliation", "Сверка"),
                            ("correction", "Корректировка"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("reserved_before", models.IntegerField(default=0)),
                ("reserved_after", models.IntegerField(default=0)),
                ("stock_quantity_before", models.IntegerField(blank=True, null=True)),
                ("stock_quantity_after", models.IntegerField(blank=True, null=True)),
                (
                    "onec_series_id",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                ("reason", models.CharField(blank=True, default="", max_length=255)),
                ("source", models.CharField(blank=True, default="", max_length=64)),
                (
                    "idempotency_key",
                    models.CharField(db_index=True, max_length=128, unique=True),
                ),
                ("success", models.BooleanField(default=True)),
                (
                    "error_message",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to="orders.order",
                    ),
                ),
                (
                    "order_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to="orders.orderitem",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to="products.product",
                    ),
                ),
                (
                    "store",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to="stores.store",
                    ),
                ),
            ],
            options={
                "verbose_name": "Складская операция",
                "verbose_name_plural": "Складские операции",
                "db_table": "stores_stock_movement",
                "ordering": ["-created_at"],
            },
        ),
    ]
