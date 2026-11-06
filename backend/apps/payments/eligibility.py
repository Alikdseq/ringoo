"""
Допустимость онлайн-оплаты заказа (единый источник для API и initiate).

Статус заказа (Order.status) ≠ статус платежа (Payment.status).
Оплата разрешена только для payment_type=online и статусов new/confirmed,
если нет успешного/блокирующего платежа.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.orders.models import Order
    from apps.payments.models import Payment


@dataclass(frozen=True)
class PaymentEligibility:
    can_pay: bool
    code: str
    detail: str
    latest_payment_status: str | None = None


# Заказ ещё ждёт онлайн-оплату (не путать с Payment.STATUS_*).
PAYABLE_ORDER_STATUSES = frozenset({"new", "confirmed"})

# Эти статусы платежа запрещают новый/повторный initiate.
BLOCKING_PAYMENT_STATUSES = frozenset(
    {
        "paid",
        "needs_review",
        "reversed",
        "refunded",
    }
)

# Активный платёж можно продолжить (тот же confirmation_url).
RESUMABLE_PAYMENT_STATUSES = frozenset({"registered", "pending", "created"})


def evaluate_order_payment_eligibility(order: "Order") -> PaymentEligibility:
    """
    Чистая проверка без HTTP к ЮKassa.
    Используется в OrderSerializer.can_pay и как предварительный фильтр.
    """
    from apps.orders.models import Order
    from apps.payments.models import Payment
    from apps.payments.services import online_payment_provider

    latest: Payment | None = order.payments.order_by("-created_at").first()
    latest_status = latest.status if latest else None

    if order.payment_type != Order.PAYMENT_ONLINE:
        return PaymentEligibility(
            False,
            "not_online",
            "Онлайн-оплата недоступна для этого способа оплаты",
            latest_status,
        )

    if order.status == Order.STATUS_CANCELLED:
        return PaymentEligibility(
            False, "order_cancelled", "Заказ отменён", latest_status
        )

    if order.status == Order.STATUS_COMPLETED:
        return PaymentEligibility(
            False, "order_completed", "Заказ уже выполнен", latest_status
        )

    if order.status == Order.STATUS_IN_PROGRESS:
        return PaymentEligibility(
            False,
            "order_status",
            "Заказ нельзя оплатить в текущем статусе",
            latest_status,
        )

    if order.status not in PAYABLE_ORDER_STATUSES:
        return PaymentEligibility(
            False,
            "order_status",
            "Заказ нельзя оплатить в текущем статусе",
            latest_status,
        )

    if not online_payment_provider():
        return PaymentEligibility(
            False,
            "payments_disabled",
            "Онлайн-оплата временно недоступна",
            latest_status,
        )

    # Успешный / блокирующий платёж
    blocking = (
        order.payments.filter(status__in=BLOCKING_PAYMENT_STATUSES)
        .order_by("-created_at")
        .first()
    )
    if blocking:
        if blocking.status == Payment.STATUS_PAID:
            return PaymentEligibility(
                False, "already_paid", "Заказ уже оплачен", blocking.status
            )
        return PaymentEligibility(
            False,
            "payment_blocked",
            "Оплата этого заказа недоступна (платёж на проверке или закрыт)",
            blocking.status,
        )

    if latest and latest.status in RESUMABLE_PAYMENT_STATUSES:
        return PaymentEligibility(
            True, "ok", "Можно продолжить оплату", latest.status
        )

    # failed / expired / нет платежа — можно создать новый
    return PaymentEligibility(True, "ok", "Можно оплатить", latest_status)


def assert_order_payable_or_raise(order: "Order") -> None:
    """Жёсткая проверка перед create/reuse платежа (без HTTP)."""
    from apps.payments.services import PaymentError

    elig = evaluate_order_payment_eligibility(order)
    if not elig.can_pay:
        raise PaymentError(elig.detail, code=elig.code)
