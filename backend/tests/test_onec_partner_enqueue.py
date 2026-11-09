"""Регистрация не падает; partner sync ставится только при флагах."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()


@override_settings(
    ADMIN_OTP_ENABLED=False,
    ONE_C_API_ENABLED=False,
    ONE_C_SYNC_PARTNER_ON_REGISTER=False,
)
class PartnerEnqueueTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_succeeds_without_onec(self):
        resp = self.client.post(
            "/api/v1/auth/register/",
            {
                "phone": "79007778899",
                "password": "longpassword1",
                "first_name": "Иван",
                "last_name": "Тестов",
                "consent_personal_data": True,
                "consent_offer": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        user = User.objects.get(phone="79007778899")
        self.assertFalse(user.onec_partner_id)

    @override_settings(ONE_C_API_ENABLED=True, ONE_C_SYNC_PARTNER_ON_REGISTER=True)
    @patch("apps.users.tasks.sync_user_partner_to_onec_task.delay")
    def test_register_enqueues_partner_task(self, delay_mock):
        resp = self.client.post(
            "/api/v1/auth/register/",
            {
                "phone": "79007778800",
                "password": "longpassword1",
                "first_name": "Иван",
                "last_name": "Тестов",
                "consent_personal_data": True,
                "consent_offer": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(delay_mock.called)

    @override_settings(ONE_C_API_ENABLED=True, ONE_C_SYNC_PARTNER_ON_REGISTER=True)
    def test_partner_register_idempotent_skips_second_call(self):
        from unittest.mock import MagicMock

        from integrations.onec.registration import register_user_in_onec

        user = User.objects.create_user(
            phone="79007778811",
            password="longpassword1",
            first_name="Иван",
            last_name="Тестов",
        )
        mock_client = MagicMock()
        mock_client.register_partner.return_value = {
            "ClientId": "guid-partner-1",
            "created": True,
        }

        first = register_user_in_onec(user, client=mock_client)
        self.assertFalse(first.skipped)
        user.refresh_from_db()
        self.assertEqual(user.onec_partner_id, "guid-partner-1")

        second = register_user_in_onec(user, client=mock_client)
        self.assertTrue(second.skipped)
        self.assertEqual(mock_client.register_partner.call_count, 1)
