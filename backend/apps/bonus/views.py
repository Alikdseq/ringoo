"""
API бонусной системы (задача 2.1.5).
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BonusAccount, BonusTransaction
from .serializers import BonusAccountSerializer, BonusTransactionSerializer


class BonusAccountView(APIView):
    """
    GET /api/v1/bonus/
    Получить или создать BonusAccount для текущего пользователя.
    Возвращает баланс и первую страницу транзакций (paginated).
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        account, _ = BonusAccount.objects.get_or_create(
            user=request.user,
            defaults={},
        )
        from rest_framework.pagination import PageNumberPagination

        pager = PageNumberPagination()
        page_size = getattr(pager, "page_size", 20)
        transactions_page = list(account.transactions.all()[:page_size])
        context = {"transactions": transactions_page, "request": request}
        serializer = BonusAccountSerializer(account, context=context)
        return Response(serializer.data)


class BonusTransactionsView(APIView):
    """
    GET /api/v1/bonus/transactions/
    История транзакций текущего пользователя с пагинацией и фильтрацией по reason.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        account, _ = BonusAccount.objects.get_or_create(
            user=request.user,
            defaults={},
        )
        qs = account.transactions.all().order_by("-created_at")
        reason = request.query_params.get("reason")
        if reason:
            qs = qs.filter(reason=reason)
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = BonusTransactionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = BonusTransactionSerializer(qs, many=True)
        return Response(serializer.data)
