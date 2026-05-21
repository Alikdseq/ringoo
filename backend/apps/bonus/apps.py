from django.apps import AppConfig


class BonusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bonus"
    verbose_name = "Bonus"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        from apps.bonus.signals import (
            award_bonus_on_order_confirmed,
            create_bonus_account_for_new_user,
        )

        post_save.connect(
            create_bonus_account_for_new_user,
            sender=get_user_model(),
            dispatch_uid="bonus.create_bonus_account_for_new_user",
        )
        from apps.orders.models import Order

        post_save.connect(
            award_bonus_on_order_confirmed,
            sender=Order,
            dispatch_uid="bonus.award_bonus_on_order_confirmed",
        )
