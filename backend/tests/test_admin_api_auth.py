"""
Admin API: staff, RBAC по группам Django.
"""

from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.admin_api.permissions import RINGOO_GROUP_CATALOG, RINGOO_GROUP_ORDERS
from apps.orders.models import Order
from apps.users.models import CustomUser


class TestAdminAPIAuth(TestCase):
    def setUp(self):
        self.client = APIClient()
        Group.objects.get_or_create(name=RINGOO_GROUP_ORDERS)
        Group.objects.get_or_create(name=RINGOO_GROUP_CATALOG)
        self.staff = CustomUser.objects.create_user(
            "79990003333",
            password="staffpass123",
            is_staff=True,
        )
        self.user = CustomUser.objects.create_user(
            "79990004444",
            password="userpass123",
        )

    def test_non_staff_forbidden(self):
        self.client.force_authenticate(self.user)
        r = self.client.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(r.status_code, 403)

    def test_staff_without_group_forbidden(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(r.status_code, 403)

    def test_staff_with_orders_group_dashboard_ok(self):
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.client.force_authenticate(self.staff)
        r = self.client.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(r.status_code, 200)

    def test_staff_orders_group_cannot_access_catalog(self):
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_ORDERS))
        self.client.force_authenticate(self.staff)
        r = self.client.get("/api/v1/admin/products/")
        self.assertEqual(r.status_code, 403)

    def test_staff_catalog_group_can_list_products(self):
        self.staff.groups.add(Group.objects.get(name=RINGOO_GROUP_CATALOG))
        self.client.force_authenticate(self.staff)
        r = self.client.get("/api/v1/admin/products/")
        self.assertEqual(r.status_code, 200)
