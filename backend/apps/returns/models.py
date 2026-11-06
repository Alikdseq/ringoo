"""Заявки на возврат товара и связанные денежные операции."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ReturnRequest(models.Model):
    # Grounds
    GROUND_QUALITY_OK = "quality_ok"  # надлежащее качество (ст. 26.1)
    GROUND_DEFECT = "defect"  # недостаток (ст. 18–24)
    GROUND_TECH_COMPLEX_DEFECT = "tech_complex_defect"
    GROUND_CANCEL_BEFORE_HANDOVER = "cancel_before_handover"
    GROUND_CHOICES = [
        (GROUND_QUALITY_OK, "Надлежащее качество (дистанционный отказ)"),
        (GROUND_DEFECT, "Недостаток товара"),
        (GROUND_TECH_COMPLEX_DEFECT, "Недостаток технически сложного товара"),
        (GROUND_CANCEL_BEFORE_HANDOVER, "Отказ до передачи"),
    ]

    # Consumer demand
    DEMAND_REFUND = "refund_money"
    DEMAND_REPLACE = "replace"
    DEMAND_REPAIR = "repair"
    DEMAND_PRICE_REDUCE = "price_reduce"
    DEMAND_EXPENSE = "expense_reimburse"
    DEMAND_CHOICES = [
        (DEMAND_REFUND, "Возврат денежных средств"),
        (DEMAND_REPLACE, "Замена"),
        (DEMAND_REPAIR, "Ремонт / устранение недостатков"),
        (DEMAND_PRICE_REDUCE, "Уменьшение цены"),
        (DEMAND_EXPENSE, "Возмещение расходов на устранение"),
    ]

    RETURN_METHOD_PICKUP = "seller_pickup_point"
    RETURN_METHOD_CARRIER = "carrier"
    RETURN_METHOD_POST = "post"
    RETURN_METHOD_COURIER = "courier"
    RETURN_METHOD_CHOICES = [
        (RETURN_METHOD_PICKUP, "Пункт / магазин продавца"),
        (RETURN_METHOD_CARRIER, "Перевозчик"),
        (RETURN_METHOD_POST, "Почта / организация связи"),
        (RETURN_METHOD_COURIER, "Курьер"),
    ]

    STATUS_REQUESTED = "requested"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_AWAITING_SHIPMENT = "awaiting_shipment"
    STATUS_IN_TRANSIT = "in_transit"
    STATUS_RECEIVED = "received"
    STATUS_INSPECTION = "inspection"
    STATUS_REFUND_PENDING = "refund_pending"
    STATUS_REFUND_PROCESSING = "refund_processing"
    STATUS_PARTIALLY_REFUNDED = "partially_refunded"
    STATUS_REFUNDED = "refunded"
    STATUS_RESTOCKED = "restocked"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Заявка создана"),
        (STATUS_UNDER_REVIEW, "На рассмотрении"),
        (STATUS_APPROVED, "Согласовано"),
        (STATUS_REJECTED, "Отказ"),
        (STATUS_AWAITING_SHIPMENT, "Ожидается отправка товара"),
        (STATUS_IN_TRANSIT, "В пути"),
        (STATUS_RECEIVED, "Товар получен"),
        (STATUS_INSPECTION, "Проверка"),
        (STATUS_REFUND_PENDING, "Ожидается возврат денег"),
        (STATUS_REFUND_PROCESSING, "Провайдер обрабатывает возврат"),
        (STATUS_PARTIALLY_REFUNDED, "Частично возвращены деньги"),
        (STATUS_REFUNDED, "Деньги возвращены"),
        (STATUS_RESTOCKED, "Товар принят на склад"),
        (STATUS_COMPLETED, "Завершено"),
        (STATUS_CANCELLED, "Отменено"),
    ]

    ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        STATUS_REQUESTED: {STATUS_UNDER_REVIEW, STATUS_CANCELLED},
        STATUS_UNDER_REVIEW: {
            STATUS_APPROVED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        },
        STATUS_APPROVED: {
            STATUS_AWAITING_SHIPMENT,
            STATUS_REFUND_PENDING,  # cancel before handover / no goods return needed
            STATUS_REFUND_PROCESSING,
            STATUS_CANCELLED,
        },
        STATUS_REFUND_PENDING: {
            STATUS_REFUND_PROCESSING,
            STATUS_CANCELLED,
        },
        STATUS_AWAITING_SHIPMENT: {STATUS_IN_TRANSIT, STATUS_CANCELLED},
        STATUS_IN_TRANSIT: {STATUS_RECEIVED},
        STATUS_RECEIVED: {STATUS_INSPECTION},
        STATUS_INSPECTION: {
            STATUS_REFUND_PENDING,
            STATUS_RESTOCKED,
            STATUS_REJECTED,
        },
        STATUS_REFUND_PROCESSING: {
            STATUS_REFUNDED,
            STATUS_PARTIALLY_REFUNDED,
            STATUS_REFUND_PENDING,  # retry / needs review
        },
        STATUS_PARTIALLY_REFUNDED: {
            STATUS_REFUND_PROCESSING,
            STATUS_REFUNDED,
            STATUS_COMPLETED,
        },
        STATUS_REFUNDED: {STATUS_RESTOCKED, STATUS_COMPLETED},
        STATUS_RESTOCKED: {STATUS_COMPLETED, STATUS_REFUND_PENDING},
        STATUS_REJECTED: set(),
        STATUS_COMPLETED: set(),
        STATUS_CANCELLED: set(),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=32, unique=True, db_index=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="return_requests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_requests",
    )
    ground = models.CharField(max_length=32, choices=GROUND_CHOICES)
    demand = models.CharField(
        max_length=32, choices=DEMAND_CHOICES, default=DEMAND_REFUND
    )
    description = models.TextField(blank=True, default="")
    return_method = models.CharField(
        max_length=32, choices=RETURN_METHOD_CHOICES, blank=True, default=""
    )
    contact_phone = models.CharField(max_length=32, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_REQUESTED, db_index=True
    )
    rejection_reason = models.TextField(blank=True, default="")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_returns",
    )
    requested_refund_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    approved_refund_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    goods_handed_over_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Фактическая дата передачи товара покупателю (если известна)",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "returns_returnrequest"
        ordering = ["-created_at"]
        verbose_name = "Заявка на возврат"
        verbose_name_plural = "Заявки на возврат"

    def __str__(self) -> str:
        return self.number

    def can_transition(self, new_status: str) -> bool:
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())


class ReturnItem(models.Model):
    CONDITION_PENDING = "pending_inspection"
    CONDITION_SELLABLE = "sellable"
    CONDITION_DEFECTIVE = "defective"
    CONDITION_DAMAGED = "damaged"
    CONDITION_QUARANTINE = "quarantine"
    CONDITION_SUPPLIER = "supplier_return"
    CONDITION_CHOICES = [
        (CONDITION_PENDING, "Ожидает проверки"),
        (CONDITION_SELLABLE, "Пригоден к продаже"),
        (CONDITION_DEFECTIVE, "Дефект"),
        (CONDITION_DAMAGED, "Повреждён"),
        (CONDITION_QUARANTINE, "Карантин"),
        (CONDITION_SUPPLIER, "Возврат поставщику"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest, on_delete=models.CASCADE, related_name="items"
    )
    order_item = models.ForeignKey(
        "orders.OrderItem", on_delete=models.PROTECT, related_name="return_items"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Snapshots for history
    product_title = models.CharField(max_length=255, blank=True, default="")
    color_label = models.CharField(max_length=255, blank=True, default="")
    color_id = models.UUIDField(null=True, blank=True)
    onec_series_id = models.CharField(max_length=64, blank=True, default="")
    condition = models.CharField(
        max_length=32, choices=CONDITION_CHOICES, default=CONDITION_PENDING
    )
    restocked_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "returns_returnitem"
        constraints = [
            models.UniqueConstraint(
                fields=["return_request", "order_item"],
                name="returns_item_unique_per_request",
            )
        ]

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("quantity >= 1")
        if self.restocked_quantity > self.quantity:
            raise ValidationError("restocked_quantity > quantity")


class ReturnEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest, on_delete=models.CASCADE, related_name="events"
    )
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32, blank=True, default="")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    message = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "returns_returnevent"
        ordering = ["created_at"]


class MoneyRefund(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_NEEDS_REVIEW = "needs_review"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает"),
        (STATUS_PROCESSING, "В обработке"),
        (STATUS_SUCCEEDED, "Успех"),
        (STATUS_FAILED, "Ошибка"),
        (STATUS_NEEDS_REVIEW, "Сверка"),
    ]

    PROVIDER_YOOKASSA = "yookassa"
    PROVIDER_SBER = "sber"
    PROVIDER_MANUAL = "manual"
    PROVIDER_CHOICES = [
        (PROVIDER_YOOKASSA, "ЮKassa"),
        (PROVIDER_SBER, "Сбер"),
        (PROVIDER_MANUAL, "Ручной"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(
        ReturnRequest, on_delete=models.CASCADE, related_name="money_refunds"
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="money_refunds",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    provider_refund_id = models.CharField(max_length=128, blank=True, default="")
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)
    error_message = models.CharField(max_length=512, blank=True, default="")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "returns_moneyrefund"
        ordering = ["-created_at"]
