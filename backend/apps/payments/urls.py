from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "sber/callback/",
        views.SberCallbackView.as_view(),
        name="sber-callback",
    ),
]
