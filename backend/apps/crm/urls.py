"""
URL-маршруты CRM (заявки на отсутствующий товар).
"""

from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("missing-product/", views.MissingProductRequestCreateView.as_view(), name="missing-product-create"),
]
