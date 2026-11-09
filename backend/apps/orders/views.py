"""
API заказов: создание, список, детали (задачи 1.5.4, 1.5.5).
Создание заказа выполняется в одной транзакции с атомарным резервом остатков.
"""

import hashlib
import logging
from decimal import Decimal

from django.conf import settings as django_settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.services import normalize_phone

from config.throttling import (
    GuestAccessRecoverAnonThrottle,
    GuestAccessRecoverConfirmAnonThrottle,
    OrderCreateAnonRateThrottle,
    OrderCreateRateThrottle,
    OrderRateAnonThrottle,
    OrderTrackAnonThrottle,
)

from .models import ManagerRating, Order, OrderItem
from .serializers import (
    ManagerRatingCreateSerializer,
    ManagerRatingSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
from .tasks import send_order_notifications

logger = logging.getLogger(__name__)


class InsufficientStockError(Exception):
    """Недостаточно остатка при атомарном резерве (в рамках транзакции)."""
    pass


def _order_idempotency_cache_key(request, raw_key: str) -> str:
    """
    SEC-005: namespace идемпотентности привязан к клиенту.
    Auth → user id; guest → hash(session_key). Не используем IP (NAT).
    """
    key_digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:40]
    if request.user and request.user.is_authenticated:
        scope = f"u:{request.user.pk}"
    else:
        if not getattr(request, "session", None):
            scope = "g:nosession"
        else:
            if not request.session.session_key:
                request.session.create()
            sk = request.session.session_key or ""
            sk_digest = hashlib.sha256(sk.encode("utf-8")).hexdigest()[:32]
            scope = f"g:{sk_digest}"
    return f"order_idempotency:{scope}:{key_digest}"


def _build_items_from_cart(cart):
    """Собрать items для сериализатора из корзины."""
    return [
        {
            "product_id": str(item.product_id),
            "quantity": item.quantity,
            "price": str(item.price_at_add),
        }
        for item in cart.items.select_related("product").all()
    ]


class OrderListCreateView(APIView):
    """
    GET /api/v1/orders/ — список заказов (только для авторизованных).
    POST /api/v1/orders/ — создание заказа (гость или пользователь).
    Rate limiting: на POST — 20/час (user) или 10/час (anon по IP).
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request.method == "POST":
            if self.request.user.is_authenticated:
                return [OrderCreateRateThrottle()]
            return [OrderCreateAnonRateThrottle()]
        return []

    def get(self, request):
        # SEC-001: staff не получает «все заказы» через customer API —
        # чужие заказы только через /api/v1/admin/orders/ (MFA + группа).
        qs = Order.objects.prefetch_related(
            "items", "manager_rating", "payments"
        ).filter(user=request.user)

        # Фильтр по статусу
        status_filter = request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Фильтры по типу доставки и способу оплаты
        delivery_type = request.query_params.get("delivery_type", "").strip()
        if delivery_type:
            qs = qs.filter(delivery_type=delivery_type)

        payment_type = request.query_params.get("payment_type", "").strip()
        if payment_type:
            qs = qs.filter(payment_type=payment_type)

        # Фильтр по периоду (дата создания заказа, локальная дата без времени)
        date_from = (request.query_params.get("date_from") or "").strip()
        if date_from:
            d_from = parse_date(date_from)
            if d_from:
                qs = qs.filter(created_at__date__gte=d_from)

        date_to = (request.query_params.get("date_to") or "").strip()
        if date_to:
            d_to = parse_date(date_to)
            if d_to:
                qs = qs.filter(created_at__date__lte=d_to)

        # Поиск по номеру заказа, телефону или ФИО
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search)
                | Q(phone__icontains=search)
                | Q(full_name__icontains=search)
            )

        # Сортировка по дате создания (по умолчанию — по убыванию)
        ordering = (request.query_params.get("ordering") or "").strip()
        if ordering == "created_at":
            qs = qs.order_by("created_at")
        else:
            qs = qs.order_by("-created_at")

        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        idempotency_key = (request.headers.get("X-Idempotency-Key") or "").strip()[:128]
        cache_key = None
        if idempotency_key:
            cache_key = _order_idempotency_cache_key(request, idempotency_key)
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(
                    cached["data"],
                    status=cached["status"],
                )

        # Мутабельная копия: из тела нельзя полагаться только на session-корзину (разные cookie / гость).
        if not request.data:
            data = {}
        elif isinstance(request.data, dict):
            data = {**request.data}
        else:
            data = request.data.copy()

        from_cart_flag = data.pop("from_cart", None)
        want_cart = (
            from_cart_flag in (True, "true", "1", "yes")
            if from_cart_flag is not None
            else False
        )

        cart = None
        if want_cart:
            from apps.cart.models import Cart

            cart = Cart.get_or_create_cart(request)
            if not data.get("items"):
                # Старый путь: состав только из серверной корзины
                if not cart.items.exists():
                    return Response(
                        {"code": "ORDER_INVALID_ITEMS", "detail": "Корзина пуста."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                data["items"] = _build_items_from_cart(cart)
                data["total_amount"] = str(cart.get_total())
                data.setdefault("delivery_cost", "0")
            else:
                # SPA прислала снимок позиций — сервер пересчитает цены в OrderCreateSerializer.
                # Для non-online корзина очищается после заказа; для online — только после оплаты.
                data.setdefault("delivery_cost", "0")

        serializer = OrderCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        attrs = serializer.validated_data
        store_id = attrs.get("store")
        delivery_type = attrs.get("delivery_type")
        items_data = attrs["items"]
        payment_type = attrs["payment_type"]
        is_online_payment = payment_type == Order.PAYMENT_ONLINE

        from apps.products.models import Product

        try:
            with transaction.atomic():
                order = Order(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=attrs["full_name"],
                    phone=attrs["phone"],
                    email=attrs.get("email"),
                    delivery_type=delivery_type,
                    delivery_address=attrs.get("delivery_address") or {},
                    store_id=store_id,
                    payment_type=payment_type,
                    total_amount=attrs["total_amount"],
                    delivery_cost=attrs.get("delivery_cost", Decimal("0")),
                    bonus_used=attrs.get("bonus_used", Decimal("0")),
                    comment=attrs.get("comment"),
                    consent_personal_data=attrs.get("consent_personal_data", False),
                    # Online: запомнить корзину, очистим после succeeded.
                    checkout_cart_id=(cart.id if cart and is_online_payment else None),
                )
                order.save()

                from apps.users.consent import record_consent
                from apps.users.models import ConsentRecord

                record_consent(
                    request,
                    ConsentRecord.TYPE_ORDER_PDN,
                    user=order.user,
                    order=order,
                )
                if attrs.get("consent_marketing"):
                    record_consent(
                        request,
                        ConsentRecord.TYPE_MARKETING,
                        user=order.user,
                        order=order,
                    )

                product_ids = [it["product_id"] for it in items_data]
                products_by_id = {
                    str(p.id): p
                    for p in Product.objects.filter(pk__in=product_ids, is_active=True)
                }

                from integrations.onec.orders import (
                    InsufficientStockAtStore,
                    plan_and_reserve_at_store,
                )

                # Резерв только в выбранном магазине (без поиска по сети / перемещений).
                if not store_id:
                    raise InsufficientStockError()

                for it in items_data:
                    product = products_by_id.get(str(it["product_id"]))
                    if not product:
                        raise InsufficientStockError()
                    try:
                        lines = plan_and_reserve_at_store(
                            product=product,
                            quantity=it["quantity"],
                            price=it["price"],
                            store_id=store_id,
                        )
                    except InsufficientStockAtStore as exc:
                        raise InsufficientStockError() from exc
                    for line in lines:
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            product_title=product.title,
                            product_sku=product.sku,
                            quantity=line["quantity"],
                            price=line["price"],
                            item_total=line["item_total"],
                            onec_product_code=line["onec_product_code"],
                            onec_series_id=line["onec_series_id"],
                            color_id=it.get("color_id"),
                            color_label=it.get("color_label") or "",
                            color_slug=it.get("color_slug") or "",
                            color_hex=it.get("color_hex") or "",
                        )

                # Наличные / карта при получении / перевод — заказ принят, корзину чистим.
                # Online — корзина живёт до подтверждённой оплаты (webhook/sync → paid);
                # clear вычитает только qty из OrderItem, не всю корзину.
                if cart and not is_online_payment:
                    cart.items.all().delete()

                logger.info(
                    "order_created order_id=%s payment_type=%s online=%s "
                    "checkout_cart_id=%s items=%s",
                    order.pk,
                    payment_type,
                    is_online_payment,
                    order.checkout_cart_id,
                    order.items.count(),
                )

        except InsufficientStockError:
            detail = (
                "Недостаточно товара в выбранном магазине. "
                "Выберите магазин, где все позиции корзины есть в наличии."
            )
            return Response(
                {"code": "INSUFFICIENT_STOCK", "detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        send_order_notifications.delay(order.id)

        from .tasks import enqueue_order_sync

        order_pk = order.id

        def _enqueue_onec():
            # Сначала paid=false; для online после оплаты Сбера уйдёт paid=true
            enqueue_order_sync(order_pk, paid=False)

        transaction.on_commit(_enqueue_onec)

        response_data = OrderSerializer(order).data
        # SEC-006: plaintext guest token только в ответе создания (не в БД, не в логах).
        if order.user_id is None:
            from .guest_access import issue_guest_access_token

            guest_token = issue_guest_access_token(order)
            response_data = {**response_data, "guest_access_token": guest_token}
        response = Response(response_data, status=status.HTTP_201_CREATED)
        if cache_key:
            cache.set(
                cache_key,
                {"data": response_data, "status": status.HTTP_201_CREATED},
                timeout=getattr(django_settings, "ORDER_IDEMPOTENCY_CACHE_TIMEOUT", 86400),
            )
        return response


class OrderDetailView(RetrieveAPIView):
    """
    GET /api/v1/orders/{id}/ — детали заказа.
    Доступ: только владелец (в т.ч. staff со своим заказом).
    Админский просмотр чужих заказов — /api/v1/admin/orders/{id}/.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    queryset = Order.objects.prefetch_related("items", "payments")

    def get_queryset(self):
        # SEC-001: без staff-bypass
        return (
            Order.objects.prefetch_related("items", "payments")
            .filter(user=self.request.user)
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class OrderReorderView(APIView):
    """
    POST /api/v1/orders/{id}/reorder/ — повтор заказа: добавить позиции в корзину.
    INT-026: сохраняет color и store заказа; цена — актуальная (не snapshot).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from apps.cart.models import Cart, CartItem
        from apps.products.models import ProductColor
        from apps.stores.models import Stock, Store

        order = (
            Order.objects.select_related("store")
            .prefetch_related("items__product", "items__color")
            .filter(pk=pk, user=request.user)
            .first()
        )
        if not order:
            return Response(
                {"detail": "Заказ не найден или нет прав."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cart = Cart.get_or_create_cart(request)
        added = 0
        skipped: list[dict] = []
        order_store = order.store
        if order_store_id := order.store_id:
            # Не подменяем магазин: если точка недоступна — позиции с store пропускаем
            if not Store.objects.filter(pk=order_store_id, is_active=True).exists():
                order_store = None

        for order_item in order.items.all():
            title = order_item.product_title or (
                order_item.product.title if order_item.product_id else "Товар"
            )
            if not order_item.product_id:
                skipped.append({"product_title": title, "reason": "product_missing"})
                continue
            product = order_item.product
            if not product or not product.is_active:
                skipped.append({"product_title": title, "reason": "product_inactive"})
                continue

            color = order_item.color
            if order_item.color_id:
                color = ProductColor.objects.filter(
                    pk=order_item.color_id, product_id=product.pk, is_active=True
                ).first()
                if color is None:
                    skipped.append(
                        {"product_title": title, "reason": "color_unavailable"}
                    )
                    continue

            store = order_store
            if order.store_id and store is None:
                skipped.append({"product_title": title, "reason": "store_unavailable"})
                continue

            # Актуальная цена (не snapshot заказа) — checkout всё равно сверит
            unit_price = (
                color.effective_price if color is not None else product.price
            )

            need_qty = int(order_item.quantity)
            if store is not None:
                available = Stock.available_quantity_at_store(product.pk, store.pk)
                if available < need_qty:
                    skipped.append(
                        {
                            "product_title": title,
                            "reason": "insufficient_stock",
                            "available": available,
                        }
                    )
                    continue

            item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                store=store,
                color=color,
                defaults={
                    "quantity": need_qty,
                    "price_at_add": unit_price,
                },
            )
            if not created:
                item.quantity += need_qty
                item.price_at_add = unit_price
                item.save(
                    update_fields=["quantity", "price_at_add", "updated_at"]
                )
            added += 1

        from apps.cart.views import _get_cart_queryset
        from apps.cart.serializers import CartSerializer

        cart = _get_cart_queryset().get(pk=cart.pk)
        cart_data = CartSerializer(cart, context={"request": request}).data
        return Response(
            {
                "cart": cart_data,
                "added_count": added,
                "skipped": skipped,
                "partial": bool(skipped),
            },
            status=status.HTTP_200_OK,
        )


def _phone_matches_order(stored_phone: str, submitted: str) -> bool:
    """Сравнение телефона заказа и ввода: нормализация РФ, иначе точное совпадение по цифрам."""
    n_stored = normalize_phone(stored_phone or "")
    n_sub = normalize_phone(submitted or "")
    if n_stored and n_sub:
        return n_stored == n_sub
    ds = "".join(c for c in str(stored_phone or "") if c.isdigit())
    du = "".join(c for c in str(submitted or "") if c.isdigit())
    return bool(ds) and bool(du) and ds == du


def _guest_track_response(request, order, *, phone: str, order_number: str):
    """
    SEC-006: полные ПДн только при валидном guest_token.
    Phone+number без токена — урезанный статус (без контактов/адреса/состава).
    Legacy phone+number полный доступ закрыт.
    """
    from .guest_access import guest_may_access_order

    if guest_may_access_order(
        request, order, phone=phone, order_number=order_number
    ):
        return Response(OrderSerializer(order).data)

    if _phone_matches_order(order.phone, phone):
        return Response(
            {
                "order_number": order.order_number,
                "status": order.status,
                "created_at": order.created_at,
                "payment_type": order.payment_type,
                "delivery_type": order.delivery_type,
                "guest_token_required": True,
            }
        )
    return None


class OrderTrackView(APIView):
    """
    GET /api/v1/orders/track/?order_number=…&phone=…&guest_token=…
    SEC-006: полный заказ — с guest_token; без токена — урезанный статус.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OrderTrackAnonThrottle]

    def get(self, request):
        order_number = (request.query_params.get("order_number") or "").strip()
        phone = (request.query_params.get("phone") or "").strip()
        if not order_number or not phone:
            return Response(
                {"detail": "Укажите номер заказа и телефон."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = (
            Order.objects.prefetch_related("items")
            .filter(order_number=order_number)
            .first()
        )
        if not order or not _phone_matches_order(order.phone, phone):
            return Response(
                {"detail": "Заказ не найден или телефон не совпадает."},
                status=status.HTTP_404_NOT_FOUND,
            )
        resp = _guest_track_response(
            request, order, phone=phone, order_number=order_number
        )
        if resp is None:
            return Response(
                {"detail": "Заказ не найден или телефон не совпадает."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return resp


class OrderStatusView(APIView):
    """
    POST /api/v1/orders/status/
    Тело: order_number, phone, optional guest_token.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OrderTrackAnonThrottle]

    def post(self, request):
        data = request.data or {}
        order_number = str(data.get("order_number") or "").strip()
        phone = str(data.get("phone") or "").strip()
        if not order_number or not phone:
            return Response(
                {"detail": "Укажите номер заказа и телефон."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = (
            Order.objects.prefetch_related("items")
            .select_related("store")
            .filter(order_number=order_number)
            .first()
        )
        if not order or not _phone_matches_order(order.phone, phone):
            return Response(
                {"detail": "Заказ не найден или телефон не совпадает."},
                status=status.HTTP_404_NOT_FOUND,
            )
        resp = _guest_track_response(
            request, order, phone=phone, order_number=order_number
        )
        if resp is None:
            return Response(
                {"detail": "Заказ не найден или телефон не совпадает."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return resp


class OrderCancelView(APIView):
    """
    POST /api/v1/orders/{id}/cancel/

    Авторизованный: отмена своего заказа.
    Гость: требуется guest_token (SEC-006). Phone+number недостаточно.
    Разрешено только для статусов new и processing.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OrderTrackAnonThrottle]

    def post(self, request, pk):
        order = (
            Order.objects.prefetch_related("items", "manager_rating")
            .select_related("store")
            .filter(pk=pk)
            .first()
        )
        if not order:
            return Response({"detail": "Заказ не найден."}, status=status.HTTP_404_NOT_FOUND)

        # Доступ: владелец (auth) или guest_token (SEC-006).
        # SEC-001: is_staff сам по себе не даёт отменять чужие заказы.
        if request.user.is_authenticated:
            if order.user_id != request.user.id:
                return Response(
                    {"detail": "Нет прав для отмены этого заказа."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            from .guest_access import guest_may_access_order

            data = request.data or {}
            order_number = str(data.get("order_number") or "").strip()
            phone = str(data.get("phone") or "").strip()
            if not guest_may_access_order(
                request, order, phone=phone, order_number=order_number
            ):
                return Response(
                    {"detail": "Нет прав для отмены этого заказа."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        from .services import (
            OrderCancelError,
            cancel_order_and_release_stock,
            customer_may_cancel_order,
        )

        if not customer_may_cancel_order(order):
            # FUNC-009: оплаченный / недопустимый статус
            from .services import order_has_successful_payment

            if order_has_successful_payment(order):
                return Response(
                    {
                        "detail": (
                            "Заказ уже оплачен. Для отмены и возврата "
                            "обратитесь в поддержку."
                        ),
                        "code": "paid_order_cancel_forbidden",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": "Отмена доступна только для новых или подтверждённых заказов."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = cancel_order_and_release_stock(order, reason="user_cancel")
        except OrderCancelError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderRateView(APIView):
    """
    POST /api/v1/orders/rate/ — отправить оценку менеджера по заказу (ТЗ EPIC 2).
    Авторизованный: свой order_id.
    Гость: guest_token (+ order_number); phone+number недостаточно (SEC-006).
    Один заказ — одна оценка. Заказ не должен быть отменён.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OrderRateAnonThrottle]

    def post(self, request):
        ser = ManagerRatingCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        order_id = data.get("order_id")
        order_number = (data.get("order_number") or "").strip()
        phone = (data.get("phone") or "").strip()
        rating = data["rating"]
        comment = (data.get("comment") or "").strip() or None

        order = None
        if order_id and request.user.is_authenticated:
            order = Order.objects.filter(
                pk=order_id,
                user=request.user,
            ).first()
        if order is None and order_number:
            from .guest_access import guest_may_access_order

            candidate = Order.objects.filter(
                order_number=order_number, user__isnull=True
            ).first()
            if candidate and guest_may_access_order(
                request, candidate, phone=phone, order_number=order_number
            ):
                order = candidate

        if not order:
            return Response(
                {"detail": "Заказ не найден или нет прав для оценки."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if order.is_cancelled():
            return Response(
                {"detail": "Нельзя оценить отменённый заказ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if hasattr(order, "manager_rating") and order.manager_rating:
            return Response(
                {"detail": "Оценка по этому заказу уже отправлена."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.stores.models import Manager
        manager_id = data.get("manager_id")
        manager = None
        if manager_id:
            manager = Manager.objects.filter(pk=manager_id, is_active=True).first()
        if not manager:
            return Response(
                {"detail": "Укажите активного менеджера (manager_id)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        manager_rating = ManagerRating.objects.create(
            order=order,
            manager=manager,
            rating=rating,
            comment=comment,
        )

        to_email = getattr(
            django_settings,
            "MANAGER_RATING_NOTIFY_EMAIL",
            None,
        )
        if to_email:
            from integrations.email_service import send_manager_rating
            send_manager_rating(
                to_email=to_email,
                order_number=order.order_number,
                manager_name=manager.name,
                rating=rating,
                comment=comment,
            )

        return Response(
            ManagerRatingSerializer(manager_rating).data,
            status=status.HTTP_201_CREATED,
        )


class ManagerRatingSummaryView(APIView):
    """
    GET /api/v1/orders/ratings-summary/ — рейтинг менеджеров для «О нас» и ЛК (ТЗ EPIC 2).
    Публичный endpoint: средняя оценка, количество, последние отзывы (без персональных данных).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Avg, Count

        qs = ManagerRating.objects.all()
        agg = qs.aggregate(
            average=Avg("rating"),
            count=Count("id"),
        )
        recent_qs = (
            ManagerRating.objects.order_by("-created_at")
            .select_related("manager")
            .values("rating", "comment", "created_at", "manager__name")[:10]
        )
        recent = [
            {
                "rating": r["rating"],
                "comment": r["comment"],
                "created_at": r["created_at"],
                "manager_name": r.get("manager__name"),
            }
            for r in recent_qs
        ]
        return Response({
            "average": round(agg["average"] or 0, 1),
            "count": agg["count"] or 0,
            "recent": recent,
        })


class GuestAccessRecoverRequestView(APIView):
    """
    POST /api/v1/orders/guest-access/recover/
    SEC-006: восстановление гостевого доступа через email OTP.
    Ответ одинаков независимо от существования заказа.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [GuestAccessRecoverAnonThrottle]

    def post(self, request):
        from .guest_access import PUBLIC_RECOVER_DETAIL, request_guest_access_recovery

        data = request.data or {}
        order_number = str(data.get("order_number") or "").strip()
        email = str(data.get("email") or "").strip()
        request_guest_access_recovery(order_number=order_number, email=email)
        return Response({"detail": PUBLIC_RECOVER_DETAIL}, status=status.HTTP_200_OK)


class GuestAccessRecoverConfirmView(APIView):
    """
    POST /api/v1/orders/guest-access/recover/confirm/
    Тело: order_number, token (recovery). Выдаёт новый guest_access_token.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [GuestAccessRecoverConfirmAnonThrottle]

    def post(self, request):
        from .guest_access import confirm_guest_access_recovery

        data = request.data or {}
        order_number = str(data.get("order_number") or "").strip()
        token = str(data.get("token") or data.get("recovery_token") or "").strip()
        guest_token = confirm_guest_access_recovery(
            order_number=order_number, recovery_token=token
        )
        if not guest_token:
            return Response(
                {"detail": "Ссылка восстановления недействительна или устарела."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = Order.objects.filter(order_number=order_number, user__isnull=True).first()
        return Response(
            {
                "guest_access_token": guest_token,
                "order_id": str(order.pk) if order else None,
                "order_number": order_number,
            },
            status=status.HTTP_200_OK,
        )
