# API Документация

## Обзор

Ringoo API предоставляет RESTful интерфейс для работы с интернет-магазином.

## Базовый URL

```
Development: http://localhost:8000/api/v1/
Production: https://your-domain.com/api/v1/
```

## Аутентификация

API использует JWT (JSON Web Tokens) для аутентификации.

### Получение токенов (логин)

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "+79991234567",
  "password": "your-password"
}
```

Поле `username` может содержать телефон в любом привычном формате; на бэкенде выполняется нормализация.

**Ответ:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Регистрация: `POST /api/v1/auth/register/` (телефон, пароль, ФИО) — в ответе также выдаются `access` и `refresh`.

### Использование токенов

Добавьте заголовок в каждый запрос:
```http
Authorization: Bearer <access_token>
```

### Обновление токенов

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

## Endpoints

### Аутентификация

- `POST /api/v1/auth/token/` - Вход (телефон/логин + пароль), выдача JWT
- `POST /api/v1/auth/token/refresh/` - Обновление access token
- `POST /api/v1/auth/register/` - Регистрация
- `GET /api/v1/auth/me/` - Информация о текущем пользователе (без признака `is_staff` в теле ответа)
- `GET /api/v1/auth/staff-access/` - Проверка доступа к админ-UI: `200` и `{"staff": true}` только для сотрудников; иначе `403`

### Каталог товаров

- `GET /api/v1/products/products/` - Список товаров (с фильтрацией и поиском). Параметры: `category` (slug), `brand`, `model` (ключ линейки из product-models), `min_price`, `max_price`, `search`, `in_stock` (`true`/`1`), `store` (slug магазина — только товары в наличии в этом магазине), `rating_min` (число), `ordering` (`popular`, `price_asc`, `price_desc`, `rating_desc`, `created_at`), `page`, `page_size`. В ответе списка есть поле `created_at` (для бейджей «новинка»). В объекте `colors[]` у товара могут быть `price` и `old_price` (цена варианта цвета; при отсутствии используется базовая цена товара).
- `GET /api/v1/products/products/product-models/` - Линейки моделей в текущей выборке (те же фильтры, что у списка, **без** `model`). Ответ: `{ "results": [{ "key": "iphone-17-pro-max", "label": "iPhone 17 Pro Max", "count": 12 }] }`.
- `GET /api/v1/products/products/{slug}/` - Детали товара
- `GET /api/v1/products/products/{product_id}/stock/` - Наличие товара в магазинах (`product_id` — UUID)
- `GET /api/v1/categories/` - Список категорий
- `GET /api/v1/categories/{slug}/` - Детали категории

### Корзина

- `GET /api/v1/cart/` - Получить корзину
- `POST /api/v1/cart/items/` - Добавить товар в корзину
- `PATCH /api/v1/cart/items/{id}/` - Обновить количество товара
- `DELETE /api/v1/cart/items/{id}/` - Удалить товар из корзины
- `POST /api/v1/cart/clear/` - Очистить корзину

### Заказы

- `GET /api/v1/orders/` - Список заказов пользователя
- `POST /api/v1/orders/` - Создать заказ
- `GET /api/v1/orders/{id}/` - Детали заказа

### Магазины

- `GET /api/v1/stores/` - Список магазинов
- `GET /api/v1/stores/by-slug/{slug}/` - Страница магазина (описание, SEO, галерея, менеджеры)
- `GET /api/v1/stores/by-slug/{slug}/products/` - Товары в наличии в магазине (пагинация как у каталога)
- `GET /api/v1/stores/managers/` - Список менеджеров с рейтингом
- `GET /api/v1/stores/managers/by-slug/{slug}/` - Профиль менеджера
- `GET /api/v1/stores/managers/by-slug/{slug}/reviews/` - Отзывы о менеджере
- `GET /api/v1/stores/{id}/` - Детали магазина (по UUID)
- `GET /api/v1/stores/{id}/stock/` - Остатки товаров в магазине

### Бонусы

Публичные маршруты `bonus/` в `api_urls` **временно отключены** (см. `backend/config/api_urls.py`). Не используйте `GET /api/v1/bonus/` до включения на бэкенде и обновления этой документации.

### Контент

- `GET /api/v1/content/tags/` - Теги (для фильтров блога и новостей)
- `GET /api/v1/content/articles/` - Список статей блога
- `GET /api/v1/content/articles/{slug}/` - Детали статьи
- `GET /api/v1/content/news/` - Список новостей
- `GET /api/v1/content/news/{slug}/` - Детали новости
- `GET /api/v1/content/reviews/` - Список отзывов
- `POST /api/v1/content/reviews/` - Создать отзыв
- `GET /api/v1/content/page-gallery/?placement=stores_hero|about_hero` - Галерея hero-блока страниц «Магазины» / «О нас»

### Admin API (staff)

- `GET|POST /api/v1/admin/managers/` — список менеджеров (`?store=`, `?search=`, `?is_active=`)
- `POST /api/v1/admin/managers/create/` — создать менеджера (multipart: `photo`, `photo_2`)
- `PATCH|DELETE /api/v1/admin/managers/{id}/` — изменить / удалить
- `GET /api/v1/admin/content/page-gallery/?placement=` — галереи страниц (staff)
- `POST /api/v1/admin/content/page-gallery/create/` — загрузить изображение (multipart)
- `PATCH|DELETE /api/v1/admin/content/page-gallery/{id}/` — изменить / удалить

## Документация API

### Swagger UI

Интерактивная документация доступна по адресу:
```
http://localhost:8000/api/docs/
```

### ReDoc

Альтернативная документация:
```
http://localhost:8000/api/redoc/
```

### OpenAPI Schema

JSON схема доступна по адресу:
```
http://localhost:8000/api/schema/
```

## Пагинация

Большинство списков используют пагинацию:

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/v1/products/?page=2",
  "previous": null,
  "results": [...]
}
```

## Фильтрация

### Товары

- `?category=slug` - Фильтр по категории
- `?min_price=1000&max_price=5000` - Фильтр по цене
- `?search=название` - Поиск по названию
- `?ordering=price` - Сортировка (price, -price, created_at, -created_at)

### Заказы

- `?status=new` - Фильтр по статусу
- `?ordering=-created_at` - Сортировка по дате

## Коды ошибок

- `200` - Успешно
- `201` - Создано
- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Не найдено
- `429` - Превышен лимит запросов
- `500` - Внутренняя ошибка сервера

## Примеры запросов

### Получить список товаров

```bash
curl -X GET "http://localhost:8000/api/v1/products/?category=smartphones&min_price=10000" \
  -H "Authorization: Bearer <token>"
```

### Добавить товар в корзину

```bash
curl -X POST "http://localhost:8000/api/v1/cart/items/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "product": "uuid",
    "quantity": 2,
    "store": "uuid"
  }'
```

### Создать заказ

```bash
curl -X POST "http://localhost:8000/api/v1/orders/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Иван Иванов",
    "phone": "+79991234567",
    "delivery_type": "delivery",
    "delivery_address": {
      "city": "Владикавказ",
      "street": "ул. Ленина",
      "house": "10",
      "apartment": "5"
    },
    "payment_type": "cash",
    "bonus_used": 0
  }'
```

## Rate Limiting

API использует rate limiting для защиты от злоупотреблений:

- **Анонимные пользователи:** 100 запросов/час
- **Авторизованные пользователи:** 1000 запросов/час
При превышении лимита возвращается статус `429 Too Many Requests`.

## Версионирование

Текущая версия API: **v1**

В будущем могут быть добавлены новые версии (v2, v3 и т.д.) для обратной совместимости.

---

**Дата создания:** 2026-02-05  
**Версия:** 1.0  
**Статус:** В разработке
