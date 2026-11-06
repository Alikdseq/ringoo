"""Бизнес-логика возвратов: FSM, частичные суммы, деньги, restock после inspection."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.payments.models import Payment
from apps.returns.models import MoneyRefund, ReturnEvent, ReturnItem, ReturnRequest
from apps.stores import stock_ops

logger = logging.getLogger(__name__)


def _gen_number() -> str:
    stamp = timezone.now().strftime("%Y%m%d")
    return f"RET-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def _line_amount(order_item, qty: int) -> Decimal:
    unit = Decimal(str(getattr(order_item, "price", None) or order_item.unit_price))
    return (unit * Decimal(qty)).quantize(Decimal("0.01"))


def already_returned_qty(order_item_id) -> int:
    agg = (
        ReturnItem.objects.filter(order_item_id=order_item_id)
        .exclude(
            return_request__status__in=[
                ReturnRequest.STATUS_CANCELLED,
                ReturnRequest.STATUS_REJECTED,
            ]
        )
        .aggregate(s=Sum("quantity"))
    )
    return int(agg["s"] or 0)


@transaction.atomic
def create_return_request(
    *,
    order,
    user,
    ground: str,
    demand: str,
    description: str,
    items: list[dict],
    return_method: str = "",
    contact_phone: str = "",
    contact_email: str = "",
) -> ReturnRequest:
    """
    items: [{order_item_id, quantity}, ...]
    Не инициирует деньги и не меняет склад.
    """
    if not items:
        raise ValueError("Нужна хотя бы одна позиция")
    rr = ReturnRequest.objects.create(
        number=_gen_number(),
        order=order,
        user=user if getattr(user, "is_authenticated", False) else None,
        ground=ground,
        demand=demand or ReturnRequest.DEMAND_REFUND,
        description=(description or "")[:4000],
        return_method=return_method or "",
        contact_phone=(contact_phone or "")[:32],
        contact_email=(contact_email or "")[:254],
        goods_handed_over_at=(
            order.updated_at
            if getattr(order, "status", None) == getattr(order, "STATUS_COMPLETED", "completed")
            else None
        ),
    )
    total = Decimal("0.00")
    for raw in items:
        oi = order.items.select_for_update().get(pk=raw["order_item_id"])
        qty = int(raw["quantity"])
        if qty < 1 or qty > int(oi.quantity):
            raise ValueError("Некорректное количество")
        used = already_returned_qty(oi.pk)
        if used + qty > int(oi.quantity):
            raise ValueError("Превышено доступное для возврата количество")
        line = _line_amount(oi, qty)
        ReturnItem.objects.create(
            return_request=rr,
            order_item=oi,
            quantity=qty,
            unit_price=getattr(oi, "price", None) or getattr(oi, "unit_price"),
            line_refund_amount=line,
            product_title=getattr(oi, "product_title", "") or str(oi.product_id),
            color_label=getattr(oi, "color_label", "") or "",
            color_id=getattr(oi, "color_id", None),
            onec_series_id=getattr(oi, "onec_series_id", "") or "",
        )
        total += line
    rr.requested_refund_amount = total
    rr.save(update_fields=["requested_refund_amount", "updated_at"])
    _event(rr, "", ReturnRequest.STATUS_REQUESTED, user, "created")
    return rr


def _event(rr, frm, to, actor, message, **meta):
    ReturnEvent.objects.create(
        return_request=rr,
        from_status=frm or "",
        to_status=to or "",
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        message=message or "",
        meta=meta or {},
    )


@transaction.atomic
def transition_return(
    rr: ReturnRequest,
    new_status: str,
    *,
    actor=None,
    message: str = "",
    rejection_reason: str = "",
) -> ReturnRequest:
    rr = ReturnRequest.objects.select_for_update().get(pk=rr.pk)
    if not rr.can_transition(new_status):
        raise ValueError(f"Переход {rr.status} → {new_status} запрещён")
    old = rr.status
    rr.status = new_status
    if rejection_reason:
        rr.rejection_reason = rejection_reason[:2000]
    if new_status == ReturnRequest.STATUS_APPROVED and rr.approved_refund_amount <= 0:
        rr.approved_refund_amount = rr.requested_refund_amount
    rr.save()
    _event(rr, old, new_status, actor, message or new_status)
    return rr


def paid_amount_for_order(order) -> Decimal:
    paid = (
        Payment.objects.filter(order=order, status=Payment.STATUS_PAID)
        .order_by("-created_at")
        .first()
    )
    if not paid:
        # already fully refunded payment still caps by original amount
        paid = (
            Payment.objects.filter(
                order=order,
                status__in=[Payment.STATUS_REFUNDED, Payment.STATUS_NEEDS_REVIEW],
            )
            .order_by("-created_at")
            .first()
        )
    if not paid:
        return Decimal("0.00")
    return Decimal(str(paid.amount))


def refunded_so_far(payment: Payment) -> Decimal:
    agg = MoneyRefund.objects.filter(
        payment=payment, status=MoneyRefund.STATUS_SUCCEEDED
    ).aggregate(s=Sum("amount"))
    return Decimal(str(agg["s"] or 0))


@transaction.atomic
def initiate_money_refund(
    rr: ReturnRequest,
    *,
    amount: Decimal | None = None,
    actor=None,
    dry_run: bool = True,
) -> MoneyRefund:
    """
    Создаёт MoneyRefund. По умолчанию dry_run=True — не вызывает провайдера
    (безопасно для staging без реальных возвратов).
    """
    rr = ReturnRequest.objects.select_for_update().get(pk=rr.pk)
    payment = (
        Payment.objects.select_for_update()
        .filter(order_id=rr.order_id, status=Payment.STATUS_PAID)
        .order_by("-created_at")
        .first()
    )
    if payment is None:
        raise ValueError("Нет оплаченного платежа для возврата")
    amount = Decimal(str(amount if amount is not None else rr.approved_refund_amount))
    if amount <= 0:
        raise ValueError("Сумма возврата должна быть > 0")
    already = refunded_so_far(payment)
    cap = Decimal(str(payment.amount))
    if already + amount > cap:
        raise ValueError("Сумма возвратов превысит оплаченную")
    key = f"ret:{rr.pk}:{amount}:{already}"
    existing = MoneyRefund.objects.filter(idempotency_key=key).first()
    if existing:
        return existing

    provider = MoneyRefund.PROVIDER_YOOKASSA
    if payment.provider == "sber" or getattr(payment, "sber_order_id", None):
        provider = MoneyRefund.PROVIDER_SBER

    mr = MoneyRefund.objects.create(
        return_request=rr,
        payment=payment,
        amount=amount,
        currency="RUB",
        provider=provider,
        status=MoneyRefund.STATUS_PENDING,
        idempotency_key=key[:128],
    )
    transition_return(
        rr,
        ReturnRequest.STATUS_REFUND_PROCESSING,
        actor=actor,
        message="money_refund_created",
    )

    if dry_run:
        mr.status = MoneyRefund.STATUS_NEEDS_REVIEW
        mr.error_message = "dry_run: provider API not called"
        mr.save(update_fields=["status", "error_message", "updated_at"])
        _event(rr, "", "", actor, "money_refund_dry_run", money_refund_id=str(mr.pk))
        return mr

    if provider == MoneyRefund.PROVIDER_YOOKASSA:
        from integrations.yookassa.client import YooKassaClient

        client = YooKassaClient()
        yk_id = payment.yookassa_payment_id
        if not yk_id:
            mr.status = MoneyRefund.STATUS_FAILED
            mr.error_message = "Нет yookassa_payment_id"
            mr.save()
            return mr
        mr.status = MoneyRefund.STATUS_PROCESSING
        mr.save(update_fields=["status", "updated_at"])
        data = client.create_refund(
            payment_id=yk_id, amount=amount, idempotence_key=mr.idempotency_key
        )
        mr.provider_refund_id = str(data.get("id") or "")
        st = str(data.get("status") or "")
        if st == "succeeded":
            mr.status = MoneyRefund.STATUS_SUCCEEDED
            mr.confirmed_at = timezone.now()
        else:
            mr.status = MoneyRefund.STATUS_PROCESSING
        mr.save()
        return mr

    # Sber: без согласованного reverse/refund API — только сверка
    mr.status = MoneyRefund.STATUS_NEEDS_REVIEW
    mr.error_message = "Sber refund requires business decision / manual ops"
    mr.save()
    return mr


@transaction.atomic
def inspect_and_maybe_restock(
    rr: ReturnRequest,
    *,
    item_updates: list[dict],
    actor=None,
    store_id=None,
) -> ReturnRequest:
    """
    item_updates: [{return_item_id, condition, restock_qty?}]
    Restock только для sellable и только через stock_ops.
    """
    rr = ReturnRequest.objects.select_for_update().get(pk=rr.pk)
    if rr.status not in (
        ReturnRequest.STATUS_INSPECTION,
        ReturnRequest.STATUS_RECEIVED,
        ReturnRequest.STATUS_REFUNDED,
    ):
        if rr.status == ReturnRequest.STATUS_RECEIVED:
            transition_return(rr, ReturnRequest.STATUS_INSPECTION, actor=actor)
            rr.refresh_from_db()
        else:
            raise ValueError("Проверка возможна после получения товара")

    for upd in item_updates:
        item = ReturnItem.objects.select_for_update().get(
            pk=upd["return_item_id"], return_request=rr
        )
        condition = upd["condition"]
        item.condition = condition
        restock_qty = int(upd.get("restock_qty") or 0)
        if condition == ReturnItem.CONDITION_SELLABLE and restock_qty > 0:
            remaining = item.quantity - item.restocked_quantity
            if restock_qty > remaining:
                raise ValueError("restock_qty превышает доступное")
            target_store = store_id or rr.order.store_id
            if not target_store:
                raise ValueError("Не указан склад для restock")
            stock_ops.restock_at_store(
                product_id=item.order_item.product_id,
                store_id=target_store,
                amount=restock_qty,
                series_id=item.onec_series_id or "",
                idempotency_key=f"return_restock:{item.pk}:{item.restocked_quantity + restock_qty}",
                order_id=rr.order_id,
                order_item_id=item.order_item_id,
                reason=f"return:{rr.number}",
                source="returns.inspect",
            )
            item.restocked_quantity += restock_qty
        item.save()
    if any(i.restocked_quantity > 0 for i in rr.items.all()):
        transition_return(rr, ReturnRequest.STATUS_RESTOCKED, actor=actor, message="restock")
    return rr
