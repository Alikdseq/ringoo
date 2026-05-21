"""
Unit-тесты контента: сериализаторы (2.2.5), API (2.2.6).
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.users.models import CustomUser

from .models import Article, News, Review, Tag


class TestContentSerializers(TestCase):
    """Тесты сериализаторов контента (задача 2.2.5)."""

    def setUp(self):
        self.tag = Tag.objects.create(name="Тест", slug="test")
        self.user = CustomUser.objects.create_user(
            phone="+79991234567",
            username="+79991234567",
            password="testpass123",
        )

    def test_tag_serializer(self):
        from .serializers import TagSerializer

        data = TagSerializer(self.tag).data
        self.assertEqual(str(self.tag.id), data["id"])
        self.assertEqual(self.tag.name, data["name"])
        self.assertEqual(self.tag.slug, data["slug"])

    def test_article_serializer(self):
        from .serializers import ArticleSerializer

        article = Article.objects.create(
            title="Статья",
            slug="article-1",
            content="Текст",
            author=self.user,
            is_published=True,
        )
        article.tags.add(self.tag)
        data = ArticleSerializer(article).data
        self.assertEqual(data["title"], "Статья")
        self.assertEqual(data["slug"], "article-1")
        self.assertEqual(len(data["tags"]), 1)
        self.assertEqual(data["tags"][0]["name"], "Тест")

    def test_news_serializer(self):
        from .serializers import NewsSerializer

        news = News.objects.create(
            title="Новость",
            slug="news-1",
            content="Текст",
            is_published=True,
            is_featured=True,
        )
        data = NewsSerializer(news).data
        self.assertEqual(data["title"], "Новость")
        self.assertTrue(data["is_featured"])

    def test_review_serializer(self):
        from .serializers import ReviewSerializer

        category = Category.objects.create(title="Кат", slug="cat")
        product = Product.objects.create(
            title="Товар",
            slug="product-1",
            price=Decimal("100"),
            category=category,
        )
        review = Review.objects.create(
            product=product,
            user=self.user,
            name="Иван",
            rating=5,
            comment="Отлично",
            is_approved=True,
        )
        data = ReviewSerializer(review).data
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["comment"], "Отлично")
        self.assertTrue(data["is_approved"])


@override_settings(
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False}
)
class TestContentAPI(TestCase):
    """Тесты API контента (задача 2.2.6)."""

    def setUp(self):
        self.client = APIClient()
        self.tag = Tag.objects.create(name="API-тег", slug="api-tag")
        Article.objects.create(
            title="Публ статья",
            slug="pub-article",
            content="Контент",
            is_published=True,
        )
        Article.objects.create(
            title="Черновик",
            slug="draft-article",
            content="Текст",
            is_published=False,
        )

    def test_tag_list(self):
        url = reverse("api_v1:content:tag-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        slugs = [t["slug"] for t in data]
        self.assertIn("api-tag", slugs)

    def test_article_list_only_published(self):
        url = reverse("api_v1:content:article-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("results", data)
        titles = [a["title"] for a in results]
        self.assertIn("Публ статья", titles)
        self.assertNotIn("Черновик", titles)

    def test_article_detail_by_slug(self):
        url = reverse(
            "api_v1:content:article-detail",
            kwargs={"slug": "pub-article"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["slug"], "pub-article")

    def test_review_list_filter_by_product(self):
        category = Category.objects.create(title="C", slug="c")
        product = Product.objects.create(
            title="P",
            slug="p1",
            price=Decimal("10"),
            category=category,
        )
        Review.objects.create(
            product=product,
            name="Гость",
            email="g@test.com",
            rating=4,
            comment="Норм",
            is_approved=True,
        )
        url = reverse("api_v1:content:review-list")
        response = self.client.get(url, {"product": str(product.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("results", data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rating"], 4)

    def test_review_create(self):
        category = Category.objects.create(title="C2", slug="c2")
        product = Product.objects.create(
            title="P2",
            slug="p2",
            price=Decimal("20"),
            category=category,
        )
        url = reverse("api_v1:content:review-list")
        payload = {
            "product": str(product.id),
            "name": "Гость",
            "email": "guest@test.com",
            "rating": 5,
            "comment": "Супер товар",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.filter(product=product).count(), 1)
