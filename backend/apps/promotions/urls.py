"""
URL-маршруты промокодов (задача 2.3.4).
"""

from django.urls import path

from . import views

app_name = "promocodes"

urlpatterns = [
    path("validate/", views.PromoCodeValidateView.as_view(), name="validate"),
]
