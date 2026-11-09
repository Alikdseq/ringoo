"""
Представления для пользователя и аутентификации.

Модель угроз (JWT + csrf_exempt на token/register/refresh/logout):
- Основной поток — Bearer JWT в заголовке; SessionAuthentication включён в DRF для админки/сессии
  гостевой корзины. Для запросов с JWT в Authorization CSRF не требуется.
- Эндпоинты входа/регистрации/refresh помечены csrf_exempt, т.к. это не browser form POST к
  session-cookie, а JSON API (как типично для SPA + SimpleJWT). При смешении cookie-сессии и
  опасных действиях через браузер держите SameSite и не храните секреты в JS — см. HttpOnly-куки JWT.
"""

import logging
from typing import ClassVar

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.db import transaction

from apps.cart.services import merge_guest_cart_into_user
from config.throttling import (
    AuthLoginAnonThrottle,
    AuthMfaVerifyUserThrottle,
    AuthRefreshAnonThrottle,
    AuthRegisterAnonThrottle,
)

from .admin_mfa import (
    ADMIN_MFA_CLAIM,
    ADMIN_MFA_CLAIM_VALUE,
    admin_otp_required,
    issue_tokens_with_admin_mfa,
    request_has_admin_mfa,
    staff_needs_mfa_step,
    user_has_confirmed_totp,
    verify_totp_code,
)
from .jwt_cookies import (
    clear_jwt_cookies,
    client_uses_cookie_auth,
    set_jwt_cookies,
    strip_tokens_from_response_data,
)
from .models import CustomUser, DeliveryAddress, UserProfile
from .serializers import (
    DeliveryAddressSerializer,
    MarketingOptInSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .security_logging import log_login_failed, log_token_refresh_failed
from .services import normalize_phone, record_successful_password_login

logger = logging.getLogger(__name__)


class AdminMfaAwareTokenRefreshSerializer(serializers.Serializer):
    """
    Refresh that preserves admin_mfa claim across rotation.
    Does not grant MFA if the old refresh lacked the claim.
    """

    refresh = serializers.CharField()

    def validate(self, attrs):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        from rest_framework_simplejwt.tokens import AccessToken

        # Read claim before rotation/blacklist of the presented refresh.
        try:
            old = RefreshToken(attrs["refresh"])
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        had_mfa = old.get(ADMIN_MFA_CLAIM) == ADMIN_MFA_CLAIM_VALUE

        base = TokenRefreshSerializer(context=self.context)
        data = base.validate(attrs)
        if not had_mfa:
            return data
        access_token = AccessToken(data["access"])
        access_token[ADMIN_MFA_CLAIM] = ADMIN_MFA_CLAIM_VALUE
        data["access"] = str(access_token)
        if data.get("refresh"):
            new_refresh = RefreshToken(data["refresh"])
            new_refresh[ADMIN_MFA_CLAIM] = ADMIN_MFA_CLAIM_VALUE
            data["refresh"] = str(new_refresh)
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Вход по телефону/логину и паролю. Нормализует телефон, принимает username или phone."""

    def validate(self, attrs):
        # Принимаем и "username", и "phone" (фронт может слать любое поле)
        raw = (attrs.get("username") or attrs.get("phone") or "")
        if isinstance(raw, str):
            raw = raw.strip()
        password = attrs.get("password")
        if not raw:
            raise serializers.ValidationError(
                {"username": "Укажите телефон или логин."},
                code="blank",
            )
        if not password:
            raise serializers.ValidationError(
                {"password": "Укажите пароль."},
                code="blank",
            )
        attrs = {**attrs, "username": raw, "password": password}
        username = raw
        # Нормализация телефона (79187020987). Родитель SimpleJWT всегда читает attrs["phone"] (USERNAME_FIELD).
        normalized = normalize_phone(username)
        if normalized:
            attrs = {**attrs, "username": normalized, "phone": normalized}
        else:
            # Не телефон (например, "admin") — передаём как есть; бэкенд ищет по phone=lookup
            attrs = {**attrs, "phone": raw}
        try:
            return super().validate(attrs)
        except AuthenticationFailed:
            # В БД телефон мог быть в другом формате — пробуем исходное значение
            if normalized and normalized != username:
                attrs = {**attrs, "phone": username, "username": username}
                return super().validate(attrs)
            raise


@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Регистрация: телефон (логин), пароль, ФИО. Возвращает JWT (автовход).
    """

    authentication_classes: ClassVar[list] = []
    permission_classes = (AllowAny,)
    throttle_classes = [AuthRegisterAnonThrottle]

    def post(self, request):
        serializer = RegisterSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        # JWT-регистрация без django.contrib.auth.login — сливаем гостевую корзину вручную (как при token login).
        merge_guest_cart_into_user(request, user)
        # 1С-контрагент: асинхронно, не ломает регистрацию (флаги OFF → no-op / pending).
        try:
            from .tasks import enqueue_partner_sync_after_register

            enqueue_partner_sync_after_register(user)
        except Exception:  # noqa: BLE001
            pass
        refresh = RefreshToken.for_user(user)
        access_s = str(refresh.access_token)
        refresh_s = str(refresh)
        body = {
            "detail": "Регистрация успешна.",
            "access": access_s,
            "refresh": refresh_s,
        }
        if client_uses_cookie_auth(request):
            body = strip_tokens_from_response_data(body)
        response = Response(body, status=status.HTTP_201_CREATED)
        set_jwt_cookies(response, access_s, refresh_s)
        record_successful_password_login(request, user)
        return response


class StaffAccessView(APIView):
    """
    GET /api/v1/auth/staff-access/
    Проверка доступа к админ-панели: 200 только для is_staff.
    При ADMIN_OTP_ENABLED требуется JWT-claim admin_mfa (после TOTP).
    Не подмешивает признак staff в публичный ответ /auth/me/.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        otp_on = admin_otp_required()
        mfa_ok = (not otp_on) or request_has_admin_mfa(request)
        if otp_on and not mfa_ok:
            return Response(
                {
                    "detail": "Требуется подтверждение второго фактора (TOTP).",
                    "code": "admin_mfa_required",
                    "mfa_enrolled": user_has_confirmed_totp(request.user),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        from apps.admin_api.permissions import ALL_ADMIN_GROUPS

        user = request.user
        if user.is_superuser:
            groups = list(ALL_ADMIN_GROUPS)
        else:
            groups = list(
                user.groups.filter(name__in=ALL_ADMIN_GROUPS)
                .order_by("name")
                .values_list("name", flat=True)
            )
        return Response(
            {
                "staff": True,
                "is_superuser": bool(user.is_superuser),
                "groups": groups,
                "admin_mfa": True if (otp_on and mfa_ok) else (not otp_on),
            }
        )


class AdminMfaStatusView(APIView):
    """GET /api/v1/auth/mfa/status/ — enrollment / verified claim (без секретов)."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        needs = staff_needs_mfa_step(user)
        return Response(
            {
                "otp_enabled": admin_otp_required(),
                "staff": bool(user.is_staff or user.is_superuser),
                "mfa_required": needs,
                "mfa_enrolled": user_has_confirmed_totp(user) if needs else False,
                "admin_mfa_verified": request_has_admin_mfa(request),
            }
        )


class AdminMfaVerifyView(APIView):
    """
    POST /api/v1/auth/mfa/verify/  body: { "totp": "123456" }
    После пароля staff подтверждает TOTP → новые JWT с admin_mfa=1.
    """

    permission_classes = (IsAuthenticated,)
    throttle_classes = [AuthMfaVerifyUserThrottle]

    def post(self, request):
        from apps.audit.services import log_admin_action

        user = request.user
        if not (user.is_staff or user.is_superuser):
            return Response(
                {"detail": "Только для сотрудников.", "code": "not_staff"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not admin_otp_required():
            access, refresh = issue_tokens_with_admin_mfa(user)
            body = {"access": access, "refresh": refresh, "admin_mfa": True}
            if client_uses_cookie_auth(request):
                body = strip_tokens_from_response_data(body)
            response = Response(body, status=status.HTTP_200_OK)
            set_jwt_cookies(response, access, refresh)
            return response
        if not user_has_confirmed_totp(user):
            log_admin_action(
                request,
                action="mfa_verify_denied_unenrolled",
                model_name="auth.mfa",
                object_id=str(user.pk),
                object_repr="totp_unenrolled",
            )
            return Response(
                {
                    "detail": (
                        "TOTP-устройство не зарегистрировано. "
                        "Выполните enrollment через Django Admin / ops (см. ADMIN_MFA_SETUP)."
                    ),
                    "code": "mfa_not_enrolled",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        code = ""
        if isinstance(request.data, dict):
            code = str(request.data.get("totp") or request.data.get("token") or "")
        if not verify_totp_code(user, code):
            log_admin_action(
                request,
                action="mfa_verify_failed",
                model_name="auth.mfa",
                object_id=str(user.pk),
                object_repr="totp_failed",
            )
            return Response(
                {"detail": "Неверный код подтверждения.", "code": "mfa_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        access, refresh = issue_tokens_with_admin_mfa(user)
        log_admin_action(
            request,
            action="mfa_verify_ok",
            model_name="auth.mfa",
            object_id=str(user.pk),
            object_repr="totp_ok",
        )
        body = {"access": access, "refresh": refresh, "admin_mfa": True}
        if client_uses_cookie_auth(request):
            body = strip_tokens_from_response_data(body)
        response = Response(body, status=status.HTTP_200_OK)
        set_jwt_cookies(response, access, refresh)
        return response


class UserMeView(APIView):
    """
    GET /api/v1/auth/me/ — текущий пользователь (с профилем и согласиями).
    PATCH /api/v1/auth/me/ — только marketing_opt_in (отзыв/выдача согласия на рассылку).
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = (
            CustomUser.objects.select_related("profile")
            .filter(pk=request.user.pk)
            .first()
        )
        if not user:
            return Response(
                {"detail": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = MarketingOptInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opt = serializer.validated_data["marketing_opt_in"]
        user = request.user
        if not isinstance(user, CustomUser):
            return Response(
                {"detail": "Некорректный тип пользователя."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        user.marketing_opt_in = opt
        user.marketing_opt_in_at = now if opt else None
        user.save(update_fields=["marketing_opt_in", "marketing_opt_in_at", "updated_at"])
        refreshed = (
            CustomUser.objects.select_related("profile")
            .filter(pk=user.pk)
            .first()
        )
        return Response(UserSerializer(refreshed).data)


class UserDataExportView(APIView):
    """
    GET /api/v1/auth/me/export/
    Копия персональных данных пользователя (профиль, адреса, заказы) в JSON.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from apps.orders.models import Order

        user = (
            CustomUser.objects.select_related("profile")
            .filter(pk=request.user.pk)
            .first()
        )
        if not user:
            return Response(
                {"detail": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )
        addresses = DeliveryAddress.objects.filter(user=user).order_by(
            "-is_default", "-created_at"
        )
        orders = (
            Order.objects.filter(user=user)
            .prefetch_related("items")
            .order_by("-created_at")[:500]
        )
        order_payload = []
        for o in orders:
            order_payload.append(
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "created_at": o.created_at.isoformat(),
                    "status": o.status,
                    "total_amount": str(o.total_amount),
                    "delivery_cost": str(o.delivery_cost),
                    "delivery_type": o.delivery_type,
                    "payment_type": o.payment_type,
                    "full_name": o.full_name,
                    "phone": o.phone,
                    "email": o.email or "",
                    "consent_personal_data": o.consent_personal_data,
                    "items": [
                        {
                            "product_title": i.product_title,
                            "product_sku": i.product_sku or "",
                            "quantity": i.quantity,
                            "price": str(i.price),
                            "item_total": str(i.item_total),
                        }
                        for i in o.items.all()
                    ],
                }
            )
        data = {
            "exported_at": timezone.now().isoformat(),
            "user": UserSerializer(user).data,
            "delivery_addresses": DeliveryAddressSerializer(addresses, many=True).data,
            "orders": order_payload,
        }
        return Response(data)


class TokenObtainPairViewNoCSRF(TokenObtainPairView):
    """Вход по телефону и паролю. Нормализация телефона, без CSRF."""

    serializer_class = CustomTokenObtainPairSerializer
    authentication_classes: ClassVar[list] = []
    permission_classes = (AllowAny,)
    throttle_classes = [AuthLoginAnonThrottle]

    def post(self, request, *args, **kwargs):
        # Явно собираем payload для SimpleJWT (поле логина — phone), без подмены request._full_data:
        # иначе на части версий DRF/парсеров username не попадает в validated attrs → authenticate(None).
        src = request.data
        if hasattr(src, "copy"):
            data = dict(src.copy())
        elif isinstance(src, dict):
            data = {**src}
        else:
            data = {}

        login_raw = data.get("username") or data.get("phone") or ""
        if isinstance(login_raw, str):
            login_raw = login_raw.strip()
        password = data.get("password")
        pwd_ok = password is not None and str(password) != ""

        if not login_raw or not pwd_ok:
            body: dict = {"detail": "Укажите телефон (username или phone) и пароль в JSON."}
            if not login_raw:
                body["username"] = ["Обязательное поле."]
            if not pwd_ok:
                body["password"] = ["Обязательное поле."]
            return Response(body, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={"phone": login_raw, "password": password})
        try:
            try:
                serializer.is_valid(raise_exception=True)
            except ValidationError:
                log_login_failed(request, login_raw)
                raise
            except AuthenticationFailed:
                log_login_failed(request, login_raw)
                raise
            except TokenError as e:
                log_login_failed(request, login_raw, reason="token_error")
                raise InvalidToken(e.args[0]) from e

            # SPA-логин по JWT не вызывает сигнал user_logged_in — явно переносим корзину гостя по session_key.
            merge_guest_cart_into_user(request, serializer.user)

            payload = dict(serializer.validated_data)
            user = serializer.user
            # Password login never grants admin_mfa; staff must call /auth/mfa/verify/.
            if staff_needs_mfa_step(user):
                payload["admin_mfa_required"] = True
                payload["mfa_enrolled"] = user_has_confirmed_totp(user)
                payload["admin_mfa"] = False
            if client_uses_cookie_auth(request):
                payload = strip_tokens_from_response_data(payload)
            response = Response(payload, status=status.HTTP_200_OK)
            if isinstance(serializer.validated_data, dict):
                access = serializer.validated_data.get("access")
                refresh = serializer.validated_data.get("refresh")
                if access and refresh:
                    set_jwt_cookies(response, access, refresh)
            try:
                record_successful_password_login(request, serializer.user)
            except Exception:
                logger.exception("record_successful_password_login failed after token issue")
            return response
        except (OperationalError, ProgrammingError):
            logger.exception("POST /auth/token/ database error (migrations? DB down?)")
            return Response(
                {
                    "detail": (
                        "Ошибка базы данных при выдаче токена. "
                        "Выполните миграции: python manage.py migrate "
                        "(нужны таблицы token_blacklist, django_axes и др.)."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


@method_decorator(csrf_exempt, name="dispatch")
class CookieTokenRefreshView(TokenRefreshView):
    """
    Обновление access; refresh из тела или из HttpOnly-куки (для режима NEXT_PUBLIC_USE_AUTH_COOKIES).
    Сохраняет admin_mfa claim только если он уже был в refresh (refresh не обходит MFA).
    """

    authentication_classes: ClassVar[list] = []
    permission_classes = (AllowAny,)
    throttle_classes = [AuthRefreshAnonThrottle]
    serializer_class = AdminMfaAwareTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            data = {**request.data}
        elif hasattr(request.data, "copy"):
            data = request.data.copy()
        else:
            data = {}
        if not data.get("refresh"):
            ref = request.COOKIES.get(settings.JWT_COOKIE_REFRESH_NAME)
            if ref:
                data["refresh"] = ref
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            log_token_refresh_failed(request, reason="validation_error")
            raise
        except TokenError as e:
            log_token_refresh_failed(request, reason="token_error")
            raise InvalidToken(e.args[0]) from e
        validated = serializer.validated_data
        payload = dict(validated)
        if client_uses_cookie_auth(request):
            payload = strip_tokens_from_response_data(payload)
        response = Response(payload, status=status.HTTP_200_OK)
        access = validated.get("access")
        refresh = validated.get("refresh")
        if access:
            set_jwt_cookies(response, access, refresh)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/ — blacklist refresh (тело или кука) и сброс HttpOnly JWT-кук.
    """

    authentication_classes: ClassVar[list] = []
    permission_classes = (AllowAny,)

    def post(self, request):
        raw = None
        if hasattr(request, "data") and request.data is not None:
            raw = request.data.get("refresh")
        if not raw:
            raw = request.COOKIES.get(settings.JWT_COOKIE_REFRESH_NAME)
        response = Response({"detail": "Выход выполнен."}, status=status.HTTP_200_OK)
        if raw:
            try:
                token = RefreshToken(raw)
                token.blacklist()
            except Exception:
                pass
        clear_jwt_cookies(response)
        return response


class DeliveryAddressListCreateView(ListCreateAPIView):
    """
    GET /api/v1/auth/addresses/ — список адресов текущего пользователя.
    POST /api/v1/auth/addresses/ — добавить адрес.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = DeliveryAddressSerializer

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user).order_by(
            "-is_default", "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DeliveryAddressDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/auth/addresses/<id>/ — один адрес (только свой).
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = DeliveryAddressSerializer

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)


class DeleteAccountView(APIView):
    """
    POST /api/v1/auth/delete-account/
    Удаление своих данных (по запросу): анонимизация пользователя, удаление адресов и профиля.
    Тело: {"confirm": "DELETE_MY_ACCOUNT"}.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        confirm = (request.data.get("confirm") or "").strip()
        if confirm != "DELETE_MY_ACCOUNT":
            return Response(
                {"detail": "Отправьте confirm: \"DELETE_MY_ACCOUNT\" для подтверждения."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        with transaction.atomic():
            from apps.cart.models import Cart
            from apps.wishlist.models import WishlistItem

            Cart.objects.filter(user=user).delete()
            WishlistItem.objects.filter(user=user).delete()
            from apps.orders.services.anonymize import anonymize_orders_for_user

            anonymize_orders_for_user(user)
            DeliveryAddress.objects.filter(user=user).delete()
            UserProfile.objects.filter(user=user).update(
                first_name="",
                last_name="",
                middle_name="",
            )
            user.email = None
            user.phone = f"deleted_{user.id}"
            user.set_unusable_password()
            user.is_active = False
            user.marketing_opt_in = False
            user.marketing_opt_in_at = None
            user.privacy_policy_accepted_at = None
            user.save(
                update_fields=[
                    "email",
                    "phone",
                    "password",
                    "is_active",
                    "marketing_opt_in",
                    "marketing_opt_in_at",
                    "privacy_policy_accepted_at",
                    "updated_at",
                ]
            )
        return Response(
            {"detail": "Аккаунт и персональные данные удалены."},
            status=status.HTTP_200_OK,
        )
