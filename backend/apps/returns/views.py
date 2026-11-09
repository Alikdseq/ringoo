"""Customer + Admin API для возвратов."""

from __future__ import annotations

from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.permissions import (
    RINGOO_GROUP_ORDERS,
    admin_permissions,
)
from apps.orders.models import Order
from apps.returns.flags import returns_enabled
from apps.returns.models import ReturnRequest
from apps.returns.services import (
    create_return_request,
    initiate_money_refund,
    inspect_and_maybe_restock,
    transition_return,
)

RETURNS_DISABLED_PAYLOAD = {
    "detail": (
        "Функциональность возвратов временно отключена. "
        "Обратитесь в магазин для решения вопроса о возврате."
    ),
    "code": "returns_temporarily_disabled",
}


def _returns_disabled_response() -> Response:
    return Response(RETURNS_DISABLED_PAYLOAD, status=status.HTTP_403_FORBIDDEN)


def _serialize_return(rr: ReturnRequest) -> dict:
    return {
        "id": str(rr.pk),
        "number": rr.number,
        "order_id": str(rr.order_id),
        "order_number": getattr(rr.order, "order_number", ""),
        "ground": rr.ground,
        "demand": rr.demand,
        "status": rr.status,
        "description": rr.description,
        "return_method": rr.return_method,
        "requested_refund_amount": str(rr.requested_refund_amount),
        "approved_refund_amount": str(rr.approved_refund_amount),
        "rejection_reason": rr.rejection_reason,
        "created_at": rr.created_at,
        "updated_at": rr.updated_at,
        "items": [
            {
                "id": str(it.pk),
                "order_item_id": str(it.order_item_id),
                "quantity": it.quantity,
                "unit_price": str(it.unit_price),
                "line_refund_amount": str(it.line_refund_amount),
                "product_title": it.product_title,
                "color_label": it.color_label,
                "color_id": str(it.color_id) if it.color_id else None,
                "condition": it.condition,
                "restocked_quantity": it.restocked_quantity,
            }
            for it in rr.items.all()
        ],
        "events": [
            {
                "from_status": e.from_status,
                "to_status": e.to_status,
                "message": e.message,
                "created_at": e.created_at,
            }
            for e in rr.events.all()
        ],
    }


class CustomerReturnCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not returns_enabled():
            return _returns_disabled_response()
        order_id = request.data.get("order_id")
        order = get_object_or_404(Order, pk=order_id)
        if order.user_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Запрещено."}, status=status.HTTP_403_FORBIDDEN)
        try:
            rr = create_return_request(
                order=order,
                user=request.user,
                ground=request.data.get("ground") or ReturnRequest.GROUND_QUALITY_OK,
                demand=request.data.get("demand") or ReturnRequest.DEMAND_REFUND,
                description=request.data.get("description") or "",
                items=request.data.get("items") or [],
                return_method=request.data.get("return_method") or "",
                contact_phone=request.data.get("contact_phone") or "",
                contact_email=request.data.get("contact_email") or "",
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_return(rr), status=status.HTTP_201_CREATED)


class CustomerReturnListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not returns_enabled():
            return _returns_disabled_response()
        qs = (
            ReturnRequest.objects.filter(user=request.user)
            .prefetch_related("items", "events")
            .order_by("-created_at")[:50]
        )
        return Response([_serialize_return(rr) for rr in qs])


class CustomerReturnDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not returns_enabled():
            return _returns_disabled_response()
        rr = get_object_or_404(
            ReturnRequest.objects.prefetch_related("items", "events"), pk=pk
        )
        if rr.user_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "Запрещено."}, status=status.HTTP_403_FORBIDDEN)
        return Response(_serialize_return(rr))


class AdminReturnListView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)

    def get(self, request):
        if not returns_enabled():
            return _returns_disabled_response()
        qs = ReturnRequest.objects.prefetch_related("items").order_by("-created_at")
        status_f = request.query_params.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        order_f = request.query_params.get("order")
        if order_f:
            qs = qs.filter(order__order_number__icontains=order_f)
        qs = qs[:100]
        return Response(
            [
                {
                    "id": str(rr.pk),
                    "number": rr.number,
                    "order_number": rr.order.order_number,
                    "status": rr.status,
                    "ground": rr.ground,
                    "requested_refund_amount": str(rr.requested_refund_amount),
                    "created_at": rr.created_at,
                    "items_count": rr.items.count(),
                }
                for rr in qs
            ]
        )


class AdminReturnDetailView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)

    def get(self, request, pk):
        if not returns_enabled():
            return _returns_disabled_response()
        rr = get_object_or_404(
            ReturnRequest.objects.prefetch_related("items", "events", "money_refunds"),
            pk=pk,
        )
        data = _serialize_return(rr)
        data["money_refunds"] = [
            {
                "id": str(m.pk),
                "amount": str(m.amount),
                "status": m.status,
                "provider": m.provider,
                "provider_refund_id": m.provider_refund_id,
                "idempotency_key": m.idempotency_key,
                "error_message": m.error_message,
            }
            for m in rr.money_refunds.all()
        ]
        return Response(data)


class AdminReturnTransitionView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)

    def post(self, request, pk):
        if not returns_enabled():
            return _returns_disabled_response()
        rr = get_object_or_404(ReturnRequest, pk=pk)
        new_status = request.data.get("status")
        try:
            rr = transition_return(
                rr,
                new_status,
                actor=request.user,
                message=request.data.get("message") or "",
                rejection_reason=request.data.get("rejection_reason") or "",
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_return(rr))


class AdminReturnRefundView(APIView):
    """Инициация денежного возврата. По умолчанию dry_run=true (без вызова провайдера)."""

    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)

    def post(self, request, pk):
        if not returns_enabled():
            return _returns_disabled_response()
        rr = get_object_or_404(ReturnRequest, pk=pk)
        dry_run = request.data.get("dry_run", True)
        if isinstance(dry_run, str):
            dry_run = dry_run.lower() in ("1", "true", "yes")
        amount = request.data.get("amount")
        try:
            mr = initiate_money_refund(
                rr,
                amount=Decimal(str(amount)) if amount is not None else None,
                actor=request.user,
                dry_run=bool(dry_run),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "id": str(mr.pk),
                "status": mr.status,
                "amount": str(mr.amount),
                "provider": mr.provider,
                "dry_run": bool(dry_run),
                "error_message": mr.error_message,
            }
        )


class AdminReturnInspectView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_ORDERS)

    def post(self, request, pk):
        if not returns_enabled():
            return _returns_disabled_response()
        rr = get_object_or_404(ReturnRequest, pk=pk)
        try:
            rr = inspect_and_maybe_restock(
                rr,
                item_updates=request.data.get("items") or [],
                actor=request.user,
                store_id=request.data.get("store_id"),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_return(rr))
