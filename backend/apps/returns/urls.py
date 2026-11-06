from django.urls import path

from apps.returns.views import (
    AdminReturnDetailView,
    AdminReturnInspectView,
    AdminReturnListView,
    AdminReturnRefundView,
    AdminReturnTransitionView,
    CustomerReturnCreateView,
    CustomerReturnDetailView,
    CustomerReturnListView,
)

app_name = "returns"

urlpatterns = [
    path("", CustomerReturnListView.as_view(), name="list"),
    path("create/", CustomerReturnCreateView.as_view(), name="create"),
    path("<uuid:pk>/", CustomerReturnDetailView.as_view(), name="detail"),
]
