"""
URL-маршруты корзины.
"""

from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.CartView.as_view(), name="cart"),
    path("items/", views.CartItemCreateView.as_view(), name="cart-item-create"),
    path("items/<uuid:pk>/", views.CartItemDetailView.as_view(), name="cart-item-detail"),
    path("clear/", views.CartClearView.as_view(), name="cart-clear"),
]
