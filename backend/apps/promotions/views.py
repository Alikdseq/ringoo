"""
API промокодов и акций (валидация промокода, список активных акций).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Promotion
from .serializers import PromotionListSerializer, PromoCodeValidateSerializer
from .services import apply_promo_code


class PromotionListView(ListAPIView):
    """
    GET /api/v1/promotions/
    Список активных акций (is_active=True и текущее время в [start_date, end_date]).
    Фильтр: ?category=slug — только акции, затронувшие эту категорию.
    """

    permission_classes = (AllowAny,)
    serializer_class = PromotionListSerializer

    def get_queryset(self):
        now = timezone.now()
        qs = (
            Promotion.objects.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
            )
            .prefetch_related("categories")
            .order_by("-end_date")
        )
        category_slug = self.request.query_params.get("category")
        if category_slug:
            qs = qs.filter(categories__slug=category_slug).distinct()
        return qs


class PromoCodeValidateView(APIView):
    """
    POST /api/v1/promocodes/validate/
    Тело: { "code": "SALE10", "order_amount": "1000.00" }.
    Ответ: { "valid": true, "discount": "100.00" } или 400 с сообщением.
    """

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PromoCodeValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        code = serializer.validated_data["code"]
        order_amount = serializer.validated_data["order_amount"]

        discount = apply_promo_code(code, order_amount)
        if discount is None:
            return Response(
                {"detail": "Промокод недействителен или не подходит под сумму заказа."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"valid": True, "discount": str(discount)},
            status=status.HTTP_200_OK,
        )
