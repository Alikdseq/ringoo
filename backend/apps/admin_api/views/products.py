"""Admin API: Товары и категории — список (все), создание, PATCH, массовые операции."""

import csv
from decimal import Decimal, InvalidOperation

from django.db.models import Prefetch, Q
from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_admin_action
from apps.products.models import Category, Product, ProductColor, ProductImage, ProductSpec
from apps.products.serializers import ProductDetailSerializer
from apps.products.services.bulk_import import build_import_template_xlsx, run_bulk_import
from apps.products.utils import slugify_product_title, unique_product_slug
from config.public_urls import absolute_media_url

from ..permissions import RINGOO_GROUP_CATALOG, admin_permissions


class CategoryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "title",
            "slug",
            "parent",
            "description",
            "image",
            "is_active",
            "sort_order",
            "meta_title",
            "meta_description",
            "onec_code",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "onec_code", "created_at", "updated_at")


class ProductAdminListSerializer(serializers.ModelSerializer):
    category = CategoryAdminSerializer(read_only=True)
    available_quantity_total = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "title", "slug", "sku", "category", "price", "old_price",
            "is_active", "is_featured", "brand", "onec_code", "onec_type",
            "created_at", "updated_at", "available_quantity_total",
        )
        read_only_fields = fields

    def get_available_quantity_total(self, obj):
        """
        Суммарное доступное количество по всем складам:
        суммируем Stock.available_quantity (или quantity - reserved_quantity).
        """
        total = 0
        try:
            for stock in obj.stock_items.all():
                qty = getattr(stock, "available_quantity", None)
                if qty is None:
                    qty = max(0, (stock.quantity or 0) - (stock.reserved_quantity or 0))
                total += qty or 0
        except Exception:
            return 0
        return total


class ProductAdminUpdateSerializer(serializers.ModelSerializer):
    """
    PATCH товара. При наличии onec_code поля 1С (цена, title, sku, category…)
    отклоняются; локальные SEO/описания/публикация остаются доступны.
    """

    onec_code = serializers.CharField(read_only=True)
    onec_type = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "title",
            "slug",
            "sku",
            "category",
            "brand",
            "price",
            "old_price",
            "description",
            "short_description",
            "meta_title",
            "meta_description",
            "is_active",
            "is_featured",
            "onec_code",
            "onec_type",
        )
        read_only_fields = ("onec_code", "onec_type")

    def validate(self, attrs):
        from apps.products.onec_protection import (
            ONEC_MANAGED_PRODUCT_FIELDS,
            product_is_onec_managed,
            reject_onec_managed_writes,
        )

        instance = self.instance
        if instance is None or not product_is_onec_managed(instance):
            return attrs

        # Разрешаем no-op (то же значение), запрещаем реальное изменение.
        changed = []
        for field in attrs:
            if field not in ONEC_MANAGED_PRODUCT_FIELDS:
                continue
            new_val = attrs[field]
            old_val = getattr(instance, field, None)
            if field == "category":
                old_val = getattr(instance, "category_id", None)
                new_cmp = getattr(new_val, "pk", new_val)
                old_cmp = old_val
            else:
                new_cmp = new_val
                old_cmp = old_val
            if str(new_cmp) != str(old_cmp):
                changed.append(field)
        if changed:
            reject_onec_managed_writes(instance, changed)
        # Не записываем 1С-поля даже при no-op — только локальные.
        for field in list(attrs.keys()):
            if field in ONEC_MANAGED_PRODUCT_FIELDS:
                attrs.pop(field, None)
        return attrs


class ProductAdminCreateSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = (
            "title",
            "slug",
            "sku",
            "category",
            "brand",
            "price",
            "old_price",
            "description",
            "short_description",
            "meta_title",
            "meta_description",
            "is_active",
            "is_featured",
        )

    def create(self, validated_data):
        raw_slug = (validated_data.pop("slug", None) or "").strip()
        if raw_slug:
            base = slugify_product_title(raw_slug)
        else:
            base = slugify_product_title(validated_data.get("title", ""))
        validated_data["slug"] = unique_product_slug(base)
        return super().create(validated_data)


def _filter_admin_products_queryset(queryset, params):
    """
    Применяет фильтры и поиск для списка товаров админки.

    Параметры:
    - search: подстрочный поиск по названию и артикулу
    - category: UUID категории
    - brand: строка бренда (точное совпадение, без учёта регистра)
    - is_active: true/false/1/0
    - ordering: created_at, -created_at, price, -price, title, -title
    """
    qs = queryset
    search = (params.get("search") or "").strip()
    category_id = (params.get("category") or "").strip()
    brand = (params.get("brand") or "").strip()
    is_active = (params.get("is_active") or "").strip().lower()
    ordering = (params.get("ordering") or "").strip()

    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(sku__icontains=search))
    if category_id:
        qs = qs.filter(category_id=category_id)
    if brand:
        qs = qs.filter(brand__iexact=brand)
    if is_active in {"true", "false", "1", "0"}:
        qs = qs.filter(is_active=is_active in {"true", "1"})

    allowed_ordering = {
        "created_at",
        "-created_at",
        "price",
        "-price",
        "title",
        "-title",
    }
    if ordering in allowed_ordering:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("-created_at")

    return qs


class ProductAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    serializer_class = ProductAdminListSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        base_qs = Product.objects.select_related("category").prefetch_related("stock_items").all()
        return _filter_admin_products_queryset(base_qs, self.request.query_params)


class ProductAdminDetailView(RetrieveAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Product.objects.select_related("category").prefetch_related(
        Prefetch(
            "colors",
            queryset=ProductColor.objects.filter(is_active=True).order_by("sort_order", "label"),
        ),
        Prefetch(
            "images",
            queryset=ProductImage.objects.select_related("color").order_by("sort_order", "created_at"),
        ),
        "specs",
        "stock_items",
    )
    serializer_class = ProductDetailSerializer
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class ProductAdminUpdateView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Product.objects.all()
    serializer_class = ProductAdminUpdateSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def perform_update(self, serializer):
        instance = serializer.save()
        log_admin_action(
            self.request,
            action="product_update",
            model_name="products.Product",
            object_id=str(instance.pk),
            object_repr=instance.title or str(instance.pk),
            changes=serializer.validated_data,
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Product.objects.all()
    serializer_class = ProductAdminCreateSerializer


class ProductAdminBulkSetActiveView(APIView):
    """
    POST /api/v1/admin/products/bulk/set-active/ — массовая активация/деактивация товаров.
    Тело: { "product_ids": [uuid, ...], "is_active": true/false }
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        product_ids = request.data.get("product_ids") or []
        is_active = request.data.get("is_active")

        if not isinstance(product_ids, list) or not product_ids:
            return Response(
                {"detail": "product_ids is required and must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if is_active is None:
            return Response(
                {"detail": "is_active is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_active_bool = (
            is_active
            if isinstance(is_active, bool)
            else str(is_active).strip().lower() in {"true", "1", "yes"}
        )

        updated = Product.objects.filter(id__in=product_ids).update(is_active=is_active_bool)
        return Response({"updated": updated})


class ProductAdminBulkUpdatePricesView(APIView):
    """
    POST /api/v1/admin/products/bulk/update-prices/ — массовое изменение цен.

    Тело:
    {
      "product_ids": [uuid, ...],
      "mode": "percent" | "absolute",
      "value": 10.0,
      "direction": "increase" | "decrease",
      "field": "price" | "old_price"
    }
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        product_ids = request.data.get("product_ids") or []
        mode = (request.data.get("mode") or "").strip()
        direction = (request.data.get("direction") or "increase").strip().lower()
        field = (request.data.get("field") or "price").strip()
        raw_value = request.data.get("value")

        if not isinstance(product_ids, list) or not product_ids:
            return Response(
                {"detail": "product_ids is required and must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if mode not in {"percent", "absolute"}:
            return Response(
                {"detail": "mode must be 'percent' or 'absolute'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if direction not in {"increase", "decrease"}:
            return Response(
                {"detail": "direction must be 'increase' or 'decrease'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if field not in {"price", "old_price"}:
            return Response(
                {"detail": "field must be 'price' or 'old_price'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            value = Decimal(str(raw_value))
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"detail": "value must be a valid number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if value < 0:
            return Response(
                {"detail": "value must be non-negative."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sign = Decimal("1") if direction == "increase" else Decimal("-1")

        qs = Product.objects.filter(id__in=product_ids).only("id", field, "onec_code")
        to_update = []
        skipped_onec = []

        for product in qs:
            if product.onec_code:
                skipped_onec.append(str(product.pk))
                continue
            current = getattr(product, field)
            if current is None:
                continue

            if mode == "percent":
                factor = Decimal("1") + sign * (value / Decimal("100"))
                new_value = current * factor
            else:
                new_value = current + sign * value

            if new_value < 0:
                new_value = Decimal("0")

            if new_value != current:
                setattr(product, field, new_value)
                to_update.append(product)

        if to_update:
            Product.objects.bulk_update(to_update, [field])

        return Response(
            {
                "updated": len(to_update),
                "skipped_onec_managed": len(skipped_onec),
                "skipped_onec_ids": skipped_onec[:50],
                "code": (
                    "onec_managed_prices_skipped" if skipped_onec else None
                ),
            }
        )


class ProductAdminExportView(APIView):
    """
    GET /api/v1/admin/products/export/ — экспорт каталога в CSV.
    Использует те же фильтры, что и список товаров.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def get(self, request):
        base_qs = Product.objects.select_related("category").prefetch_related("stock_items").all()
        qs = _filter_admin_products_queryset(base_qs, request.query_params)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="products.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "title",
                "sku",
                "category",
                "brand",
                "price",
                "old_price",
                "is_active",
                "available_quantity_total",
            ]
        )

        for product in qs:
            total_stock = 0
            try:
                for stock in product.stock_items.all():
                    qty = getattr(stock, "available_quantity", None)
                    if qty is None:
                        qty = max(0, (stock.quantity or 0) - (stock.reserved_quantity or 0))
                    total_stock += qty or 0
            except Exception:
                total_stock = 0

            writer.writerow(
                [
                    str(product.id),
                    product.title,
                    product.sku or "",
                    product.category.title if product.category_id else "",
                    product.brand or "",
                    str(product.price),
                    str(product.old_price) if product.old_price is not None else "",
                    "1" if product.is_active else "0",
                    str(total_stock),
                ]
            )

        return response


class CategoryAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Category.objects.all().order_by("sort_order", "title")
    serializer_class = CategoryAdminSerializer
    pagination_class = None


class CategoryAdminUpdateSerializer(serializers.ModelSerializer):
    """
    Локальный контент категории. Поля иерархии/названия из 1С (onec_code)
    не принимаются через PATCH — обновляются импортом каталога.
    """

    onec_code = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = (
            "description",
            "image",
            "is_active",
            "sort_order",
            "meta_title",
            "meta_description",
            "onec_code",
        )
        read_only_fields = ("onec_code",)


class CategoryAdminUpdateView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Category.objects.all()
    serializer_class = CategoryAdminUpdateSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        from django.conf import settings

        if not getattr(settings, "CATEGORY_MANUAL_MUTATIONS_ENABLED", False):
            return Response(
                {
                    "detail": (
                        "Ручное удаление категорий отключено: иерархия управляется из 1С."
                    ),
                    "code": "category_manual_mutations_disabled",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryAdminCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "title",
            "slug",
            "parent",
            "description",
            "image",
            "is_active",
            "sort_order",
            "meta_title",
            "meta_description",
        )


class CategoryAdminCreateView(CreateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = Category.objects.all()
    serializer_class = CategoryAdminCreateSerializer

    def create(self, request, *args, **kwargs):
        from django.conf import settings

        if not getattr(settings, "CATEGORY_MANUAL_MUTATIONS_ENABLED", False):
            return Response(
                {
                    "detail": (
                        "Ручное создание категорий отключено: иерархия управляется из 1С."
                    ),
                    "code": "category_manual_mutations_disabled",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


class ProductImageAdminSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    color = serializers.PrimaryKeyRelatedField(
        queryset=ProductColor.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ProductImage
        fields = (
            "id",
            "product",
            "image",
            "image_url",
            "color",
            "is_main",
            "alt_text",
            "sort_order",
        )
        read_only_fields = ("id", "image_url", "product")

    def validate_color(self, color):
        product = self.context.get("product")
        if color is not None and product is not None and color.product_id != product.pk:
            raise serializers.ValidationError("Цвет не принадлежит этому товару.")
        return color

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return absolute_media_url(request, obj.image.url)


class ProductImageAdminListCreateView(CreateAPIView, ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    serializer_class = ProductImageAdminSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        product_id = self.kwargs.get("pk")
        if product_id:
            try:
                ctx["product"] = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                pass
        return ctx

    def get_queryset(self):
        product_id = self.kwargs.get("pk")
        return ProductImage.objects.filter(product_id=product_id).order_by("sort_order", "created_at")

    def perform_create(self, serializer):
        product_id = self.kwargs.get("pk")
        product = Product.objects.get(pk=product_id)
        serializer.save(product=product)


class ProductImageAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        try:
            inst = self.get_object()
            ctx["product"] = inst.product
        except Exception:
            pass
        return ctx


class ProductSpecAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpec
        fields = ("id", "product", "name", "value", "sort_order")
        read_only_fields = ("id", "product")


class ProductSpecAdminListCreateView(CreateAPIView, ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    serializer_class = ProductSpecAdminSerializer

    def get_queryset(self):
        product_id = self.kwargs.get("pk")
        return ProductSpec.objects.filter(product_id=product_id).order_by("sort_order", "name")

    def perform_create(self, serializer):
        product_id = self.kwargs.get("pk")
        product = Product.objects.get(pk=product_id)
        serializer.save(product=product)


class ProductSpecAdminUpdateDeleteView(UpdateAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    queryset = ProductSpec.objects.all()
    serializer_class = ProductSpecAdminSerializer
    http_method_names = ["patch", "delete"]
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


def _xlsx_import_disabled_response():
    return Response(
        {
            "detail": (
                "Импорт товаров из XLSX временно отключён. "
                "Каталог синхронизируется из 1С."
            ),
            "code": "xlsx_import_temporarily_disabled",
        },
        status=status.HTTP_403_FORBIDDEN,
    )


class ProductImportTemplateDownloadView(APIView):
    """GET — скачать шаблон XLSX для массового импорта товаров."""

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def get(self, request):
        from django.conf import settings

        if not getattr(settings, "PRODUCT_XLSX_IMPORT_ENABLED", False):
            return _xlsx_import_disabled_response()
        data = build_import_template_xlsx()
        response = HttpResponse(
            data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="ringoo_products_import_template.xlsx"'
        )
        return response


class ProductBulkImportView(APIView):
    """
    POST multipart: file (xlsx), archive (zip, опционально).
    Структура ZIP: {sku}/{color_slug}/фото.jpg или {sku}/фото.jpg (без цвета).
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from django.conf import settings

        if not getattr(settings, "PRODUCT_XLSX_IMPORT_ENABLED", False):
            return _xlsx_import_disabled_response()
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Укажите поле file (.xlsx)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > 8 * 1024 * 1024:
            return Response(
                {"detail": "XLSX не больше 8 МБ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        xlsx_bytes = upload.read()
        archive = request.FILES.get("archive")
        zip_bytes = None
        if archive:
            if archive.size > 80 * 1024 * 1024:
                return Response(
                    {"detail": "ZIP не больше 80 МБ."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            zip_bytes = archive.read()
        result = run_bulk_import(xlsx_bytes, zip_bytes)
        code = (
            status.HTTP_200_OK
            if result["ok"]
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(result, status=code)
