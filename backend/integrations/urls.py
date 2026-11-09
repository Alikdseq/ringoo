"""Публичные маршруты интеграций (не путать с admin/onec/sync)."""

from django.urls import path

from integrations.onec.inbound_views import OneCOrderStatusInboundView

app_name = "integrations"

urlpatterns = [
    path(
        "1c/orders/status/",
        OneCOrderStatusInboundView.as_view(),
        name="onec-order-status-inbound",
    ),
]
