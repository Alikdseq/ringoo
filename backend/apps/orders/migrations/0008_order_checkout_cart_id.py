from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_onec_sync_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="checkout_cart_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text=(
                    "Для online: id корзины сохраняется при создании заказа; "
                    "позиции корзины удаляются только после подтверждённой оплаты."
                ),
                null=True,
                verbose_name="Корзина checkout (online)",
            ),
        ),
    ]
