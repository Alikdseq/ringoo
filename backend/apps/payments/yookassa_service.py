"""
Сервис оплаты через ЮKassa: создание платежа, сверка статуса, webhook.
Сумма всегда из Order.total_amount. Успех — только после GET /payments/{id}.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders.models import Order
from integrations.yookassa.client import YooKassaClient, YooKassaError

from .models import Payment
from .services import InitiateResult, PaymentError, apply_late_payment_policy

logger = logging.getLogger(__name__)


def _frontend_url() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _return_url(order: Order) -> str:
    raw = getattr(settings, "YOOKASSA_RETURN_URL", "").strip()
    if raw:
        return raw.format(order_id=order.id, order_number=order.order_number)
    return f"{_frontend_url()}/orders/{order.id}/payment/return"


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    blocked = {"password", "secret", "authorization", "card", "payment_method"}
    return {k: v for k, v in data.items() if k.lower() not in blocked}


def _create_yookassa_payment_row(order: Order) -> Payment:
    from apps.payments.eligibility import assert_order_payable_or_raise

    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        assert_order_payable_or_raise(locked)

        active = (
            Payment.objects.select_for_update()
            .filter(
                order=locked,
                provider=Payment.PROVIDER_YOOKASSA,
                status__in=(Payment.STATUS_REGISTERED, Payment.STATUS_PENDING),
            )
            .exclude(form_url="")
            .order_by("-created_at")
            .first()
        )
        if active and active.form_url and active.yookassa_payment_id:
            return active

        dangling = (
            Payment.objects.select_for_update()
            .filter(
                order=locked,
                provider=Payment.PROVIDER_YOOKASSA,
                status=Payment.STATUS_CREATED,
                yookassa_payment_id__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if dangling:
            return dangling

        amount = Decimal(locked.total_amount)
        if amount <= 0:
            raise PaymentError("Сумма заказа должна быть больше нуля", code="zero_amount")

        payment_id = uuid.uuid4()
        is_test = bool(getattr(settings, "YOOKASSA_TEST_MODE", True))
        return Payment.objects.create(
            id=payment_id,
            order=locked,
            provider=Payment.PROVIDER_YOOKASSA,
            status=Payment.STATUS_CREATED,
            amount=amount,
            amount_kopecks=Payment.rubles_to_kopecks(amount),
            currency="RUB",
            merchant_order_number=payment_id.hex,
            is_test=is_test,
        )


def initiate_yookassa_payment(
    order: Order,
    *,
    client: YooKassaClient | None = None,
) -> InitiateResult:
    """
    Создаёт платёж в ЮKassa (redirect) и возвращает confirmation_url как form_url.
    HTTP — вне DB-транзакции. Повторный вызов переиспользует активный платёж.
    """
    if client is None and not bool(getattr(settings, "YOOKASSA_ENABLED", False)):
        raise PaymentError(
            "Онлайн-оплата временно недоступна.",
            code="payments_disabled",
        )

    logger.info(
        "payment_creation_started order_id=%s provider=yookassa",
        order.pk,
    )
    payment = _create_yookassa_payment_row(order)
    if (
        payment.status in (Payment.STATUS_REGISTERED, Payment.STATUS_PENDING)
        and payment.form_url
        and payment.yookassa_payment_id
    ):
        # Перед reuse — сверка с ЮKassa (не создаём второй платёж вслепую).
        try:
            synced = sync_payment_from_yookassa(payment, client=client)
        except PaymentError as exc:
            if exc.code in (
                "yookassa_status_failed",
                "yookassa_unreachable",
                "yookassa_no_id",
            ):
                raise PaymentError(
                    "Не удалось проверить статус текущего платежа. Попробуйте позже.",
                    code="payment_status_unknown",
                ) from exc
            raise

        if synced.status == Payment.STATUS_PAID:
            raise PaymentError("Заказ уже оплачен", code="already_paid")
        if synced.status in (
            Payment.STATUS_NEEDS_REVIEW,
            Payment.STATUS_REVERSED,
            Payment.STATUS_REFUNDED,
        ):
            raise PaymentError(
                "Оплата этого заказа недоступна",
                code="payment_blocked",
            )
        if synced.status in (Payment.STATUS_FAILED, Payment.STATUS_EXPIRED):
            # Предыдущий платёж закрыт — не отдаём старый form_url; создаём новый ниже.
            if synced.form_url:
                Payment.objects.filter(pk=synced.pk).update(form_url="")
            payment = _create_yookassa_payment_row(order)
        elif synced.form_url and synced.yookassa_payment_id:
            logger.info(
                "payment_created order_id=%s payment_id=%s reused=1",
                order.pk,
                synced.pk,
            )
            return InitiateResult(
                payment=synced, form_url=synced.form_url, reused=True
            )

    order_ref = Order.objects.get(pk=order.pk)
    return_url = _return_url(order_ref)

    try:
        api = client or YooKassaClient()
    except YooKassaError as exc:
        logger.warning(
            "payment_creation_failed order_id=%s payment_id=%s code=%s",
            order.pk,
            payment.pk,
            exc.code,
        )
        raise PaymentError(
            exc.message if exc.code == "yookassa_misconfigured" else "Онлайн-оплата не настроена.",
            code=exc.code if exc.code.startswith("yookassa_") else "yookassa_misconfigured",
        ) from exc

    try:
        result = api.create_payment(
            amount=payment.amount,
            return_url=return_url,
            description=f"Заказ {order_ref.order_number}",
            metadata={
                "order_id": str(order_ref.id),
                "order_number": str(order_ref.order_number),
                "payment_id": str(payment.id),
            },
            idempotence_key=str(payment.id),
            currency="RUB",
            capture=True,
        )
    except YooKassaError as exc:
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(pk=payment.pk)
            p.status = Payment.STATUS_FAILED
            p.form_url = ""
            p.error_code = str(exc.code or "")[:32]
            p.error_message = str(exc.message)[:512]
            p.register_response = _sanitize(exc.payload)
            p.save(
                update_fields=[
                    "status",
                    "form_url",
                    "error_code",
                    "error_message",
                    "register_response",
                    "updated_at",
                ]
            )
        logger.warning(
            "payment_creation_failed order_id=%s payment_id=%s code=%s",
            order_ref.pk,
            payment.pk,
            exc.code,
        )
        raise PaymentError(
            "Не удалось создать платёж. Попробуйте позже.",
            code="yookassa_create_failed",
        ) from exc

    yk_id = str(result.get("id") or "").strip()
    confirmation = result.get("confirmation") or {}
    confirmation_url = str(confirmation.get("confirmation_url") or "").strip()
    if not yk_id or not confirmation_url:
        with transaction.atomic():
            p = Payment.objects.select_for_update().get(pk=payment.pk)
            p.status = Payment.STATUS_FAILED
            p.error_message = "ЮKassa не вернула confirmation_url"
            p.register_response = _sanitize(result)
            p.save(
                update_fields=[
                    "status",
                    "error_message",
                    "register_response",
                    "updated_at",
                ]
            )
        raise PaymentError(
            "Не удалось создать платёж. Попробуйте позже.",
            code="yookassa_create_failed",
        )

    with transaction.atomic():
        p = Payment.objects.select_for_update().get(pk=payment.pk)
        if p.status == Payment.STATUS_PAID:
            return InitiateResult(
                payment=p, form_url=p.form_url or confirmation_url, reused=True
            )
        p.yookassa_payment_id = yk_id
        p.form_url = confirmation_url
        p.status = Payment.STATUS_REGISTERED
        p.register_response = _sanitize(result)
        p.error_code = ""
        p.error_message = ""
        p.is_test = bool(result.get("test")) or p.is_test
        p.save(
            update_fields=[
                "yookassa_payment_id",
                "form_url",
                "status",
                "register_response",
                "error_code",
                "error_message",
                "is_test",
                "updated_at",
            ]
        )
        logger.info(
            "payment_created order_id=%s payment_id=%s yk_id=%s reused=0",
            order_ref.pk,
            p.pk,
            yk_id,
        )
        return InitiateResult(payment=p, form_url=p.form_url, reused=False)


def _amount_matches(local: Decimal, remote_value: str | None) -> bool:
    if remote_value is None:
        return False
    try:
        return Decimal(str(local)).quantize(Decimal("0.01")) == Decimal(
            str(remote_value)
        ).quantize(Decimal("0.01"))
    except Exception:
        return False


def _reject_untrusted_yk_paid(
    locked: Payment,
    data: dict[str, Any],
) -> str | None:
    """
    INT-005: обязательные metadata.order_id и metadata.payment_id + сумма/валюта/id.
    Пустые metadata отклоняют succeeded (не только при несовпадении).
    """
    amount = data.get("amount") or {}
    remote_value = amount.get("value") if isinstance(amount, dict) else None
    remote_currency = amount.get("currency") if isinstance(amount, dict) else None

    if not _amount_matches(locked.amount, remote_value):
        return "Сумма в ЮKassa не совпадает с заказом"
    if not remote_currency or str(remote_currency).upper() != "RUB":
        return "Валюта ЮKassa не совпадает с платежом"
    if locked.currency and str(locked.currency).upper() not in ("RUB", "643"):
        return "Локальная валюта платежа некорректна"

    meta = data.get("metadata")
    if not isinstance(meta, dict) or not meta:
        return "Метаданные платежа отсутствуют"
    meta_order = str(meta.get("order_id") or "").strip()
    meta_payment = str(meta.get("payment_id") or "").strip()
    if not meta_order:
        return "metadata.order_id обязателен"
    if not meta_payment:
        return "metadata.payment_id обязателен"
    if meta_order != str(locked.order_id):
        return "metadata.order_id не принадлежит этому платежу"
    if meta_payment != str(locked.id):
        return "metadata.payment_id не принадлежит этому платежу"

    remote_id = str(data.get("id") or "").strip()
    if not remote_id:
        return "payment_id ЮKassa отсутствует"
    if locked.yookassa_payment_id and remote_id != locked.yookassa_payment_id:
        return "payment_id ЮKassa не совпадает"

    return None


def sync_payment_from_yookassa(
    payment: Payment,
    *,
    client: YooKassaClient | None = None,
    from_webhook: bool = False,
) -> Payment:
    with transaction.atomic():
        locked = (
            Payment.objects.select_for_update()
            .only(
                "id",
                "status",
                "yookassa_payment_id",
                "merchant_order_number",
                "amount",
                "currency",
                "order_id",
            )
            .get(pk=payment.pk)
        )
        if locked.status == Payment.STATUS_PAID:
            return Payment.objects.select_related("order").get(pk=locked.pk)
        if locked.status in (Payment.STATUS_REVERSED, Payment.STATUS_REFUNDED):
            return Payment.objects.select_related("order").get(pk=locked.pk)
        yk_id = locked.yookassa_payment_id
        payment_pk = locked.pk

    if not yk_id:
        raise PaymentError("Платёж ЮKassa ещё не создан", code="yookassa_no_id")

    try:
        api = client or YooKassaClient()
        data = api.get_payment(yk_id)
    except YooKassaError as exc:
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=payment_pk)
            locked.error_message = str(exc.message)[:512]
            locked.last_status_checked_at = timezone.now()
            if from_webhook:
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
            code="yookassa_status_failed",
        ) from exc

    remote_status = str(data.get("status") or "").strip().lower()

    with transaction.atomic():
        locked = (
            Payment.objects.select_for_update()
            .select_related("order")
            .get(pk=payment_pk)
        )
        if locked.status == Payment.STATUS_PAID:
            return locked
        if locked.status in (Payment.STATUS_REVERSED, Payment.STATUS_REFUNDED):
            return locked

        locked.last_status_response = _sanitize(data)
        locked.last_status_checked_at = timezone.now()
        if from_webhook:
            locked.callback_received_at = timezone.now()
        if "test" in data:
            locked.is_test = bool(data.get("test"))

        order = Order.objects.select_for_update().get(pk=locked.order_id)

        if remote_status == "succeeded":
            binding_error = _reject_untrusted_yk_paid(locked, data)
            if binding_error:
                logger.warning(
                    "YooKassa paid rejected payment=%s reason=%s",
                    locked.pk,
                    binding_error,
                )
                # INT-005: remote succeeded, но привязка недостоверна → needs_review,
                # не PAID и не «тихо failed» (деньги у провайдера могли списаться).
                locked.error_message = binding_error
                locked.status = Payment.STATUS_NEEDS_REVIEW
                locked.save()
                return locked

            if order.status == Order.STATUS_CANCELLED:
                locked.status = Payment.STATUS_NEEDS_REVIEW
                locked.error_message = "Оплата после отмены — обработка политики…"
                locked.save()
                pid = locked.pk

                def _run_late():
                    # Политика late-payment для ЮKassa: manual/revive без Sber reverse.
                    apply_late_payment_policy(pid, client=None)

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
            locked.error_code = ""
            locked.error_message = ""
            try:
                with transaction.atomic():
                    locked.save()
            except IntegrityError:
                Payment.objects.filter(pk=locked.pk).update(
                    status=Payment.STATUS_FAILED,
                    error_message="Дубликат оплаты отклонён (constraint)",
                    paid_at=None,
                )
                return Payment.objects.select_related("order").get(pk=locked.pk)

            if order.status == Order.STATUS_NEW:
                from apps.orders.services.transitions import transition_order_status

                order = transition_order_status(
                    order,
                    Order.STATUS_CONFIRMED,
                    reason="yookassa_paid",
                )

            logger.info(
                "payment_succeeded order_id=%s payment_id=%s remote_status=succeeded",
                order.pk,
                locked.pk,
            )

            order_pk = order.pk

            def _after_paid():
                from apps.cart.checkout_clear import clear_cart_after_successful_payment
                from apps.orders.models import Order as OrderModel
                from apps.orders.tasks import enqueue_order_sync

                try:
                    clear_cart_after_successful_payment(OrderModel.objects.get(pk=order_pk))
                except Exception:
                    logger.exception(
                        "cart_clear_failed order_id=%s after yookassa paid",
                        order_pk,
                    )
                enqueue_order_sync(order_pk, paid=True)

            transaction.on_commit(_after_paid)
            return locked

        if remote_status == "canceled":
            locked.status = Payment.STATUS_FAILED
            # Не отдаём старый confirmation_url при repay (старый URL на стороне ЮKassa
            # может ещё жить до expiry — новый initiate создаёт новый Payment).
            locked.form_url = ""
            cancellation = data.get("cancellation_details") or {}
            reason = str(cancellation.get("reason") or "Платёж отменён")
            party = str(cancellation.get("party") or "")
            locked.error_code = reason[:32]
            locked.error_message = (
                f"{reason}" + (f" (party={party})" if party else "")
            )[:512]
            locked.save()
            logger.info(
                "payment_canceled order_id=%s payment_id=%s reason=%s party=%s",
                locked.order_id,
                locked.pk,
                reason[:64],
                party[:32],
            )
            return locked

        if remote_status in ("pending", "waiting_for_capture"):
            locked.status = Payment.STATUS_PENDING
            locked.save()
            logger.info(
                "payment_status_checked order_id=%s payment_id=%s status=%s",
                locked.order_id,
                locked.pk,
                remote_status,
            )
            return locked

        # неизвестный статус — не повышаем до paid
        locked.status = Payment.STATUS_PENDING
        locked.error_message = f"Статус ЮKassa: {remote_status}"[:512]
        locked.save()
        return locked


# События, для которых имеет смысл инициировать re-fetch (SEC-007 / INT-004).
YOOKASSA_WEBHOOK_EVENTS = frozenset(
    {
        "payment.succeeded",
        "payment.waiting_for_capture",
        "payment.canceled",
        "refund.succeeded",
    }
)


def _reject_untrusted_yk_refund(
    locked: Payment,
    data: dict[str, Any],
) -> str | None:
    """
    INT-004: возврат принимается только после GET /refunds/{id}.
    Полный refund → refunded; частичный/чужой → без смены в refunded.
    Статус заказа здесь не меняем (нет утверждённого refund flow).
    """
    remote_status = str(data.get("status") or "").strip().lower()
    if remote_status != "succeeded":
        return f"Статус возврата ЮKassa не succeeded: {remote_status or 'empty'}"

    remote_payment_id = str(data.get("payment_id") or "").strip()
    if not remote_payment_id:
        return "refund.payment_id отсутствует"
    if not locked.yookassa_payment_id:
        return "Локальный платёж без yookassa_payment_id"
    if remote_payment_id != locked.yookassa_payment_id:
        return "refund.payment_id не принадлежит этому платежу"

    amount = data.get("amount") or {}
    remote_value = amount.get("value") if isinstance(amount, dict) else None
    remote_currency = amount.get("currency") if isinstance(amount, dict) else None
    if not remote_currency or str(remote_currency).upper() != "RUB":
        return "Валюта возврата ЮKassa некорректна"
    if locked.currency and str(locked.currency).upper() not in ("RUB", "643"):
        return "Локальная валюта платежа некорректна"
    if not _amount_matches(locked.amount, remote_value):
        parsed = _parse_money(remote_value)
        if parsed is None:
            return "Сумма возврата не разобрана"
        if parsed <= 0:
            return "Сумма возврата должна быть больше нуля"
        # Частичная сумма не отклоняется здесь: её сверяют с остатком платежа.
        return None

    refund_id = str(data.get("id") or "").strip()
    if not refund_id:
        return "refund_id отсутствует"
    return None


def _parse_money(raw: Any) -> Decimal | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return Decimal(str(raw)).quantize(Decimal("0.01"))
    except (ArithmeticError, ValueError):
        return None


def _refunded_so_far(payment: Payment) -> Decimal:
    from django.db.models import Sum

    from .models import PaymentRefund

    agg = PaymentRefund.objects.filter(payment=payment).aggregate(total=Sum("amount"))
    return Decimal(str(agg["total"] or 0)).quantize(Decimal("0.01"))


def _release_reservation_after_full_refund(order: Order) -> None:
    """
    Полный возврат денег по заказу, который ещё не ушёл покупателю:
    отмена и одно снятие резерва. Quantity склада не увеличивается.
    Уже выданный заказ (in_progress / completed) не трогаем.
    """
    if order.status not in (Order.STATUS_NEW, Order.STATUS_CONFIRMED):
        logger.info(
            "payment_refund_stock_unchanged order_id=%s order_status=%s",
            order.pk,
            order.status,
        )
        return
    from apps.orders.services import cancel_order_and_release_stock

    cancel_order_and_release_stock(
        order,
        reason="yookassa_full_refund",
        allow_paid=False,
    )


def sync_refund_from_yookassa(
    refund_id: str,
    *,
    client: YooKassaClient | None = None,
    from_webhook: bool = False,
) -> Payment | None:
    """
    Подтверждает возврат через GET /refunds/{id}.
    Полная сумма → платёж refunded. Если заказ ещё new/confirmed, он отменяется
    и резерв снимается один раз. Quantity склада не растёт.
    Частичная сумма копится в refunded_amount, исходная amount не меняется,
    заказ и резерв не трогаются. Повтор того же refund_id ничего не добавляет.
    """
    from .models import PaymentRefund

    rid = str(refund_id or "").strip()
    if not rid or len(rid) > 128:
        logger.warning("YooKassa refund sync: invalid refund_id")
        return None

    prior = (
        PaymentRefund.objects.filter(provider_refund_id=rid)
        .select_related("payment")
        .first()
    )
    if prior is not None:
        return prior.payment

    existing = (
        Payment.objects.filter(
            provider=Payment.PROVIDER_YOOKASSA,
            yookassa_refund_id=rid,
            status=Payment.STATUS_REFUNDED,
        )
        .select_related("order")
        .first()
    )
    if existing is not None:
        return existing

    try:
        api = client or YooKassaClient()
        data = api.get_refund(rid)
    except YooKassaError as exc:
        logger.warning(
            "YooKassa refund GET failed refund_id=%s code=%s",
            rid,
            getattr(exc, "code", ""),
        )
        raise PaymentError(
            "Не удалось проверить статус возврата",
            code="yookassa_refund_status_failed",
        ) from exc

    remote_payment_id = str(data.get("payment_id") or "").strip()
    if not remote_payment_id:
        logger.warning("YooKassa refund sync: missing payment_id refund_id=%s", rid)
        return None

    with transaction.atomic():
        locked = (
            Payment.objects.select_for_update()
            .select_related("order")
            .filter(
                provider=Payment.PROVIDER_YOOKASSA,
                yookassa_payment_id=remote_payment_id,
            )
            .first()
        )
        if locked is None:
            logger.warning(
                "YooKassa refund sync: payment not found yk_payment=%s refund=%s",
                remote_payment_id,
                rid,
            )
            return None

        if from_webhook:
            locked.callback_received_at = (
                locked.callback_received_at or timezone.now()
            )
        locked.last_status_checked_at = timezone.now()
        locked.last_status_response = _sanitize(
            {"refund": data, "event": "refund.sync"}
        )

        if PaymentRefund.objects.filter(provider_refund_id=rid).exists():
            return locked

        if locked.status == Payment.STATUS_REFUNDED and locked.yookassa_refund_id == rid:
            locked.save(
                update_fields=[
                    "callback_received_at",
                    "last_status_checked_at",
                    "last_status_response",
                    "updated_at",
                ]
            )
            return locked

        if locked.status == Payment.STATUS_REFUNDED:
            locked.error_message = "Возврат сверх уже полностью возвращённого платежа"[:512]
            locked.save(
                update_fields=[
                    "error_message",
                    "callback_received_at",
                    "last_status_checked_at",
                    "last_status_response",
                    "updated_at",
                ]
            )
            return locked

        binding_error = _reject_untrusted_yk_refund(locked, data)
        if binding_error:
            logger.warning(
                "YooKassa refund rejected payment=%s reason=%s",
                locked.pk,
                binding_error,
            )
            # Частичный / чужой — needs_review только если был paid; иначе оставить как есть
            if locked.status == Payment.STATUS_PAID:
                locked.status = Payment.STATUS_NEEDS_REVIEW
            locked.error_message = binding_error[:512]
            locked.save()
            return locked

        if locked.status not in (
            Payment.STATUS_PAID,
            Payment.STATUS_NEEDS_REVIEW,
        ):
            locked.error_message = (
                f"Refund при статусе платежа {locked.status}"[:512]
            )
            locked.status = Payment.STATUS_NEEDS_REVIEW
            locked.save()
            return locked

        amount_node = data.get("amount") or {}
        remote_value = amount_node.get("value") if isinstance(amount_node, dict) else None
        refunded_now = _parse_money(remote_value)
        if refunded_now is None or refunded_now <= 0:
            locked.error_message = "Сумма возврата не разобрана"[:512]
            if locked.status == Payment.STATUS_PAID:
                locked.status = Payment.STATUS_NEEDS_REVIEW
            locked.save()
            return locked

        already = _refunded_so_far(locked)
        cap = Decimal(str(locked.amount)).quantize(Decimal("0.01"))
        if already + refunded_now > cap:
            locked.error_message = "Сумма возвратов превысит оплаченную"[:512]
            if locked.status == Payment.STATUS_PAID:
                locked.status = Payment.STATUS_NEEDS_REVIEW
            locked.save()
            return locked

        try:
            with transaction.atomic():
                PaymentRefund.objects.create(
                    payment=locked,
                    provider_refund_id=rid,
                    amount=refunded_now,
                    currency="RUB",
                )
        except IntegrityError:
            return Payment.objects.select_related("order").get(pk=locked.pk)

        total = (already + refunded_now).quantize(Decimal("0.01"))
        locked.refunded_amount = total
        locked.yookassa_refund_id = rid
        locked.refunded_at = timezone.now()
        locked.error_code = ""
        locked.error_message = ""
        full = total == cap
        if full:
            locked.status = Payment.STATUS_REFUNDED
        elif locked.status == Payment.STATUS_NEEDS_REVIEW:
            locked.status = Payment.STATUS_PAID
        locked.save()
        logger.info(
            "payment_refund_applied order_id=%s payment_id=%s refund_id=%s full=%s",
            locked.order_id,
            locked.pk,
            rid,
            int(full),
        )
        if full:
            order = Order.objects.select_for_update().get(pk=locked.order_id)
            _release_reservation_after_full_refund(order)
        return locked


def handle_yookassa_webhook(
    payload: dict[str, Any],
    *,
    client: YooKassaClient | None = None,
) -> Payment | None:
    """
    Разбирает уведомление, затем перезапрашивает платёж/возврат через API.
    Сам webhook НЕ является доказательством оплаты или возврата.
    """
    if not isinstance(payload, dict):
        return None

    event = str(payload.get("event") or "").strip()
    if event and event not in YOOKASSA_WEBHOOK_EVENTS:
        logger.info("YooKassa webhook: ignored event=%s", event)
        return None

    obj = payload.get("object")
    if not isinstance(obj, dict):
        logger.warning("YooKassa webhook: missing object event=%s", event)
        return None

    yk_id = str(obj.get("id") or "").strip()
    if not yk_id or len(yk_id) > 128:
        logger.warning("YooKassa webhook: missing/invalid object id event=%s", event)
        return None

    # INT-004: refund object.id — это refund_id, не payment_id
    if event == "refund.succeeded":
        try:
            return sync_refund_from_yookassa(
                yk_id, client=client, from_webhook=True
            )
        except PaymentError:
            logger.warning("YooKassa refund webhook sync failed refund_id=%s", yk_id)
            return None
        except Exception:
            logger.warning(
                "YooKassa refund webhook unexpected error refund_id=%s",
                yk_id,
                exc_info=True,
            )
            return None

    payment = Payment.objects.filter(
        provider=Payment.PROVIDER_YOOKASSA,
        yookassa_payment_id=yk_id,
    ).first()

    if payment is None:
        # Fallback по metadata (если webhook пришёл раньше сохранения id — редко)
        meta = obj.get("metadata") or {}
        if isinstance(meta, dict):
            local_pid = str(meta.get("payment_id") or "").strip()
            if local_pid:
                payment = Payment.objects.filter(
                    provider=Payment.PROVIDER_YOOKASSA, pk=local_pid
                ).first()

    if payment is None:
        logger.warning("YooKassa webhook: payment not found yk_id=%s event=%s", yk_id, event)
        return None

    # Debounce повторных webhook → API ЮKassa (SEC-007), не блокируя первую сверку.
    from django.conf import settings as dj_settings
    from django.core.cache import cache

    debounce = int(
        getattr(dj_settings, "YOOKASSA_WEBHOOK_SYNC_DEBOUNCE_SECONDS", 2) or 0
    )
    if debounce > 0:
        cache_key = f"yk_webhook_sync:{payment.pk}"
        if cache.get(cache_key):
            # Недавно синкали — вернуть текущее состояние без внешнего запроса
            if payment.status in (
                Payment.STATUS_PAID,
                Payment.STATUS_REFUNDED,
                Payment.STATUS_REVERSED,
                Payment.STATUS_FAILED,
                Payment.STATUS_EXPIRED,
                Payment.STATUS_NEEDS_REVIEW,
            ):
                return payment
        cache.set(cache_key, "1", timeout=debounce)

    try:
        return sync_payment_from_yookassa(
            payment, client=client, from_webhook=True
        )
    except PaymentError:
        logger.warning("YooKassa webhook sync failed payment=%s", payment.pk)
        return payment
    except Exception:
        # Временная недоступность API / неожиданный сбой — без PAID
        logger.warning(
            "YooKassa webhook sync unexpected error payment=%s",
            payment.pk,
            exc_info=True,
        )
        return payment
