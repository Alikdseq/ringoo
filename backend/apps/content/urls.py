"""
URL-маршруты контента (задача 2.2.6).
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "content"

router = DefaultRouter()
router.register(r"tags", views.TagViewSet, basename="tag")
router.register(r"articles", views.ArticleViewSet, basename="article")
router.register(r"news", views.NewsViewSet, basename="news")
router.register(r"reviews", views.ReviewViewSet, basename="review")

urlpatterns = [
    path("page-gallery/", views.PageGalleryListView.as_view(), name="page-gallery-list"),
    path("", include(router.urls)),
]
