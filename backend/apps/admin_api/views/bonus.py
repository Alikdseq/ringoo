"""Admin API: Бонусы — список счетов, детали, ручная корректировка."""

from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bonus.models import BonusAccount, BonusTransaction
from apps.bonus.services import admin_adjust

from ..permissions import IsStaff


class BonusAccountListSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = BonusAccount
        fields = (
            "id", "user", "user_phone", "user_email",
            "balance", "total_earned", "total_spent", "updated_at",
        )
        read_only_fields = fields


class BonusTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusTransaction
        fields = ("id", "amount", "reason", "related_order", "description", "created_at")
        read_only_fields = fields


class BonusAccountDetailSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    transactions = BonusTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = BonusAccount
        fields = (
            "id", "user", "user_phone", "user_email",
            "balance", "total_earned", "total_spent", "updated_at", "transactions",
        )
        read_only_fields = fields


class BonusAccountAdminListView(ListAPIView):
    permission_classes = [IsStaff]
    serializer_class = BonusAccountListSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = BonusAccount.objects.select_related("user").order_by("-updated_at")
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(user__phone__icontains=search) | Q(user__email__icontains=search))
        return qs


class BonusAccountAdminDetailView(RetrieveAPIView):
    permission_classes = [IsStaff]
    queryset = BonusAccount.objects.select_related("user").prefetch_related("transactions")
    serializer_class = BonusAccountDetailSerializer
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class BonusAccountAdjustView(APIView):
    permission_classes = [IsStaff]

    def post(self, request, pk):
        account = BonusAccount.objects.filter(pk=pk).select_related("user").first()
        if not account:
            return Response({"detail": "Счёт не найден."}, status=status.HTTP_404_NOT_FOUND)
        amount = request.data.get("amount")
        description = (request.data.get("description") or "").strip() or None
        if amount is None:
            return Response({"amount": ["Обязательное поле."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount_dec = Decimal(str(amount))
        except Exception:
            return Response({"amount": ["Некорректное значение."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            txn = admin_adjust(account, amount_dec, description)
            return Response(BonusTransactionSerializer(txn).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
