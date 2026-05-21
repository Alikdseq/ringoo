"""
URL-маршруты бонусной системы (задача 2.1.5).
"""

from django.urls import path

from . import views

app_name = "bonus"

urlpatterns = [
    path("", views.BonusAccountView.as_view(), name="account"),
    path("transactions/", views.BonusTransactionsView.as_view(), name="transactions"),
]
