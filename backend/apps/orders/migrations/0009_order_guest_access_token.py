from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0008_order_checkout_cart_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="guest_access_token_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
                verbose_name="Хеш guest access token",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="guest_access_token_expires_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Срок действия guest access token",
            ),
        ),
    ]
