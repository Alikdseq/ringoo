"""
Celery-задачи CRM (задача 2.4.4). Заглушка отправки заявки в CRM.
"""

import logging

from config.optional_task import shared_task

from config.pii import mask_phone

logger = logging.getLogger(__name__)

_PRODUCT_NAME_LOG_MAX = 80


def _product_name_for_log(name: str) -> str:
    s = (name or "").strip()
    if len(s) <= _PRODUCT_NAME_LOG_MAX:
        return s or "—"
    return s[:_PRODUCT_NAME_LOG_MAX] + "…"


@shared_task
def send_missing_product_request_to_crm(request_id):
    """
    Отправить заявку на отсутствующий товар в CRM (заглушка).

    В реальной интеграции здесь вызов API CRM или отправка в очередь.
    """
    from .models import MissingProductRequest

    try:
        req = MissingProductRequest.objects.get(id=request_id)
    except MissingProductRequest.DoesNotExist:
        logger.warning("send_missing_product_request_to_crm: request %s not found", request_id)
        return

    logger.info(
        "CRM stub: would send request id=%s product_name=%s contact_phone=%s",
        request_id,
        _product_name_for_log(req.product_name),
        mask_phone(req.contact_phone),
    )
    # Заглушка: реальная отправка в CRM не реализована

    # E.3: уведомление менеджера по email
    try:
        from integrations.email_service import send_missing_product_request_to_manager

        send_missing_product_request_to_manager(req)
    except Exception as e:
        logger.exception(
            "send_missing_product_request_to_crm: manager email failed: %s",
            e,
        )
