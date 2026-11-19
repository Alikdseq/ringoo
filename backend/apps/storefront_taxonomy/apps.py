from django.apps import AppConfig


class StorefrontTaxonomyConfig(AppConfig):
    """
    Экспериментальная витринная классификация (S1.x).

    НЕ используется публичным каталогом Ringoo: витрина строится на products.Category
    (иерархия 1С) и флагах is_catalog_main. Таблицы приложения сохраняются для
    совместимости БД; новые назначения товаров через эту систему в витрину не идут.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.storefront_taxonomy"
    verbose_name = "Витринная таксономия (не используется витриной)"
