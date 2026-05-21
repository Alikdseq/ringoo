"""
Permission для Admin API — staff + разграничение по группам Django.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

RINGOO_GROUP_ORDERS = "ringoo_orders"
RINGOO_GROUP_CATALOG = "ringoo_catalog"
RINGOO_GROUP_CONTENT = "ringoo_content"
RINGOO_GROUP_CRM = "ringoo_crm"
RINGOO_GROUP_REPORTS = "ringoo_reports"
RINGOO_GROUP_USERS = "ringoo_users"
RINGOO_GROUP_STORES = "ringoo_stores"

ALL_ADMIN_GROUPS = (
    RINGOO_GROUP_ORDERS,
    RINGOO_GROUP_CATALOG,
    RINGOO_GROUP_CONTENT,
    RINGOO_GROUP_CRM,
    RINGOO_GROUP_REPORTS,
    RINGOO_GROUP_USERS,
    RINGOO_GROUP_STORES,
)


class IsStaff(BasePermission):
    """Разрешает доступ только пользователям с is_staff=True."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


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
    """Стандартный набор: auth + staff + группа."""
    return [IsAuthenticated, IsStaff, HasAdminGroupPermission(group_name)]


def admin_permissions_dashboard():
    """Дашборд: staff с хотя бы одной admin-группой или superuser."""
    return [IsAuthenticated, IsStaff, HasAnyAdminGroup]
