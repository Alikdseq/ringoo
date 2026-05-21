"""
API корзины (задача 1.4.4).
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.throttling import CartReadRateThrottle, CartWriteAnonRateThrottle, CartWriteRateThrottle

from .models import Cart, CartItem
from .serializers import (
    CartItemCreateSerializer,
    CartSerializer,
    CartItemUpdateSerializer,
)


def _get_cart_queryset():
    """Корзина с prefetch items -> product (category), store, color."""
    return Cart.objects.prefetch_related(
        "items__product__category",
        "items__product__images",
        "items__product__colors",
        "items__store",
        "items__color",
    )


class CartView(APIView):
    """
    GET /api/v1/cart/ — получить или создать корзину, вернуть с товарами.
    """

    permission_classes = [AllowAny]
    throttle_classes = [CartReadRateThrottle]

    def get(self, request):
        cart = Cart.get_or_create_cart(request)
        cart = _get_cart_queryset().get(pk=cart.pk)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartItemCreateView(APIView):
    """
    POST /api/v1/cart/items/ — добавить товар в корзину.
    Валидация product, quantity, store (опционально). Проверка наличия (Stock).
    Добавить или обновить CartItem, вернуть обновлённую корзину.
    """

    permission_classes = [AllowAny]
    throttle_classes = [CartWriteAnonRateThrottle, CartWriteRateThrottle]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        product_id = data["product"]
        quantity = data["quantity"]
        store_id = data.get("store")
        color_obj = data.get("_color_obj")
        color_id = color_obj.id if color_obj else None

        cart = Cart.get_or_create_cart(request)

        from apps.products.models import Product
        from apps.stores.models import Stock

        product = Product.objects.get(pk=product_id)
        if store_id:
            stock = Stock.objects.filter(
                product=product, store_id=store_id
            ).first()
            if not stock or stock.available_quantity < quantity:
                return Response(
                    {"detail": "Недостаточно товара в выбранном магазине."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        unit_price = color_obj.effective_price() if color_obj else product.price

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            store_id=store_id,
            color_id=color_id,
            defaults={
                "quantity": quantity,
                "price_at_add": unit_price,
            },
        )
        if not created:
            item.quantity += quantity
            if store_id:
                stock = Stock.objects.get(product=product, store_id=store_id)
                if stock.available_quantity < item.quantity:
                    return Response(
                        {"detail": "Недостаточно товара в выбранном магазине."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            item.save(update_fields=["quantity", "updated_at"])

        cart = _get_cart_queryset().get(pk=cart.pk)
        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    """
    PATCH /api/v1/cart/items/{id}/ — изменить quantity (0 = удалить).
    DELETE /api/v1/cart/items/{id}/ — удалить позицию.
    """

    permission_classes = [AllowAny]
    throttle_classes = [CartWriteAnonRateThrottle, CartWriteRateThrottle]

    def patch(self, request, pk):
        cart = Cart.get_or_create_cart(request)
        try:
            item = CartItem.objects.select_related("product", "store").get(
                pk=pk, cart=cart
            )
        except CartItem.DoesNotExist:
            return Response(
                {"detail": "Позиция не найдена."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CartItemUpdateSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_quantity = serializer.validated_data["quantity"]

        if new_quantity == 0:
            item.delete()
            cart = _get_cart_queryset().get(pk=cart.pk)
            return Response(CartSerializer(cart).data)

        if item.store_id:
            from apps.stores.models import Stock

            stock = Stock.objects.filter(
                product=item.product, store=item.store
            ).first()
            if stock and stock.available_quantity < new_quantity:
                return Response(
                    {"detail": "Недостаточно товара в выбранном магазине."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer.save()
        cart = _get_cart_queryset().get(pk=cart.pk)
        return Response(CartSerializer(cart).data)

    def delete(self, request, pk):
        cart = Cart.get_or_create_cart(request)
        deleted, _ = CartItem.objects.filter(pk=pk, cart=cart).delete()
        if not deleted:
            return Response(
                {"detail": "Позиция не найдена."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartClearView(APIView):
    """
    POST /api/v1/cart/clear/ — удалить все позиции из корзины.
    """

    permission_classes = [AllowAny]
    throttle_classes = [CartWriteAnonRateThrottle, CartWriteRateThrottle]

    def post(self, request):
        cart = Cart.get_or_create_cart(request)
        CartItem.objects.filter(cart=cart).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
