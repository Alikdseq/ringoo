"""
Сервис записи аудита: кто и когда изменил объект в админке.
"""

from apps.audit.models import AuditLog


def log_admin_action(
    request,
    action: str,
    model_name: str,
    object_id: str = "",
    object_repr: str = "",
    changes: dict | None = None,
):
    """
    Записать действие сотрудника в AuditLog.
    Вызывать из Admin API после изменения заказа, товара и т.д.
    """
    if not request or not getattr(request, "user", None):
        return
    user = request.user
    if not user.is_authenticated:
        return
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=(object_repr or "")[:255],
        changes=changes or {},
    )
