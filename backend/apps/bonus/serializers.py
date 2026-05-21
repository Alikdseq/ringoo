"""
Сериализаторы бонусной системы (задача 2.1.4).
"""

from rest_framework import serializers

from .models import BonusAccount, BonusTransaction


class BonusTransactionSerializer(serializers.ModelSerializer):
    """Транзакция: id, amount, reason, related_order, description, created_at."""

    related_order = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = BonusTransaction
        fields = (
            "id",
            "amount",
            "reason",
            "reason_display",
            "related_order",
            "description",
            "created_at",
        )
        read_only_fields = fields


class BonusAccountSerializer(serializers.ModelSerializer):
    """
    Бонусный счёт: balance, total_earned, total_spent, updated_at.
    transactions — вложенная страница (передаётся в context['transactions']).
    """

    transactions = serializers.SerializerMethodField()

    class Meta:
        model = BonusAccount
        fields = (
            "id",
            "balance",
            "total_earned",
            "total_spent",
            "updated_at",
            "transactions",
        )
        read_only_fields = fields

    def get_transactions(self, obj):
        """Страница транзакций из context (view передаёт список для текущей страницы)."""
        txns = self.context.get("transactions", [])
        return BonusTransactionSerializer(txns, many=True).data
