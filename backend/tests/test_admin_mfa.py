"""
Admin MFA: staff JWT without admin_mfa claim cannot use Admin API;
TOTP verify grants claim; refresh does not invent MFA.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.admin_api.permissions import RINGOO_GROUP_ORDERS
from apps.users.admin_mfa import ADMIN_MFA_CLAIM, ADMIN_MFA_CLAIM_VALUE, issue_tokens_with_admin_mfa

User = get_user_model()


def _staff(**kwargs):
    defaults = dict(
        phone="79003000001",
        password="pass12345xx",
        is_staff=True,
    )
    defaults.update(kwargs)
    password = defaults.pop("password")
    user = User.objects.create_user(**defaults)
    user.set_password(password)
    user.save()
    Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
    user.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
    return user


@override_settings(ADMIN_OTP_ENABLED=True)
class AdminMfaGateTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.staff = _staff()

    def test_password_login_marks_mfa_required_without_admin_claim(self):
        resp = self.api.post(
            "/api/v1/auth/token/",
            {"username": self.staff.phone, "password": "pass12345xx"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("admin_mfa_required"))
        self.assertFalse(resp.data.get("admin_mfa"))
        access = resp.data.get("access")
        self.assertTrue(access)
        from rest_framework_simplejwt.tokens import AccessToken

        payload = AccessToken(access)
        self.assertNotEqual(payload.get(ADMIN_MFA_CLAIM), ADMIN_MFA_CLAIM_VALUE)

    def test_staff_without_mfa_claim_denied_admin_api(self):
        refresh = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = self.api.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(resp.status_code, 403)

    def test_staff_with_mfa_claim_allowed_admin_api(self):
        access, _refresh = issue_tokens_with_admin_mfa(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.api.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(resp.status_code, 200)

    def test_customer_login_unaffected(self):
        customer = User.objects.create_user(
            phone="79003000099", password="pass12345xx", is_staff=False
        )
        resp = self.api.post(
            "/api/v1/auth/token/",
            {"username": customer.phone, "password": "pass12345xx"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("admin_mfa_required", resp.data)

    def test_refresh_without_claim_does_not_grant_mfa(self):
        refresh = RefreshToken.for_user(self.staff)
        resp = self.api.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        from rest_framework_simplejwt.tokens import AccessToken

        access = AccessToken(resp.data["access"])
        self.assertNotEqual(access.get(ADMIN_MFA_CLAIM), ADMIN_MFA_CLAIM_VALUE)

    def test_mfa_verify_unenrolled_denied(self):
        refresh = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = self.api.post(
            "/api/v1/auth/mfa/verify/",
            {"totp": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "mfa_not_enrolled")

    def test_mfa_verify_success_issues_claim(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django_otp.oath import totp

        device = TOTPDevice.objects.create(
            user=self.staff, name="default", confirmed=True
        )
        code = str(totp(device.bin_key)).zfill(6)
        refresh = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = self.api.post(
            "/api/v1/auth/mfa/verify/",
            {"totp": code},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        self.assertTrue(resp.data.get("admin_mfa"))
        from rest_framework_simplejwt.tokens import AccessToken

        access = AccessToken(resp.data["access"])
        self.assertEqual(access.get(ADMIN_MFA_CLAIM), ADMIN_MFA_CLAIM_VALUE)

    def test_staff_access_requires_mfa_claim(self):
        refresh = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = self.api.get("/api/v1/auth/staff-access/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "admin_mfa_required")

    def test_client_cannot_forge_admin_mfa_via_body(self):
        """Body/query cannot set admin_mfa; only signed JWT claim after TOTP."""
        refresh = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = self.api.post(
            "/api/v1/auth/mfa/verify/",
            {"totp": "000000", "admin_mfa": 1},
            format="json",
        )
        self.assertIn(resp.status_code, (400, 403))
        resp2 = self.api.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(resp2.status_code, 403)

    def test_refresh_preserves_mfa_claim_only_when_present(self):
        access, refresh_s = issue_tokens_with_admin_mfa(self.staff)
        resp = self.api.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_s},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        from rest_framework_simplejwt.tokens import AccessToken

        new_access = AccessToken(resp.data["access"])
        self.assertEqual(new_access.get(ADMIN_MFA_CLAIM), ADMIN_MFA_CLAIM_VALUE)
        # Old access without refresh rotation misuse: plain access still needs claim
        plain = RefreshToken.for_user(self.staff)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {plain.access_token}")
        denied = self.api.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(denied.status_code, 403)
        # Valid MFA access still works
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        ok = self.api.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(ok.status_code, 200)

    def test_blacklisted_refresh_cannot_reissue_mfa(self):
        _access, refresh_s = issue_tokens_with_admin_mfa(self.staff)
        first = self.api.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_s},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        # With ROTATE+BLACKLIST, reusing old refresh must fail
        second = self.api.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_s},
            format="json",
        )
        self.assertIn(second.status_code, (401, 400))
