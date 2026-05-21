"""
API v1 URL configuration.
"""

from django.urls import path, include

app_name = 'api_v1'

urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("products/", include("apps.products.urls")),
    path("stores/", include("apps.stores.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    # Бонусы: приложение apps.bonus остаётся в проекте, публичный API временно отключён.
    # path("bonus/", include("apps.bonus.urls")),
    path("content/", include("apps.content.urls")),
    path("promocodes/", include("apps.promotions.urls")),
    path("promotions/", include("apps.promotions.promotion_urls")),
    path("crm/", include("apps.crm.urls")),
    path("legal/", include("apps.users.legal_urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("admin/", include("apps.admin_api.urls")),
]
