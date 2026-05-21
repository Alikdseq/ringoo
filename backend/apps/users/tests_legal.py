"""
Тесты юридических endpoint'ов (согласие на аналитику).
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import ConsentRecord


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False})
class AnalyticsConsentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("api_v1:legal:analytics-consent")

    def test_accepts_consent_and_creates_record(self):
        response = self.client.post(self.url, {"consent": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            ConsentRecord.objects.filter(
                consent_type=ConsentRecord.TYPE_ANALYTICS
            ).exists()
        )

    def test_reject_does_not_create_record(self):
        before = ConsentRecord.objects.filter(
            consent_type=ConsentRecord.TYPE_ANALYTICS
        ).count()
        response = self.client.post(self.url, {"consent": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        after = ConsentRecord.objects.filter(
            consent_type=ConsentRecord.TYPE_ANALYTICS
        ).count()
        self.assertEqual(before, after)
