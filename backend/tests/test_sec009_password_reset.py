"""SEC-009: восстановление пароля по email."""

from __future__ import annotations

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://shop.test",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec009",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sec009s",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class Sec009PasswordResetTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(
            phone="79009110001",
            password="OldPassword1!",
            email="buyer@example.com",
        )

    def test_request_known_and_unknown_same_response(self):
        r1 = self.api.post(
            "/api/v1/auth/password-reset/",
            {"email": "buyer@example.com"},
            format="json",
        )
        r2 = self.api.post(
            "/api/v1/auth/password-reset/",
            {"email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["detail"], r2.json()["detail"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password", mail.outbox[0].body)

    def test_confirm_sets_new_password_and_invalidates_old(self):
        uid = urlsafe_base64_encode(force_bytes(str(self.user.pk)))
        token = PasswordResetTokenGenerator().make_token(self.user)
        # выдать refresh до смены
        refresh = RefreshToken.for_user(self.user)
        old_refresh = str(refresh)

        resp = self.api.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "NewPassword2!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword2!"))
        self.assertFalse(self.user.check_password("OldPassword1!"))

        login = self.api.post(
            "/api/v1/auth/token/",
            {"username": self.user.phone, "password": "NewPassword2!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

        # старый refresh должен быть в blacklist (если таблица доступна)
        bad = self.api.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": old_refresh},
            format="json",
        )
        self.assertIn(bad.status_code, (401, 400))

    def test_reuse_token_fails(self):
        uid = urlsafe_base64_encode(force_bytes(str(self.user.pk)))
        token = PasswordResetTokenGenerator().make_token(self.user)
        first = self.api.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "NewPassword3!"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.api.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "NewPassword4!"},
            format="json",
        )
        self.assertEqual(second.status_code, 400)

    def test_bad_token_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(str(self.user.pk)))
        resp = self.api.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": "not-a-real-token", "new_password": "NewPassword5!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_weak_password_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(str(self.user.pk)))
        token = PasswordResetTokenGenerator().make_token(self.user)
        resp = self.api.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
