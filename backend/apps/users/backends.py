"""
Бэкенд аутентификации по полю phone.
Django ModelBackend принимает только username/password, а при USERNAME_FIELD=phone
SimpleJWT передаёт authenticate(request, phone=..., password=...).
Без этого бэкенда вход по телефону и паролю не работает (всегда 401/500).

Поиск по нескольким вариантам записи телефона (наследие: +7… в БД vs 7918… после normalize_phone).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .services import normalize_phone


def _phone_lookup_keys(raw: str) -> list[str]:
    """Уникальные ключи для ORM lookup по полю phone."""
    s = (raw or "").strip()
    if not s:
        return []
    out: list[str] = []
    for key in (s,):
        if key and key not in out:
            out.append(key)
    n = normalize_phone(s)
    if n and n not in out:
        out.append(n)
    if n and f"+{n}" not in out:
        out.append(f"+{n}")
    return out


class PhoneBackend(ModelBackend):
    """Вход по полю phone (и при необходимости по username для совместимости)."""

    def authenticate(self, request, username=None, password=None, phone=None, **kwargs):
        UserModel = get_user_model()
        lookup = phone if phone is not None else username
        if lookup is None or not lookup or password is None:
            return None
        if isinstance(lookup, str):
            lookup = lookup.strip()
        if not lookup:
            return None

        user = None
        for key in _phone_lookup_keys(lookup):
            try:
                user = UserModel.objects.get(phone=key)
                break
            except UserModel.DoesNotExist:
                continue
            except UserModel.MultipleObjectsReturned:
                return None

        if user is None:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
