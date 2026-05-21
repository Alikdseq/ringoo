"""Admin API: Остатки (Stock) — GET список, PATCH quantity, drill-down."""

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_admin_action
from apps.stores.models import Stock, Store

from ..permissions import RINGOO_GROUP_STORES, admin_permissions


class StockListSerializer:
    """Минимальный сериализатор для списка остатков."""

    @staticmethod
    def to_representation(obj):
        return {
            "id": str(obj.id),
            "product": str(obj.product_id),
            "product_title": obj.product.title if obj.product_id else "",
            "store": str(obj.store_id),
            "store_name": obj.store.name if obj.store_id else "",
            "quantity": obj.quantity,
            "reserved_quantity": obj.reserved_quantity,
            "available_quantity": obj.available_quantity,
        }


class StockAdminListView(APIView):
    """
    GET /api/v1/admin/stores/stock/ — список остатков.
    Параметры: ?product=uuid, ?store=uuid
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_STORES)

    def get(self, request):
        qs = Stock.objects.select_related("product", "store").order_by(
            "product__title", "store__name"
        )
        product_id = request.query_params.get("product", "").strip()
        store_id = request.query_params.get("store", "").strip()
        if product_id:
            qs = qs.filter(product_id=product_id)
        if store_id:
            qs = qs.filter(store_id=store_id)

        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            data = [StockListSerializer.to_representation(s) for s in page]
            return paginator.get_paginated_response(data)
        data = [StockListSerializer.to_representation(s) for s in qs]
        return Response(data)


class StockAdminUpdateView(UpdateAPIView):
    """
    PATCH /api/v1/admin/stores/stock/{id}/ — изменение quantity (и при необходимости reserved_quantity).
    Доступ: staff.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_STORES)
    queryset = Stock.objects.select_related("product", "store")
    http_method_names = ["patch"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        before = {"quantity": instance.quantity, "reserved_quantity": instance.reserved_quantity}
        quantity = request.data.get("quantity")
        reserved = request.data.get("reserved_quantity")

        if quantity is not None:
            try:
                q = int(quantity)
                if q < 0:
                    return Response(
                        {"quantity": ["Не может быть отрицательным."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                instance.quantity = q
            except (TypeError, ValueError):
                return Response(
                    {"quantity": ["Некорректное значение."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if reserved is not None:
            try:
                r = int(reserved)
                if r < 0:
                    return Response(
                        {"reserved_quantity": ["Не может быть отрицательным."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if instance.quantity < r:
                    return Response(
                        {"reserved_quantity": ["Не может превышать quantity."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                instance.reserved_quantity = r
            except (TypeError, ValueError):
                return Response(
                    {"reserved_quantity": ["Некорректное значение."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        instance.save()
        after = {"quantity": instance.quantity, "reserved_quantity": instance.reserved_quantity}
        if before != after:
            log_admin_action(
                request,
                action="update",
                model_name="Stock",
                object_id=str(instance.pk),
                object_repr=f"{instance.product_id} @ {instance.store_id}",
                changes={"stock": {"from": before, "to": after}},
            )
        return Response(StockListSerializer.to_representation(instance))


class StockStoresSummaryView(APIView):
    """GET /admin/stores/stock/stores-summary/ — магазины с агрегатами остатков."""

    permission_classes = admin_permissions(RINGOO_GROUP_STORES)

    def get(self, request):
        stores = Store.objects.order_by("city", "name")
        rows = []
        for store in stores:
            qs = Stock.objects.filter(store=store)
            total_skus = qs.values("product_id").distinct().count()
            low_stock_count = qs.filter(quantity__lte=2).count()
            rows.append(
                {
                    "id": str(store.id),
                    "name": store.name,
                    "slug": store.slug,
                    "city": store.city,
                    "is_active": store.is_active,
                    "total_skus": total_skus,
                    "low_stock_count": low_stock_count,
                }
            )
        return Response(rows)


class StockByStoreCategoriesView(APIView):
    """GET /admin/stores/stock/by-store/{store_id}/categories/"""

    permission_classes = admin_permissions(RINGOO_GROUP_STORES)

    def get(self, request, store_id):
        if not Store.objects.filter(pk=store_id).exists():
            return Response({"detail": "Магазин не найден."}, status=status.HTTP_404_NOT_FOUND)

        agg = (
            Stock.objects.filter(store_id=store_id)
            .values(
                "product__category_id",
                "product__category__title",
                "product__category__slug",
            )
            .annotate(stock_count=Count("id"))
            .order_by("product__category__title")
        )
        rows = []
        for row in agg:
            cat_id = row["product__category_id"]
            if not cat_id:
                continue
            rows.append(
                {
                    "category_id": str(cat_id),
                    "title": row["product__category__title"] or "—",
                    "slug": row["product__category__slug"] or "",
                    "stock_count": row["stock_count"],
                }
            )
        uncategorized = (
            Stock.objects.filter(store_id=store_id, product__category__isnull=True).count()
        )
        if uncategorized:
            rows.append(
                {
                    "category_id": "",
                    "title": "Без категории",
                    "slug": "",
                    "stock_count": uncategorized,
                }
            )
        return Response(rows)


class StockByStoreProductsView(APIView):
    """GET /admin/stores/stock/by-store/{store_id}/products/?category=uuid"""

    permission_classes = admin_permissions(RINGOO_GROUP_STORES)

    def get(self, request, store_id):
        if not Store.objects.filter(pk=store_id).exists():
            return Response({"detail": "Магазин не найден."}, status=status.HTTP_404_NOT_FOUND)

        qs = Stock.objects.filter(store_id=store_id).select_related("product", "store").order_by(
            "product__title"
        )
        category_id = (request.query_params.get("category") or "").strip()
        if category_id == "__none__":
            qs = qs.filter(product__category__isnull=True)
        elif category_id:
            qs = qs.filter(product__category_id=category_id)

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(product__title__icontains=search) | Q(product__sku__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            data = [StockListSerializer.to_representation(s) for s in page]
            return paginator.get_paginated_response(data)
        data = [StockListSerializer.to_representation(s) for s in qs]
        return Response(data)
