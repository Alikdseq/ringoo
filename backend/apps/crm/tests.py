"""
Unit-тесты приложения CRM (заявки на отсутствующий товар, задача 2.4.4).
"""

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import ConsentRecord, CustomUser

from .models import MissingProductRequest
from .tasks import send_missing_product_request_to_crm


class MissingProductRequestModelTest(TestCase):
    def test_create_minimal(self):
        req = MissingProductRequest.objects.create(
            product_name="Товар X",
            contact_phone="+79991234567",
        )
        self.assertIsNotNone(req.id)
        self.assertEqual(req.status, MissingProductRequest.STATUS_NEW)
        self.assertIsNone(req.user_id)
        self.assertIsNone(req.contact_email)
        self.assertIsNone(req.comment)

    def test_create_with_user(self):
        user = CustomUser.objects.create_user(
            phone="+79990000000",
            username="+79990000000",
            email="user@test.com",
        )
        req = MissingProductRequest.objects.create(
            user=user,
            product_name="Товар Y",
            contact_phone="+79990000000",
            contact_email="user@test.com",
            comment="Нужен срочно",
        )
        self.assertEqual(req.user, user)
        self.assertEqual(req.contact_email, "user@test.com")


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False})
class MissingProductRequestCreateAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("api_v1:crm:missing-product-create")

    @patch("apps.crm.views.send_missing_product_request_to_crm")
    def test_create_anonymous(self, mock_task):
        data = {
            "product_name": "Телефон XYZ",
            "contact_phone": "+79991234567",
            "contact_email": "guest@example.com",
            "comment": "Ищу этот товар",
            "consent_personal_data": True,
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            ConsentRecord.objects.filter(consent_type=ConsentRecord.TYPE_CRM_LEAD).exists()
        )
        self.assertIn("id", response.data)
        self.assertEqual(response.data["product_name"], data["product_name"])
        self.assertEqual(response.data["contact_phone"], data["contact_phone"])
        mock_task.delay.assert_called_once()
        call_arg = mock_task.delay.call_args[0][0]
        self.assertEqual(call_arg, response.data["id"])

    @patch("apps.crm.views.send_missing_product_request_to_crm")
    def test_create_authenticated_sets_user(self, mock_task):
        user = CustomUser.objects.create_user(
            phone="+79997777777",
            username="+79997777777",
            email="auth@test.com",
        )
        self.client.force_authenticate(user=user)
        data = {
            "product_name": "Товар",
            "contact_phone": "+79997777777",
            "consent_personal_data": True,
            "consent_marketing": True,
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 201)
        req = MissingProductRequest.objects.get(id=response.data["id"])
        self.assertEqual(req.user, user)

    def test_create_validation_phone_required(self):
        response = self.client.post(
            self.url,
            {"product_name": "Товар"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_requires_consent_personal_data(self):
        response = self.client.post(
            self.url,
            {
                "product_name": "Товар",
                "contact_phone": "+79991234567",
                "consent_personal_data": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class SendMissingProductRequestToCrmTaskTest(TestCase):
    def test_task_logs_and_does_not_raise(self):
        req = MissingProductRequest.objects.create(
            product_name="Товар",
            contact_phone="+79991234567",
        )
        result = send_missing_product_request_to_crm(str(req.id))
        self.assertIsNone(result)

    def test_task_handles_missing_request(self):
        result = send_missing_product_request_to_crm("00000000-0000-0000-0000-000000000000")
        self.assertIsNone(result)
