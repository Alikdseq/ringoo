"""
Входящие уведомления 1С → Ringoo: статус выполнения и оплата в магазине.

Онлайн-оплата (ЮKassa) сюда не относится: её ставит webhook платежей.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.orders.models import OneCInboundEvent, Order
from apps.orders.services.transitions import OrderTransitionError, transition_order_status

logger = logging.getLogger(__name__)


class OneCInboundError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "bad_request",
        http_status: int = 400,
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)


# Способы оплаты из 1С → коды Order.payment_type
_PAYMENT_METHOD_ALIASES = {
    "cash": Order.PAYMENT_CASH,
    "card_on_pickup": Order.PAYMENT_CARD_ON_DELIVERY,
    "card_on_delivery": Order.PAYMENT_CARD_ON_DELIVERY,
    "bank_transfer": Order.PAYMENT_BANK_TRANSFER,
    "online": Order.PAYMENT_ONLINE,
}


def _summary_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Без персональных данных и полных реквизитов."""
    out: dict[str, Any] = {
        "order_number": data.get("order_number"),
        "status": data.get("status"),
        "result": data.get("result"),
        "source": data.get("source"),
        "occurred_at": data.get("occurred_at"),
    }
    pay = data.get("payment")
    if isinstance(pay, dict):
        out["payment"] = {
            "status": pay.get("status"),
            "method": pay.get("method"),
            "amount": pay.get("amount"),
            "currency": pay.get("currency"),
            "payment_reference": pay.get("payment_reference"),
        }
    return out


def _parse_amount(raw: Any) -> Decimal:
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise OneCInboundError(
            "Некорректная сумма оплаты",
            code="invalid_amount",
            http_status=400,
        ) from exc
    if amount <= 0:
        raise OneCInboundError(
            "Сумма оплаты должна быть больше нуля",
            code="invalid_amount",
            http_status=400,
        )
    return amount.quantize(Decimal("0.01"))


def _event_type(data: dict[str, Any]) -> str:
    has_status = bool(data.get("status"))
    has_payment = isinstance(data.get("payment"), dict)
    if has_status and has_payment:
        return OneCInboundEvent.EVENT_COMBINED
    if has_payment:
        return OneCInboundEvent.EVENT_PAYMENT
    return OneCInboundEvent.EVENT_STATUS


def _apply_fulfillment(order: Order, data: dict[str, Any]) -> Order:
    status = (data.get("status") or "").strip()
    if not status:
        return order
    result = (data.get("result") or "").strip() or None
    if status not in (
        Order.STATUS_NEW,
        Order.STATUS_PROCESSING,
        Order.STATUS_READY,
        Order.STATUS_CLOSED,
    ):
        raise OneCInboundError(
            f"Недопустимый status: {status}",
            code="invalid_status",
            http_status=400,
        )
    if status == Order.STATUS_NEW:
        raise OneCInboundError(
            "1С не может вернуть заказ в new",
            code="invalid_status",
            http_status=409,
        )
    try:
        return transition_order_status(
            order,
            status,
            closure_result=result,
            reason="onec_inbound",
            skip_onec_cancel=True,
        )
    except OrderTransitionError as exc:
        http = 409 if exc.code in ("invalid_transition", "order_closed") else 400
        raise OneCInboundError(exc.message, code=exc.code, http_status=http) from exc


def _apply_payment(order: Order, payment: dict[str, Any]) -> Order:
    pay_status = (payment.get("status") or "").strip()
    if pay_status not in (
        Order.PAYMENT_STATUS_PAID,
        Order.PAYMENT_STATUS_REFUNDED,
        Order.PAYMENT_STATUS_UNPAID,
    ):
        raise OneCInboundError(
            f"Недопустимый payment.status: {pay_status}",
            code="invalid_payment_status",
            http_status=400,
        )

    if pay_status == Order.PAYMENT_STATUS_UNPAID:
        if order.payment_status == Order.PAYMENT_STATUS_PAID:
            raise OneCInboundError(
                "Нельзя сбросить paid → unpaid через 1С",
                code="payment_downgrade_forbidden",
                http_status=409,
            )
        return order

    method_raw = (payment.get("method") or "").strip()
    method = _PAYMENT_METHOD_ALIASES.get(method_raw)
    if not method:
        raise OneCInboundError(
            f"Недопустимый payment.method: {method_raw}",
            code="invalid_payment_method",
            http_status=400,
        )

    # Онлайн уже оплачен шлюзом — согласованное состояние, без второго учёта.
    if order.payment_type == Order.PAYMENT_ONLINE:
        from apps.orders.services import order_has_successful_payment

        if (
            order.payment_status == Order.PAYMENT_STATUS_PAID
            or order_has_successful_payment(order)
        ):
            if pay_status == Order.PAYMENT_STATUS_PAID:
                return order
            raise OneCInboundError(
                "Онлайн-заказ уже оплачен; refund через 1С не принимается этим API",
                code="online_payment_conflict",
                http_status=409,
            )
        raise OneCInboundError(
            "Для online-оплаты статус paid ставит ЮKassa, не 1С",
            code="online_payment_owned_by_gateway",
            http_status=409,
        )

    if method != order.payment_type:
        raise OneCInboundError(
            f"Способ оплаты не совпадает с заказом ({order.payment_type})",
            code="payment_method_mismatch",
            http_status=409,
        )

    amount = _parse_amount(payment.get("amount"))
    currency = (payment.get("currency") or "RUB").strip().upper()
    if currency not in ("RUB", "RUR", "643"):
        raise OneCInboundError(
            f"Неподдерживаемая валюта: {currency}",
            code="invalid_currency",
            http_status=400,
        )

    expected = (order.total_amount or Decimal("0")).quantize(Decimal("0.01"))
    if amount != expected:
        raise OneCInboundError(
            f"Сумма {amount} не совпадает с суммой заказа {expected}",
            code="amount_mismatch",
            http_status=409,
        )

    if pay_status == Order.PAYMENT_STATUS_PAID:
        if order.payment_status == Order.PAYMENT_STATUS_PAID:
            return order  # идемпотентно без event_id (event_id ловится выше)
        order.payment_status = Order.PAYMENT_STATUS_PAID
        order.onec_paid = True
        order.save(update_fields=["payment_status", "onec_paid", "updated_at"])
        return order

    if pay_status == Order.PAYMENT_STATUS_REFUNDED:
        if order.payment_status == Order.PAYMENT_STATUS_UNPAID:
            raise OneCInboundError(
                "Нельзя отметить refunded для неоплаченного заказа",
                code="refund_without_paid",
                http_status=409,
            )
        order.payment_status = Order.PAYMENT_STATUS_REFUNDED
        order.save(update_fields=["payment_status", "updated_at"])
        return order

    return order


@transaction.atomic
def process_inbound_order_event(data: dict[str, Any]) -> dict[str, Any]:
    """
    Обработать JSON от 1С. Возвращает тело успешного ответа.
    Бросает OneCInboundError при отказе (после записи error-события, если есть event_id).
    """
    event_id = (data.get("event_id") or "").strip()
    if not event_id:
        raise OneCInboundError(
            "event_id обязателен",
            code="event_id_required",
            http_status=400,
        )
    if len(event_id) > 128:
        raise OneCInboundError(
            "event_id слишком длинный",
            code="event_id_invalid",
            http_status=400,
        )

    existing = (
        OneCInboundEvent.objects.select_for_update()
        .filter(event_id=event_id)
        .first()
    )
    if existing and existing.processing_result in (
        OneCInboundEvent.RESULT_SUCCESS,
        OneCInboundEvent.RESULT_DUPLICATE,
    ):
        order_number = existing.order_number
        order = existing.order
        return {
            "success": True,
            "order_number": order_number,
            "order_status": order.status if order else None,
            "closure_result": order.closure_result if order else None,
            "payment_status": order.payment_status if order else None,
            "duplicate": True,
            "message": "Event already processed",
        }

    order_number = (data.get("order_number") or "").strip()
    if not order_number:
        raise OneCInboundError(
            "order_number обязателен",
            code="order_number_required",
            http_status=400,
        )

    has_status = bool((data.get("status") or "").strip())
    has_payment = isinstance(data.get("payment"), dict)
    if not has_status and not has_payment:
        raise OneCInboundError(
            "Нужен status и/или payment",
            code="empty_update",
            http_status=400,
        )

    occurred_at = None
    raw_occ = data.get("occurred_at")
    if raw_occ:
        occurred_at = parse_datetime(str(raw_occ))
        if occurred_at is None:
            raise OneCInboundError(
                "Некорректный occurred_at",
                code="invalid_occurred_at",
                http_status=400,
            )

    order = (
        Order.objects.select_for_update()
        .filter(order_number=order_number)
        .first()
    )
    if not order:
        OneCInboundEvent.objects.update_or_create(
            event_id=event_id,
            defaults={
                "order": None,
                "order_number": order_number,
                "event_type": _event_type(data),
                "status_received": (data.get("status") or "")[:32],
                "result_received": (data.get("result") or "")[:32],
                "payment_status_received": (
                    (data.get("payment") or {}).get("status") or ""
                    if isinstance(data.get("payment"), dict)
                    else ""
                )[:32],
                "processing_result": OneCInboundEvent.RESULT_ERROR,
                "error_code": "order_not_found",
                "error_message": "Order not found",
                "payload_summary": _summary_payload(data),
                "occurred_at": occurred_at,
            },
        )
        raise OneCInboundError(
            "Order not found",
            code="order_not_found",
            http_status=404,
        )

    try:
        if has_payment:
            order = _apply_payment(order, data["payment"])
        if has_status:
            order = _apply_fulfillment(order, data)
        order.refresh_from_db()
    except OneCInboundError as exc:
        OneCInboundEvent.objects.update_or_create(
            event_id=event_id,
            defaults={
                "order": order,
                "order_number": order_number,
                "event_type": _event_type(data),
                "status_received": (data.get("status") or "")[:32],
                "result_received": (data.get("result") or "")[:32],
                "payment_status_received": (
                    (data.get("payment") or {}).get("status") or ""
                    if isinstance(data.get("payment"), dict)
                    else ""
                )[:32],
                "processing_result": OneCInboundEvent.RESULT_ERROR,
                "error_code": exc.code,
                "error_message": exc.message[:512],
                "payload_summary": _summary_payload(data),
                "occurred_at": occurred_at,
            },
        )
        raise

    OneCInboundEvent.objects.update_or_create(
        event_id=event_id,
        defaults={
            "order": order,
            "order_number": order_number,
            "event_type": _event_type(data),
            "status_received": (data.get("status") or "")[:32],
            "result_received": (data.get("result") or "")[:32],
            "payment_status_received": (
                (data.get("payment") or {}).get("status") or ""
                if isinstance(data.get("payment"), dict)
                else ""
            )[:32],
            "processing_result": OneCInboundEvent.RESULT_SUCCESS,
            "error_code": "",
            "error_message": "",
            "payload_summary": _summary_payload(data),
            "occurred_at": occurred_at or timezone.now(),
        },
    )

    return {
        "success": True,
        "order_number": order.order_number,
        "order_status": order.status,
        "closure_result": order.closure_result,
        "payment_status": order.payment_status,
        "duplicate": False,
        "message": "Order updated successfully",
    }
