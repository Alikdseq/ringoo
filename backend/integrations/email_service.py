"""
Сервис отправки email (интеграции 2.4.2).

Функции: подтверждение заказа, изменение статуса заказа, оценка менеджера.
В логах не светятся персональные данные (email маскируется).
"""

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

from config.pii import mask_email

logger = logging.getLogger(__name__)


def send_new_login_alert(
    *, recipient_email: str, phone_display: str, new_ip: str, previous_ip: str
) -> bool:
    """
    Уведомление о входе с нового IP (без HTML-шаблона, короткое текстовое письмо).
    """
    if not recipient_email:
        return False
    subject = "Вход в аккаунт Ringoo с нового адреса"
    body = (
        "Здравствуйте.\n\n"
        f"В ваш аккаунт (телефон {phone_display}) выполнен вход с нового IP-адреса.\n"
        f"Текущий вход: {new_ip}\n"
        f"Предыдущий сохранённый IP: {previous_ip}\n\n"
        "Если это были не вы, смените пароль в личном кабинете.\n"
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
        logger.info(
            "send_new_login_alert: sent to %s new_ip=%s",
            mask_email(recipient_email),
            new_ip,
        )
        return True
    except Exception as e:
        logger.exception("send_new_login_alert failed: %s", e)
        return False


def _get_recipient_from_order(order):
    """Email получателя: order.email или user.email."""
    if order.email:
        return order.email
    if order.user_id and order.user.email:
        return order.user.email
    return None


def send_order_confirmation(order):
    """
    Отправить письмо о подтверждении заказа.

    Returns:
        bool: True если письмо отправлено, False если некуда отправлять или ошибка.
    """
    recipient = _get_recipient_from_order(order)
    if not recipient:
        logger.warning("send_order_confirmation: no email for order %s", order.order_number)
        return False

    total_with_delivery = order.total_amount + (order.delivery_cost or 0)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    rating_link = f"{frontend_url}/order-rate?order={order.order_number}"
    context = {
        "full_name": order.full_name,
        "order_number": order.order_number,
        "total_amount": order.total_amount,
        "delivery_cost": order.delivery_cost,
        "total_with_delivery": total_with_delivery,
        "rating_link": rating_link,
    }

    subject = f"Подтверждение заказа {order.order_number}"
    text_body = render_to_string("emails/order_confirmation.txt", context)
    html_body = render_to_string("emails/order_confirmation.html", context)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info(
            "send_order_confirmation: sent to %s for order %s",
            mask_email(recipient),
            order.order_number,
        )
        return True
    except Exception as e:
        logger.exception("send_order_confirmation failed for order %s: %s", order.order_number, e)
        return False


def send_order_status_change(order, old_status=None):
    """
    Отправить письмо об изменении статуса заказа.

    Args:
        order: экземпляр Order (уже с новым status).
        old_status: предыдущее значение status (строка) или None.

    Returns:
        bool: True если письмо отправлено, False иначе.
    """
    recipient = _get_recipient_from_order(order)
    if not recipient:
        logger.warning("send_order_status_change: no email for order %s", order.order_number)
        return False

    status_display_map = dict(order.STATUS_CHOICES)
    old_status_display = status_display_map.get(old_status, old_status or "—")
    new_status_display = order.get_status_display()

    context = {
        "full_name": order.full_name,
        "order_number": order.order_number,
        "old_status_display": old_status_display,
        "new_status_display": new_status_display,
    }

    subject = f"Статус заказа {order.order_number} изменён"
    text_body = render_to_string("emails/order_status_change.txt", context)
    html_body = render_to_string("emails/order_status_change.html", context)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info(
            "send_order_status_change: sent to %s for order %s",
            mask_email(recipient),
            order.order_number,
        )
        return True
    except Exception as e:
        logger.exception(
            "send_order_status_change failed for order %s: %s",
            order.order_number,
            e,
        )
        return False


def send_manager_rating(to_email, order_number, rating, comment=None, manager_name=None):
    """
    Отправить письмо об оценке менеджера (заказ, менеджер, оценка, комментарий).

    Args:
        to_email: email получателя (менеджер/админ).
        order_number: номер заказа.
        rating: оценка (1–5).
        comment: необязательный комментарий.
        manager_name: ФИО менеджера, которому поставлена оценка.

    Returns:
        bool: True если письмо отправлено, False при ошибке.
    """
    if not to_email:
        logger.warning("send_manager_rating: to_email is empty")
        return False

    context = {
        "order_number": order_number,
        "rating": rating,
        "comment": comment or "",
        "manager_name": manager_name or "",
    }

    subject = f"Оценка по заказу {order_number}"
    text_body = render_to_string("emails/manager_rating.txt", context)
    html_body = render_to_string("emails/manager_rating.html", context)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info(
            "send_manager_rating: sent to %s for order %s",
            mask_email(to_email),
            order_number,
        )
        return True
    except Exception as e:
        logger.exception(
            "send_manager_rating failed for order %s: %s",
            order_number,
            e,
        )
        return False


def send_missing_product_request_to_manager(req):
    """
    Отправить менеджеру уведомление о новой заявке «Не нашли товар».

    Args:
        req: экземпляр MissingProductRequest (apps.crm.models).

    Returns:
        bool: True если письмо отправлено, False если некуда отправлять или ошибка.
    """
    to_email = getattr(settings, "MANAGER_EMAIL", None) or getattr(
        settings, "MANAGER_RATING_NOTIFY_EMAIL", ""
    )
    if not to_email:
        logger.warning("send_missing_product_request_to_manager: MANAGER_EMAIL not set")
        return False

    context = {
        "contact_name": getattr(req, "contact_name", "") or "",
        "contact_phone": req.contact_phone,
        "product_name": req.product_name,
        "contact_email": req.contact_email or "",
        "comment": req.comment or "",
        "created_at": req.created_at,
    }

    subject = f"Заявка «Не нашли товар»: {req.product_name[:50]}"
    text_body = render_to_string("emails/missing_product_request.txt", context)
    html_body = render_to_string("emails/missing_product_request.html", context)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info(
            "send_missing_product_request_to_manager: sent to %s for request %s",
            to_email,
            req.id,
        )
        return True
    except Exception as e:
        logger.exception(
            "send_missing_product_request_to_manager failed for request %s: %s",
            req.id,
            e,
        )
        return False
