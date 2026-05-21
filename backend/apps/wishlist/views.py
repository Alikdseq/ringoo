"""
API избранного: список, добавить, удалить (ТЗ EPIC 3 — избранные товары в ЛК).
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WishlistItem
from .serializers import WishlistItemCreateSerializer, WishlistItemSerializer


class WishlistListView(APIView):
    """
    GET /api/v1/wishlist/ — список избранных товаров текущего пользователя.
    POST /api/v1/wishlist/ — добавить товар в избранное (body: { "product_id": "uuid" }).
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            WishlistItem.objects.filter(user=self.request.user)
            .select_related("product", "product__category")
            .prefetch_related("product__images")
            .order_by("-created_at")
        )

    def get(self, request):
        items = self.get_queryset()
        serializer = WishlistItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request):
        ser = WishlistItemCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        product_id = ser.validated_data["product_id"]
        item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product_id=product_id,
            defaults={},
        )
        if not created:
            return Response(
                WishlistItemSerializer(item).data,
                status=status.HTTP_200_OK,
            )
        item = self.get_queryset().get(pk=item.pk)
        return Response(
            WishlistItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class WishlistItemDetailView(APIView):
    """
    DELETE /api/v1/wishlist/<product_id>/ — удалить товар из избранного.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        deleted, _ = WishlistItem.objects.filter(
            user=request.user,
            product_id=product_id,
        ).delete()
        if not deleted:
            return Response(
                {"detail": "Товар не найден в избранном."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
