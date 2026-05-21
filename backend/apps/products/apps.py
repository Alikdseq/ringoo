from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
    verbose_name = 'Products'

    def ready(self):
        from .signals import _connect_cache_invalidation
        _connect_cache_invalidation()
