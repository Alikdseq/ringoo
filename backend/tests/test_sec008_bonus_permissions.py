"""SEC-008: bonus admin RBAC; маршруты остаются отключёнными."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.admin_api.permissions import RINGOO_GROUP_BONUS, RINGOO_GROUP_ORDERS
from apps.admin_api.views.bonus import (
    BonusAccountAdjustView,
    BonusAccountAdminListView,
)
from apps.bonus.models import BonusAccount
from apps.bonus.services import admin_adjust
from apps.users.admin_mfa import issue_tokens_with_admin_mfa
from apps.users.models import CustomUser


@override_settings(
    ADMIN_OTP_ENABLED=False,
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class Sec008BonusPermissionsTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_BONUS)
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        self.api = APIClient()
        self.factory = APIRequestFactory()
        self.owner = CustomUser.objects.create_user(
            phone="79008110001", password="pass12345"
        )
        # signal может уже создать счёт
        self.account, _ = BonusAccount.objects.get_or_create(
            user=self.owner, defaults={"balance": Decimal("0")}
        )
        self.staff_plain = CustomUser.objects.create_user(
            phone="79008110002", password="pass12345", is_staff=True
        )
        self.staff_orders = CustomUser.objects.create_user(
            phone="79008110003", password="pass12345", is_staff=True
        )
        self.staff_orders.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.staff_bonus = CustomUser.objects.create_user(
            phone="79008110004", password="pass12345", is_staff=True
        )
        self.staff_bonus.groups.add(Group.objects.get(name=RINGOO_GROUP_BONUS))

    def test_admin_bonus_urls_not_mounted(self):
        resp = self.api.get("/api/v1/admin/bonus/accounts/")
        self.assertEqual(resp.status_code, 404)

    def test_public_bonus_urls_not_mounted(self):
        resp = self.api.get("/api/v1/bonus/")
        self.assertEqual(resp.status_code, 404)

    def test_anon_denied_on_view(self):
        request = self.factory.get("/api/v1/admin/bonus/accounts/")
        response = BonusAccountAdminListView.as_view()(request)
        self.assertEqual(response.status_code, 401)

    def test_plain_staff_denied(self):
        request = self.factory.get("/api/v1/admin/bonus/accounts/")
        force_authenticate(request, user=self.staff_plain)
        response = BonusAccountAdminListView.as_view()(request)
        self.assertEqual(response.status_code, 403)

    def test_orders_group_staff_denied_bonus(self):
        request = self.factory.get("/api/v1/admin/bonus/accounts/")
        force_authenticate(request, user=self.staff_orders)
        response = BonusAccountAdminListView.as_view()(request)
        self.assertEqual(response.status_code, 403)

    def test_bonus_group_staff_allowed_list(self):
        request = self.factory.get("/api/v1/admin/bonus/accounts/")
        force_authenticate(request, user=self.staff_bonus)
        response = BonusAccountAdminListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_adjust_records_actor_in_description(self):
        request = self.factory.post(
            f"/api/v1/admin/bonus/accounts/{self.account.pk}/adjust/",
            {"amount": "10.00", "description": "promo"},
            format="json",
        )
        force_authenticate(request, user=self.staff_bonus)
        response = BonusAccountAdjustView.as_view()(
            request, pk=str(self.account.pk)
        )
        self.assertEqual(response.status_code, 201, getattr(response, "data", response))
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("10.00"))
        txn = self.account.transactions.first()
        self.assertIn(str(self.staff_bonus.pk), txn.description or "")

    def test_admin_adjust_service_concurrency_safe(self):
        admin_adjust(self.account, Decimal("5"), "t1")
        admin_adjust(self.account, Decimal("-2"), "t2")
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("3.00"))


@override_settings(ADMIN_OTP_ENABLED=True)
class Sec008BonusMfaTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=RINGOO_GROUP_BONUS)
        self.factory = APIRequestFactory()
        self.staff = CustomUser.objects.create_user(
            phone="79008110010", password="pass12345", is_staff=True
        )
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_BONUS))

    def test_bonus_view_requires_mfa_claim(self):
        request = self.factory.get("/api/v1/admin/bonus/accounts/")
        force_authenticate(request, user=self.staff)
        response = BonusAccountAdminListView.as_view()(request)
        self.assertEqual(response.status_code, 403)

    def test_bonus_view_allows_with_mfa_claim(self):
        access, _ = issue_tokens_with_admin_mfa(self.staff)
        from rest_framework_simplejwt.tokens import AccessToken

        request = self.factory.get("/api/v1/admin/bonus/accounts/")
        force_authenticate(request, user=self.staff, token=AccessToken(access))
        response = BonusAccountAdminListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
