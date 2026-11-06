"""
Отправка заказов в 1С (POST SiteOrders/orders и /cancel).

Схема: paid=false при создании → paid=true после подтверждённой оплаты Сбера.
Гостевые заказы: регистрация ClientId; при неопределённом результате — без автоповтора.
HTTP к 1С выполняется вне длительных DB-транзакций.
"""

from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .client import OneCClient, OneCClientError
from .registration import OneCRegistrationError, register_user_in_onec
from .url_utils import OneCBaseUrlError, normalize_onec_base_url

logger = logging.getLogger(__name__)

# Для SiteOrders повтор с тем же orderId безопасен (идемпотентность 1С).
_ORDER_RETRYABLE_STATUS = {500, 502, 503, 504}
# Таймаут/обрыв: операция могла выполниться — повтор orderId допустим; регистрация — нет.
_FATAL_STATUS = {400, 401, 403, 404, 409, 422}


class OneCOrderSyncError(Exception):
    """Ошибка синхронизации заказа с 1С (для задач / логов)."""

    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class OneCOrderSyncBlocked(OneCOrderSyncError):
    """Блокер конфигурации или данных (склад, ClientId, коды товаров)."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False)


def order_sync_enabled() -> bool:
    return bool(
        getattr(settings, "ONE_C_ORDER_SYNC_ENABLED", False)
        and getattr(settings, "ONE_C_API_ENABLED", False)
    )


def assert_onec_base_url_configured() -> str:
    """Проверка URL без сети. Бросает OneCOrderSyncBlocked при ошибке."""
    try:
        return normalize_onec_base_url(
            getattr(settings, "ONE_C_API_BASE_URL", None)
            or ""
        )
    except OneCBaseUrlError as exc:
        raise OneCOrderSyncBlocked(str(exc)) from exc


def split_full_name(full_name: str) -> tuple[str, str, str]:
    """ФИО → (lastName, firstName, middleName)."""
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], parts[0], ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], " ".join(parts[2:])


def resolve_warehouse_id(order) -> str:
    """
    warehouseId = Store.onec_warehouse_id выбранного магазина заказа
    (самовывоз и доставка). Без общего ONE_C_DEFAULT_WAREHOUSE_ID.
    """
    store = order.store
    if store is None:
        raise OneCOrderSyncBlocked(
            "Для синхронизации с 1С нужен выбранный магазин заказа"
        )
    wid = (store.onec_warehouse_id or "").strip()
    if not wid:
        raise OneCOrderSyncBlocked(
            f"У магазина {store.slug!r} не задан onec_warehouse_id"
        )
    return wid


def ensure_onec_client_id(order, *, client: OneCClient | None = None) -> str:
    """
    ClientId из заказа, пользователя или гостевой регистрации в 1С.
    Неопределённый результат гостя → pending_review, без автоповтора.
    """
    from apps.orders.models import Order

    existing = (order.onec_client_id or "").strip()
    if existing:
        return existing

    if order.onec_sync_status == Order.ONEC_SYNC_PENDING_REVIEW and not existing:
        raise OneCOrderSyncBlocked(
            "Регистрация гостя в 1С требует сверки (неопределённый результат). "
            "Автоповтор запрещён."
        )

    if order.user_id:
        user = order.user
        partner = (getattr(user, "onec_partner_id", None) or "").strip()
        if partner:
            return partner
        result = register_user_in_onec(user, client=client)
        if not result.partner_id:
            raise OneCOrderSyncBlocked(
                result.message or "Нет ClientId у пользователя (сверка с 1С)"
            )
        return result.partner_id

    last_name, first_name, middle_name = split_full_name(order.full_name)
    if not last_name or not first_name:
        raise OneCOrderSyncBlocked("Для гостевого заказа нужны фамилия и имя")
    phone = (order.phone or "").strip()
    if not phone:
        raise OneCOrderSyncBlocked("Для гостевого заказа нужен телефон")

    api = client or OneCClient()
    try:
        data = api.register_partner(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            phone=phone,
        )
    except OneCClientError as exc:
        # Таймаут, обрыв, 500 — 1С могла создать контрагента; автоповтор запрещён
        indeterminate = exc.status_code is None or exc.status_code >= 500
        if indeterminate:
            raise OneCOrderSyncError(
                f"Неопределённый результат регистрации гостя: {exc}",
                retryable=False,
                status_code=exc.status_code,
            ) from exc
        if exc.status_code in _FATAL_STATUS:
            raise OneCOrderSyncBlocked(f"Регистрация гостя отклонена: {exc}") from exc
        raise OneCOrderSyncError(
            str(exc),
            retryable=False,
            status_code=exc.status_code,
        ) from exc
    except OneCRegistrationError as exc:
        raise OneCOrderSyncBlocked(exc.public_message) from exc

    client_id = str(data.get("ClientId") or data.get("partnerId") or "").strip()
    if not client_id:
        raise OneCOrderSyncBlocked("1С не вернула ClientId при регистрации гостя")
    return client_id


def _amount_number(value: Decimal | float | int | str) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01")))


def build_order_items_payload(order) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in order.items.all():
        code = (item.onec_product_code or "").strip()
        if not code and item.product_id:
            code = (getattr(item.product, "onec_code", None) or "").strip()
        if not code:
            raise OneCOrderSyncBlocked(
                f"У позиции «{item.product_title}» нет кода номенклатуры 1С"
            )
        series_raw = (item.onec_series_id or "").strip()
        items.append(
            {
                "productCode": code,
                "quantity": int(item.quantity),
                "amount": _amount_number(item.item_total),
                "seriesId": series_raw if series_raw else None,
            }
        )
    if not items:
        raise OneCOrderSyncBlocked("В заказе нет позиций для 1С")
    return items


def build_order_payload(order, *, paid: bool, client_id: str, warehouse_id: str) -> dict[str, Any]:
    created = order.created_at
    if timezone.is_naive(created):
        created = timezone.make_aware(created, timezone.get_current_timezone())
    return {
        "orderId": str(order.pk),
        "orderNumber": order.order_number,
        "orderDate": created.isoformat(),
        "warehouseId": warehouse_id,
        "ClientId": client_id,
        "paid": bool(paid),
        "items": build_order_items_payload(order),
    }


def payload_for_paid_transition(order, *, paid: bool) -> dict[str, Any]:
    snap = dict(order.onec_payload_snapshot or {})
    if not snap:
        raise OneCOrderSyncBlocked("Нет снимка payload для перехода paid")
    required = ("orderId", "orderNumber", "orderDate", "warehouseId", "ClientId", "items")
    missing = [k for k in required if k not in snap]
    if missing:
        raise OneCOrderSyncBlocked(f"Повреждён снимок payload, нет полей: {missing}")
    return {
        "orderId": snap["orderId"],
        "orderNumber": snap["orderNumber"],
        "orderDate": snap["orderDate"],
        "warehouseId": snap["warehouseId"],
        "ClientId": snap["ClientId"],
        "paid": bool(paid),
        "items": snap["items"],
    }


def _snapshot_without_paid(payload: dict[str, Any]) -> dict[str, Any]:
    snap = dict(payload)
    snap.pop("paid", None)
    return snap


def _save_order_fields(order, **fields) -> None:
    fields["updated_at"] = timezone.now()
    for key, value in fields.items():
        setattr(order, key, value)
    order.save(update_fields=[*fields.keys()])


def plan_and_reserve_at_store(
    *,
    product,
    quantity: int,
    price: Decimal,
    store_id,
) -> list[dict[str, Any]]:
    """
    Планирует строки заказа и атомарно резервирует остаток ТОЛЬКО в store_id.
    Серийные единицы — отдельные строки quantity=1 с конкретным seriesId.
    Не ищет товар в других магазинах.
    """
    from apps.stores import stock_ops
    from apps.stores.models import Stock

    if quantity <= 0:
        return []

    code = (getattr(product, "onec_code", None) or "").strip()
    rows = list(
        Stock.objects.select_for_update()
        .filter(product_id=product.pk, store_id=store_id)
        .order_by("onec_series_id", "pk")
    )
    serial_rows = [r for r in rows if (r.onec_series_id or "").strip()]

    if serial_rows:
        picked: list[str] = []
        for row in serial_rows:
            if len(picked) >= quantity:
                break
            available = int(row.quantity) - int(row.reserved_quantity)
            take = min(max(0, available), quantity - len(picked))
            for _ in range(take):
                picked.append(row.onec_series_id)
        if len(picked) < quantity:
            raise InsufficientStockAtStore()
        lines = []
        for sid in picked:
            if not stock_ops.reserve_at_store(
                product.pk,
                store_id,
                1,
                series_id=sid,
                reason="checkout_reserve",
                source="plan_and_reserve_at_store",
            ):
                raise InsufficientStockAtStore()
            lines.append(
                {
                    "quantity": 1,
                    "price": price,
                    "item_total": price,
                    "onec_product_code": code,
                    "onec_series_id": sid,
                }
            )
        return lines

    if not stock_ops.reserve_at_store(
        product.pk,
        store_id,
        quantity,
        reason="checkout_reserve",
        source="plan_and_reserve_at_store",
    ):
        raise InsufficientStockAtStore()
    return [
        {
            "quantity": quantity,
            "price": price,
            "item_total": price * quantity,
            "onec_product_code": code,
            "onec_series_id": "",
        }
    ]


class InsufficientStockAtStore(Exception):
    """Недостаточно остатка в выбранном магазине."""


def release_order_item_reservations(order) -> None:
    """Снимает резерв по позициям в магазине заказа (без подмены склада). INT-009 ledger."""
    from apps.stores import stock_ops

    store_id = order.store_id
    if not store_id:
        return
    for item in order.items.all():
        if not item.product_id:
            continue
        stock_ops.release_at_store(
            item.product_id,
            store_id,
            int(item.quantity),
            series_id=(item.onec_series_id or "").strip(),
            idempotency_key=f"release:order:{order.pk}:item:{item.pk}",
            order_id=order.pk,
            order_item_id=item.pk,
            reason="order_cancel_release",
            source="release_order_item_reservations",
        )


def reserve_order_item_reservations(order) -> bool:
    """Повторный резерв по уже сохранённым позициям (late payment revive). INT-009."""
    from apps.stores import stock_ops

    store_id = order.store_id
    if not store_id:
        return False
    for item in order.items.all():
        if not item.product_id:
            continue
        ok = stock_ops.reserve_at_store(
            item.product_id,
            store_id,
            int(item.quantity),
            series_id=(item.onec_series_id or "").strip(),
            idempotency_key=f"reserve:order:{order.pk}:item:{item.pk}:revive",
            order_id=order.pk,
            order_item_id=item.pk,
            reason="late_payment_revive",
            source="reserve_order_item_reservations",
        )
        if not ok:
            return False
    return True


def allocate_series_for_quantity(
    product_id,
    quantity: int,
    *,
    preferred_store_id=None,
) -> list[str]:
    """
    Подбор seriesId только в указанном магазине (без других точек).
    preferred_store_id обязателен для серийной логики заказа.
    """
    from apps.stores.models import Stock

    if quantity <= 0 or not preferred_store_id:
        return []
    rows = list(
        Stock.objects.filter(
            product_id=product_id,
            store_id=preferred_store_id,
        )
        .exclude(onec_series_id="")
        .order_by("pk")
    )
    picked: list[str] = []
    for row in rows:
        if len(picked) >= quantity:
            break
        available = int(row.quantity) - int(row.reserved_quantity)
        take = min(max(0, available), quantity - len(picked))
        for _ in range(take):
            picked.append(row.onec_series_id)
    return picked


def plan_order_item_lines(
    *,
    product,
    quantity: int,
    price: Decimal,
    preferred_store_id=None,
) -> list[dict[str, Any]]:
    """
    Планирование строк без резерва (для тестов/превью).
    Резерв при оформлении — через plan_and_reserve_at_store.
    """
    code = (getattr(product, "onec_code", None) or "").strip()
    series_ids = allocate_series_for_quantity(
        product.pk, quantity, preferred_store_id=preferred_store_id
    )
    if series_ids and len(series_ids) == quantity:
        return [
            {
                "quantity": 1,
                "price": price,
                "item_total": price,
                "onec_product_code": code,
                "onec_series_id": sid,
            }
            for sid in series_ids
        ]
    return [
        {
            "quantity": quantity,
            "price": price,
            "item_total": price * quantity,
            "onec_product_code": code,
            "onec_series_id": "",
        }
    ]


def _prepare_sync_claim(
    order_id,
    *,
    paid: bool,
    force: bool,
    client: OneCClient | None,
) -> dict[str, Any]:
    """
    Короткая транзакция: проверки, ClientId (если уже есть), claim, snapshot.
    HTTP регистрации гостя — снаружи, через отдельный шаг.
    """
    from apps.orders.models import Order

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .select_related("store", "user")
            .prefetch_related("items__product")
            .get(pk=order_id)
        )

        if order.status == Order.STATUS_CANCELLED and not force:
            return {"skip": True, "result": {
                "ok": False, "skipped": True, "reason": "order_cancelled",
                "order_id": str(order.pk),
            }}

        if paid and order.onec_paid and order.onec_sync_status == Order.ONEC_SYNC_PAID:
            return {"skip": True, "result": {
                "ok": True, "skipped": True, "reason": "already_paid_synced",
                "order_id": str(order.pk), "documentId": order.onec_document_id,
            }}

        if (
            not paid
            and order.onec_sync_status
            in (Order.ONEC_SYNC_SYNCED, Order.ONEC_SYNC_PAID)
            and order.onec_document_id
            and not force
        ):
            return {"skip": True, "result": {
                "ok": True, "skipped": True, "reason": "already_synced",
                "order_id": str(order.pk), "documentId": order.onec_document_id,
            }}

        if order.onec_sync_status == Order.ONEC_SYNC_PENDING_REVIEW and not force:
            return {"skip": True, "result": {
                "ok": False, "skipped": True, "reason": "pending_review",
                "order_id": str(order.pk),
            }}

        if (
            order.onec_sync_status == Order.ONEC_SYNC_PENDING
            and (order.onec_sync_claim or "").strip()
            and not force
        ):
            return {"skip": True, "result": {
                "ok": False, "skipped": True, "reason": "sync_in_flight",
                "order_id": str(order.pk),
            }}

        if not order_sync_enabled() and client is None:
            _save_order_fields(
                order,
                onec_sync_status=Order.ONEC_SYNC_DISABLED,
                onec_last_error="ONE_C_ORDER_SYNC_ENABLED/ONE_C_API_ENABLED выключены",
            )
            return {"skip": True, "result": {
                "ok": False, "skipped": True, "reason": "sync_disabled",
                "order_id": str(order.pk),
            }}

        try:
            assert_onec_base_url_configured()
        except OneCOrderSyncBlocked as exc:
            _save_order_fields(
                order,
                onec_sync_status=Order.ONEC_SYNC_BLOCKED,
                onec_last_error=str(exc)[:512],
            )
            return {"skip": True, "result": {
                "ok": False, "blocked": True, "reason": str(exc),
                "order_id": str(order.pk),
            }}

        has_client = bool((order.onec_client_id or "").strip())
        if not has_client and order.user_id:
            partner = (getattr(order.user, "onec_partner_id", None) or "").strip()
            has_client = bool(partner)

        needs_external_reg = (
            not has_client
            and not order.onec_payload_snapshot
        )
        if needs_external_reg:
            return {
                "skip": False,
                "needs_guest_reg": not bool(order.user_id),
                "needs_user_reg": bool(order.user_id),
                "order_id": str(order.pk),
                "paid": paid,
            }

        try:
            if order.onec_payload_snapshot:
                payload = payload_for_paid_transition(order, paid=paid)
                client_id = str(payload["ClientId"])
                warehouse_id = str(payload["warehouseId"])
            else:
                warehouse_id = resolve_warehouse_id(order)
                # Только уже известный ClientId (HTTP регистрации — снаружи)
                client_id = (order.onec_client_id or "").strip()
                if not client_id and order.user_id:
                    client_id = (
                        getattr(order.user, "onec_partner_id", None) or ""
                    ).strip()
                if not client_id:
                    raise OneCOrderSyncBlocked("Нет ClientId для заказа")
                payload = build_order_payload(
                    order, paid=paid, client_id=client_id, warehouse_id=warehouse_id
                )
        except OneCOrderSyncBlocked as exc:
            _save_order_fields(
                order,
                onec_sync_status=Order.ONEC_SYNC_BLOCKED,
                onec_last_error=str(exc)[:512],
            )
            return {"skip": True, "result": {
                "ok": False, "blocked": True, "reason": str(exc),
                "order_id": str(order.pk),
            }}

        claim = uuid.uuid4().hex
        if not order.onec_payload_snapshot:
            order.onec_payload_snapshot = _snapshot_without_paid(payload)
        _save_order_fields(
            order,
            onec_client_id=client_id,
            onec_warehouse_id=warehouse_id,
            onec_payload_snapshot=order.onec_payload_snapshot,
            onec_sync_attempts=int(order.onec_sync_attempts or 0) + 1,
            onec_sync_status=Order.ONEC_SYNC_PENDING,
            onec_sync_claim=claim,
            onec_last_error="",
        )
        return {
            "skip": False,
            "needs_guest_reg": False,
            "claim": claim,
            "payload": payload,
            "paid": paid,
            "order_id": str(order.pk),
            "order_number": order.order_number,
        }


def _finish_guest_registration(order_id, *, client: OneCClient | None) -> dict[str, Any]:
    """HTTP регистрации гостя вне транзакции + короткая запись результата."""
    from apps.orders.models import Order

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .select_related("user")
            .get(pk=order_id)
        )
        if (order.onec_client_id or "").strip():
            return {"ok": True, "client_id": order.onec_client_id}
        # снимок полей для HTTP
        full_name = order.full_name
        phone = order.phone
        user = order.user

    if user is not None:
        # не должно сюда попадать
        return {"ok": True}

    last_name, first_name, middle_name = split_full_name(full_name)
    api = client or OneCClient()
    try:
        data = api.register_partner(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            phone=(phone or "").strip(),
        )
        client_id = str(data.get("ClientId") or data.get("partnerId") or "").strip()
        if not client_id:
            raise OneCOrderSyncBlocked("1С не вернула ClientId при регистрации гостя")
    except OneCClientError as exc:
        indeterminate = exc.status_code is None or exc.status_code >= 500
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            if indeterminate:
                _save_order_fields(
                    order,
                    onec_sync_status=Order.ONEC_SYNC_PENDING_REVIEW,
                    onec_last_error=f"Неопределённый результат регистрации гостя: {exc}"[:512],
                    onec_sync_claim="",
                )
            else:
                _save_order_fields(
                    order,
                    onec_sync_status=Order.ONEC_SYNC_BLOCKED,
                    onec_last_error=str(exc)[:512],
                    onec_sync_claim="",
                )
        return {
            "ok": False,
            "indeterminate": indeterminate,
            "error": str(exc),
            "retryable": False,
        }
    except OneCOrderSyncBlocked as exc:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            _save_order_fields(
                order,
                onec_sync_status=Order.ONEC_SYNC_BLOCKED,
                onec_last_error=str(exc)[:512],
            )
        return {"ok": False, "blocked": True, "error": str(exc), "retryable": False}

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        _save_order_fields(order, onec_client_id=client_id, onec_last_error="")
    return {"ok": True, "client_id": client_id}


def _apply_sync_result(
    order_id,
    *,
    claim: str,
    paid: bool,
    result: dict[str, Any] | None,
    http_error: OneCClientError | None,
) -> dict[str, Any]:
    from apps.orders.models import Order

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if (order.onec_sync_claim or "") != claim:
            return {
                "ok": False,
                "skipped": True,
                "reason": "stale_claim",
                "order_id": str(order.pk),
            }

        if http_error is not None:
            msg = str(http_error)[:512]
            # Таймаут/сеть: документ мог создаться — статус error, повтор orderId допустим
            retryable = (
                http_error.status_code is None
                or http_error.status_code in _ORDER_RETRYABLE_STATUS
            )
            if http_error.status_code in _FATAL_STATUS:
                retryable = False
            status = (
                Order.ONEC_SYNC_PENDING_REVIEW
                if http_error.status_code is None
                else Order.ONEC_SYNC_ERROR
            )
            _save_order_fields(
                order,
                onec_last_error=msg,
                onec_sync_status=status,
                onec_sync_claim="",
            )
            raise OneCOrderSyncError(
                msg, retryable=retryable, status_code=http_error.status_code
            )

        assert result is not None
        doc_id = str(result.get("documentId") or "").strip()
        doc_number = str(result.get("documentNumber") or "").strip()
        doc_type = str(result.get("documentType") or "").strip()
        posted = bool(result.get("posted", False))

        if not doc_id:
            _save_order_fields(
                order,
                onec_sync_status=Order.ONEC_SYNC_PENDING_REVIEW,
                onec_last_error="Ответ 1С без documentId — требуется сверка",
                onec_sync_claim="",
            )
            return {
                "ok": False,
                "order_id": str(order.pk),
                "reason": "missing_document_id",
            }

        if not paid:
            order.onec_order_document_id = order.onec_order_document_id or doc_id
            order.onec_paid = False
            sync_status = Order.ONEC_SYNC_SYNCED
        else:
            order.onec_paid = True
            sync_status = Order.ONEC_SYNC_PAID

        if paid and not posted:
            sync_status = Order.ONEC_SYNC_ERROR
            last_error = "1С приняла paid=true, но документ не проведён (posted=false)"
        else:
            last_error = ""

        _save_order_fields(
            order,
            onec_order_document_id=order.onec_order_document_id,
            onec_document_id=doc_id,
            onec_document_number=doc_number or order.onec_document_number,
            onec_document_type=doc_type or order.onec_document_type,
            onec_paid=order.onec_paid,
            onec_posted=posted,
            onec_sync_status=sync_status,
            onec_last_error=last_error,
            onec_synced_at=timezone.now(),
            onec_sync_claim="",
        )
        return {
            "ok": sync_status in (Order.ONEC_SYNC_SYNCED, Order.ONEC_SYNC_PAID),
            "order_id": str(order.pk),
            "paid": paid,
            "documentId": doc_id,
            "documentNumber": doc_number,
            "documentType": doc_type,
            "posted": posted,
            "created": bool(result.get("created")),
            "http_status": result.get("http_status"),
        }


def sync_order_to_onec(
    order_id,
    *,
    paid: bool = False,
    client: OneCClient | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Создаёт/обновляет документ заказа в 1С.
    HTTP вне длительного select_for_update.
    """
    prepared = _prepare_sync_claim(
        order_id, paid=paid, force=force, client=client
    )
    if prepared.get("skip"):
        return prepared["result"]

    if prepared.get("needs_guest_reg") or prepared.get("needs_user_reg"):
        if prepared.get("needs_guest_reg"):
            reg = _finish_guest_registration(order_id, client=client)
            if not reg.get("ok"):
                return {
                    "ok": False,
                    "order_id": str(order_id),
                    "reason": "guest_registration_failed",
                    "blocked": bool(reg.get("blocked")),
                    "pending_review": bool(reg.get("indeterminate")),
                    "error": reg.get("error", ""),
                }
        else:
            from apps.orders.models import Order

            with transaction.atomic():
                order = (
                    Order.objects.select_for_update()
                    .select_related("user", "user__profile")
                    .get(pk=order_id)
                )
                user = order.user
            if user is None:
                return {
                    "ok": False,
                    "order_id": str(order_id),
                    "reason": "user_missing",
                }
            try:
                result = register_user_in_onec(user, client=client)
            except OneCRegistrationError as exc:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(pk=order_id)
                    _save_order_fields(
                        order,
                        onec_sync_status=Order.ONEC_SYNC_BLOCKED,
                        onec_last_error=exc.public_message[:512],
                    )
                return {
                    "ok": False,
                    "order_id": str(order_id),
                    "blocked": True,
                    "error": exc.public_message,
                }
            if not result.partner_id:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(pk=order_id)
                    _save_order_fields(
                        order,
                        onec_sync_status=Order.ONEC_SYNC_PENDING_REVIEW,
                        onec_last_error=(result.message or "Сверка ClientId")[:512],
                    )
                return {
                    "ok": False,
                    "order_id": str(order_id),
                    "pending_review": True,
                    "error": result.message,
                }
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order_id)
                _save_order_fields(order, onec_client_id=result.partner_id)

        prepared = _prepare_sync_claim(
            order_id, paid=paid, force=force, client=client
        )
        if prepared.get("skip"):
            return prepared["result"]
        if prepared.get("needs_guest_reg") or prepared.get("needs_user_reg"):
            return {
                "ok": False,
                "order_id": str(order_id),
                "reason": "registration_incomplete",
            }

    claim = prepared["claim"]
    payload = prepared["payload"]
    api = client or OneCClient()
    http_error = None
    result = None
    try:
        result = api.create_or_update_order(payload)
    except OneCClientError as exc:
        http_error = exc
        logger.warning(
            "1C order sync HTTP failed order=%s status=%s",
            prepared.get("order_number"),
            exc.status_code,
        )

    return _apply_sync_result(
        order_id,
        claim=claim,
        paid=bool(prepared["paid"]),
        result=result,
        http_error=http_error,
    )


def cancel_order_in_onec(
    order_id,
    *,
    client: OneCClient | None = None,
) -> dict[str, Any]:
    """POST cancel вне длительной транзакции. Возврат денег не выполняется."""
    from apps.orders.models import Order

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.onec_sync_status == Order.ONEC_SYNC_CANCELLED:
            return {
                "ok": True,
                "skipped": True,
                "reason": "already_cancelled_in_onec",
                "order_id": str(order.pk),
            }
        if not order.onec_document_id and not order.onec_payload_snapshot:
            return {
                "ok": True,
                "skipped": True,
                "reason": "never_synced",
                "order_id": str(order.pk),
            }
        if not order_sync_enabled() and client is None:
            return {
                "ok": False,
                "skipped": True,
                "reason": "sync_disabled",
                "order_id": str(order.pk),
            }
        try:
            assert_onec_base_url_configured()
        except OneCOrderSyncBlocked as exc:
            _save_order_fields(
                order,
                onec_sync_status=Order.ONEC_SYNC_BLOCKED,
                onec_last_error=str(exc)[:512],
            )
            return {
                "ok": False,
                "blocked": True,
                "reason": str(exc),
                "order_id": str(order.pk),
            }

        if (
            order.onec_sync_status == Order.ONEC_SYNC_PENDING
            and (order.onec_sync_claim or "").strip()
        ):
            return {
                "ok": False,
                "skipped": True,
                "reason": "sync_in_flight",
                "order_id": str(order.pk),
            }

        paid = bool(order.onec_paid)
        order_id_1c = str(
            (order.onec_payload_snapshot or {}).get("orderId") or order.pk
        )
        claim = uuid.uuid4().hex
        _save_order_fields(
            order,
            onec_sync_status=Order.ONEC_SYNC_PENDING,
            onec_sync_claim=claim,
        )

    api = client or OneCClient()
    try:
        result = api.cancel_order(order_id=order_id_1c, paid=paid)
        http_error = None
    except OneCClientError as exc:
        result = None
        http_error = exc

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if (order.onec_sync_claim or "") != claim:
            return {
                "ok": False,
                "skipped": True,
                "reason": "stale_claim",
                "order_id": str(order.pk),
            }
        if http_error is not None:
            retryable = (
                http_error.status_code is None
                or http_error.status_code in _ORDER_RETRYABLE_STATUS
            )
            if http_error.status_code in _FATAL_STATUS:
                retryable = False
            _save_order_fields(
                order,
                onec_last_error=str(http_error)[:512],
                onec_sync_status=Order.ONEC_SYNC_ERROR,
                onec_sync_claim="",
            )
            raise OneCOrderSyncError(
                str(http_error),
                retryable=retryable,
                status_code=http_error.status_code,
            )

        assert result is not None
        fields = {
            "onec_sync_status": Order.ONEC_SYNC_CANCELLED,
            "onec_last_error": "",
            "onec_synced_at": timezone.now(),
            "onec_sync_claim": "",
        }
        if result.get("documentId"):
            fields["onec_document_id"] = str(result["documentId"])
        if result.get("documentNumber"):
            fields["onec_document_number"] = str(result["documentNumber"])
        if result.get("documentType"):
            fields["onec_document_type"] = str(result["documentType"])
        _save_order_fields(order, **fields)
        return {
            "ok": True,
            "order_id": str(order.pk),
            "cancelled": bool(result.get("cancelled", True)),
            "alreadyCancelled": bool(result.get("alreadyCancelled", False)),
            "paid": paid,
        }


def push_order_to_onec(order: Any, *, client: Any = None) -> dict[str, Any]:
    return sync_order_to_onec(
        order.pk if hasattr(order, "pk") else order, client=client
    )
