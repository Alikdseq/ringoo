"""
URL-маршруты избранного.
"""

from django.urls import path

from . import views

app_name = "wishlist"

urlpatterns = [
    path("", views.WishlistListView.as_view(), name="wishlist-list"),
    path(
        "<uuid:product_id>/",
        views.WishlistItemDetailView.as_view(),
        name="wishlist-item-detail",
    ),
]
