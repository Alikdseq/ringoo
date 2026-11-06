"""Admin API: Бонусы — список счетов, детали, ручная корректировка.

SEC-008: permissions = admin_permissions(RINGOO_GROUP_BONUS) + MFA.
Маршруты в urls.py остаются ЗАКОММЕНТИРОВАННЫМИ — модуль не включаем.
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.serializers import CharField, EmailField, ModelSerializer
from rest_framework.views import APIView

from apps.audit.services import log_admin_action
from apps.bonus.models import BonusAccount, BonusTransaction
from apps.bonus.services import admin_adjust

from ..permissions import RINGOO_GROUP_BONUS, admin_permissions


class BonusAccountListSerializer(ModelSerializer):
    user_phone = CharField(source="user.phone", read_only=True)
    user_email = EmailField(source="user.email", read_only=True)

    class Meta:
        model = BonusAccount
        fields = (
            "id",
            "user",
            "user_phone",
            "user_email",
            "balance",
            "total_earned",
            "total_spent",
            "updated_at",
        )
        read_only_fields = fields


class BonusTransactionSerializer(ModelSerializer):
    class Meta:
        model = BonusTransaction
        fields = (
            "id",
            "amount",
            "reason",
            "related_order",
            "description",
            "created_at",
        )
        read_only_fields = fields


class BonusAccountDetailSerializer(ModelSerializer):
    user_phone = CharField(source="user.phone", read_only=True)
    user_email = EmailField(source="user.email", read_only=True)
    transactions = BonusTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = BonusAccount
        fields = (
            "id",
            "user",
            "user_phone",
            "user_email",
            "balance",
            "total_earned",
            "total_spent",
            "updated_at",
            "transactions",
        )
        read_only_fields = fields


class BonusAccountAdminListView(ListAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_BONUS)
    serializer_class = BonusAccountListSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = BonusAccount.objects.select_related("user").order_by("-updated_at")
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(user__phone__icontains=search) | Q(user__email__icontains=search)
            )
        return qs


class BonusAccountAdminDetailView(RetrieveAPIView):
    permission_classes = admin_permissions(RINGOO_GROUP_BONUS)
    queryset = BonusAccount.objects.select_related("user").prefetch_related(
        "transactions"
    )
    serializer_class = BonusAccountDetailSerializer
    lookup_url_kwarg = "pk"
    lookup_field = "pk"


class BonusAccountAdjustView(APIView):
    """Ручная корректировка баланса. Требует ringoo_bonus + MFA."""

    permission_classes = admin_permissions(RINGOO_GROUP_BONUS)

    def post(self, request, pk):
        account = (
            BonusAccount.objects.filter(pk=pk).select_related("user").first()
        )
        if not account:
            return Response(
                {"detail": "Счёт не найден."}, status=status.HTTP_404_NOT_FOUND
            )
        amount = request.data.get("amount")
        description = (request.data.get("description") or "").strip() or None
        if amount is None:
            return Response(
                {"amount": ["Обязательное поле."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount_dec = Decimal(str(amount))
        except Exception:
            return Response(
                {"amount": ["Некорректное значение."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actor = request.user
        actor_tag = f"[admin:{actor.pk}]"
        full_description = (
            f"{actor_tag} {description}".strip()
            if description
            else actor_tag
        )
        try:
            txn = admin_adjust(account, amount_dec, full_description)
            log_admin_action(
                request,
                action="bonus_adjust",
                model_name="bonus.BonusAccount",
                object_id=str(account.pk),
                object_repr=str(account.user_id),
                changes={"amount": str(amount_dec), "txn": str(txn.pk)},
            )
            return Response(
                BonusTransactionSerializer(txn).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
