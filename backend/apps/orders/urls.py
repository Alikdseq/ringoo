"""
URL-маршруты заказов.
"""

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.OrderListCreateView.as_view(), name="order-list-create"),
    path("track/", views.OrderTrackView.as_view(), name="order-track"),
    path("status/", views.OrderStatusView.as_view(), name="order-status"),
    path("rate/", views.OrderRateView.as_view(), name="order-rate"),
    path(
        "ratings-summary/",
        views.ManagerRatingSummaryView.as_view(),
        name="ratings-summary",
    ),
    path("<uuid:pk>/reorder/", views.OrderReorderView.as_view(), name="order-reorder"),
    path("<uuid:pk>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
    path("<uuid:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
]
