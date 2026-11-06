"""
SEC-009: безопасное восстановление пароля по email.

- Ответ request одинаков для существующего/несуществующего email.
- Токен: Django PasswordResetTokenGenerator (одноразовый через password hash).
- После смены пароля — blacklist OutstandingToken пользователя.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.throttling import (
    PasswordResetAnonThrottle,
    PasswordResetConfirmAnonThrottle,
)

from .models import CustomUser

logger = logging.getLogger("ringoo.security")

token_generator = PasswordResetTokenGenerator()

PUBLIC_REQUEST_DETAIL = (
    "Если аккаунт с таким email существует, мы отправили инструкции "
    "по восстановлению пароля."
)

# Лимит писем на один email (не зависит от IP; не блокирует чужой аккаунт бесконечно).
_EMAIL_RESET_LIMIT = 3
_EMAIL_RESET_WINDOW_SEC = 3600


def _email_send_allowed(email: str) -> bool:
    key = f"pwd_reset_email:{email}"
    n = cache.get(key, 0)
    if int(n) >= _EMAIL_RESET_LIMIT:
        return False
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=_EMAIL_RESET_WINDOW_SEC)
    return True


def _frontend_reset_url(uidb64: str, token: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/reset-password?uid={uidb64}&token={token}"


def _blacklist_user_refresh_tokens(user: CustomUser) -> int:
    """Отзывает все outstanding refresh-токены пользователя."""
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
    except Exception:
        logger.exception("token_blacklist unavailable for password reset")
        return 0
    count = 0
    for outstanding in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        if created:
            count += 1
    return count


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True, max_length=64)
    token = serializers.CharField(required=True, max_length=128)
    new_password = serializers.CharField(required=True, min_length=8, write_only=True)


class PasswordResetRequestView(APIView):
    """POST /api/v1/auth/password-reset/"""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetAnonThrottle]
    authentication_classes: list = []

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()

        user = (
            CustomUser.objects.filter(email__iexact=email, is_active=True)
            .exclude(email__isnull=True)
            .exclude(email="")
            .first()
        )
        if user is not None and _email_send_allowed(email):
            uidb64 = urlsafe_base64_encode(force_bytes(str(user.pk)))
            token = token_generator.make_token(user)
            link = _frontend_reset_url(uidb64, token)
            try:
                send_mail(
                    subject="Восстановление пароля Ringo",
                    message=(
                        "Здравствуйте!\n\n"
                        "Чтобы задать новый пароль, откройте ссылку "
                        f"(действует ограниченное время):\n{link}\n\n"
                        "Если вы не запрашивали восстановление — просто "
                        "проигнорируйте это письмо."
                    ),
                    from_email=getattr(
                        settings, "DEFAULT_FROM_EMAIL", "noreply@ringoo.local"
                    ),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception(
                    "password_reset_email_failed user_id=%s", user.pk
                )
            else:
                logger.info("password_reset_email_queued user_id=%s", user.pk)
        elif user is not None:
            logger.info("password_reset_email_rate_limited user_id=%s", user.pk)
        else:
            logger.info("password_reset_request_unknown_email")

        return Response({"detail": PUBLIC_REQUEST_DETAIL}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password-reset/confirm/"""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmAnonThrottle]
    authentication_classes: list = []

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uidb64 = ser.validated_data["uid"]
        token = ser.validated_data["token"]
        new_password = ser.validated_data["new_password"]

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid, is_active=True)
        except (CustomUser.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "Ссылка восстановления недействительна или устарела."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not token_generator.check_token(user, token):
            return Response(
                {"detail": "Ссылка восстановления недействительна или устарела."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        blacklisted = _blacklist_user_refresh_tokens(user)
        logger.info(
            "password_reset_completed user_id=%s refresh_blacklisted=%s",
            user.pk,
            blacklisted,
        )
        return Response(
            {"detail": "Пароль обновлён. Войдите с новым паролем."},
            status=status.HTTP_200_OK,
        )
