"""
Сериализаторы каталога (задача 1.2.5).
"""

from rest_framework import serializers

from config.public_urls import absolute_media_url

from .models import Category, Product, ProductColor, ProductImage, ProductSpec


class CategorySerializer(serializers.ModelSerializer):
    """Категория: id, title, slug, parent, image, description, meta_title, meta_description (SEO)."""

    class Meta:
        model = Category
        fields = (
            "id",
            "title",
            "slug",
            "parent",
            "image",
            "description",
            "meta_title",
            "meta_description",
        )
        read_only_fields = fields


class ProductColorSerializer(serializers.ModelSerializer):
    """Вариант цвета для PDP и фильтрации галереи."""

    class Meta:
        model = ProductColor
        fields = (
            "id",
            "slug",
            "label",
            "hex",
            "sort_order",
            "is_active",
            "price",
            "old_price",
        )
        read_only_fields = fields


class ProductImageSerializer(serializers.ModelSerializer):
    """Изображение товара: id, image (абсолютный URL), is_main, alt_text, color, sort_order."""

    image = serializers.SerializerMethodField()
    color = ProductColorSerializer(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image", "is_main", "alt_text", "color", "sort_order")
        read_only_fields = fields

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return absolute_media_url(request, obj.image.url)


class ProductSpecSerializer(serializers.ModelSerializer):
    """Характеристика товара: name, value."""

    class Meta:
        model = ProductSpec
        fields = ("name", "value")
        read_only_fields = fields


class ProductAutocompleteSerializer(serializers.ModelSerializer):
    """Минимальные поля для автодополнения поиска: id, title, slug, price, главное фото."""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "title", "slug", "sku", "price", "image")
        read_only_fields = fields

    def get_image(self, obj):
        main = obj.images.filter(is_main=True).first()
        if main is None:
            main = self._first_list_image(obj)
        if main and main.image:
            return main.image.url
        return None

    def _first_list_image(self, obj):
        """Главное для карточки: приоритет — is_main; иначе первое фото первого активного цвета."""
        for col in obj.colors.filter(is_active=True).order_by("sort_order"):
            img = (
                obj.images.filter(color_id=col.id, is_main=True).first()
                or obj.images.filter(color_id=col.id).order_by("sort_order", "created_at").first()
            )
            if img:
                return img
        return obj.images.order_by("sort_order", "created_at").first()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Товар для списка: основные поля, главное изображение, категория, discount_percent, available_quantity_total, availability_status.
    """

    images = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    discount_percent = serializers.SerializerMethodField()
    available_quantity_total = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "short_description",
            "price",
            "old_price",
            "category",
            "images",
            "colors",
            "discount_percent",
            "rating",
            "reviews_count",
            "is_featured",
            "created_at",
            "available_quantity_total",
            "availability_status",
        )
        read_only_fields = fields

    def get_colors(self, obj):
        """Цвета + превью первого кадра для карточки каталога (без N+1 при prefetch)."""
        imgs = list(obj.images.all())
        rows = []
        for col in obj.colors.filter(is_active=True).order_by("sort_order", "label"):
            cand = [i for i in imgs if i.color_id == col.id]
            cand.sort(key=lambda i: (not i.is_main, i.sort_order or 0, i.created_at))
            thumb = cand[0] if cand else None
            preview = None
            preview_alt = obj.title
            if thumb and thumb.image:
                request = self.context.get("request")
                preview = absolute_media_url(request, thumb.image.url)
                preview_alt = (thumb.alt_text or obj.title)[:255]
            rows.append(
                {
                    "id": str(col.id),
                    "slug": col.slug,
                    "label": col.label,
                    "hex": col.hex,
                    "sort_order": col.sort_order,
                    "is_active": col.is_active,
                    "price": str(col.price) if col.price is not None else None,
                    "old_price": str(col.old_price) if col.old_price is not None else None,
                    "preview_image": preview,
                    "preview_alt": preview_alt,
                }
            )
        return rows

    def get_images(self, obj):
        """
        До 10 изображений для карточки каталога (свайп в карточке): сначала главное, затем по sort_order.
        """
        qs = list(obj.images.select_related("color").order_by("sort_order", "created_at"))
        if not qs:
            return []
        qs.sort(key=lambda i: (not i.is_main, i.sort_order or 0, i.created_at))
        out = []
        for img in qs[:10]:
            out.append(ProductImageSerializer(img, context=self.context).data)
        return out

    def get_discount_percent(self, obj):
        return obj.discount_percent

    def get_available_quantity_total(self, obj):
        """Сумма доступного количества по всем складам (quantity - reserved_quantity)."""
        try:
            total = 0
            for stock in obj.stock_items.all():
                total += getattr(stock, "available_quantity", 0) or max(
                    0, (stock.quantity or 0) - (stock.reserved_quantity or 0)
                )
            return total
        except (AttributeError, Exception):
            return 0

    def get_availability_status(self, obj):
        """Статус наличия: in_stock | out_of_stock."""
        total = self.get_available_quantity_total(obj)
        return "in_stock" if total > 0 else "out_of_stock"


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Товар для карточки: все поля, изображения, specs, категория, stock, is_in_user_cart.
    """

    images = ProductImageSerializer(many=True, read_only=True)
    colors = ProductColorSerializer(many=True, read_only=True)
    specs = ProductSpecSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    discount_percent = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    is_in_user_cart = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "sku",
            "description",
            "short_description",
            "price",
            "old_price",
            "category",
            "brand",
            "rating",
            "reviews_count",
            "is_active",
            "is_featured",
            "meta_title",
            "meta_description",
            "images",
            "colors",
            "specs",
            "discount_percent",
            "stock",
            "availability_status",
            "is_in_user_cart",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_discount_percent(self, obj):
        return obj.discount_percent

    def get_stock(self, obj):
        """Наличие в магазинах (Stock). Использует prefetch stock_items при наличии."""
        try:
            from apps.stores.serializers import StockSerializer
            qs = obj.stock_items.select_related("store").all()
            return StockSerializer(qs, many=True).data
        except (ImportError, AttributeError):
            return []

    def get_availability_status(self, obj):
        """Статус наличия: in_stock | out_of_stock (влияет на кнопку «В корзину»)."""
        total = 0
        try:
            for stock in obj.stock_items.all():
                total += getattr(stock, "available_quantity", 0) or max(
                    0, (stock.quantity or 0) - (stock.reserved_quantity or 0)
                )
        except (AttributeError, Exception):
            pass
        return "in_stock" if total > 0 else "out_of_stock"

    def get_is_in_user_cart(self, obj):
        """True, если товар в корзине авторизованного пользователя."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        try:
            from apps.cart.models import CartItem
            return CartItem.objects.filter(
                cart__user=request.user, product=obj
            ).exists()
        except (ImportError, AttributeError):
            return False
