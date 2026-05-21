"""
API заказов: создание, список, детали (задачи 1.5.4, 1.5.5).
Создание заказа выполняется в одной транзакции с атомарным резервом остатков.
"""

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


class InsufficientStockError(Exception):
    """Недостаточно остатка при атомарном резерве (в рамках транзакции)."""
    pass


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
        qs = Order.objects.prefetch_related("items", "manager_rating")

        if not request.user.is_staff:
            qs = qs.filter(user=request.user)

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
        if idempotency_key:
            cache_key = f"order_idempotency:{idempotency_key}"
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
                # SPA прислала снимок позиций — сервер пересчитает цены в OrderCreateSerializer;
                # корзина по session всё равно очищается после успешного заказа (см. ниже).
                data.setdefault("delivery_cost", "0")

        serializer = OrderCreateSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        attrs = serializer.validated_data
        store_id = attrs.get("store")
        delivery_type = attrs.get("delivery_type")
        items_data = attrs["items"]

        from apps.stores.models import Stock
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
                    payment_type=attrs["payment_type"],
                    total_amount=attrs["total_amount"],
                    delivery_cost=attrs.get("delivery_cost", Decimal("0")),
                    bonus_used=attrs.get("bonus_used", Decimal("0")),
                    comment=attrs.get("comment"),
                    consent_personal_data=attrs.get("consent_personal_data", False),
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

                for it in items_data:
                    product = products_by_id.get(str(it["product_id"]))
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_title=product.title if product else "",
                        product_sku=product.sku if product else None,
                        quantity=it["quantity"],
                        price=it["price"],
                        item_total=it["price"] * it["quantity"],
                    )

                # Самовывоз и доставка: резерв по суммарным остаткам сети. Точка самовывоза (store)
                # задаётся для клиента; не требуем отдельной строки Stock в этом магазине — иначе
                # заказ часто падает, хотя товар есть в сети (доставка при этом проходит).
                if delivery_type in (Order.DELIVERY_PICKUP, Order.DELIVERY_DELIVERY):
                    for it in items_data:
                        if not Stock.reserve_for_delivery(
                            it["product_id"], it["quantity"]
                        ):
                            raise InsufficientStockError()

                if cart:
                    cart.items.all().delete()

        except InsufficientStockError:
            detail = "Недостаточно товара на складах для оформления заказа."
            return Response(
                {"code": "INSUFFICIENT_STOCK", "detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        send_order_notifications.delay(order.id)

        response_data = OrderSerializer(order).data
        response = Response(response_data, status=status.HTTP_201_CREATED)
        if idempotency_key:
            cache_key = f"order_idempotency:{idempotency_key}"
            cache.set(
                cache_key,
                {"data": response_data, "status": status.HTTP_201_CREATED},
                timeout=getattr(django_settings, "ORDER_IDEMPOTENCY_CACHE_TIMEOUT", 86400),
            )
        return response


class OrderDetailView(RetrieveAPIView):
    """
    GET /api/v1/orders/{id}/ — детали заказа.
    Доступ: владелец или staff.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    queryset = Order.objects.prefetch_related("items")

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items").all()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class OrderReorderView(APIView):
    """
    POST /api/v1/orders/{id}/reorder/ — повтор заказа: добавить все позиции заказа в корзину.
    Доступ: только владелец заказа (авторизованный пользователь).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from apps.cart.models import Cart, CartItem

        order = (
            Order.objects.prefetch_related("items__product")
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
        for order_item in order.items.all():
            if not order_item.product_id:
                continue
            product = order_item.product
            if not product or not product.is_active:
                continue
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                store=None,
                defaults={
                    "quantity": order_item.quantity,
                    "price_at_add": product.price,
                },
            )
            if not created:
                item.quantity += order_item.quantity
                item.price_at_add = product.price
                item.save(update_fields=["quantity", "price_at_add", "updated_at"])
            added += 1

        from apps.cart.views import _get_cart_queryset
        from apps.cart.serializers import CartSerializer

        cart = _get_cart_queryset().get(pk=cart.pk)
        return Response(
            CartSerializer(cart).data,
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


class OrderTrackView(APIView):
    """
    GET /api/v1/orders/track/?order_number=ORD-xxx&phone=+79...
    Проверка статуса заказа по номеру и телефону (гостевой заказ). Без авторизации.
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
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class OrderStatusView(APIView):
    """
    POST /api/v1/orders/status/
    Тело: {"order_number": "...", "phone": "+7..."}
    Алиас для /orders/track/ (официальная страница «Проверить заказ»).
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
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class OrderCancelView(APIView):
    """
    POST /api/v1/orders/{id}/cancel/

    Авторизованный: отмена своего заказа.
    Гость: требуется order_number + phone (как в /orders/track/).
    Разрешено только для статусов new и confirmed.
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

        # Доступ: владелец (auth) или совпадение телефона (guest).
        if request.user.is_authenticated:
            if not request.user.is_staff and order.user_id != request.user.id:
                return Response({"detail": "Нет прав для отмены этого заказа."}, status=status.HTTP_403_FORBIDDEN)
        else:
            data = request.data or {}
            order_number = str(data.get("order_number") or "").strip()
            phone = str(data.get("phone") or "").strip()
            if not order_number or not phone:
                return Response(
                    {"detail": "Укажите номер заказа и телефон."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if order.order_number != order_number or not _phone_matches_order(order.phone, phone):
                return Response(
                    {"detail": "Заказ не найден или телефон не совпадает."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if order.status not in (Order.STATUS_NEW, Order.STATUS_CONFIRMED):
            return Response(
                {"detail": "Отмена доступна только для новых или подтверждённых заказов."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status", "updated_at"])
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderRateView(APIView):
    """
    POST /api/v1/orders/rate/ — отправить оценку менеджера по заказу (ТЗ EPIC 2).
    Гость: order_number + phone. Авторизованный: order_id или order_number + phone.
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
        if order is None and order_number and phone:
            candidate = Order.objects.filter(order_number=order_number).first()
            if candidate and _phone_matches_order(candidate.phone, phone):
                order = candidate

        if not order:
            return Response(
                {"detail": "Заказ не найден или нет прав для оценки."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if order.status == Order.STATUS_CANCELLED:
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
