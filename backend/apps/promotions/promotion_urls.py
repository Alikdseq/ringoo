"""
URL-маршруты списка акций (GET /api/v1/promotions/).
"""

from django.urls import path

from . import views

app_name = "promotions"

urlpatterns = [
    path("", views.PromotionListView.as_view(), name="list"),
]
