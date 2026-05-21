"""
URL-маршруты юридических endpoint'ов.
"""

from django.urls import path

from .legal_views import AnalyticsConsentView

app_name = "legal"

urlpatterns = [
    path(
        "analytics-consent/",
        AnalyticsConsentView.as_view(),
        name="analytics-consent",
    ),
]
