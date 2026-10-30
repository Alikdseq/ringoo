"""
Сервис оплаты через Сбер ecom: регистрация, сверка статуса, callback, таймаут.
Сумма всегда из Order.total_amount в БД.

HTTP к банку выполняется ВНЕ долгой DB-транзакции (фаза A).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services import cancel_order_and_release_stock
from integrations.sber.client import SberEcomClient, SberEcomError
from integrations.sber.statuses import is_paid_one_stage, is_terminal_failure

from .models import Payment

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Публично безопасная ошибка оплаты."""

    def __init__(self, message: str, *, code: str = "payment_error"):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class InitiateResult:
    payment: Payment
    form_url: str
    reused: bool


def _frontend_url() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _build_return_urls(order: Order) -> tuple[str, str]:
    base = _frontend_url()
    success = getattr(settings, "SBER_ECOM_RETURN_URL", "").strip()
    fail = getattr(settings, "SBER_ECOM_FAIL_URL", "").strip()
    if not success:
        success = f"{base}/orders/{order.id}/payment/return"
    else:
        success = success.format(order_id=order.id, order_number=order.order_number)
    if not fail:
        fail = f"{base}/orders/{order.id}/payment/fail"
    else:
        fail = fail.format(order_id=order.id, order_number=order.order_number)
    return success, fail


def _callback_url() -> str | None:
    raw = getattr(settings, "SBER_ECOM_CALLBACK_URL", "").strip()
    return raw or None


def _session_timeout_secs() -> int:
    minutes = int(getattr(settings, "ONLINE_PAYMENT_TIMEOUT_MINUTES", 20))
    return max(60, minutes * 60)


def _late_payment_policy() -> str:
    """revive | reverse | manual (по умолчанию)."""
    raw = getattr(settings, "LATE_ONLINE_PAYMENT_POLICY", "manual") or "manual"
    return str(raw).strip().lower()


def _sanitize_bank_payload(data: dict[str, Any]) -> dict[str, Any]:
    blocked = {"password", "userName", "$PAN", "$CVC", "cvc", "pan"}
    return {k: v for k, v in data.items() if k not in blocked}


def _reject_untrusted_paid_payload(
    locked: Payment,
    data: dict[str, Any],
    amount_kopecks: int,
) -> str | None:
    """
    Fail-closed проверки перед переходом в paid / late-payment review.
    Клиентский callback и поля status/amount из браузера сюда не попадают —
    источник истины только ответ getOrderStatusExtended, сверяемый с локальным Payment.
    Возвращает текст ошибки или None, если доверие достаточное.
    """
    bank_amount = data.get("amount")
    if bank_amount is None:
        return "Ответ банка без суммы — оплата не подтверждена"
    try:
        if int(bank_amount) != int(amount_kopecks):
            return "Сумма в банке не совпадает с заказом"
    except (TypeError, ValueError):
        return "Некорректная сумма в ответе банка"

    bank_order_number = str(data.get("orderNumber") or "").strip()
    if not bank_order_number:
        return "Ответ банка без orderNumber — оплата не подтверждена"
    if bank_order_number != locked.merchant_order_number:
        return "orderNumber банка не принадлежит этому платежу"

    bank_currency = data.get("currency")
    if bank_currency is not None and str(bank_currency).strip():
        if str(bank_currency).strip() != str(locked.currency).strip():
            return "Валюта банка не совпадает с платежом"
    return None


def _phone_for_sber(phone: str) -> str | None:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) == 11 and digits.startswith("7"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+7{digits}"
    return None


def _create_payment_row(order: Order) -> Payment:
    """Короткая транзакция: валидация + запись Payment(created). Без HTTP."""
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)

        if locked.payment_type != Order.PAYMENT_ONLINE:
            raise PaymentError(
                "Онлайн-оплата недоступна для этого способа оплаты",
                code="not_online",
            )
        if locked.status == Order.STATUS_CANCELLED:
            raise PaymentError("Заказ отменён", code="order_cancelled")
        if locked.status not in (Order.STATUS_NEW, Order.STATUS_CONFIRMED):
            raise PaymentError(
                "Заказ нельзя оплатить в текущем статусе",
                code="order_status",
            )

        if (
            Payment.objects.select_for_update()
            .filter(order=locked, status=Payment.STATUS_PAID)
            .exists()
        ):
            raise PaymentError("Заказ уже оплачен", code="already_paid")

        active = (
            Payment.objects.select_for_update()
            .filter(
                order=locked,
                status__in=(Payment.STATUS_REGISTERED, Payment.STATUS_PENDING),
            )
            .exclude(form_url="")
            .order_by("-created_at")
            .first()
        )
        if active and active.form_url and active.sber_order_id:
            return active  # reuse marker: already registered

        # Повтор register для «зависшего» created без ответа банка
        dangling = (
            Payment.objects.select_for_update()
            .filter(order=locked, status=Payment.STATUS_CREATED, sber_order_id__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if dangling:
            return dangling

        amount = Decimal(locked.total_amount)
        if amount <= 0:
            raise PaymentError("Сумма заказа должна быть больше нуля", code="zero_amount")

        payment_id = uuid.uuid4()
        return Payment.objects.create(
            id=payment_id,
            order=locked,
            provider=Payment.PROVIDER_SBER,
            status=Payment.STATUS_CREATED,
            amount=amount,
            amount_kopecks=Payment.rubles_to_kopecks(amount),
            currency="643",
            merchant_order_number=payment_id.hex,
        )


def initiate_sber_payment(
    order: Order,
    *,
    client: SberEcomClient | None = None,
) -> InitiateResult:
    """
    Регистрирует одностадийный платёж в Сбере и возвращает formUrl.
    HTTP register — вне DB-транзакции.
    """
    payment = _create_payment_row(order)
    if payment.status in (Payment.STATUS_REGISTERED, Payment.STATUS_PENDING) and payment.form_url:
        return InitiateResult(payment=payment, form_url=payment.form_url, reused=True)

    order_ref = Order.objects.get(pk=order.pk)
    return_url, fail_url = _build_return_urls(order_ref)
    api = client or SberEcomClient()

    try:
        result = api.register_order(
            order_number=payment.merchant_order_number,
            amount_kopecks=payment.amount_kopecks,
            return_url=return_url,
            fail_url=fail_url,
            description=f"Заказ {order_ref.order_number}",
            email=(order_ref.email or None),
            phone=_phone_for_sber(order_ref.phone),
            session_timeout_secs=_session_timeout_secs(),
            dynamic_callback_url=_callback_url(),
        )
    except SberEcomError as exc:
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(pk=payment.pk)
            p.status = Payment.STATUS_FAILED
            p.error_code = str(exc.error_code or "")
            p.error_message = str(exc)[:512]
            p.register_response = _sanitize_bank_payload(exc.payload)
            p.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "register_response",
                    "updated_at",
                ]
            )
        logger.warning("Sber register failed order=%s: %s", order_ref.order_number, exc)
        raise PaymentError(
            "Не удалось создать платёж. Попробуйте позже.",
            code="sber_register_failed",
        ) from exc

    with transaction.atomic():
        p = Payment.objects.select_for_update().get(pk=payment.pk)
        if p.status == Payment.STATUS_PAID:
            return InitiateResult(payment=p, form_url=p.form_url or result["formUrl"], reused=True)
        p.sber_order_id = result["orderId"]
        p.form_url = result["formUrl"]
        p.status = Payment.STATUS_REGISTERED
        p.register_response = _sanitize_bank_payload(result.get("raw") or {})
        p.error_code = "0"
        p.error_message = ""
        p.save(
            update_fields=[
                "sber_order_id",
                "form_url",
                "status",
                "register_response",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        return InitiateResult(payment=p, form_url=p.form_url, reused=False)


def apply_late_payment_policy(payment_id, *, client: SberEcomClient | None = None) -> Payment:
    """
    Банк подтвердил оплату, заказ cancelled.
    Политика LATE_ONLINE_PAYMENT_POLICY: revive | reverse | manual.
    HTTP reverse — вне длительной чужой транзакции (вызывается через on_commit).
    """
    api = client or SberEcomClient()
    policy = _late_payment_policy()

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("order")
            .prefetch_related("order__items")
            .get(pk=payment_id)
        )
        order = payment.order
        logger.error(
            "Paid after cancel: order=%s payment=%s policy=%s",
            order.order_number,
            payment.pk,
            policy,
        )

        if order.status != Order.STATUS_CANCELLED:
            # Уже восстановили / обработали
            return payment

        if policy == "revive":
            order.status = Order.STATUS_CONFIRMED
            order.save(update_fields=["status", "updated_at"])
            from integrations.onec.orders import reserve_order_item_reservations

            stock_ok = reserve_order_item_reservations(order)
            payment.paid_at = timezone.now()
            payment.error_code = "0"
            if stock_ok:
                payment.status = Payment.STATUS_PAID
                payment.error_message = "Заказ восстановлен после поздней оплаты"
            else:
                payment.status = Payment.STATUS_NEEDS_REVIEW
                payment.error_message = (
                    "Оплата есть, заказ confirmed, резерв остатков неполный — сверка"
                )
            payment.save(
                update_fields=[
                    "status",
                    "paid_at",
                    "error_code",
                    "error_message",
                    "updated_at",
                ]
            )
            if payment.status == Payment.STATUS_PAID:
                order_pk = order.pk

                def _enqueue_onec_paid_revive():
                    from apps.orders.tasks import enqueue_order_sync

                    enqueue_order_sync(order_pk, paid=True)

                transaction.on_commit(_enqueue_onec_paid_revive)
            return payment

        if policy == "manual":
            payment.status = Payment.STATUS_NEEDS_REVIEW
            payment.error_message = (
                "Оплата после отмены заказа — ручная сверка "
                "(LATE_ONLINE_PAYMENT_POLICY=revive|reverse)"
            )[:512]
            payment.save(update_fields=["status", "error_message", "updated_at"])
            return payment

        # reverse: HTTP после короткой пометки
        sber_id = payment.sber_order_id
        payment.status = Payment.STATUS_NEEDS_REVIEW
        payment.error_message = "Ожидается auto-reverse…"
        payment.save(update_fields=["status", "error_message", "updated_at"])

    if policy == "reverse" and sber_id:
        try:
            api.reverse_order(order_id=sber_id)
            with transaction.atomic():
                p = Payment.objects.select_for_update().get(pk=payment_id)
                p.status = Payment.STATUS_REVERSED
                p.error_message = "Авто-reverse после оплаты отменённого заказа"
                p.save(update_fields=["status", "error_message", "updated_at"])
                return p
        except SberEcomError as exc:
            logger.exception("Auto-reverse failed payment=%s: %s", payment_id, exc)
            with transaction.atomic():
                p = Payment.objects.select_for_update().get(pk=payment_id)
                p.status = Payment.STATUS_NEEDS_REVIEW
                p.error_message = f"Reverse не удался: {exc}"[:512]
                p.save(update_fields=["status", "error_message", "updated_at"])
                return p

    return Payment.objects.get(pk=payment_id)


def sync_payment_from_bank(
    payment: Payment,
    *,
    client: SberEcomClient | None = None,
    from_callback: bool = False,
) -> Payment:
    """
    Запрашивает getOrderStatusExtended и обновляет Payment / Order.
    HTTP к банку — вне DB-транзакции; идемпотентно при уже paid.
    """
    with transaction.atomic():
        locked = (
            Payment.objects.select_for_update()
            .only(
                "id",
                "status",
                "sber_order_id",
                "merchant_order_number",
                "amount_kopecks",
                "order_id",
            )
            .get(pk=payment.pk)
        )
        if locked.status == Payment.STATUS_PAID:
            return Payment.objects.select_related("order").get(pk=locked.pk)
        if locked.status in (Payment.STATUS_REVERSED, Payment.STATUS_REFUNDED):
            return Payment.objects.select_related("order").get(pk=locked.pk)
        sber_order_id = locked.sber_order_id
        merchant_order_number = locked.merchant_order_number
        amount_kopecks = locked.amount_kopecks
        payment_pk = locked.pk

    api = client or SberEcomClient()
    client_ref = api
    try:
        if sber_order_id:
            data = api.get_order_status(order_id=sber_order_id)
        else:
            data = api.get_order_status(order_number=merchant_order_number)
    except SberEcomError as exc:
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=payment_pk)
            locked.error_message = str(exc)[:512]
            locked.last_status_checked_at = timezone.now()
            if from_callback:
                locked.callback_received_at = (
                    locked.callback_received_at or timezone.now()
                )
            locked.save(
                update_fields=[
                    "error_message",
                    "last_status_checked_at",
                    "callback_received_at",
                    "updated_at",
                ]
            )
        raise PaymentError(
            "Не удалось проверить статус оплаты",
            code="sber_status_failed",
        ) from exc

    with transaction.atomic():
        locked = Payment.objects.select_for_update().select_related("order").get(
            pk=payment_pk
        )
        if locked.status == Payment.STATUS_PAID:
            return locked
        if locked.status in (Payment.STATUS_REVERSED, Payment.STATUS_REFUNDED):
            return locked

        locked.last_status_response = _sanitize_bank_payload(data)
        locked.last_status_checked_at = timezone.now()
        if from_callback:
            locked.callback_received_at = timezone.now()

        order_status = data.get("orderStatus")
        action_code = data.get("actionCode")
        try:
            locked.sber_order_status = (
                int(order_status) if order_status is not None else None
            )
        except (TypeError, ValueError):
            locked.sber_order_status = None
        try:
            locked.action_code = int(action_code) if action_code is not None else None
        except (TypeError, ValueError):
            locked.action_code = None

        # Ранний отказ при явной рассинхронизации суммы (любой статус ответа банка).
        bank_amount = data.get("amount")
        if bank_amount is not None:
            try:
                if int(bank_amount) != int(amount_kopecks):
                    logger.warning(
                        "Sber amount mismatch payment=%s local=%s bank=%s",
                        locked.pk,
                        amount_kopecks,
                        bank_amount,
                    )
                    locked.error_message = "Сумма в банке не совпадает с заказом"
                    locked.status = Payment.STATUS_FAILED
                    locked.save()
                    return locked
            except (TypeError, ValueError):
                locked.error_message = "Некорректная сумма в ответе банка"
                locked.status = Payment.STATUS_FAILED
                locked.save()
                return locked

        order = Order.objects.select_for_update().get(pk=locked.order_id)

        if is_paid_one_stage(
            order_status=locked.sber_order_status,
            action_code=locked.action_code,
        ):
            binding_error = _reject_untrusted_paid_payload(
                locked, data, amount_kopecks
            )
            if binding_error:
                logger.warning(
                    "Sber paid rejected payment=%s reason=%s",
                    locked.pk,
                    binding_error,
                )
                locked.error_message = binding_error
                locked.status = Payment.STATUS_FAILED
                locked.save()
                return locked

            if order.status == Order.STATUS_CANCELLED:
                locked.status = Payment.STATUS_NEEDS_REVIEW
                locked.error_message = "Оплата после отмены — обработка политики…"
                locked.save()
                pid = locked.pk

                def _run_late():
                    apply_late_payment_policy(pid, client=client_ref)

                transaction.on_commit(_run_late)
                return locked

            other_paid = (
                Payment.objects.select_for_update()
                .filter(order=order, status=Payment.STATUS_PAID)
                .exclude(pk=locked.pk)
                .exists()
            )
            if other_paid:
                locked.status = Payment.STATUS_FAILED
                locked.error_message = "Дубликат оплаты отклонён"
                locked.save()
                return locked

            locked.status = Payment.STATUS_PAID
            locked.paid_at = timezone.now()
            locked.error_code = "0"
            locked.error_message = ""
            try:
                # Savepoint: IntegrityError иначе ломает внешний atomic.
                with transaction.atomic():
                    locked.save()
            except IntegrityError:
                # Гонка: другой платёж уже paid на этом заказе (unique constraint).
                Payment.objects.filter(pk=locked.pk).update(
                    status=Payment.STATUS_FAILED,
                    error_message="Дубликат оплаты отклонён (constraint)",
                    paid_at=None,
                    error_code="",
                )
                return Payment.objects.select_related("order").get(pk=locked.pk)

            if order.status == Order.STATUS_NEW:
                order.status = Order.STATUS_CONFIRMED
                order.save(update_fields=["status", "updated_at"])

            order_pk = order.pk

            def _enqueue_onec_paid():
                from apps.orders.tasks import enqueue_order_sync

                # Переход paid=false → paid=true тем же orderId и составом
                enqueue_order_sync(order_pk, paid=True)

            transaction.on_commit(_enqueue_onec_paid)
            return locked

        if locked.sber_order_status == 3:
            locked.status = Payment.STATUS_REVERSED
            locked.save()
            return locked

        if locked.sber_order_status == 4:
            locked.status = Payment.STATUS_REFUNDED
            locked.save()
            return locked

        if is_terminal_failure(order_status=locked.sber_order_status):
            locked.status = Payment.STATUS_FAILED
            locked.error_message = str(
                data.get("actionCodeDescription")
                or data.get("errorMessage")
                or "Оплата отклонена"
            )[:512]
            locked.save()
            return locked

        if locked.status in (Payment.STATUS_CREATED, Payment.STATUS_REGISTERED):
            locked.status = Payment.STATUS_PENDING
        locked.save()
        return locked


def handle_sber_callback(
    payload: dict[str, Any],
    *,
    client: SberEcomClient | None = None,
) -> Payment | None:
    md_order = str(payload.get("mdOrder") or "").strip()
    order_number = str(payload.get("orderNumber") or "").strip()

    payment = None
    if md_order:
        payment = Payment.objects.filter(sber_order_id=md_order).first()
    if payment is None and order_number:
        payment = Payment.objects.filter(merchant_order_number=order_number).first()
    if payment is None:
        logger.warning(
            "Sber callback: payment not found mdOrder=%s orderNumber=%s",
            md_order,
            order_number,
        )
        return None

    try:
        return sync_payment_from_bank(payment, client=client, from_callback=True)
    except PaymentError:
        logger.warning("Sber callback sync failed payment=%s", payment.pk)
        return payment


def reconcile_open_payments(
    *,
    client: SberEcomClient | None = None,
    older_than_minutes: int = 2,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Сверка зависших платежей с банком (пропущенный callback / падение сайта).
    """
    api = client or SberEcomClient()
    cutoff = timezone.now() - timedelta(minutes=max(0, older_than_minutes))
    qs = (
        Payment.objects.filter(
            status__in=(
                Payment.STATUS_CREATED,
                Payment.STATUS_REGISTERED,
                Payment.STATUS_PENDING,
            ),
            created_at__lt=cutoff,
        )
        .exclude(sber_order_id__isnull=True)
        .exclude(sber_order_id="")
        .order_by("created_at")[:limit]
    )

    synced = 0
    paid = 0
    errors = 0
    for payment in qs:
        try:
            updated = sync_payment_from_bank(payment, client=api)
            synced += 1
            if updated.status == Payment.STATUS_PAID:
                paid += 1
            elif updated.status == Payment.STATUS_NEEDS_REVIEW:
                paid += 0
        except PaymentError:
            errors += 1
    return {
        "synced": synced,
        "became_paid_or_terminal": paid,
        "errors": errors,
        "older_than_minutes": older_than_minutes,
    }


def find_hung_payments(*, pending_minutes: int = 30) -> dict[str, Any]:
    """Снимок для мониторинга (без вызова банка)."""
    now = timezone.now()
    pending_cut = now - timedelta(minutes=pending_minutes)
    pending = list(
        Payment.objects.filter(
            status__in=(
                Payment.STATUS_REGISTERED,
                Payment.STATUS_PENDING,
                Payment.STATUS_CREATED,
            ),
            created_at__lt=pending_cut,
        ).values(
            "id",
            "order_id",
            "merchant_order_number",
            "sber_order_id",
            "status",
            "created_at",
            "amount",
        )[:200]
    )
    needs_review = list(
        Payment.objects.filter(status=Payment.STATUS_NEEDS_REVIEW).values(
            "id",
            "order_id",
            "merchant_order_number",
            "sber_order_id",
            "error_message",
            "updated_at",
            "amount",
        )[:200]
    )
    return {
        "pending_older_than_minutes": pending_minutes,
        "pending_count": len(pending),
        "needs_review_count": len(needs_review),
        "pending": pending,
        "needs_review": needs_review,
    }


def expire_unpaid_online_orders(
    *,
    now=None,
    client: SberEcomClient | None = None,
) -> dict[str, Any]:
    """
    Перед отменой — сверка незавершённых платежей с банком.
    Если оплачен — заказ не отменяем.
    """
    now = now or timezone.now()
    minutes = int(getattr(settings, "ONLINE_PAYMENT_TIMEOUT_MINUTES", 20))
    cutoff = now - timedelta(minutes=minutes)
    api = client  # может быть None → sync создаст клиент; для тестов передаём mock

    qs = (
        Order.objects.filter(
            payment_type=Order.PAYMENT_ONLINE,
            status__in=(Order.STATUS_NEW, Order.STATUS_CONFIRMED),
            created_at__lt=cutoff,
        )
        .exclude(payments__status=Payment.STATUS_PAID)
        .distinct()
    )

    cancelled = 0
    rescued = 0
    for order in qs.iterator():
        # 1) Сверка с банком ВНЕ блокировки отмены
        open_payments = Payment.objects.filter(
            order_id=order.pk,
            status__in=(
                Payment.STATUS_CREATED,
                Payment.STATUS_REGISTERED,
                Payment.STATUS_PENDING,
            ),
        ).exclude(sber_order_id__isnull=True).exclude(sber_order_id="")
        for payment in open_payments:
            try:
                updated = sync_payment_from_bank(payment, client=api)
                if updated.status == Payment.STATUS_PAID:
                    rescued += 1
            except PaymentError:
                logger.warning(
                    "Expire: bank sync failed payment=%s order=%s",
                    payment.pk,
                    order.order_number,
                )

        # 2) Отмена если всё ещё не paid
        with transaction.atomic():
            locked = Order.objects.select_for_update().get(pk=order.pk)
            if locked.status == Order.STATUS_CANCELLED:
                continue
            if Payment.objects.filter(order=locked, status=Payment.STATUS_PAID).exists():
                continue
            if locked.created_at >= cutoff:
                continue
            cancel_order_and_release_stock(
                locked,
                reason=f"online_payment_timeout_{minutes}m",
            )
            Payment.objects.filter(
                order=locked,
                status__in=(
                    Payment.STATUS_CREATED,
                    Payment.STATUS_REGISTERED,
                    Payment.STATUS_PENDING,
                ),
            ).update(
                status=Payment.STATUS_EXPIRED,
                updated_at=now,
                error_message="Истёк срок оплаты",
            )
            cancelled += 1

    return {
        "cancelled": cancelled,
        "rescued_paid": rescued,
        "timeout_minutes": minutes,
        "cutoff": cutoff.isoformat(),
    }
