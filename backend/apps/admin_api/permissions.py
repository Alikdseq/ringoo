"""
Permission для Admin API — staff + разграничение по группам Django + MFA.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.users.admin_mfa import admin_otp_required, request_has_admin_mfa

RINGOO_GROUP_ORDERS = "ringoo_orders"
RINGOO_GROUP_CATALOG = "ringoo_catalog"
RINGOO_GROUP_CONTENT = "ringoo_content"
RINGOO_GROUP_CRM = "ringoo_crm"
RINGOO_GROUP_REPORTS = "ringoo_reports"
RINGOO_GROUP_USERS = "ringoo_users"
RINGOO_GROUP_STORES = "ringoo_stores"
# SEC-008: финансовые операции с бонусами — отдельная группа (модуль пока выключен)
RINGOO_GROUP_BONUS = "ringoo_bonus"

ALL_ADMIN_GROUPS = (
    RINGOO_GROUP_ORDERS,
    RINGOO_GROUP_CATALOG,
    RINGOO_GROUP_CONTENT,
    RINGOO_GROUP_CRM,
    RINGOO_GROUP_REPORTS,
    RINGOO_GROUP_USERS,
    RINGOO_GROUP_STORES,
    RINGOO_GROUP_BONUS,
)


class IsStaff(BasePermission):
    """Разрешает доступ только пользователям с is_staff=True."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminMfaVerified(BasePermission):
    """
    Когда ADMIN_OTP_ENABLED — требуется JWT-claim admin_mfa=1
    (выдаётся только после успешного TOTP на /auth/mfa/verify/).
    """

    message = "Требуется подтверждение второго фактора (TOTP)."

    def has_permission(self, request, view):
        if not admin_otp_required():
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not (user.is_staff or user.is_superuser):
            return False
        return request_has_admin_mfa(request)


def _user_has_admin_group(user, group_name: str) -> bool:
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()


def HasAdminGroupPermission(group_name: str):
    """Фабрика permission-класса для группы."""

    class _HasAdminGroup(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            if not user or not user.is_authenticated or not user.is_staff:
                return False
            return _user_has_admin_group(user, group_name)

    _HasAdminGroup.__name__ = f"HasAdminGroup_{group_name}"
    return _HasAdminGroup


class HasAnyAdminGroup(BasePermission):
    """Superuser или хотя бы одна группа ringoo_*."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_staff:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=ALL_ADMIN_GROUPS).exists()


def admin_permissions(group_name: str):
    """Стандартный набор: auth + staff + MFA + группа."""
    return [IsAuthenticated, IsStaff, AdminMfaVerified, HasAdminGroupPermission(group_name)]


def admin_permissions_dashboard():
    """Дашборд: staff с MFA и хотя бы одной admin-группой или superuser."""
    return [IsAuthenticated, IsStaff, AdminMfaVerified, HasAnyAdminGroup]
