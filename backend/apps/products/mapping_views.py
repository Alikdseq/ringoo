"""Админ API: ручное сопоставление ProductColor ↔ 1С."""

from __future__ import annotations

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.permissions import RINGOO_GROUP_CATALOG, admin_permissions
from apps.products.models import ProductColor


class ProductColorMappingListView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def get(self, request):
        qs = ProductColor.objects.select_related("product").order_by(
            "product__title", "sort_order"
        )
        status_f = request.query_params.get("mapping_status")
        if status_f:
            qs = qs.filter(mapping_status=status_f)
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(label__icontains=q)
                | Q(sku__icontains=q)
                | Q(onec_code__icontains=q)
                | Q(product__title__icontains=q)
            )
        qs = qs[:200]
        return Response(
            [
                {
                    "id": str(c.pk),
                    "product_id": str(c.product_id),
                    "product_title": c.product.title,
                    "product_onec_code": c.product.onec_code or "",
                    "label": c.label,
                    "slug": c.slug,
                    "hex": c.hex or "",
                    "sku": c.sku,
                    "barcode": c.barcode,
                    "onec_code": c.onec_code,
                    "onec_characteristic_ref": c.onec_characteristic_ref,
                    "mapping_status": c.mapping_status,
                }
                for c in qs
            ]
        )


class ProductColorMappingUpdateView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def patch(self, request, pk):
        try:
            color = ProductColor.objects.select_related("product").get(pk=pk)
        except ProductColor.DoesNotExist:
            return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)
        for field in ("sku", "barcode", "onec_code", "onec_characteristic_ref", "mapping_status"):
            if field in request.data:
                setattr(color, field, request.data.get(field) or "")
        if color.mapping_status == ProductColor.MAPPING_MATCHED and not color.onec_code:
            return Response(
                {"detail": "Для matched нужен onec_code варианта."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # conflict: same onec_code on another color
        if color.onec_code:
            clash = (
                ProductColor.objects.filter(onec_code=color.onec_code)
                .exclude(pk=color.pk)
                .first()
            )
            if clash:
                color.mapping_status = ProductColor.MAPPING_CONFLICT
        color.save()
        return Response(
            {
                "id": str(color.pk),
                "onec_code": color.onec_code,
                "mapping_status": color.mapping_status,
                "sku": color.sku,
            }
        )
