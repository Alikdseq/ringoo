"""
Модели заказов: Order, OrderItem (задачи 1.5.1, 1.5.2).
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


def _generate_order_number():
    """Уникальный номер заказа: ORD-YYYYMMDD-6hex."""
    from django.utils import timezone
    import random
    date_part = timezone.now().strftime("%Y%m%d")
    suffix = f"{random.randint(0, 0xFFFFFF):06x}"
    return f"ORD-{date_part}-{suffix}"


class Order(models.Model):
    """Заказ."""

    DELIVERY_PICKUP = "pickup"
    DELIVERY_DELIVERY = "delivery"
    DELIVERY_CHOICES = [
        (DELIVERY_PICKUP, "Самовывоз"),
        (DELIVERY_DELIVERY, "Доставка"),
    ]

    PAYMENT_CASH = "cash"
    PAYMENT_CARD_ON_DELIVERY = "card_on_delivery"
    PAYMENT_BANK_TRANSFER = "bank_transfer"
    PAYMENT_ONLINE = "online"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Наличными"),
        (PAYMENT_CARD_ON_DELIVERY, "Картой при получении"),
        (PAYMENT_BANK_TRANSFER, "Банковский перевод"),
        (PAYMENT_ONLINE, "Онлайн"),
    ]

    # Fulfillment lifecycle (отдельно от payment_status).
    STATUS_NEW = "new"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новый заказ"),
        (STATUS_PROCESSING, "В обработке"),
        (STATUS_READY, "Готов"),
        (STATUS_CLOSED, "Завершён"),
    ]
    # Устаревшие коды (до миграции 0012); оставлены как алиасы для чтения старых тестов/логов.
    STATUS_CONFIRMED = STATUS_PROCESSING
    STATUS_IN_PROGRESS = STATUS_PROCESSING
    STATUS_COMPLETED = STATUS_CLOSED
    STATUS_CANCELLED = "cancelled"  # legacy DB value → мигрируется в closed+cancelled

    CLOSURE_COMPLETED = "completed"
    CLOSURE_CANCELLED = "cancelled"
    CLOSURE_RESULT_CHOICES = [
        (CLOSURE_COMPLETED, "Получен"),
        (CLOSURE_CANCELLED, "Отменён"),
    ]

    PAYMENT_STATUS_UNPAID = "unpaid"
    PAYMENT_STATUS_PAID = "paid"
    PAYMENT_STATUS_REFUNDED = "refunded"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_UNPAID, "Не оплачен"),
        (PAYMENT_STATUS_PAID, "Оплачен"),
        (PAYMENT_STATUS_REFUNDED, "Возвращён"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Пользователь",
    )
    order_number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        verbose_name="Номер заказа",
    )
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(max_length=50, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        verbose_name="Тип доставки",
    )
    delivery_address = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Адрес доставки",
        help_text="city, street, house, apartment, postal_code",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Магазин (самовывоз)",
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        verbose_name="Способ оплаты",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name="Статус выполнения",
        db_index=True,
    )
    closure_result = models.CharField(
        max_length=20,
        choices=CLOSURE_RESULT_CHOICES,
        blank=True,
        null=True,
        verbose_name="Результат закрытия",
        help_text="Заполняется только при status=closed: completed|cancelled",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_UNPAID,
        db_index=True,
        verbose_name="Статус оплаты",
        help_text="Независимо от статуса выполнения. Online: ЮKassa; cash/card: 1С.",
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма заказа",
    )
    delivery_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Стоимость доставки",
    )
    bonus_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Списано бонусов",
    )
    bonus_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Начислено бонусов",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    consent_personal_data = models.BooleanField(
        default=False,
        verbose_name="Согласие на обработку персональных данных",
    )
    confirmation_email_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Письмо подтверждения заказа отправлено",
        help_text="Заполняется после успешной отправки; защита от повторной рассылки при retry Celery.",
    )
    anonymized_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Обезличен (удаление аккаунта)",
    )
    checkout_cart_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Корзина checkout (online)",
        help_text=(
            "Для online: id корзины сохраняется при создании заказа; "
            "позиции корзины удаляются только после подтверждённой оплаты."
        ),
    )
    # SEC-006: гостевой доступ (в БД только хеш; plaintext не хранится)
    guest_access_token_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Хеш guest access token",
    )
    guest_access_token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Срок действия guest access token",
    )

    # --- Синхронизация с 1С (SiteOrders) ---
    ONEC_SYNC_PENDING = "pending"
    ONEC_SYNC_SYNCED = "synced"
    ONEC_SYNC_PAID = "paid_synced"
    ONEC_SYNC_CANCELLED = "cancelled"
    ONEC_SYNC_ERROR = "error"
    ONEC_SYNC_BLOCKED = "blocked"
    ONEC_SYNC_DISABLED = "disabled"
    ONEC_SYNC_PENDING_REVIEW = "pending_review"
    ONEC_SYNC_CHOICES = [
        (ONEC_SYNC_PENDING, "Ожидает отправки"),
        (ONEC_SYNC_SYNCED, "Заказ в 1С (paid=false)"),
        (ONEC_SYNC_PAID, "Реализация в 1С (paid=true)"),
        (ONEC_SYNC_CANCELLED, "Отменён в 1С"),
        (ONEC_SYNC_ERROR, "Ошибка синхронизации"),
        (ONEC_SYNC_BLOCKED, "Заблокирован (нет склада/клиента)"),
        (ONEC_SYNC_DISABLED, "Синхронизация выключена"),
        (ONEC_SYNC_PENDING_REVIEW, "Требует сверки с 1С"),
    ]

    onec_client_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="ClientId 1С",
        help_text="UUID контрагента из SiteRegistration/registrate",
    )
    onec_warehouse_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="warehouseId 1С",
    )
    onec_document_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="documentId 1С (текущий)",
    )
    onec_document_number = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="documentNumber 1С",
    )
    onec_document_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="documentType 1С",
    )
    onec_order_document_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="documentId ЗаказКлиента",
        help_text="Сохраняется при первом paid=false; после оплаты текущий — реализация",
    )
    onec_paid = models.BooleanField(
        default=False,
        verbose_name="paid принят в 1С",
        help_text="Последний успешно принятый признак оплаты документа в 1С",
    )
    onec_posted = models.BooleanField(
        default=False,
        verbose_name="Документ проведён в 1С",
    )
    onec_sync_status = models.CharField(
        max_length=20,
        choices=ONEC_SYNC_CHOICES,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Статус синхронизации 1С",
    )
    onec_last_error = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Последняя ошибка 1С",
    )
    onec_synced_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Последняя успешная синхронизация 1С",
    )
    onec_sync_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Попыток синхронизации 1С",
    )
    onec_sync_claim = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Токен захвата sync-задачи",
        help_text="Защита от параллельных воркеров и устаревших HTTP-ответов",
    )
    onec_payload_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Снимок payload SiteOrders",
        help_text="Исходный запрос (кроме paid) для идемпотентных повторов и перехода paid=true",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = "orders_order"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            # Имена из 0001/0007 — иначе makemigrations предлагает RenameIndex.
            models.Index(fields=["order_number"], name="orders_orde_order_n_f3ada5_idx"),
            models.Index(fields=["status"], name="orders_orde_status_c6dd84_idx"),
            models.Index(fields=["user"], name="orders_orde_user_id_a87c6f_idx"),
            models.Index(fields=["created_at"], name="orders_orde_created_0e92de_idx"),
            models.Index(fields=["onec_sync_status"], name="orders_orde_onec_sy_7a1c2d_idx"),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"

    def is_cancelled(self) -> bool:
        if self.status == self.STATUS_CANCELLED:  # legacy pre-migrate
            return True
        return (
            self.status == self.STATUS_CLOSED
            and self.closure_result == self.CLOSURE_CANCELLED
        )

    def is_fulfilled(self) -> bool:
        return (
            self.status == self.STATUS_CLOSED
            and self.closure_result == self.CLOSURE_COMPLETED
        )

    def is_terminal(self) -> bool:
        return self.status == self.STATUS_CLOSED or self.is_cancelled()

    def display_status_code(self) -> str:
        """Код для UI: closed+result → completed|cancelled, иначе status."""
        if self.status == self.STATUS_CLOSED:
            return self.closure_result or self.STATUS_CLOSED
        return self.status

    def save(self, *args, **kwargs):
        if not self.order_number:
            while True:
                self.order_number = _generate_order_number()
                if not Order.objects.filter(order_number=self.order_number).exists():
                    break
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Позиция заказа."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="Товар",
    )
    product_title = models.CharField(
        max_length=255,
        verbose_name="Название на момент заказа",
    )
    product_sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Артикул",
    )
    color = models.ForeignKey(
        "products.ProductColor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="Цвет (ссылка)",
    )
    color_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Название цвета (снимок)",
    )
    color_slug = models.SlugField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Slug цвета (снимок)",
    )
    color_hex = models.CharField(
        max_length=12,
        blank=True,
        default="",
        verbose_name="HEX цвета (снимок)",
    )
    onec_product_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Код номенклатуры 1С",
        help_text="productCode для SiteOrders (снимок на момент заказа)",
    )
    onec_series_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="seriesId 1С",
        help_text="UUID серии; пусто → в JSON уходит null",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена на момент заказа",
    )
    item_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма по позиции",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "orders_orderitem"
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product_title} × {self.quantity}"

    def save(self, *args, **kwargs):
        if self.price is not None and self.quantity is not None:
            self.item_total = self.price * self.quantity
        super().save(*args, **kwargs)


class ManagerRating(models.Model):
    """
    Оценка конкретного менеджера по заказу (ТЗ: рейтинг привязан к менеджеру и магазину).
    Один заказ — одна оценка; оценка указывает, какому менеджеру она поставлена.
    """

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="manager_rating",
        verbose_name="Заказ",
    )
    manager = models.ForeignKey(
        "stores.Manager",
        on_delete=models.PROTECT,
        related_name="ratings",
        verbose_name="Менеджер",
        null=True,
        blank=True,
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Оценка (1–5)",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата оценки")

    class Meta:
        db_table = "orders_managerrating"
        verbose_name = "Оценка менеджера"
        verbose_name_plural = "Оценки менеджеров"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["rating"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["manager"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} — {self.manager_id or '?'} — {self.rating}"


class OneCInboundEvent(models.Model):
    """
    Журнал входящих событий 1С → сайт (статус заказа / оплата в магазине).
    event_id уникален — идемпотентность повторных доставок.
    """

    EVENT_STATUS = "status"
    EVENT_PAYMENT = "payment"
    EVENT_COMBINED = "combined"
    EVENT_TYPE_CHOICES = [
        (EVENT_STATUS, "Статус заказа"),
        (EVENT_PAYMENT, "Оплата"),
        (EVENT_COMBINED, "Статус и оплата"),
    ]

    RESULT_SUCCESS = "success"
    RESULT_DUPLICATE = "duplicate"
    RESULT_ERROR = "error"
    RESULT_CHOICES = [
        (RESULT_SUCCESS, "Успех"),
        (RESULT_DUPLICATE, "Дубликат"),
        (RESULT_ERROR, "Ошибка"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name="ID события 1С",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onec_inbound_events",
        verbose_name="Заказ",
    )
    order_number = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Номер заказа",
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        verbose_name="Тип события",
    )
    status_received = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Полученный status",
    )
    result_received = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Полученный result",
    )
    payment_status_received = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Полученный payment.status",
    )
    processing_result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default=RESULT_SUCCESS,
        db_index=True,
        verbose_name="Результат обработки",
    )
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.CharField(max_length=512, blank=True, default="")
    payload_summary = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Краткое тело (без секретов)",
    )
    occurred_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "orders_onec_inbound_event"
        verbose_name = "Входящее событие 1С"
        verbose_name_plural = "Входящие события 1С"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["processing_result", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_id} ({self.processing_result})"
