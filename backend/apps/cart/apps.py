from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cart'
    verbose_name = 'Cart'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from .signals import merge_cart_on_login

        user_logged_in.connect(merge_cart_on_login, dispatch_uid="cart.merge_on_login")
