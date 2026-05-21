"""
Unit-тесты для приложения users.
"""

from decimal import Decimal

from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.orders.services.anonymize import ANONYMIZED_FULL_NAME, ANONYMIZED_PHONE
from apps.products.models import Category, Product

from .models import ConsentRecord, CustomUser
from .services import is_valid_phone, normalize_phone, record_successful_password_login


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestPhoneNormalization(TestCase):
    """Нормализация и валидация телефона."""

    def test_normalize_phone_russia_10_digits(self):
        self.assertEqual(normalize_phone("9991234567"), "79991234567")

    def test_normalize_phone_russia_8_prefix(self):
        self.assertEqual(normalize_phone("89991234567"), "79991234567")

    def test_normalize_phone_russia_plus7(self):
        self.assertEqual(normalize_phone("+7 999 123-45-67"), "79991234567")

    def test_normalize_phone_invalid_empty(self):
        self.assertIsNone(normalize_phone(""))
        self.assertIsNone(normalize_phone("abc"))

    def test_is_valid_phone_valid(self):
        self.assertTrue(is_valid_phone("+79991234567"))
        self.assertTrue(is_valid_phone("89991234567"))
        self.assertTrue(is_valid_phone("9991234567"))

    def test_is_valid_phone_invalid(self):
        self.assertFalse(is_valid_phone(""))
        self.assertFalse(is_valid_phone("123"))
        self.assertFalse(is_valid_phone("12345678901"))


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestTokenRefreshView(TestCase):
    """POST /api/v1/auth/token/refresh/"""

    def setUp(self):
        self.client = APIClient()
        self.refresh_url = "/api/v1/auth/token/refresh/"

    def tearDown(self):
        cache.clear()

    def test_failed_login_emits_security_log(self):
        CustomUser.objects.create_user("79990001122", password="correctpass12")
        with self.assertLogs("ringoo.security.auth", level="WARNING") as cm:
            r = self.client.post(
                "/api/v1/auth/token/",
                {"username": "79990001122", "password": "wrong-password"},
                format="json",
            )
        self.assertEqual(r.status_code, 401)
        self.assertTrue(any("auth_login_failed" in x for x in cm.output))

    def test_token_refresh_success_200(self):
        CustomUser.objects.create_user("79991234567", password="secretpass123")
        login = self.client.post(
            "/api/v1/auth/token/",
            {"username": "79991234567", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.json())

    def test_token_login_when_db_phone_has_plus_prefix(self):
        """В БД остался телефон с «+», в запросе — нормализованный 7… — всё равно 200."""
        u = CustomUser.objects.create_user("79991234567", password="secretpass123")
        CustomUser.objects.filter(pk=u.pk).update(phone="+79991234567")
        login = self.client.post(
            "/api/v1/auth/token/",
            {"username": "+7 999 123-45-67", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.json())
        refresh_token = login.json()["refresh"]
        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestUserMeAndStaffAccess(TestCase):
    """GET /auth/me/ без is_staff; GET /auth/staff-access/ только для staff."""

    def setUp(self):
        self.client = APIClient()

    def test_me_response_excludes_is_staff(self):
        user = CustomUser.objects.create_user("79991112233", password="secretpass123")
        self.client.force_authenticate(user=user)
        r = self.client.get("/api/v1/auth/me/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertNotIn("is_staff", r.json())

    def test_staff_access_forbidden_for_regular_user(self):
        user = CustomUser.objects.create_user("79991112244", password="secretpass123")
        self.client.force_authenticate(user=user)
        r = self.client.get("/api/v1/auth/staff-access/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_access_ok_for_staff(self):
        user = CustomUser.objects.create_user(
            "79991112255", password="secretpass123", is_staff=True
        )
        self.client.force_authenticate(user=user)
        r = self.client.get("/api/v1/auth/staff-access/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json().get("staff"), True)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestNewLoginNotification(TestCase):
    """Письмо при успешном входе с нового IP (если есть email)."""

    def test_sends_mail_when_ip_changes(self):
        user = CustomUser.objects.create_user(
            "79994445566",
            password="secretpass123",
            email="user@example.com",
        )
        CustomUser.objects.filter(pk=user.pk).update(last_login_ip="203.0.113.1")
        req = RequestFactory().post("/api/v1/auth/token/")
        req.META["REMOTE_ADDR"] = "203.0.113.99"
        mail.outbox.clear()
        record_successful_password_login(req, user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("нового", mail.outbox[0].subject.lower())

    def test_no_mail_on_first_ip(self):
        user = CustomUser.objects.create_user(
            "79994445577",
            password="secretpass123",
            email="user2@example.com",
        )
        req = RequestFactory().post("/api/v1/auth/token/")
        req.META["REMOTE_ADDR"] = "198.51.100.5"
        mail.outbox.clear()
        record_successful_password_login(req, user)
        self.assertEqual(len(mail.outbox), 0)
        user.refresh_from_db()
        self.assertEqual(user.last_login_ip, "198.51.100.5")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestRegisterConsentAndPrivacyAPI(TestCase):
    """152-ФЗ: согласия при регистрации; экспорт и маркетинг в ЛК."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/v1/auth/register/"

    def tearDown(self):
        cache.clear()

    def test_register_requires_consent_personal_data(self):
        r = self.client.post(
            self.register_url,
            {
                "phone": "+79991112233",
                "password": "longpassword1",
                "consent_personal_data": False,
                "consent_offer": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_requires_consent_offer(self):
        r = self.client.post(
            self.register_url,
            {
                "phone": "+79991112255",
                "password": "longpassword1",
                "consent_personal_data": True,
                "consent_offer": False,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_sets_privacy_and_marketing_timestamps(self):
        r = self.client.post(
            self.register_url,
            {
                "phone": "+79991112244",
                "password": "longpassword1",
                "consent_personal_data": True,
                "consent_offer": True,
                "consent_marketing": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.json())
        user = CustomUser.objects.get(phone="79991112244")
        self.assertIsNotNone(user.privacy_policy_accepted_at)
        self.assertTrue(user.marketing_opt_in)
        self.assertIsNotNone(user.marketing_opt_in_at)

    def test_me_export_and_marketing_patch(self):
        user = CustomUser.objects.create_user("79993334455", password="longpassword1")
        self.client.force_authenticate(user=user)
        exp = self.client.get("/api/v1/auth/me/export/")
        self.assertEqual(exp.status_code, status.HTTP_200_OK)
        body = exp.json()
        self.assertIn("user", body)
        self.assertIn("delivery_addresses", body)
        self.assertIn("orders", body)
        patch = self.client.patch(
            "/api/v1/auth/me/",
            {"marketing_opt_in": True},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertTrue(patch.json().get("marketing_opt_in"))
        patch_off = self.client.patch(
            "/api/v1/auth/me/",
            {"marketing_opt_in": False},
            format="json",
        )
        self.assertEqual(patch_off.status_code, status.HTTP_200_OK)
        self.assertFalse(patch_off.json().get("marketing_opt_in"))


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestJwtLoginMergesGuestCart(TestCase):
    """После POST /auth/token/ гостевая корзина по session сливается с пользователем (без session login)."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(title="Кат", slug="cat-jwt-merge")
        self.product = Product.objects.create(
            title="Товар JWT",
            slug="product-jwt-merge",
            price=Decimal("100.00"),
            category=self.category,
            is_active=True,
        )

    def tearDown(self):
        cache.clear()

    def test_token_login_merges_guest_cart_into_user_cart(self):
        CustomUser.objects.create_user("79995550101", password="secretpass123")
        # Сессия гостя (как при просмотре каталога / корзины)
        self.client.get("/api/v1/cart/")
        add = self.client.post(
            "/api/v1/cart/items/",
            {"product": str(self.product.id), "quantity": 2},
            format="json",
        )
        self.assertIn(add.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), add.json())

        login = self.client.post(
            "/api/v1/auth/token/",
            {"username": "79995550101", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.json())
        access = login.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        cart = self.client.get("/api/v1/cart/")
        self.assertEqual(cart.status_code, status.HTTP_200_OK)
        body = cart.json()
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["quantity"], 2)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestDeleteAccountAnonymizesOrders(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            "79996667788",
            password="deletepass123",
        )
        self.order = Order.objects.create(
            user=self.user,
            order_number="ORD-TEST-ANON-01",
            full_name="Иван Иванов",
            phone="79996667788",
            email="ivan@example.com",
            delivery_type=Order.DELIVERY_PICKUP,
            payment_type=Order.PAYMENT_CASH,
            total_amount=Decimal("100.00"),
            consent_personal_data=True,
        )

    def test_delete_account_anonymizes_orders(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post(
            "/api/v1/auth/delete-account/",
            {"confirm": "DELETE_MY_ACCOUNT"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.full_name, ANONYMIZED_FULL_NAME)
        self.assertEqual(self.order.phone, ANONYMIZED_PHONE)
        self.assertIsNone(self.order.email)
        self.assertIsNotNone(self.order.anonymized_at)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    },
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False},
)
class TestConsentRecordOnRegister(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_consent_records(self):
        r = self.client.post(
            "/api/v1/auth/register/",
            {
                "phone": "79997778899",
                "password": "registerpass1",
                "consent_personal_data": True,
                "consent_offer": True,
                "consent_marketing": True,
            },
            format="json",
            HTTP_X_AUTH_COOKIES="1",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        user = CustomUser.objects.get(phone="79997778899")
        self.assertGreaterEqual(
            ConsentRecord.objects.filter(user=user).count(),
            3,
        )
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=user, consent_type=ConsentRecord.TYPE_PRIVACY
            ).exists()
        )
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=user, consent_type=ConsentRecord.TYPE_OFFER
            ).exists()
        )
