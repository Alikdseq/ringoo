"""
URL-маршруты каталога (категории и товары).
"""

from django.urls import path

from apps.stores import views as stores_views

from . import views

app_name = "products"

urlpatterns = [
    path("categories/", views.CategoryViewSet.as_view({"get": "list"}), name="category-list"),
    path(
        "categories/<uuid:pk>/",
        views.CategoryViewSet.as_view({"get": "retrieve"}),
        name="category-detail",
    ),
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/brands/", views.ProductBrandsListView.as_view(), name="product-brands"),
    path(
        "products/autocomplete/",
        views.ProductAutocompleteView.as_view(),
        name="product-autocomplete",
    ),
    path(
        "products/<slug:slug>/",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
    path(
        "products/<uuid:pk>/stock/",
        stores_views.ProductStockView.as_view(),
        name="product-stock",
    ),
]
