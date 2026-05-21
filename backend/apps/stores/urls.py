"""
URL-маршруты магазинов и остатков.
"""

from django.urls import path

from . import views

app_name = "stores"

urlpatterns = [
    path(
        "managers/by-slug/<str:slug>/reviews/",
        views.ManagerReviewsBySlugView.as_view(),
        name="manager-reviews-by-slug",
    ),
    path(
        "managers/by-slug/<str:slug>/",
        views.ManagerDetailBySlugView.as_view(),
        name="manager-detail-by-slug",
    ),
    path("managers/", views.ManagerListView.as_view(), name="manager-list"),
    path(
        "by-slug/<str:slug>/products/",
        views.StoreProductsBySlugView.as_view(),
        name="store-products-by-slug",
    ),
    path(
        "by-slug/<str:slug>/",
        views.StoreBySlugView.as_view(),
        name="store-by-slug",
    ),
    path("", views.StoreListView.as_view(), name="store-list"),
    path("<uuid:pk>/stock/", views.StockListView.as_view(), name="store-stock"),
    path("<uuid:pk>/", views.StoreDetailView.as_view(), name="store-detail"),
]
